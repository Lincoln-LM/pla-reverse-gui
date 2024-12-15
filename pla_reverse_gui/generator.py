"""Spawner prediction generator"""

import numpy as np
import numba
from numba.typed import List as TypedList
from numba_pokemon_prngs.util import rotate_left_u64
from numba_pokemon_prngs.xorshift import Xoroshiro128PlusRejection
from numba_pokemon_prngs.data.encounter.encounter_area_la import EncounterAreaLA, SlotLA
from numba_pokemon_prngs.enums import LAWeather, LATime
from numba_progress.numba_atomic import atomic_add


@numba.njit()
def advance_seed(seed: np.uint64, ko_count: int) -> np.uint64:
    """Advance a seed by the amount of kos you do"""
    seed0 = np.uint64(seed)
    seed1 = np.uint64(0x82A2B175229D6A5B)
    for _ in range(ko_count):
        # generator_seed = rng.next()

        seed1 ^= seed0
        seed0 = rotate_left_u64(seed0, 24) ^ seed1 ^ (seed1 << np.uint64(16))
        seed1 = rotate_left_u64(seed1, 37)
        # rng.next() # unused

        seed1 ^= seed0
        seed0 = rotate_left_u64(seed0, 24) ^ seed1 ^ (seed1 << np.uint64(16))
        seed1 = rotate_left_u64(seed1, 37)

    return seed0 + seed1

