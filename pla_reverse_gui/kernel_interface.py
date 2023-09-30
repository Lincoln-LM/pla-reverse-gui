"""Interface for pla_reverse's kernels"""
import os

import numpy as np
import pyopencl as cl
from numba_pokemon_prngs.xorshift import Xoroshiro128PlusRejection

# pylint: disable=no-name-in-module
from qtpy.QtCore import QThread, Signal

# pylint: enable=no-name-in-module

from .pla_reverse_main import pla_reverse
from .util import get_personal_index, get_personal_info

# TODO: selection for ctx
os.environ["PYOPENCL_CTX"] = ""


class ComputeFixedSeedsThread(QThread):
    """Interface for fixed_seed shader"""

    finished = Signal()
    log = Signal(str)
    results = Signal(object)
    init_progress_bar = Signal(int)
    progress = Signal(int)

    def __init__(self, *args) -> None:
        super().__init__()
        self.args = args

    def run(self):
        """Thread work"""
        (
            species_form,
            basculin_gender,
            shiny_rolls,
            ivs,
            ability,
            nature,
            gender,
            measured_species,
            heights,
            weights,
            imperial,
        ) = self.args
        personal_info = get_personal_info(*species_form)
        if basculin_gender is not None and species_form == (550, 2):
            gender_ratio = (0, 254)[basculin_gender]
        else:
            gender_ratio = personal_info.gender_ratio
        self.log.emit("Computing possible sizes....")
        sizes_set = set(
            pla_reverse.size.all_possible_sizes(
                get_personal_index(*measured_species[0]),
                heights[0],
                weights[0],
                imperial,
            )
        )
        for measured_species_, height, weight in zip(
            measured_species[1:], heights[1:], weights[1:]
        ):
            sizes_set &= set(
                pla_reverse.size.all_possible_sizes(
                    get_personal_index(*measured_species_), height, weight, imperial
                )
            )
        self.log.emit(f"{len(sizes_set)} possible sizes.")
        self.log.emit("Setting kernel constants....")
        kernel_constants = {
            "SHINY_ROLLS": shiny_rolls,
            "IV_CONST": pla_reverse.matrix.vec_to_int(
                pla_reverse.matrix.iv_const(shiny_rolls)
            ),
            "SEED_MAT": ",".join(
                str(pla_reverse.matrix.vec_to_int(row))
                for row in pla_reverse.matrix.generalized_inverse(
                    pla_reverse.matrix.iv_matrix(shiny_rolls)
                )
            ),
            "NULL_SPACE": ",".join(
                str(pla_reverse.matrix.vec_to_int(row))
                for row in pla_reverse.matrix.nullspace(
                    pla_reverse.matrix.iv_matrix(shiny_rolls)
                )
            ),
            "IVS": ",".join(str(iv) for iv in ivs),
            "TWO_ABILITIES": str(
                personal_info.ability_1 != personal_info.ability_2
            ).lower(),
            "ABILITY": ability,
            "GENDER_RATIO": gender_ratio,
            "GENDER": gender,
            "NATURE": nature,
            "SIZES": ",".join(
                str(size) for size in pla_reverse.size.build_sizes_table(sizes_set)
            ),
        }
        self.log.emit("Computing expected seeds....")
        expected_seeds = pla_reverse.odds.calc_expected_seeds(
            personal_info.ability_1 != personal_info.ability_2,
            gender,
            gender_ratio,
            sizes_set,
        )
        self.log.emit(f"{expected_seeds} expected fixed seeds")

        context = cl.create_some_context()
        queue = cl.CommandQueue(context)

        self.log.emit("Building kernel....")
        program = cl.Program(
            context,
            pla_reverse.shaders.build_shader_code(
                "fixed_seed_shader", kernel_constants
            ),
        ).build()

        host_results = np.zeros(round(expected_seeds * 1.5), np.uint64)
        host_count = np.zeros(1, np.int32)

        device_results = cl.Buffer(
            context, cl.mem_flags.READ_WRITE, host_results.nbytes
        )
        device_count = cl.Buffer(context, cl.mem_flags.READ_WRITE, host_count.nbytes)

        cl.enqueue_copy(queue, device_results, host_results)
        cl.enqueue_copy(queue, device_count, host_count)

        program.find_fixed_seeds(
            queue, (32**2, 32**2, 32**2), None, device_count, device_results
        )

        host_results = np.empty_like(host_results)
        host_count = np.empty_like(host_count)

        self.log.emit("Processing....")

        cl.enqueue_copy(queue, host_results, device_results)
        cl.enqueue_copy(queue, host_count, device_count)

        self.log.emit(f"{host_count[0]} fixed seeds found!")
        results = host_results[: host_count[0]]

        self.init_progress_bar.emit(host_count[0])
        self.log.emit("Verifying all fixed seeds....")
        for i, fixed_seed in enumerate(results):
            rng = Xoroshiro128PlusRejection(fixed_seed)
            rng.advance(2 + kernel_constants["SHINY_ROLLS"])
            _ivs = tuple(rng.next_rand(32) for _ in range(6))
            _ability = rng.next_rand(2)
            if 1 <= kernel_constants["GENDER_RATIO"] <= 253:
                gender_val = rng.next_rand(253)
                _gender = (gender_val + 1) < kernel_constants["GENDER_RATIO"]
            _nature = rng.next_rand(25)
            _height = rng.next_rand(0x81) + rng.next_rand(0x80)
            _weight = rng.next_rand(0x81) + rng.next_rand(0x80)
            if _ivs != ivs:
                self.log.emit(f"IVs were wrong! {_ivs} {ivs}")
                return
            if kernel_constants["TWO_ABILITIES"] == "true" and _ability != ability:
                self.log.emit(f"Ability was wrong! {_ability} {ability}")
                return
            if 1 <= gender_ratio <= 253 and _gender != gender:
                self.log.emit(f"Gender was wrong! {_gender} {gender}")
                return
            if _nature != nature:
                self.log.emit(f"Nature was wrong! {_nature} {nature}")
                return
            if (
                _height,
                _weight,
            ) not in sizes_set:
                self.log.emit(
                    f"Height/Weight was wrong! {_height} {_weight} {sizes_set}"
                )
                return
            self.progress.emit(i)

        self.log.emit("All fixed seeds found were valid!")
        self.results.emit(results)


