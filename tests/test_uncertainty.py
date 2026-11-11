import numpy as np

from timetravel3d.geometry import Pose, project, triangulate
from timetravel3d.uncertainty import projection_jacobian, positional_uncertainty, coverage_mask, budget_mask


def fixture():
    X = np.array([[0., 0, 3], [.4, .2, 6], [-.3, -.1, 12]])
    K = np.array([[800., 0, 320], [0, 800, 240], [0, 0, 1]])
    poses = [Pose(np.eye(3), np.array([x, 0., 0.])) for x in [0., -1., 1.]]
    return X, K, poses


def archive(views=2):
    X, K, poses = fixture()
    return {'points': X, 'view_ids': np.arange(views), 'rotations': np.array([p.R for p in poses[:views]]),
        'translations': np.array([p.t for p in poses[:views]]), 'intrinsics': np.array([K] * views),
        'obs_view': np.repeat(np.arange(views), 3), 'obs_point': np.tile(np.arange(3), views),
        'obs_xy': np.concatenate([project(X, K, p)[0] for p in poses[:views]])}


def test_projection_derivative_against_finite_difference():
    X, K, poses = fixture()
    p = poses[1]
    numerical = np.column_stack([(project(X[:1] + np.eye(3)[i] * 1e-6, K, p)[0][0] -
        project(X[:1] - np.eye(3)[i] * 1e-6, K, p)[0][0]) / 2e-6 for i in range(3)])
    np.testing.assert_allclose(projection_jacobian(X[0], p.R, p.t, K), numerical, atol=1e-6)


def test_covariance_tracks_depth_and_additional_views():
    risk = positional_uncertainty(archive(2))
    assert np.all(np.diff(risk) > 0)
    assert np.all(positional_uncertainty(archive(3)) < risk)


def test_coverage_budget_and_scale_invariance():
    a = archive()
    risk = positional_uncertainty(a)
    scaled = dict(a, points=a['points'] * 5, translations=a['translations'] * 5)
    np.testing.assert_allclose(positional_uncertainty(scaled), risk * 5, rtol=1e-8)
    assert coverage_mask(a, risk, .7).sum() == budget_mask(risk, .7).sum() == 3
    np.testing.assert_array_equal(coverage_mask(a, risk, .5), coverage_mask(scaled, risk * 5, .5))


def test_uncertainty_correlates_with_actual_noise_error():
    X, K, poses = fixture()
    rng = np.random.default_rng(92)
    errors = []
    for _ in range(200):
        a = project(X, K, poses[0])[0] + rng.normal(0, .5, (3, 2))
        b = project(X, K, poses[1])[0] + rng.normal(0, .5, (3, 2))
        recovered, _ = triangulate(a, b, K, K, *poses[:2])
        errors.append(np.linalg.norm(recovered - X, axis=1))
    empirical = np.sqrt(np.mean(np.array(errors) ** 2, axis=0))
    np.testing.assert_allclose(empirical, positional_uncertainty(archive()), rtol=.2)
