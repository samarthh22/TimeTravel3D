from pathlib import Path

import cv2
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from timetravel3d.evaluation import align_camera_poses, load_scan_samples, read_pfm, stereo_ground_truth
from timetravel3d.geometry import Pose
from timetravel3d.output import write_ply


def test_pfm_vertical_flip_and_big_endian(tmp_path):
    expected = np.array([[1., 2, np.inf], [4, 5, 6]])
    for endian, sign in [("<", -1), (">", 1)]:
        p = tmp_path / f"{sign}.pfm"
        with p.open("wb") as f:
            f.write(f"Pf\n3 2\n{sign}\n".encode())
            f.write(np.flipud(expected).astype(endian + "f4").tobytes())
        np.testing.assert_array_equal(read_pfm(p), expected)


def test_camera_similarity_handles_collinear_centers():
    rotation = Rotation.from_euler("xyz", [.2, -.1, .3]).as_matrix()
    translation, scale = np.array([2., 3, 4]), 2.5
    estimated = {i: Pose(np.eye(3), np.array([-float(i), 0, 0])) for i in range(4)}
    reference = {i: Pose(p.R @ rotation.T, scale * p.t - p.R @ rotation.T @ translation)
                 for i, p in estimated.items()}
    s, R, t, report = align_camera_poses(estimated, reference)
    assert s == pytest.approx(scale)
    np.testing.assert_allclose(R, rotation, atol=1e-12)
    np.testing.assert_allclose(t, translation, atol=1e-12)
    assert report["camera_center_rmse_m"] < 1e-12


def test_scan_alignment_matrix_applied_before_comparison(tmp_path):
    write_ply(tmp_path / "scan1.ply", np.array([[0., 0, 0], [1, 0, 0]]), np.zeros((2, 3), int))
    (tmp_path / "scan_alignment.mlp").write_text('<MeshLabProject><MeshGroup><MLMesh filename="scan1.ply"><MLMatrix44>1 0 0 5 0 1 0 2 0 0 1 3 0 0 0 1</MLMatrix44></MLMesh></MeshGroup></MeshLabProject>')
    sampled, _ = load_scan_samples(tmp_path, 10)
    np.testing.assert_allclose(sampled, [[5, 2, 3], [6, 2, 3]])


def test_stereo_ground_truth_uses_baseline_units_and_nonocclusion_mask(tmp_path):
    (tmp_path / "calib.txt").write_text("cam0=[10 0 1.5; 0 10 1.5; 0 0 1]\ncam1=[10 0 1.5; 0 10 1.5; 0 0 1]\ndoffs=0\nbaseline=100\nwidth=3\nheight=3\n")
    disparity = np.full((3, 3), 2, np.float32)
    with (tmp_path / "disp0GT.pfm").open("wb") as f:
        f.write(b"Pf\n3 3\n-1\n")
        f.write(np.flipud(disparity).tobytes())
    mask = np.full((3, 3), 255, np.uint8)
    mask[0, 0] = 128
    cv2.imwrite(str(tmp_path / "mask0nocc.png"), mask)
    K = np.array([[10., 0, 1], [0, 10, 1], [0, 0, 1]])
    data = {"intrinsics": np.array([K, K]), "names": np.array(["im0.png", "im1.png"]),
        "view_ids": np.array([0, 1]), "obs_view": np.array([0, 0]), "obs_point": np.array([0, 1]),
        "obs_xy": np.array([[1., 1], [0, 0]]), "points": np.array([[0., 0, 5], [-.5, -.5, 5]]),
        "translations": np.array([[0, 0, 0], [-1., 0, 0]])}
    errors, protocol = stereo_ground_truth(data, tmp_path, tmp_path)
    assert errors["point_error_m"][0] == pytest.approx(0.)
    assert np.isnan(errors["point_error_m"][1])
    assert protocol["scale_to_meters"] == pytest.approx(.1)
