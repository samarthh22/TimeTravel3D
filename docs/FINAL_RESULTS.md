# Final study and presentation evidence

**66/69 runs completed.** Every supplied scene was attempted using bounded subsets: 27 stereo pairs, 5 rig scenes and 13 DSLR scenes. Twelve additional multi-view subsets received three seeds. This does not process every multi-view image.

## Defensible contribution

V2 combines continuous conditional point uncertainty with a spatial coverage reservation policy. It retains exactly ceil(80% of baseline points). Ground truth never enters scoring or selection. The original V1 method/results remain available.

Controlled Gaussian-noise validation: mean of ten seed-level median 3D errors fell **29.64%** against retaining all points and **16.39%** against the same-budget reprojection ranking.

On eligible held-out V2 multi-view subsets at seed 22, the proposal improved median sampled-scan distance on **9/11** subsets versus the full baseline and **6/11** versus equal-budget reprojection ranking. Mean relative change versus baseline: **11.96%**. Positive means lower distance.

Median retained image-grid coverage across primary successful subsets: **100.0%**. Coverage refers to occupied baseline image cells, not dense surface completeness.

The controlled study supports the mechanism under its noise assumptions. Real-scene results define a narrower empirical contribution and do not prove universal superiority or field-level novelty. Camera bias can dominate conditional point uncertainty.

## Primary results at seed 22

