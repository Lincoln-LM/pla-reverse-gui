"""Spawner prediction generator"""

import numpy as np
import numba
from numba_pokemon_prngs.util import rotate_left_u64
from numba_pokemon_prngs.xorshift import Xoroshiro128PlusRejection
from numba_pokemon_prngs.data.encounter.encounter_area_la import EncounterAreaLA, SlotLA
from numba_pokemon_prngs.enums import LAWeather, LATime


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


@numba.njit()
def generate(
    seed: np.uint64,
    min_adv: int,
    max_adv: int,
    spawn_count: int,
    encounter_table: EncounterAreaLA,
    weather: LAWeather,
    time: LATime,
    species_info: dict[tuple[int, int], tuple[int, int, bool]],
    gender_filter: tuple,
    nature_filter: tuple,
    shiny_filter: np.uint8,
    alpha_filter: np.uint8,
    iv_filters: tuple,
):
    """Spawner prediction generator"""
    results = []

    # faster to reinit rather than create new objects
    group_rng = Xoroshiro128PlusRejection(0, 0)
    generator_rng = Xoroshiro128PlusRejection(0, 0)
    fixed_rng = Xoroshiro128PlusRejection(0, 0)

    queue = []
    if spawn_count == 1:
        # single spawners always start by catching two consecutive mons
        queue.append(
            ([np.uint8(1), np.uint8(1)], advance_seed(advance_seed(seed, 1), 1))
        )
    elif spawn_count > 1:
        # triple/double spawners always start by catching the two mons there
        queue.append(([np.uint8(2)], advance_seed(seed, 2)))
    if spawn_count == 3:
        # triple spawners also have the option of catching the third mon
        queue.append(([np.uint8(3)], advance_seed(seed, 3)))
    initial_advances = len(queue[0][0])
    while len(queue) != 0:
        # TODO: guard clause/return early for filters
        item = queue.pop()
        advance = len(item[0]) - initial_advances
        if advance >= min_adv:
            ko_path, group_seed = item
            group_rng.re_init(group_seed)
            for _ in range(spawn_count):
                generator_rng.re_init(group_rng.next())
                slot: SlotLA = encounter_table.calc_slot(
                    generator_rng.next() * 5.421010862427522e-20,
                    np.int64(time),
                    np.int64(weather),  # 1/2**64
                )
                gender_ratio, shiny_rolls, filtered_species = species_info[
                    (slot.species, slot.form)
                ]
                if ((not alpha_filter) or slot.is_alpha) and filtered_species:
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
                    if shiny_filter == 15 or shiny_filter & shiny:
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
                        if passes_ivs:
                            ability = fixed_rng.next_rand(2)
                            gender = (
                                0
                                if gender_ratio == 0
                                else 1
                                if gender_ratio == 254
                                else 2
                            )
                            if 1 <= gender_ratio < 254:
                                gender = (fixed_rng.next_rand(253) + 1) < gender_ratio
                            if len(gender_filter) == 0 or gender in gender_filter:
                                nature = fixed_rng.next_rand(25)
                                if len(nature_filter) == 0 or nature in nature_filter:
                                    height = fixed_rng.next_rand(
                                        0x81
                                    ) + fixed_rng.next_rand(0x80)
                                    weight = fixed_rng.next_rand(
                                        0x81
                                    ) + fixed_rng.next_rand(0x80)
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

                group_rng.next()

        if advance >= (max_adv - 1):
            continue
        for kos in range(1, spawn_count + 1):
            new_item = (ko_path + [np.uint8(kos)], advance_seed(group_seed, kos))
            queue.append(new_item)
    return results
