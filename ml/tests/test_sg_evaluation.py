import importlib.util
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "sg_eval", Path(__file__).parents[1] / "scripts/evaluate_sg_detector.py"
)
sg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sg)


def test_matching_never_counts_two_predictions_for_one_plate():
    truth = np.array([[0, 0, 10, 10]])
    predictions = np.array([[0, 0, 10, 10], [1, 1, 9, 9], [20, 20, 30, 30]])
    assert sg.matched_plates(truth, predictions) == 1


def test_polygon_and_box_labels_have_the_same_enclosing_box(tmp_path):
    labels = tmp_path / "labels.txt"
    labels.write_text("0 .5 .5 .4 .2\n0 .3 .4 .7 .4 .7 .6 .3 .6")
    np.testing.assert_allclose(
        sg.read_labels(labels, 100, 100), [[30, 40, 70, 60], [30, 40, 70, 60]]
    )


@pytest.mark.parametrize(
    "name", ["../escape.jpg", "/escape.jpg", "C:/escape.jpg", "test\\images\\escape.jpg"]
)
def test_unsafe_archive_members_are_rejected(name):
    with pytest.raises(ValueError):
        sg.safe_member(name)


def test_archive_prefers_test_extracts_only_that_split_and_preserves_original(tmp_path):
    archive = tmp_path / "sg.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("data.yaml", "nc: 1\nnames: ['license-plate']")
        for split in ["train", "valid", "test"]:
            zipped.writestr(f"{split}/images/image.jpg", b"fixture")
            zipped.writestr(f"{split}/labels/image.txt", "0 .5 .5 .4 .2")
    before = sg.digest(archive)
    root, split, metadata = sg.prepare_dataset(archive, tmp_path / "out")
    assert split == "test"
    assert not (root / "train").exists()
    assert (root / "test/images/image.jpg").exists()
    assert sg.digest(archive) == before == metadata["archive_sha256"]


def test_training_only_archive_is_not_presented_as_held_out(tmp_path):
    archive = tmp_path / "sg.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("data.yaml", "nc: 1\nnames: ['license-plate']")
        zipped.writestr("train/images/image.jpg", b"fixture")
    with pytest.raises(ValueError, match="no provided test/valid"):
        sg.prepare_dataset(archive, tmp_path / "out")
