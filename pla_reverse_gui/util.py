"""Utility functions"""

from numba_pokemon_prngs.data.personal import PERSONAL_INFO_LA, PersonalInfo8LA
from numba_pokemon_prngs.data import SPECIES_EN

EVO_LINES = [
    ((722, 0), (723, 0), (724, 1)),
    ((155, 0), (156, 0), (157, 1)),
    ((501, 0), (502, 0), (503, 1)),
    ((399, 0), (400, 0)),
    ((396, 0), (397, 0), (398, 0)),
    ((403, 0), (404, 0), (405, 0)),
    ((265, 0), (266, 0), (267, 0), (268, 0), (269, 0)),
    ((77, 0), (78, 0)),
    (
        (133, 0),
        (134, 0),
        (135, 0),
        (136, 0),
        (196, 0),
        (197, 0),
        (470, 0),
        (471, 0),
        (700, 0),
    ),
    ((41, 0), (42, 0), (169, 0)),
    ((425, 0), (426, 0)),
    ((401, 0), (402, 0)),
    ((418, 0), (419, 0)),
    (
        (412, 0),
        (412, 1),
        (412, 2),
        (413, 0),
        (413, 1),
        (413, 2),
        (414, 0),
        (414, 1),
        (414, 2),
    ),
    ((74, 0), (75, 0), (76, 0)),
    ((234, 0), (899, 0)),
    ((446, 0), (143, 0)),
    ((46, 0), (47, 0)),
    ((172, 0), (25, 0), (26, 0)),
    ((63, 0), (64, 0), (65, 0)),
    ((390, 0), (391, 0), (392, 0)),
    ((427, 0), (428, 0)),
    ((420, 0), (421, 0), (421, 1)),
    ((54, 0), (55, 0)),
    ((415, 0), (416, 0)),
    ((123, 0), (900, 0), (900, 1), (212, 0)),
    ((214, 0),),
    ((439, 0), (122, 0)),
    ((190, 0), (424, 0)),
    ((129, 0), (130, 0)),
    ((422, 0), (422, 1), (423, 0), (423, 1)),
    ((211, 1), (904, 0)),
    ((440, 0), (113, 0), (242, 0)),
    ((406, 0), (315, 0), (407, 0)),
    ((455, 0),),
    ((548, 0), (549, 1), (549, 2)),
    ((114, 0), (465, 0)),
    ((339, 0), (340, 0)),
    ((453, 0), (454, 0)),
    ((280, 0), (281, 0), (282, 0), (475, 0)),
    ((193, 0), (469, 0)),
    ((449, 0), (450, 0)),
    ((417, 0),),
    ((434, 0), (435, 0)),
    ((216, 0), (217, 0), (901, 0)),
    ((704, 0), (705, 1), (706, 1)),
    ((95, 0), (208, 0)),
    ((111, 0), (112, 0), (464, 0)),
    ((438, 0), (185, 0)),
    ((108, 0), (463, 0)),
    ((175, 0), (176, 0), (468, 0)),
    ((387, 0), (388, 0), (389, 0)),
    ((137, 0), (233, 0), (474, 0)),
    ((92, 0), (93, 0), (94, 0)),
    ((442, 0),),
    ((198, 0), (430, 0)),
    (
        (201, 0),
        (201, 1),
        (201, 2),
        (201, 3),
        (201, 4),
        (201, 5),
        (201, 6),
        (201, 7),
        (201, 8),
        (201, 9),
        (201, 10),
        (201, 11),
        (201, 12),
        (201, 13),
        (201, 14),
        (201, 15),
        (201, 16),
        (201, 17),
        (201, 18),
        (201, 19),
        (201, 20),
        (201, 21),
        (201, 22),
        (201, 23),
        (201, 24),
        (201, 25),
        (201, 26),
        (201, 27),
    ),
    ((363, 0), (364, 0), (365, 0)),
    ((223, 0), (224, 0)),
    ((451, 0), (452, 0)),
    ((58, 1), (59, 1), (59, 2)),
    ((431, 0), (432, 0)),
    ((66, 0), (67, 0), (68, 0)),
    ((441, 0),),
    ((355, 0), (356, 0), (477, 0)),
    ((393, 0), (394, 0), (395, 0)),
    ((458, 0), (226, 0)),
    ((550, 2), (902, 0), (902, 1)),
    ((37, 0), (37, 1), (38, 0), (38, 1)),
    ((72, 0), (73, 0)),
    ((456, 0), (457, 0)),
    ((240, 0), (126, 0), (467, 0)),
    ((81, 0), (82, 0), (462, 0)),
    ((436, 0), (437, 0)),
    ((239, 0), (125, 0), (466, 0)),
    ((207, 0), (472, 0)),
    ((443, 0), (444, 0), (445, 0)),
    ((299, 0), (476, 0)),
    ((100, 1), (101, 1), (101, 2)),
    ((479, 0), (479, 1), (479, 2), (479, 3), (479, 4), (479, 5)),
    ((433, 0), (358, 0)),
    ((200, 0), (429, 0)),
    ((173, 0), (35, 0), (36, 0)),
    ((215, 0), (215, 1), (903, 0), (461, 0)),
    ((361, 0), (362, 0), (478, 0)),
    ((408, 0), (409, 0)),
    ((410, 0), (411, 0)),
    ((220, 0), (221, 0), (473, 0)),
    ((712, 0), (713, 1), (713, 2)),
    ((459, 0), (460, 0)),
    ((570, 1), (571, 1)),
    ((627, 0), (628, 1)),
    ((447, 0), (448, 0)),
]


def path_to_string(path: tuple[int]) -> str:
    """Convert a path to a string with custom labels"""
    return "->".join(
        (
            str(n) if n < 10 else
            "Clear Wave" if n == 255 else
            f"Ghost {n - 10}" if n < 20 else
            "Invalid"
        ) for n in path
    )

# TODO: this is hacky and only needed because result_table relies on checking the string
def string_to_path(string: str) -> tuple[int]:
    """Convert a string with custom labels to a path"""
    return tuple(
        (
            255 if n == "Clear Wave" else
            int(n.split(" ")[1]) + 10 if n.startswith("Ghost") else
            int(n)
        ) for n in string.split("->")
    )

def get_name_en(species: int, form: int = 0, is_alpha: bool = False) -> str:
    """Return the english name of a pokemon given its species, form, and alpha status"""
    return f"{'Alpha ' if is_alpha else ''}{SPECIES_EN[species]}{f'-{form}' if form else ''}"


def get_personal_info(species: int, form: int = 0) -> PersonalInfo8LA:
    """Return the personal info of a pokemon given its species and form"""
    base_info = PERSONAL_INFO_LA[species]
    if form == 0:
        return base_info
    return PERSONAL_INFO_LA[base_info.form_stats_index + form - 1]


def get_personal_index(species: int, form: int = 0) -> int:
    """Return the personal info index of a pokemon given its species and form"""
    if form == 0:
        return species
    return PERSONAL_INFO_LA[species].form_stats_index + form - 1


def find_evo_line(species: int, form: int = 0) -> tuple[tuple[int, int]]:
    """Find the evolution line of a pokemon given its species and form"""
    return next(
        (line for line in EVO_LINES if (species, form) in line), ((species, form),)
    )


def calc_effort_level(iv: int) -> int:
    """Calculate the initial effort levels of a pokemon"""
    if iv >= 31:
        return 3
    if iv >= 26:
        return 2
    if iv >= 20:
        return 1
    return 0
