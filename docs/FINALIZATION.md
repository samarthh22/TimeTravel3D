# Presentation finalization

## Geometry correction

Minimal-gauge bundle adjustment fixes the first seed pose and the norm of the
second seed translation. The second pose's rotation and translation direction
can now improve. This removes seven similarity degrees of freedom without
locking an inaccurate initial relative pose. The earlier two-fixed-pose BA
remains available via `minimal_gauge_ba: false` for reproducibility.

On the development delivery_area rig subset, median distance to the same
200,000-point scan sample changed from 0.75565 m to 0.09215 m. Camera center
RMSE after alignment changed from 0.04466 m to 0.00430 m. This improvement belongs
to the geometric baseline, not to the proposed confidence filter.

For ETH3D's explicitly rectified stereo input, `configs/rectified.yaml` uses
the acquisition constraint R=I and translation along negative X, with unknown
unit scale. It never reads supplied extrinsics or GT disparity for reconstruction.
Reports label this `rectified_stereo`, not general estimated-pose SfM. The
original essential-matrix estimated-pose mode remains the default two-view mode.
