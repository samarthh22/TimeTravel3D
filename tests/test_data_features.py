import cv2
import numpy as np
import pytest

from timetravel3d.data import read_cameras, read_views
from timetravel3d.features import extract, match


def test_empty_colmap_observation_lines_and_noncontiguous_ids(tmp_path):
    (tmp_path / "cameras.txt").write_text("# cameras\n7 PINHOLE 640 480 800 810 320.5 240.5\n")
    (tmp_path / "a.png").touch()
    (tmp_path / "b.png").touch()
    (tmp_path / "images.txt").write_text("# poses\n9 1 0 0 0 0 0 0 7 a.png\n\n15 1 0 0 0 -1 0 0 7 b.png\n\n")
    cams = read_cameras(tmp_path / "cameras.txt")
    views = read_views(tmp_path / "images.txt", tmp_path)
    assert [v.id for v in views] == [9, 15]
    assert cams[7].K[0, 2] == 320
    np.testing.assert_allclose(views[1].center, [1, 0, 0])


def test_reject_distortion_instead_of_guessing(tmp_path):
    p = tmp_path / "cameras.txt"
    p.write_text("1 OPENCV 640 480 800 800 320 240 0 0 0 0\n")
    with pytest.raises(ValueError, match="Unsupported camera"):
        read_cameras(p)


def test_sift_recovers_image_translation():
    rng = np.random.default_rng(4)
    image = rng.integers(0, 256, (360, 480, 3), dtype=np.uint8)
    translated = cv2.warpAffine(image, np.float32([[1, 0, 12], [0, 1, 7]]), (480, 360))
    a, b = extract(image), extract(translated)
    pairs = match(a, b)
    assert len(pairs) > 40
    np.testing.assert_allclose(np.median(b.xy[pairs[:, 1]] - a.xy[pairs[:, 0]], axis=0), [12, 7], atol=.1)


def test_blank_image_graceful_empty_matches():
    f = extract(np.zeros((80, 80, 3), np.uint8))
    assert match(f, f).shape == (0, 2)
