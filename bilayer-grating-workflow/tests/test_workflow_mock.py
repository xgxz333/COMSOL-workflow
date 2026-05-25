import copy
import importlib.util
import json
import os
import sys
import tempfile

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.backends import AnalyticMockBackend
from bilayer_workflow.workflow import evaluate_candidate, run_search


def config():
    path = os.path.join(os.path.dirname(__file__), "..", "configs", "default_search.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_candidate_evaluation_saves_outputs():
    settings = config()
    with tempfile.TemporaryDirectory() as directory:
        result = evaluate_candidate({}, settings, AnalyticMockBackend(), directory)
        assert result["attrs"]["valid_geometry"]
        if importlib.util.find_spec("matplotlib") is not None:
            assert os.path.exists(os.path.join(directory, "geometry.png"))
        assert os.path.exists(os.path.join(directory, "amorphous", "modes.csv"))


def test_short_mock_search():
    settings = copy.deepcopy(config())
    settings["optimization"]["method"] = "Random"
    settings["optimization"]["iterations"] = 2
    settings["optimization"]["batch_size"] = 2
    with tempfile.TemporaryDirectory() as directory:
        best = run_search(settings, AnalyticMockBackend(), directory)
        assert best is not None
        assert os.path.exists(os.path.join(directory, "history.csv"))
        if importlib.util.find_spec("matplotlib") is not None:
            assert os.path.exists(os.path.join(directory, "progress.png"))


if __name__ == "__main__":
    test_candidate_evaluation_saves_outputs()
    test_short_mock_search()
    print("mock workflow tests passed")