| Subset | Split | Cameras | Baseline points | Selected points | Baseline error (m) | Proposed error (m) | Reduction (%) | Grid retained (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dslr_courtyard | development | 6/6 | 3465 | 2772 | 0.0229 | 0.0222 | 3.1641 | 100.0 |
| dslr_delivery_area | development | 6/6 | 1225 | 980 | 0.0159 | 0.0153 | 4.0606 | 100.0 |
| dslr_electro | development | 6/6 | 883 | 707 | 0.0378 | 0.0325 | 14.0523 | 100.0 |
| dslr_facade | held_out_multiview | 6/6 | 2291 | 1833 | 0.1404 | 0.1281 | 8.7383 | 100.0 |
| dslr_kicker | held_out_multiview | 5/6 | 936 | 749 | 0.0230 | 0.0210 | 8.6610 | 100.0 |
| dslr_meadow | development | 5/6 | 238 | 191 | 0.1411 | 0.1081 | 23.3578 | 100.0 |
| dslr_office | held_out_multiview | 5/6 | 154 | 124 | 0.0218 | 0.0200 | 8.0897 | 100.0 |
| dslr_pipes | held_out_multiview | 3/6 | 236 | 189 | 0.0131 | 0.0120 | 8.9196 | 100.0 |
| dslr_playground | held_out_multiview | 6/6 | 815 | 652 | 0.0499 | 0.0311 | 37.7190 | 100.0 |
| dslr_relief | held_out_multiview | 6/6 | 1852 | 1482 | 0.0110 | 0.0103 | 6.4655 | 100.0 |
| dslr_relief_2 | held_out_multiview | 6/6 | 1694 | 1356 | 0.0180 | 0.0173 | 3.5399 | 100.0 |
| dslr_terrace | held_out_multiview | 6/6 | 890 | 712 | 0.1155 | 0.0706 | 38.9199 | 100.0 |
| dslr_terrains | held_out_multiview | 6/6 | 665 | 532 | 0.0306 | 0.0307 | -0.2686 | 100.0 |
| rig_delivery_area | development | 5/5 | 562 | 450 | 0.0761 | 0.0662 | 13.0334 | 100.0 |
| rig_electro | development | 5/5 | 276 | 221 | 0.0258 | 0.0216 | 16.2629 | 100.0 |
| rig_forest | held_out_multiview | 5/5 | 1654 | 1324 | 0.0119 | 0.0102 | 14.5038 | 100.0 |
| rig_terrains | held_out_multiview | 5/5 | 347 | 278 | 0.0141 | 0.0146 | -3.7220 | 100.0 |
| two_view_delivery_area_1l | development_stereo | 2/2 | 311 | 249 | 0.1626 | 0.1494 | 8.1163 | 100.0 |
| two_view_delivery_area_1s | development_stereo | 2/2 | 482 | 386 | 0.0530 | 0.0450 | 15.2142 | 100.0 |
| two_view_delivery_area_2l | development_stereo | 2/2 | 329 | 264 | 0.3497 | 0.2142 | 38.7646 | 100.0 |
| two_view_delivery_area_2s | development_stereo | 2/2 | 307 | 246 | 0.1608 | 0.1325 | 17.6131 | 100.0 |
| two_view_delivery_area_3l | development_stereo | 2/2 | 230 | 184 | 0.3549 | 0.2732 | 23.0238 | 100.0 |
| two_view_delivery_area_3s | development_stereo | 2/2 | 268 | 215 | 0.4842 | 0.4156 | 14.1739 | 100.0 |
| two_view_electro_1l | development_stereo | 2/2 | 595 | 476 | 0.0662 | 0.0605 | 8.6525 | 100.0 |
| two_view_electro_1s | development_stereo | 2/2 | 497 | 398 | 0.0170 | 0.0150 | 11.9422 | 100.0 |
| two_view_electro_2l | development_stereo | 2/2 | 475 | 380 | 0.2393 | 0.2393 | 0.0000 | 100.0 |
| two_view_electro_2s | development_stereo | 2/2 | 168 | 135 | 0.1223 | 0.1200 | 1.9107 | 100.0 |
| two_view_electro_3l | development_stereo | 2/2 | 142 | 114 | 0.1437 | 0.1437 | 0.0000 | 100.0 |
| two_view_electro_3s | development_stereo | 2/2 | 119 | 96 | 0.0262 | 0.0262 | 0.0000 | 100.0 |
| two_view_facade_1s | development_stereo | 2/2 | 612 | 490 | 0.8449 | 0.6877 | 18.6031 | 100.0 |
| two_view_forest_1s | development_stereo | 2/2 | 1226 | 981 | 0.0336 | 0.0329 | 2.2151 | 100.0 |
| two_view_forest_2s | development_stereo | 2/2 | 1131 | 905 | 0.0323 | 0.0291 | 9.8003 | 100.0 |
| two_view_playground_1l | development_stereo | 2/2 | 572 | 458 | 0.3229 | 0.3229 | 0.0000 | 100.0 |
| two_view_playground_1s | development_stereo | 2/2 | 574 | 460 | 0.1760 | 0.1760 | 0.0000 | 100.0 |
| two_view_playground_2l | development_stereo | 2/2 | 510 | 408 | 0.1418 | 0.1316 | 7.1897 | 100.0 |
| two_view_playground_2s | development_stereo | 2/2 | 274 | 220 | 0.0659 | 0.0605 | 8.2355 | 100.0 |
| two_view_playground_3l | development_stereo | 2/2 | 1039 | 832 | 0.0365 | 0.0363 | 0.4158 | 100.0 |
| two_view_playground_3s | development_stereo | 2/2 | 1070 | 856 | 0.0204 | 0.0201 | 1.7145 | 100.0 |
| two_view_terrace_1s | development_stereo | 2/2 | 488 | 391 | 2.5934 | 1.7060 | 34.2205 | 100.0 |
| two_view_terrace_2s | development_stereo | 2/2 | 481 | 385 | 0.0413 | 0.0376 | 8.8742 | 100.0 |
| two_view_terrains_1l | development_stereo | 2/2 | 448 | 359 | 0.0080 | 0.0077 | 3.7392 | 100.0 |
| two_view_terrains_1s | development_stereo | 2/2 | 700 | 560 | 0.0051 | 0.0052 | -2.5479 | 100.0 |
| two_view_terrains_2l | development_stereo | 2/2 | 156 | 125 | 0.0169 | 0.0170 | -0.8948 | 100.0 |
| two_view_terrains_2s | development_stereo | 2/2 | 149 | 120 | 0.0043 | 0.0042 | 1.9638 | 100.0 |

## Every attempted failure

- rig_playground, seed 12: ValueError: Nonpositive camera-alignment scale
- rig_playground, seed 22: ValueError: Nonpositive camera-alignment scale
- rig_playground, seed 32: ValueError: Nonpositive camera-alignment scale

## Repeated-seed checks

| Subset | Completed seeds | Proposal reduction vs baseline (%) |
|---|---|---|
| dslr_facade | 12, 22, 32 | 8.74, 8.74, 8.74 |
| dslr_kicker | 12, 22, 32 | 8.66, 8.66, 8.66 |
| dslr_office | 12, 22, 32 | 8.09, 8.09, 8.09 |
| dslr_pipes | 12, 22, 32 | 8.92, 8.92, 8.92 |
| dslr_playground | 12, 22, 32 | 37.72, 37.72, 37.72 |
| dslr_relief | 12, 22, 32 | 6.47, 6.47, 6.47 |
| dslr_relief_2 | 12, 22, 32 | 3.54, 3.54, 3.54 |
| dslr_terrace | 12, 22, 32 | 38.92, 38.92, 38.92 |
| dslr_terrains | 12, 22, 32 | -0.27, -0.27, -0.27 |
| rig_forest | 12, 22, 32 | 14.50, 14.50, 14.50 |
| rig_playground | none | not evaluable |
| rig_terrains | 12, 22, 32 | -3.72, -3.72, -3.72 |

Seeds assess repeatability within a scene. They are not independent new scenes and are not pooled as such for uncertainty intervals. RANSAC results can be identical across seeds on easy scenes.

## Scope and limitations

- Stereo results use the declared rectified acquisition constraint and are labeled rectified_stereo. General estimated-pose results remain in the V1 archive.
- Multi-view results estimate camera poses and use minimal-gauge BA. Some registrations can remain incomplete. Reported scan distance uses a fixed 500,000-point sample after camera-pose alignment.
- V1 used all two-view scenes. Additional multi-view subsets were withheld from V2 development, but some physical scenes were previously seen in V1 stereo experiments. This is not a pristine external test set.
- Grid bounds and denominators stay frozen. Equal-count residual, raw angle, support and coverage-matched controls appear in the full CSV.
- Bootstrap intervals in summary.json resample the eligible primary held-out subsets. The small, related subset collection limits statistical/generalization claims.
- Synthetic cameras and correspondences are known. That study tests measurement uncertainty rather than SIFT mismatches or camera estimation.

## Reproduce

```powershell
python scripts/run_final_study.py
python scripts/synthetic_study.py
python scripts/report_final_study.py
```

Protocol: configs/final_protocol.json. Detailed rows, failures, source revisions and selected images: benchmarks/final/manifest.json. Earlier measurements: benchmarks/measured/.
