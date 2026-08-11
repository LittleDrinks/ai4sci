import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dataset import load_dataset
from eval import evaluate_representation, representations


def test_reuses_prototype_dataset():
    dataset = load_dataset()
    assert len(dataset["artifacts"]) == 7
    assert len(dataset["events"]) == 14
    assert dataset["events"][0]["id"] == "evt-01"


def test_all_representations_are_complete():
    dataset = load_dataset()
    results = [evaluate_representation(rep, dataset) for rep in representations(dataset)]
    assert all(result["passed"] for result in results)
