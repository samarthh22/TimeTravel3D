import cv2
import numpy as np

from timetravel3d.geometry import Pose, angles, estimate_relative, project, triangulate


def synthetic():
    rng = np.random.default_rng(17)
    X = rng.uniform([-2, -1, 4], [2, 1, 10], (300, 3))
    K1 = np.array([[800., 0, 320], [0, 820, 240], [0, 0, 1]])
    K2 = np.array([[950., 0, 300], [0, 910, 210], [0, 0, 1]])
    p1 = Pose(np.eye(3), np.zeros(3))
    p2 = Pose(cv2.Rodrigues(np.array([0.02, 0.08, -0.01]))[0], np.array([-1., .03, .02]))
    return X, K1, K2, p1, p2


def test_triangulation_with_different_intrinsics():
    X, K1, K2, p1, p2 = synthetic()
    a, b = project(X, K1, p1)[0], project(X, K2, p2)[0]
    recovered, valid = triangulate(a, b, K1, K2, p1, p2)
    assert valid.all()
    np.testing.assert_allclose(recovered, X, atol=1e-9)
    assert np.max(np.linalg.norm(project(recovered, K2, p2)[0] - b, axis=1)) < 1e-8


def test_essential_pose_direction_and_outliers():
    X, K1, K2, p1, p2 = synthetic()
    a, b = project(X, K1, p1)[0], project(X, K2, p2)[0]
    b[:50] = np.random.default_rng(3).uniform([0, 0], [640, 480], (50, 2))
    cv2.setRNGSeed(22)
    pose, ids, points, _ = estimate_relative(a, b, K1, K2, .5)
    assert len(ids) > 230
    assert np.count_nonzero(ids < 50) < 5
    assert np.linalg.norm(pose.R - p2.R) < .01
    assert np.dot(pose.t, p2.t / np.linalg.norm(p2.t)) > .999
    assert (project(points, K1, p1)[1] > 0).all()


def test_cheirality_and_angle_camera_center():
    K = np.eye(3)
    p1 = Pose(np.eye(3), np.zeros(3))
    p2 = Pose(np.eye(3), np.array([-1., 0, 0]))
    X = np.array([[0., 0, 5], [0., 0, -5]])
    a, b = project(X, K, p1)[0], project(X, K, p2)[0]
    _, valid = triangulate(a, b, K, K, p1, p2)
    assert valid.tolist() == [True, False]
    np.testing.assert_allclose(angles(X[:1], p1.center, p2.center), [np.degrees(np.arctan(.2))])