@numba.njit(nogil=True)
def generate_mass_outbreak(
    seed: np.uint64,
    first_wave_count: int,
    second_wave_count: int,
    first_wave_table: EncounterAreaLA,
    second_wave_table: EncounterAreaLA,
    species_info: dict[tuple[int, int], tuple[int, int, bool]],
    gender_filter: tuple,
    nature_filter: tuple,
    size_filter: tuple,
    shiny_filter: np.uint8,
    alpha_filter: np.uint8,
    iv_filters: tuple,
    parent_data: np.ndarray,
    results: TypedList,
):
    """
    Non-mass outbreak spawner prediction generator
    parent_data[0]: external uint64 count of how many pokemon have been checked
    parent_data[1]: external bool (as uint64) flag for if the search should still run (threading)
    """

    # faster to reinit rather than create new objects
    group_rng = Xoroshiro128PlusRejection(0, 0)
    generator_rng = Xoroshiro128PlusRejection(0, 0)
    fixed_rng = Xoroshiro128PlusRejection(0, 0)
    queue = []

    # outbreaks always start by catching 3 consecutive singles (seed is relative to the last 2 so only advance twice)
    queue.append(
        ([np.uint8(1)], first_wave_count - 4 - 3, 3, second_wave_count, advance_seed(advance_seed(seed, 1), 1))
    )

    # TODO: label actions, track aggressive/passive/oblivious & account for them
    while len(queue) != 0 and parent_data[1] == 0:
        item = queue.pop()
        # increment progress counter
        atomic_add(parent_data, 0, 1)
        ko_path, first_wave_count, ghost_count, second_wave_count, group_seed = item
        current_table = first_wave_table if first_wave_count != -1 else second_wave_table
        # TODO: rip out pokemon generation
        group_rng.re_init(group_seed)
        is_ghost = ko_path[-1] > 10
        spawn_count = ko_path[-1] - 10 if is_ghost else ko_path[-1]
        for _ in range(spawn_count):
            generator_rng.re_init(group_rng.next())
            group_rng.next()
            slot: SlotLA = current_table.calc_slot(
                generator_rng.next() * 5.421010862427522e-20,
                np.int64(LATime.DAY),
                np.int64(LAWeather.SUNNY),  # 1/2**64
            )
            # don't return ghosts as results
            if is_ghost:
                continue
            gender_ratio, shiny_rolls, filtered_species = species_info[
                (slot.species, slot.form)
            ]
            if not filtered_species:
                continue
            if alpha_filter and not slot.is_alpha:
                continue
            fixed_rng.re_init(generator_rng.next())
            encryption_constant = fixed_rng.next_rand(0xFFFFFFFF)
            sidtid = fixed_rng.next_rand(0xFFFFFFFF)
            for _ in range(shiny_rolls):
                pid = fixed_rng.next_rand(0xFFFFFFFF)
                xor = (
                    (pid >> 16)
                    ^ (sidtid >> 16)
                    ^ (pid & 0xFFFF)
                    ^ (sidtid & 0xFFFF)
                )
                shiny = 2 if xor == 0 else 1 if xor < 16 else 0
                if shiny:
                    break
            if shiny_filter != 15 and not (shiny_filter & shiny):
                continue
            ivs = np.zeros(6, np.uint8)
            for _ in range(slot.guaranteed_ivs):
                index = fixed_rng.next_rand(6)
                while ivs[index] != 0:
                    index = fixed_rng.next_rand(6)
                ivs[index] = 31
            for i in range(6):
                if ivs[i] == 0:
                    ivs[i] = fixed_rng.next_rand(32)
            passes_ivs = True
            for i, (minimum, maximum) in enumerate(iv_filters):
                if minimum > ivs[i]:
                    passes_ivs = False
                    break
                if maximum < ivs[i]:
                    passes_ivs = False
                    break
            if not passes_ivs:
                continue
            ability = fixed_rng.next_rand(2)
            gender = 0 if gender_ratio == 0 else 1 if gender_ratio == 254 else 2
            if slot.gender != 255:
                gender = slot.gender
            elif 1 <= gender_ratio < 254:
                gender = (fixed_rng.next_rand(253) + 1) < gender_ratio
            if len(gender_filter) != 0 and gender not in gender_filter:
                continue
            nature = fixed_rng.next_rand(25)
            if len(nature_filter) != 0 and nature not in nature_filter:
                continue
            if slot.is_alpha:
                height = weight = 255
            else:
                height = fixed_rng.next_rand(0x81) + fixed_rng.next_rand(0x80)
                weight = fixed_rng.next_rand(0x81) + fixed_rng.next_rand(0x80)
            if len(size_filter) != 0 and height not in size_filter:
                continue
            pokemon = (
                len(ko_path),
                ko_path,
                (slot.species, slot.form, slot.is_alpha),
                np.uint32(encryption_constant),
                np.uint32(pid),
                ivs,
                np.uint8(ability),
                np.uint8(gender),
                np.uint8(nature),
                np.uint8(shiny),
                np.uint8(height),
                np.uint8(weight),
            )
            results.append(pokemon)
            # TODO: level rand?

        for kos in range(1, min(5, first_wave_count + 1)):
            new_item = (
                ko_path + [np.uint8(kos)],
                first_wave_count - kos,
                ghost_count,
                second_wave_count,
                advance_seed(group_seed, spawn_count)
            )
            queue.append(new_item)
        # ghost spawns
        if first_wave_count == 0 and second_wave_count != 0:
            if ghost_count != 0:
                for kos in range(1, min(ghost_count + 1, 4)):
                    new_item = (
                        ko_path + [np.uint8(10 + kos)],
                        first_wave_count,
                        ghost_count - kos,
                        second_wave_count,
                        advance_seed(group_seed, spawn_count)
                    )
                    queue.append(new_item)
            new_item = (
                ko_path + [np.uint8(255), np.uint8(4)],
                -1,
                ghost_count,
                second_wave_count - 4,
                advance_seed(group_seed, spawn_count)
            )
            queue.append(new_item)
        elif first_wave_count == -1:
            for kos in range(1, min(5, second_wave_count + 1)):
                new_item = (
                    ko_path + [np.uint8(kos)],
                    first_wave_count,
                    ghost_count,
                    second_wave_count - kos,
                    advance_seed(group_seed, spawn_count)
                )
                queue.append(new_item)

    return results

