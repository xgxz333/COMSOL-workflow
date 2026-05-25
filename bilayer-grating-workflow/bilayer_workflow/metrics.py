from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class ModeResult:
    state: str
    mode_index: int
    frequency_thz: float
    q_total: float
    power_up: float
    power_down: float

    @property
    def directionality_db(self):
        eps = 1e-30
        return 10.0 * math.log10((max(self.power_up, 0.0) + eps) / (max(self.power_down, 0.0) + eps))

    def to_dict(self):
        record = asdict(self)
        record["directionality_db"] = self.directionality_db
        return record


def _direction_margin(mode, desired_direction):
    if desired_direction == "up":
        return mode.directionality_db
    if desired_direction == "down":
        return -mode.directionality_db
    raise ValueError(f"Unknown desired direction: {desired_direction}")


def score_pair(amorphous, crystalline, config):
    objective = config["objective"]
    simulation = config["simulation"]
    weights = objective["weights"]

    if min(amorphous.q_total, crystalline.q_total) < objective["minimum_q"]:
        return float("-inf"), {}

    window_low, window_high = simulation["frequency_window_thz"]
    if not (
        window_low <= amorphous.frequency_thz <= window_high
        and window_low <= crystalline.frequency_thz <= window_high
    ):
        return float("-inf"), {}

    a_margin = _direction_margin(amorphous, objective["amorphous_direction"])
    c_margin = _direction_margin(crystalline, objective["crystalline_direction"])
    switching_margin = min(a_margin, c_margin)
    cap_db = objective["directionality_cap_db"]
    floor_db = objective["minimum_directionality_db"]
    tol = objective["frequency_tolerance_thz"]

    min_log_q = math.log10(min(amorphous.q_total, crystalline.q_total))
    average_frequency = (amorphous.frequency_thz + crystalline.frequency_thz) / 2.0
    target_error = abs(average_frequency - simulation["target_frequency_thz"]) / tol
    state_mismatch = abs(amorphous.frequency_thz - crystalline.frequency_thz) / tol
    direction_reward = min(switching_margin, cap_db) / 10.0
    direction_shortfall = max(0.0, floor_db - switching_margin) / 10.0

    score = (
        weights["log_q"] * min_log_q
        + weights["directionality"] * direction_reward
        - weights["direction_shortfall"] * direction_shortfall
        - weights["target_frequency"] * target_error
        - weights["state_frequency_match"] * state_mismatch
    )
    attrs = {
        "min_log_q": min_log_q,
        "amorphous_directionality_db": amorphous.directionality_db,
        "crystalline_directionality_db": crystalline.directionality_db,
        "switching_margin_db": switching_margin,
        "average_frequency_thz": average_frequency,
        "state_frequency_difference_thz": abs(
            amorphous.frequency_thz - crystalline.frequency_thz
        ),
        "directionality_pass": switching_margin >= floor_db,
        "amorphous_mode_index": amorphous.mode_index,
        "crystalline_mode_index": crystalline.mode_index,
    }
    return score, attrs


def evaluate_mode_pairs(amorphous_modes, crystalline_modes, config):
    best_score = float("-inf")
    best = None
    for amorphous in amorphous_modes:
        for crystalline in crystalline_modes:
            score, attrs = score_pair(amorphous, crystalline, config)
            if score > best_score:
                best_score = score
                best = {
                    "objective": score,
                    "attrs": attrs,
                    "amorphous": amorphous.to_dict(),
                    "crystalline": crystalline.to_dict(),
                }
    if best is None:
        return {"objective": -1.0e9, "attrs": {"valid_pair": False}}
    best["attrs"]["valid_pair"] = True
    return best
