from abc import ABC, abstractmethod
import math

from .metrics import ModeResult


class SimulationBackend(ABC):
    @abstractmethod
    def evaluate_state(self, geometry, state, config, workspace):
        """Return a list of ModeResult objects for one PCM state."""


class AnalyticMockBackend(SimulationBackend):
    """Pipeline test backend. Its results are not electromagnetic simulation."""

    def evaluate_state(self, geometry, state, config, workspace):
        design = geometry.design
        target = config["simulation"]["target_frequency_thz"]
        shape_distance = (
            abs(design["duty_cycle"] - 0.52) / 0.20
            + abs(design["si_thickness_um"] - 0.24) / 0.15
            + abs(design["vertical_gap_um"] - 0.13) / 0.15
            + abs(design["pcm_thickness_um"] - 0.03) / 0.04
            + abs(design["kx_norm"] - 0.12) / 0.06
        )
        quality = math.exp(-shape_distance)
        sign = 1.0 if state == "amorphous" else -1.0
        directionality = sign * (2.0 + 28.0 * quality)
        frequency = target + sign * (1.5 - quality) + 12.0 * (design["period_um"] - 0.82)
        q_value = 10.0 ** (3.0 + 5.0 * quality)
        power_up = 10.0 ** (directionality / 10.0)
        modes = [
            ModeResult(state, 0, frequency, q_value, power_up, 1.0),
            ModeResult(state, 1, frequency + 8.0, q_value / 20.0, 1.0, 1.0),
        ]
        return modes


def make_backend(name):
    if name == "mock":
        return AnalyticMockBackend()
    if name == "comsol":
        from .comsol_2d import Comsol2DBackend
        return Comsol2DBackend()
    raise ValueError(f"Unknown backend: {name}")
