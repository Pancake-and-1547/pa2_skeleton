import numpy as np


def _is_floor_map_like(value) -> bool:
    has_door_state = hasattr(value, "closed_doors_mask") or hasattr(value, "door_states")
    return all(hasattr(value, attr) for attr in ["grid", "room_types"]) and has_door_state


def _closed_door_mask(value) -> np.ndarray:
    if hasattr(value, "closed_doors_mask"):
        return np.asarray(value.closed_doors_mask, dtype=bool)
    if hasattr(value, "door_states") and hasattr(value, "doors"):
        mask = np.zeros_like(value.doors, dtype=bool)
        for (r, c), is_open in value.door_states.items():
            if not is_open:
                mask[int(r), int(c)] = True
        return mask
    raise AttributeError("FloorMap-like object has no recognizable door-state representation.")


def _is_ac_like(value) -> bool:
    return all(hasattr(value, attr) for attr in ["name", "row", "col", "power_level", "mode"])


def _is_state_like(value) -> bool:
    return all(
        hasattr(value, attr)
        for attr in [
            "floor_map",
            "ac_units",
            "temperature_field",
            "outdoor_temp",
            "setpoint_temp",
            "room_weights",
            "energy_dict",
            "score",
        ]
    )


def compare_floor_map(map1, map2) -> bool:
    if not (_is_floor_map_like(map1) and _is_floor_map_like(map2)):
        return False
    if not np.array_equal(map1.grid, map2.grid):
        return False
    if not np.array_equal(map1.room_types, map2.room_types):
        return False
    if not np.array_equal(_closed_door_mask(map1), _closed_door_mask(map2)):
        return False
    return True


def compare_ac(ac1, ac2):
    if not (_is_ac_like(ac1) and _is_ac_like(ac2)):
        return False
    return (
        ac1.name == ac2.name
        and ac1.col == ac2.col
        and ac1.row == ac2.row
        and ac1.power_level == ac2.power_level
        and ac1.mode == ac2.mode
    )


def compare_state(state1, state2):
    if not (_is_state_like(state1) and _is_state_like(state2)):
        return False
    if not compare_floor_map(state1.floor_map, state2.floor_map):
        return False
    if len(state1.ac_units) != len(state2.ac_units):
        return False
    if not all(compare_ac(a, b) for a, b in zip(state1.ac_units, state2.ac_units)):
        return False
    if not np.isclose(state1.temperature_field, state2.temperature_field).all():
        return False
    if not np.isclose(state1.outdoor_temp, state2.outdoor_temp):
        return False
    if not np.isclose(state1.setpoint_temp, state2.setpoint_temp):
        return False
    if not compare_value(state1.room_weights, state2.room_weights):
        return False
    if not compare_value(state1.energy_dict, state2.energy_dict):
        return False
    if not np.isclose(state1.score, state2.score).all():
        return False
    return True


def compare_value(value1, value2):
    if _is_state_like(value1) or _is_state_like(value2):
        return compare_state(value1, value2)

    if _is_floor_map_like(value1) or _is_floor_map_like(value2):
        return compare_floor_map(value1, value2)

    if _is_ac_like(value1) or _is_ac_like(value2):
        return compare_ac(value1, value2)

    if isinstance(value1, np.ndarray) or isinstance(value2, np.ndarray):
        if not isinstance(value1, np.ndarray) or not isinstance(value2, np.ndarray):
            return False
        if value1.shape != value2.shape:
            return False
        if value1.dtype.kind in "fc" or value2.dtype.kind in "fc":
            return np.isclose(value1, value2, equal_nan=True).all()
        return np.array_equal(value1, value2, equal_nan=True)

    if isinstance(value1, dict) or isinstance(value2, dict):
        if not isinstance(value1, dict) or not isinstance(value2, dict):
            return False
        if value1.keys() != value2.keys():
            return False
        return all(compare_value(value1[key], value2[key]) for key in value1)

    if isinstance(value1, (list, tuple)) or isinstance(value2, (list, tuple)):
        if type(value1) is not type(value2):
            return False
        if len(value1) != len(value2):
            return False
        return all(compare_value(item1, item2) for item1, item2 in zip(value1, value2))

    if isinstance(value1, np.generic) or isinstance(value2, np.generic):
        try:
            return bool(np.isclose(value1, value2, equal_nan=True))
        except TypeError:
            return value1 == value2

    try:
        return value1 == value2
    except ValueError:
        return False


def find_different_parameters(student_case: dict, sample_case: dict, ignored_params=None) -> list[str]:
    ignored = set(ignored_params or [])
    differing = []
    for name in sorted(set(student_case) | set(sample_case)):
        if name in ignored:
            continue
        if name not in student_case or name not in sample_case:
            differing.append(name)
            continue
        if not compare_value(student_case[name], sample_case[name]):
            differing.append(name)
    return differing
