import cv2
import numpy as np

from timetravel3d.bundle import bundle_adjust
from timetravel3d.cli import DEFAULTS
from timetravel3d.features import Features
from timetravel3d.geometry import Pose, project
from timetravel3d.multiview import reconstruct, register_camera
from timetravel3d.tracks import build_tracks


def problem():
    rng = np.random.default_rng(33)
    X = rng.uniform([-1.5, -1, 4], [1.5, 1, 8], (80, 3))
    K = {v: np.array([[800., 0, 320], [0, 810, 240], [0, 0, 1]]) for v in range(4)}
    poses = {v: Pose(np.eye(3), np.array([-.4 * v, .02 * v, 0])) for v in range(4)}
    xy = {v: project(X, K[v], poses[v])[0] for v in poses}
    return X, K, poses, xy


def test_track_conflicts_are_rejected():
    tracks, conflicts = build_tracks([(0, 1, [(0, 0), (1, 1)]),
                                      (1, 2, [(0, 0), (1, 0)])])
    assert conflicts == 1
    assert sorted(map(len, tracks)) == [2, 3]
    nodes = [(v, k) for t in tracks for v, k in t.items()]
    assert len(nodes) == len(set(nodes))


def test_pnp_outliers_and_pose_direction():
    X, K, poses, xy = problem()
    uv = xy[3].copy()
    uv[:15] += 200
    cv2.setRNGSeed(22)
    pose, inliers = register_camera(X, uv, K[3])
    assert inliers == 65
    np.testing.assert_allclose(pose.t, poses[3].t, atol=1e-5)


def test_bundle_adjustment_reduces_independent_geometric_error():
    X, K, poses, xy = problem()
    rng = np.random.default_rng(11)
    noisy = X + rng.normal(0, .03, X.shape)
    perturbed = dict(poses)
    perturbed[3] = Pose(poses[3].R, poses[3].t + np.array([.03, .03, .01]))
    obs = [[(v, xy[v][pid]) for v in poses] for pid in range(len(X))]
    result, _, report = bundle_adjust(noisy, obs, perturbed, K, {0, 1}, max_nfev=80)
    assert report["accepted"]
    assert report["after_rmse_px"] < report["before_rmse_px"] * .02
    assert np.median(np.linalg.norm(result - X, axis=1)) < .005


def test_four_view_incremental_registration_without_given_poses():
    X, K, _, xy = problem()
    descriptors = np.random.default_rng(12).normal(0, 1, (len(X), 128)).astype(np.float32)
    features = [Features(xy[v], descriptors.copy(), np.full((len(X), 3), 128, np.uint8)) for v in K]
    cv2.setRNGSeed(22)
    result = reconstruct(features, K, DEFAULTS)
    points, _, errors, _, support, _, estimated, details = result
    assert len(estimated) == 4
    assert len(points) == len(X)
    assert (support == 4).all()
    assert np.median(errors) < 1e-4
    assert len(details["registration"]) == 2


def test_minimal_gauge_refines_seed_rotation_and_preserves_scale():
    X, K, poses, xy = problem()
    perturbed = dict(poses)
    perturbed[1] = Pose(cv2.Rodrigues(np.array([.01, .015, 0.]))[0], poses[1].t.copy())
    obs = [[(v, xy[v][pid]) for v in poses] for pid in range(len(X))]
    _, recovered, report = bundle_adjust(X + .01, obs, perturbed, K, {0, 1}, max_nfev=100, minimal_gauge=True)
    assert report['accepted']
    assert report['after_rmse_px'] < report['before_rmse_px'] * .01
    assert np.linalg.norm(recovered[1].t) == __import__('pytest').approx(np.linalg.norm(poses[1].t))
    assert np.linalg.norm(recovered[1].R - np.eye(3)) < .001
