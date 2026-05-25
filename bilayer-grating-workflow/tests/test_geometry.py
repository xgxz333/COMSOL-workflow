import os
import sys
import tempfile
import importlib.util

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.geometry import GeometryError, build_geometry, visualize_geometry


DESIGN = {
    "period_um": 0.82,
    "duty_cycle": 0.55,
    "si_thickness_um": 0.22,
    "vertical_gap_um": 0.14,
    "pcm_thickness_um": 0.03,
    "sio2_cap_thickness_um": 0.18,
    "cladding_um": 0.65,
    "pml_um": 0.45,
    "kx_norm": 0.12,
}


def test_identical_silicon_gratings():
    geometry = build_geometry(DESIGN)
    domains = {domain.name: domain for domain in geometry.domains}
    lower = domains["lower_si_grating"]
    upper = domains["upper_si_grating"]
    assert lower.x0 == upper.x0
    assert lower.x1 == upper.x1
    assert lower.height == upper.height
    assert domains["upper_pcm_cap"].z0 == upper.z1
    assert domains["top_sio2_over_pcm"].z0 == domains["upper_pcm_cap"].z1
    assert domains["top_sio2_left"].x1 == domains["upper_pcm_cap"].x0


def test_invalid_duty_cycle():
    design = dict(DESIGN, duty_cycle=1.2)
    try:
        build_geometry(design)
    except GeometryError:
        return
    raise AssertionError("An invalid duty cycle should fail.")


def test_geometry_can_be_rendered():
    if importlib.util.find_spec("matplotlib") is None:
        return
    geometry = build_geometry(DESIGN)
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "geometry.png")
        visualize_geometry(geometry, path)
        assert os.path.getsize(path) > 1000


if __name__ == "__main__":
    test_identical_silicon_gratings()
    test_invalid_duty_cycle()
    test_geometry_can_be_rendered()
    print("geometry tests passed")
