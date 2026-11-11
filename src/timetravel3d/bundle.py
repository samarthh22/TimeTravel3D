"""Sparse robust BA, fixed intrinsics, two fixed seed poses for the gauge.

This also fixes the initial relative pose: a practical constrained BA rather
than COLMAP's full gauge-minimal global optimizer.
"""
import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

from .geometry import Pose


def bundle_adjust(points, observations, poses, intrinsics, fixed, max_nfev=40):
    movable = [v for v in sorted(poses) if v not in fixed]
    camera_index = {v: i for i, v in enumerate(movable)}
    initial_cameras = np.array([np.r_[cv2.Rodrigues(poses[v].R)[0].ravel(), poses[v].t]
                                for v in movable]).reshape(-1)
    ncam = len(initial_cameras)
    initial = np.r_[initial_cameras, np.asarray(points).reshape(-1)]
    obs_point, obs_view, obs_xy = [], [], []
    for pid, obs in enumerate(observations):
        for v, xy in obs:
            obs_point.append(pid)
            obs_view.append(v)
            obs_xy.append(xy)
    obs_point, obs_view, obs_xy = np.array(obs_point), np.array(obs_view), np.array(obs_xy)
    if len(obs_point) == 0:
        raise ValueError("Bundle adjustment needs observations")
    groups = {v: np.flatnonzero(obs_view == v) for v in poses}

    def unpack(x):
        cameras = dict(poses)
        for v, idx in camera_index.items():
            params = x[idx * 6:idx * 6 + 6]
            cameras[v] = Pose(cv2.Rodrigues(params[:3])[0], params[3:6])
        return x[ncam:].reshape(-1, 3), cameras

    def residuals(x):
        xyz, cameras = unpack(x)
        predicted = np.empty_like(obs_xy, dtype=float)
        for v, ids in groups.items():
            camera = xyz[obs_point[ids]] @ cameras[v].R.T + cameras[v].t
            pixel = camera @ intrinsics[v].T
            z = np.where(np.abs(pixel[:, 2:]) < 1e-9, 1e-9, pixel[:, 2:])
            predicted[ids] = pixel[:, :2] / z
        return (predicted - obs_xy).ravel()

    sparsity = lil_matrix((len(obs_point) * 2, len(initial)), dtype=int)
    for k, (pid, v) in enumerate(zip(obs_point, obs_view)):
        sparsity[2 * k:2 * k + 2, ncam + 3 * pid:ncam + 3 * pid + 3] = 1
        if v in camera_index:
            idx = camera_index[v] * 6
            sparsity[2 * k:2 * k + 2, idx:idx + 6] = 1
    before = residuals(initial)
    result = least_squares(residuals, initial, jac_sparsity=sparsity.tocsr(),
                           loss="soft_l1", f_scale=1., x_scale="jac",
                           max_nfev=max_nfev, ftol=1e-5, xtol=1e-5, gtol=1e-5)
    robust_cost = lambda r: float(np.sum(np.sqrt(1 + r * r) - 1))
    accepted = bool(np.isfinite(result.x).all() and robust_cost(result.fun) <= robust_cost(before))
    xyz, cameras = unpack(result.x if accepted else initial)
    return xyz, cameras, {"enabled": True, "accepted": accepted,
        "converged": bool(result.success), "function_evaluations": result.nfev,
        "before_rmse_px": float(np.sqrt(np.mean(before ** 2))),
        "after_rmse_px": float(np.sqrt(np.mean(residuals(result.x if accepted else initial) ** 2))),
        "fixed_views": sorted(fixed), "message": result.message}