@numba.njit(nogil=True)
def generate_standard(
    seed: np.uint64,
    starting_path: tuple[int],
    min_adv: int,
    max_adv: int,
    spawn_count: int,
    encounter_table: EncounterAreaLA,
    weather: LAWeather,
    time: LATime,
    species_info: dict[tuple[int, int], tuple[int, int, bool]],
    gender_filter: tuple,
    nature_filter: tuple,
    size_filter: tuple,
    shiny_filter: np.uint8,
    alpha_filter: np.uint8,
    iv_filters: tuple,
    parent_data: np.ndarray,
    results: TypedList,
):
    """
    Non-mass outbreak spawner prediction generator
    parent_data[0]: external uint64 count of how many pokemon have been checked
    parent_data[1]: external bool (as uint64) flag for if the search should still run (threading)
    """

    # faster to reinit rather than create new objects
    group_rng = Xoroshiro128PlusRejection(0, 0)
    generator_rng = Xoroshiro128PlusRejection(0, 0)
    fixed_rng = Xoroshiro128PlusRejection(0, 0)

    queue = []
    if starting_path[0] == -1:
        if spawn_count == 1:
            # single spawners always start by catching two consecutive mons
            queue.append(
                ([np.uint8(1), np.uint8(1)], advance_seed(advance_seed(seed, 1), 1))
            )
        elif spawn_count > 1:
            # triple/double spawners always start by catching the two mons there
            queue.append(([np.uint8(2)], advance_seed(seed, spawn_count)))
        if spawn_count == 3:
            # triple spawners also have the option of catching the third mon
            queue.append(([np.uint8(3)], advance_seed(seed, spawn_count)))
    else:
        # initial spawns
        starting_path = (spawn_count,) + starting_path
        for kos in starting_path[:-1]:
            seed = advance_seed(seed, kos)
        queue.append(([np.uint8(kos) for kos in starting_path[1:]], seed))
    initial_advances = len(queue[0][0])
    # check parent_data[1] flag each item
    while len(queue) != 0 and parent_data[1] == 0:
        item = queue.pop()
        # increment progress counter
        atomic_add(parent_data, 0, 1)
        advance = len(item[0]) - initial_advances
        ko_path, group_seed = item
        if advance >= min_adv:
            group_rng.re_init(group_seed)
            for _ in range(ko_path[-1]):
                generator_rng.re_init(group_rng.next())
                group_rng.next()
                slot: SlotLA = encounter_table.calc_slot(
                    generator_rng.next() * 5.421010862427522e-20,
                    np.int64(time),
                    np.int64(weather),  # 1/2**64
                )
                gender_ratio, shiny_rolls, filtered_species = species_info[
                    (slot.species, slot.form)
                ]
                if not filtered_species:
                    continue
                if alpha_filter and not slot.is_alpha:
                    continue
                fixed_rng.re_init(generator_rng.next())
                encryption_constant = fixed_rng.next_rand(0xFFFFFFFF)
                sidtid = fixed_rng.next_rand(0xFFFFFFFF)
                for _ in range(shiny_rolls):
                    pid = fixed_rng.next_rand(0xFFFFFFFF)
                    xor = (
                        (pid >> 16)
                        ^ (sidtid >> 16)
                        ^ (pid & 0xFFFF)
                        ^ (sidtid & 0xFFFF)
                    )
                    shiny = 2 if xor == 0 else 1 if xor < 16 else 0
                    if shiny:
                        break
                if shiny_filter != 15 and not (shiny_filter & shiny):
                    continue
                ivs = np.zeros(6, np.uint8)
                for _ in range(slot.guaranteed_ivs):
                    index = fixed_rng.next_rand(6)
                    while ivs[index] != 0:
                        index = fixed_rng.next_rand(6)
                    ivs[index] = 31
                for i in range(6):
                    if ivs[i] == 0:
                        ivs[i] = fixed_rng.next_rand(32)
                passes_ivs = True
                for i, (minimum, maximum) in enumerate(iv_filters):
                    if minimum > ivs[i]:
                        passes_ivs = False
                        break
                    if maximum < ivs[i]:
                        passes_ivs = False
                        break
                if not passes_ivs:
                    continue
                ability = fixed_rng.next_rand(2)
                gender = 0 if gender_ratio == 0 else 1 if gender_ratio == 254 else 2
                if slot.gender != 255:
                    gender = slot.gender
                elif 1 <= gender_ratio < 254:
                    gender = (fixed_rng.next_rand(253) + 1) < gender_ratio
                if len(gender_filter) != 0 and gender not in gender_filter:
                    continue
                nature = fixed_rng.next_rand(25)
                if len(nature_filter) != 0 and nature not in nature_filter:
                    continue
                if slot.is_alpha:
                    height = weight = 255
                else:
                    height = fixed_rng.next_rand(0x81) + fixed_rng.next_rand(0x80)
                    weight = fixed_rng.next_rand(0x81) + fixed_rng.next_rand(0x80)
                if len(size_filter) != 0 and height not in size_filter:
                    continue
                pokemon = (
                    advance,
                    ko_path,
                    (slot.species, slot.form, slot.is_alpha),
                    np.uint32(encryption_constant),
                    np.uint32(pid),
                    ivs,
                    np.uint8(ability),
                    np.uint8(gender),
                    np.uint8(nature),
                    np.uint8(shiny),
                    np.uint8(height),
                    np.uint8(weight),
                )
                results.append(pokemon)
                # TODO: level rand?

        if advance >= (max_adv - 1):
            continue
        for kos in range(1, spawn_count + 1):
            new_item = (
                ko_path + [np.uint8(kos)],
                advance_seed(group_seed, ko_path[-1]),
            )
            queue.append(new_item)
    return results
