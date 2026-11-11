# Recorded ETH3D training experiments

- `results.csv` / `results.json`: 31 scenes/subsets x seven methods = 217 rows.
- `manifest.json`: software/platform, fixed configuration, selected image names,
  analysis commands and alignment/sampling provenance. Baselines were reused
  for the final analysis after fixing the unsaturated angle-ranking control.
- `comparison.png`: independently evaluated multi-view quality and point retention.

Recreate all baselines and analysis, using the repository virtual environment:

```powershell
python scripts/run_benchmarks.py --data-root .. --output results/benchmark --publish-dir benchmarks/measured
python scripts/summarize_results.py
```

No raw images, calibration archives, scans, generated 3D point clouds or
machine-specific environment paths are included. Respect ETH3D's provider terms
when obtaining or redistributing datasets. Dataset-derived plots and metric
tables here document our experimental processing.

See [evaluation protocol](../../docs/EVALUATION.md) and
[measured interpretation](../../docs/RESULTS.md). Undefined values remain null;
failed camera registrations and empty point filters are not hidden.