class ComputeGeneratorSeedsThread(QThread):
    """Interface for generator_seed shader"""

    finished = Signal()
    log = Signal(str)
    results = Signal(object)
    init_progress_bar = Signal(int)
    progress = Signal(int)

    def __init__(self, fixed_seeds) -> None:
        super().__init__()
        self.fixed_seeds = fixed_seeds

    def run(self):
        """Thread work"""
        context = cl.create_some_context()
        queue = cl.CommandQueue(context)

        total_seeds = len(self.fixed_seeds)
        step_size = total_seeds // 100

        self.log.emit("Building kernel....")
        program = cl.Program(
            context, pla_reverse.shaders.build_shader_code("generator_seed_shader", {})
        ).build()

        self.log.emit("Initializing arrays....")

        host_count = np.zeros(1, np.uint64)
        host_results = np.zeros(round(total_seeds * 1.5), np.uint64)
        host_slices = np.zeros(256, np.uint64)
        host_seeds = self.fixed_seeds
        for i in range(256):
            for k in range(8):
                if (i >> k) & 1:
                    host_slices[i] |= np.uint64(1) << np.uint64(k * 8)

        device_count = cl.Buffer(context, cl.mem_flags.READ_WRITE, host_count.nbytes)
        device_results = cl.Buffer(
            context, cl.mem_flags.WRITE_ONLY, host_results.nbytes
        )
        device_slices = cl.Buffer(context, cl.mem_flags.READ_ONLY, host_slices.nbytes)
        device_seeds = cl.Buffer(context, cl.mem_flags.READ_WRITE, host_seeds.nbytes)

        cl.enqueue_copy(queue, device_count, host_count)
        cl.enqueue_copy(queue, device_results, host_results)
        cl.enqueue_copy(queue, device_slices, host_slices)
        cl.enqueue_copy(queue, device_seeds, host_seeds)

        self.log.emit("Processing....")
        kernel = program.find_generator_seeds
        self.init_progress_bar.emit(total_seeds)
        i = 0
        while i < total_seeds:
            for j in range(min(step_size, total_seeds - i)):
                kernel(
                    queue,
                    (256, 256, 256),
                    None,
                    device_count,
                    device_results,
                    device_slices,
                    device_seeds,
                    np.uint32(i + j),
                ).wait()
            self.progress.emit(i + j)
            i += step_size

        host_count = np.empty_like(host_count)
        host_results = np.empty_like(host_results)

        cl.enqueue_copy(queue, host_results, device_results)
        cl.enqueue_copy(queue, host_count, device_count)

        results = host_results[: host_count[0]]
        self.log.emit((f"{host_count[0]} generator seeds found!"))
        self.results.emit(results)


class ComputeGroupSeedThread(QThread):
    """Interface for group_seed shader"""

    finished = Signal()
    log = Signal(str)

    def __init__(self, fixed_seeds_2, generator_seeds, multi_spawner: bool) -> None:
        super().__init__()
        self.fixed_seeds_2 = fixed_seeds_2
        self.generator_seeds = generator_seeds
        self.multi_spawner = multi_spawner

    def run(self) -> None:
        """Thread work"""
        context = cl.create_some_context()
        queue = cl.CommandQueue(context)
        self.log.emit("Building kernel....")
        program = cl.Program(
            context,
            pla_reverse.shaders.build_shader_code(
                "group_seed_shader", {"IS_MULTISPAWNER": int(self.multi_spawner)}
            ),
        ).build()
        host_results = np.zeros(1, np.uint64)

        host_generator_seeds = self.generator_seeds
        host_fixed_seeds = np.sort(self.fixed_seeds_2)

        device_results = cl.Buffer(
            context, cl.mem_flags.WRITE_ONLY, host_results.nbytes
        )
        device_generator_seeds = cl.Buffer(
            context, cl.mem_flags.READ_ONLY, host_generator_seeds.nbytes
        )
        device_fixed_seeds = cl.Buffer(
            context, cl.mem_flags.READ_ONLY, host_fixed_seeds.nbytes
        )
        self.log.emit("Processing....")

        cl.enqueue_copy(queue, device_results, host_results)
        cl.enqueue_copy(queue, device_generator_seeds, host_generator_seeds)
        cl.enqueue_copy(queue, device_fixed_seeds, host_fixed_seeds)

        kernel = program.find_group_seed
        kernel(
            queue,
            (len(host_generator_seeds),),
            None,
            device_results,
            device_generator_seeds,
            device_fixed_seeds,
            np.int32(len(host_fixed_seeds)),
        )

        host_results = np.empty_like(host_results)

        cl.enqueue_copy(queue, host_results, device_results)

        group_seed = host_results[0]
        self.log.emit(f"Group Seed Found: {group_seed:016X} | {group_seed}")
