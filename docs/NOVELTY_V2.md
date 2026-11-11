# V2: coverage-preserving uncertainty selection

The V1 weighted geometric mean saturated its angle signal at one degree and
used a fixed confidence cutoff. V2 uses a continuous information matrix and a
fixed retained-point budget. The original method and results remain archived.

For every point, stack calibrated projection derivatives with respect to X:
`J = [d(project_1)/dX; ...; d(project_n)/dX]`.
Let `sigma^2 = max(0.5^2, sum(pixel_residual^2)/(2*n-3))`.
The conditional covariance estimate is `C = sigma^2 * inverse(J.T @ J)`.
Rank points by `sqrt(trace(C))`. Derivatives incorporate depth, baseline/ray
geometry and number of observations. Residual variance accounts for image fit.
Degenerate information receives infinite risk rather than misleading certainty.

At the prespecified 80% budget, reserve the lowest-risk representative of each
occupied image grid cell, then fill remaining slots by risk. If cell owners
exceed the budget, use deterministic greedy coverage with uncertainty as a
tie-breaker. All methods get exactly the same ceil(0.8*N) point count. Controls
include raw reprojection, angle and support rankings, uncertainty without
coverage, and the same coverage policy using reprojection or angle instead.

The contribution is this implemented combination and its measured tradeoff for
this course project. Covariance estimation and coverage selection are established
ideas, not a claim of field-level invention. Conditional point covariance ignores
camera uncertainty and systematic pose bias. It is a ranking proxy, not a
calibrated accuracy guarantee. Reference: [Ceres covariance documentation](https://ceres-solver.readthedocs.io/latest/nnls_covariance.html).

`configs/final_protocol.json` freezes parameters before the additional multi-view
evaluation. Development uses the earlier scene subsets; additional multi-view
subsets are withheld for V2, with prior V1 two-view scene exposure explicitly
disclosed. Three seeds assess repeatability on those additional subsets. No GT
enters the selector. `selection.npz` is saved before GT evaluation runs.

Synthetic tests check projection derivatives by finite differences, empirical
Monte Carlo errors, greater uncertainty at longer depths, reduced uncertainty
with more observations, exact budgets and invariance under reconstruction scale.
