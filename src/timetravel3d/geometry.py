"""Core geometry, using world-to-camera [R|t] throughout."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Pose:
    R: np.ndarray
    t: np.ndarray

    @property
    def center(self):
        return -self.R.T @ self.t

    @property
    def matrix(self):
        return np.column_stack((self.R, self.t))


def normalize(xy, K):
    return cv2.undistortPoints(np.asarray(xy, np.float64).reshape(-1, 1, 2), K, None).reshape(-1, 2)


def project(points, K, pose):
    camera = np.asarray(points) @ pose.R.T + pose.t
    with np.errstate(divide="ignore", invalid="ignore"):
        pixel = camera @ K.T
        pixel = pixel[:, :2] / pixel[:, 2:]
    return pixel, camera[:, 2]


def triangulate(xy1, xy2, K1, K2, pose1, pose2):
    a, b = normalize(xy1, K1), normalize(xy2, K2)
    h = cv2.triangulatePoints(pose1.matrix, pose2.matrix, a.T, b.T).T
    points = np.full((len(h), 3), np.nan)
    finite = np.abs(h[:, 3]) > 1e-12
    points[finite] = h[finite, :3] / h[finite, 3:]
    _, z1 = project(points, K1, pose1)
    _, z2 = project(points, K2, pose2)
    valid = np.isfinite(points).all(axis=1) & (z1 > 1e-9) & (z2 > 1e-9)
    return points, valid


def angles(points, center1, center2):
    a, b = points - center1, points - center2
    denom = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
    cosine = np.divide(np.sum(a * b, axis=1), denom, out=np.ones(len(points)), where=denom > 0)
    return np.degrees(np.arccos(np.clip(cosine, -1, 1)))


def estimate_relative(xy1, xy2, K1, K2, threshold_px=1., probability=0.999):
    if len(xy1) < 8:
        raise ValueError(f"Need at least 8 matches, got {len(xy1)}")
    a, b = normalize(xy1, K1), normalize(xy2, K2)
    focal = np.mean([K1[0, 0], K1[1, 1], K2[0, 0], K2[1, 1]])
    E, mask = cv2.findEssentialMat(a, b, np.eye(3), method=cv2.RANSAC,
                                  prob=probability, threshold=threshold_px / focal)
    if E is None or mask is None:
        raise ValueError("Essential matrix estimation failed")
    inliers = np.flatnonzero(mask.ravel() != 0)
    if len(inliers) < 8:
        raise ValueError("Too few essential-matrix inliers")
    identity, best = Pose(np.eye(3), np.zeros(3)), None
    # Explicit cheirality selection avoids recoverPose's default arbitrary
    # far-point cutoff, which can silently exclude low-parallax baseline points.
    for e in np.asarray(E).reshape(-1, 3, 3):
        r1, r2, t = cv2.decomposeEssentialMat(e)
        for R in (r1, r2):
            for sign in (1, -1):
                pose = Pose(R, sign * t.ravel())
                points, valid = triangulate(xy1[inliers], xy2[inliers], K1, K2, identity, pose)
                if best is None or valid.sum() > best[0]:
                    best = (int(valid.sum()), pose, points, valid)
    if best is None or best[0] < 8:
        raise ValueError("No sufficiently supported positive-depth pose")
    _, pose, points, valid = best
    return pose, inliers[valid], points[valid], len(inliers)


def point_metrics(points, observations, poses, intrinsics):
    """Mean pixel residual and maximum pairwise ray angle per 3D track."""
    errors, parallax, support = [], [], []
    for X, obs in zip(points, observations):
        residuals, centers = [], []
        for view_id, xy in obs:
            uv, _ = project(X[None], intrinsics[view_id], poses[view_id])
            residuals.append(np.linalg.norm(uv[0] - xy))
            centers.append(poses[view_id].center)
        maximum = 0.
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                maximum = max(maximum, float(angles(X[None], centers[i], centers[j])[0]))
        errors.append(np.mean(residuals))
        parallax.append(maximum)
        support.append(len(obs))
    return np.array(errors), np.array(parallax), np.array(support, dtype=int)
