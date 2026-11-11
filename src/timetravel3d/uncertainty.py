"""Conditional point covariance and coverage-preserving confidence selection.

Covariance conditions on fixed cameras. It cannot measure systematic pose bias.
No ground truth or learned thresholds enter scoring or selection.
"""
import numpy as np


def projection_jacobian(point, R, t, K):
    camera = R @ point + t
    q = K @ camera
    if q[2] <= 1e-12:
        return np.full((2, 3), np.nan)
    return np.vstack([(K[i] * q[2] - q[i] * K[2]) / q[2] ** 2 for i in range(2)]) @ R


def positional_uncertainty(data, noise_floor_px=.5):
    if noise_floor_px <= 0:
        raise ValueError("Noise floor must be positive")
    count = len(data['points'])
    information = np.zeros((count, 3, 3))
    squared_error = np.zeros(count)
    observations = np.zeros(count, int)
    for v, R, t, K in zip(data['view_ids'], data['rotations'], data['translations'], data['intrinsics']):
        rows = np.flatnonzero(data['obs_view'] == v)
        pids = data['obs_point'][rows]
        X = data['points'][pids]
        q = (X @ R.T + t) @ K.T
        z = q[:, 2]
        J = np.stack([(K[i][None] * z[:, None] - q[:, i, None] * K[2][None]) / z[:, None] ** 2 for i in range(2)], axis=1) @ R
        np.add.at(information, pids, np.einsum('nki,nkj->nij', J, J))
        np.add.at(squared_error, pids, np.sum((q[:, :2] / z[:, None] - data['obs_xy'][rows]) ** 2, axis=1))
        np.add.at(observations, pids, 1)
    eigenvalues = np.linalg.eigvalsh(information)
    valid = (eigenvalues[:, 0] > np.maximum(eigenvalues[:, -1] * 1e-12, 1e-15)) & (observations >= 2)
    sigma2 = np.maximum(noise_floor_px ** 2, squared_error / np.maximum(2 * observations - 3, 1))
    risk = np.full(count, np.inf)
    risk[valid] = np.sqrt(sigma2[valid] * np.sum(1 / eigenvalues[valid], axis=1))
    return risk


def point_cells(data, bins=10):
    cells = [set() for _ in data['points']]
    for v in data['view_ids']:
        rows = np.flatnonzero(data['obs_view'] == v)
        if not len(rows):
            continue
        xy = data['obs_xy'][rows]
        indices = np.floor((xy - xy.min(0)) / np.maximum(np.ptp(xy, axis=0), 1e-9) * bins).astype(int).clip(0, bins - 1)
        for row, (x, y) in zip(rows, indices):
            cells[data['obs_point'][row]].add((int(v), int(x), int(y)))
    return cells


def budget_mask(risk, fraction):
    if not 0 < fraction <= 1:
        raise ValueError("Retention fraction must be in (0,1]")
    mask = np.zeros(len(risk), bool)
    count = max(1, int(np.ceil(len(risk) * fraction))) if len(risk) else 0
    mask[np.argsort(risk, kind='stable')[:count]] = True
    return mask


def coverage_mask(data, risk, fraction=.8):
    """Reserve the safest representative per occupied cell, then fill by risk.

    If representatives exceed the budget, greedy uncovered-cell gain determines
    coverage selection, breaking ties by uncertainty. Never consult evaluation.
    """
    mask = budget_mask(risk, fraction)
    budget = int(mask.sum())
    cells = point_cells(data)
    order = np.argsort(risk, kind='stable')
    owners = {}
    for pid in order:
        for cell in sorted(cells[pid]):
            owners.setdefault(cell, int(pid))
    representatives = set(owners.values())
    if len(representatives) <= budget:
        selected = representatives
    else:
        selected, covered = set(), set()
        for _ in range(budget):
            choices = [p for p in representatives if p not in selected]
            best = max(choices, key=lambda p: (len(cells[p] - covered), -risk[p], -p))
            selected.add(best)
            covered.update(cells[best])
    for pid in order:
        if len(selected) >= budget:
            break
        selected.add(int(pid))
    mask[:] = False
    mask[list(selected)] = True
    return mask


def variants(data, fraction=.8, noise_floor_px=.5):
    risk = positional_uncertainty(data, noise_floor_px)
    return risk, {
        'baseline': np.ones(len(risk), bool),
        'reprojection_budget': budget_mask(data['errors'], fraction),
        'angle_budget': budget_mask(-data['angles'], fraction),
        'support_budget': budget_mask(-data['support'].astype(float), fraction),
        'uncertainty_budget': budget_mask(risk, fraction),
        'coverage_uncertainty': coverage_mask(data, risk, fraction),
        'coverage_reprojection': coverage_mask(data, data['errors'], fraction),
        'coverage_angle': coverage_mask(data, -data['angles'], fraction)}
