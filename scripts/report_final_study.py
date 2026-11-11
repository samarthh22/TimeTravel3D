"""Build the presentation evidence report without hiding failures or weak results."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from timetravel3d.output import write_json


def bootstrap(values):
    a = np.asarray(values)
    if not len(a):
        return [None, None]
    samples = np.random.default_rng(2026).choice(a, (10000, len(a)), replace=True).mean(1)
    return np.quantile(samples, [.025, .975]).tolist()


def main():
    folder = Path('benchmarks/final')
    manifest = json.loads((folder / 'manifest.json').read_text())
    records = manifest['experiments']
    for record in records:
        if record['status'] != 'success':
            baseline_path = Path('results/final') / f"{record['experiment']}_s{record['seed']}" / 'baseline/report.json'
            if baseline_path.is_file():
                baseline = json.loads(baseline_path.read_text())
                record.update(registered_cameras=baseline['registered_cameras'], selected_cameras=baseline['selected_cameras'],
                              reconstruction_completed=True, evaluation_completed=False)
    write_json(folder / 'manifest.json', manifest)
    success = [r for r in records if r['status'] == 'success']
    primary = [r for r in success if r['seed'] == 22]
    held = [r for r in primary if r['split'] == 'held_out_multiview']
    def mapping(record):
        return {r['method']: r for r in record['rows']}
    def reduction(record, comparator='baseline'):
        m = mapping(record)
        a, b = m[comparator]['median_point_error_m'], m['coverage_uncertainty']['median_point_error_m']
        return 100 * (a - b) / a if a and b is not None else None
    eligible = [r for r in held if reduction(r) is not None]
    improvements = [reduction(r) for r in eligible]
    reproj = [reduction(r, 'reprojection_budget') for r in eligible]
    synth = json.loads(Path('benchmarks/synthetic/results.json').read_text())
    synth_mean = {method: float(np.mean([r['median_point_error_m'] for r in synth if r['method'] == method])) for method in mapping(success[0])}
    synthetic_reduction = 100 * (1 - synth_mean['coverage_uncertainty'] / synth_mean['baseline'])
    synthetic_vs_reprojection = 100 * (1 - synth_mean['coverage_uncertainty'] / synth_mean['reprojection_budget'])
    summary = {'attempted_runs': len(records), 'successful_runs': len(success), 'failed_runs': len(records) - len(success),
        'primary_successful_subsets': len(primary), 'heldout_primary_eligible': len(eligible),
        'heldout_wins_vs_baseline': sum(v > 0 for v in improvements),
        'heldout_mean_reduction_percent_vs_baseline': float(np.mean(improvements)) if improvements else None,
        'heldout_bootstrap_ci95_mean_reduction': bootstrap(improvements),
        'heldout_wins_vs_equal_budget_reprojection': sum(v > 0 for v in reproj),
        'heldout_mean_reduction_percent_vs_equal_budget_reprojection': float(np.mean(reproj)) if reproj else None,
        'primary_median_grid_retention': float(np.median([mapping(r)['coverage_uncertainty']['grid_coverage_retention'] for r in primary])),
        'synthetic_mean_of_seed_medians_m': synth_mean,
        'synthetic_reduction_vs_baseline_percent': synthetic_reduction,
        'synthetic_reduction_vs_equal_budget_reprojection_percent': synthetic_vs_reprojection,
        'failures': [{'experiment': r['experiment'], 'seed': r['seed'], 'error': r.get('error')} for r in records if r['status'] != 'success']}
    write_json(folder / 'summary.json', summary)
    lines = ['# Final study and presentation evidence', '',
        f"**{len(success)}/{len(records)} runs completed.** Every supplied scene was attempted using bounded subsets: 27 stereo pairs, 5 rig scenes and 13 DSLR scenes. Twelve additional multi-view subsets received three seeds. This does not process every multi-view image.", '',
        '## Defensible contribution', '',
        'V2 combines continuous conditional point uncertainty with a spatial coverage reservation policy. It retains exactly ceil(80% of baseline points). Ground truth never enters scoring or selection. The original V1 method/results remain available.', '',
        f"Controlled Gaussian-noise validation: mean of ten seed-level median 3D errors fell **{synthetic_reduction:.2f}%** against retaining all points and **{synthetic_vs_reprojection:.2f}%** against the same-budget reprojection ranking.", '',
        f"On eligible held-out V2 multi-view subsets at seed 22, the proposal improved median sampled-scan distance on **{sum(v>0 for v in improvements)}/{len(eligible)}** subsets versus the full baseline and **{sum(v>0 for v in reproj)}/{len(eligible)}** versus equal-budget reprojection ranking. Mean relative change versus baseline: **{np.mean(improvements):.2f}%**. Positive means lower distance.", '',
        f"Median retained image-grid coverage across primary successful subsets: **{summary['primary_median_grid_retention']*100:.1f}%**. Coverage refers to occupied baseline image cells, not dense surface completeness.", '',
        'The controlled study supports the mechanism under its noise assumptions. Real-scene results define a narrower empirical contribution and do not prove universal superiority or field-level novelty. Camera bias can dominate conditional point uncertainty.', '',
        '## Primary results at seed 22', '',
        '| Subset | Split | Cameras | Baseline points | Selected points | Baseline error (m) | Proposed error (m) | Reduction (%) | Grid retained (%) |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for record in primary:
        m = mapping(record); b, p = m['baseline'], m['coverage_uncertainty']
        fmt = lambda v: 'undefined' if v is None else f'{v:.4f}'
        lines.append(f"| {record['experiment']} | {record['split']} | {record['registered_cameras']}/{record['selected_cameras']} | {b['retained_points']} | {p['retained_points']} | {fmt(b['median_point_error_m'])} | {fmt(p['median_point_error_m'])} | {fmt(reduction(record))} | {p['grid_coverage_retention']*100:.1f} |")
    lines += ['', '## Every attempted failure', '']
    for r in summary['failures']:
        lines.append(f"- {r['experiment']}, seed {r['seed']}: {r['error']}")
    lines += ['', '## Repeated-seed checks', '', '| Subset | Completed seeds | Proposal reduction vs baseline (%) |', '|---|---|---|']
    for name in sorted({r['experiment'] for r in records if r['split'] == 'held_out_multiview'}):
        group = [r for r in success if r['experiment'] == name]
        values = [reduction(r) for r in group]
        lines.append(f"| {name} | {', '.join(str(r['seed']) for r in group) or 'none'} | {', '.join('undefined' if v is None else f'{v:.2f}' for v in values) or 'not evaluable'} |")
    lines += ['', 'Seeds assess repeatability within a scene. They are not independent new scenes and are not pooled as such for uncertainty intervals. RANSAC results can be identical across seeds on easy scenes.', '',
        '## Scope and limitations', '',
        '- Stereo results use the declared rectified acquisition constraint and are labeled rectified_stereo. General estimated-pose results remain in the V1 archive.',
        '- Multi-view results estimate camera poses and use minimal-gauge BA. Some registrations can remain incomplete. Reported scan distance uses a fixed 500,000-point sample after camera-pose alignment.',
        '- V1 used all two-view scenes. Additional multi-view subsets were withheld from V2 development, but some physical scenes were previously seen in V1 stereo experiments. This is not a pristine external test set.',
        '- Grid bounds and denominators stay frozen. Equal-count residual, raw angle, support and coverage-matched controls appear in the full CSV.',
        '- Bootstrap intervals in summary.json resample the eligible primary held-out subsets. The small, related subset collection limits statistical/generalization claims.',
        '- Synthetic cameras and correspondences are known. That study tests measurement uncertainty rather than SIFT mismatches or camera estimation.', '',
        '## Reproduce', '', '```powershell', 'python scripts/run_final_study.py', 'python scripts/synthetic_study.py', 'python scripts/report_final_study.py', '```', '',
        'Protocol: configs/final_protocol.json. Detailed rows, failures, source revisions and selected images: benchmarks/final/manifest.json. Earlier measurements: benchmarks/measured/.', '']
    Path('docs/FINAL_RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')

    methods = ['baseline', 'reprojection_budget', 'angle_budget', 'support_budget', 'coverage_uncertainty']
    labels = ['All points', 'Residual', 'Angle', 'Support', 'Proposed']
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    means = [synth_mean[m] * 100 for m in methods]
    ax.bar(labels, means, color=['#8091a5']*4 + ['#087e8b'])
    ax.set(ylabel='Mean of seed median 3D errors (cm)', title='Controlled noise study: every filter retains 80%')
    for i, y in enumerate(means): ax.text(i, y + .15, f'{y:.2f}', ha='center')
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(); fig.savefig(folder / 'synthetic_comparison.png', dpi=180); plt.close(fig)
    if eligible:
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.axhline(0, color='#64748b', lw=1)
        ax.bar(np.arange(len(eligible)), improvements, color=['#087e8b' if v>=0 else '#a34949' for v in improvements])
        ax.set_xticks(np.arange(len(eligible)), [r['experiment'] for r in eligible], rotation=35, ha='right')
        ax.set(ylabel='Median scan-distance reduction (%)', title='All eligible V2 held-out multi-view subsets, seed 22')
        ax.spines[['top','right']].set_visible(False)
        fig.tight_layout(); fig.savefig(folder / 'heldout_comparison.png', dpi=180); plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
