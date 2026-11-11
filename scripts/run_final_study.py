"""Run frozen V2 protocol across every supplied scene, with repeated holdout seeds."""
import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from timetravel3d.experiments import write_csv
from timetravel3d.output import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('..'))
    parser.add_argument('--output', type=Path, default=Path('results/final'))
    parser.add_argument('--publish', type=Path, default=Path('benchmarks/final'))
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error('Use the virtual environment')
    protocol_path = Path('configs/final_protocol.json')
    protocol = json.loads(protocol_path.read_text())
    digest = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    jobs = []
    for scene in sorted((args.data_root / 'two_view_training').iterdir()):
        if scene.is_dir():
            jobs.append(('two_view_' + scene.name, 'two-view', scene, args.data_root / 'two_view_training_gt' / scene.name, [], 22, 'development_stereo'))
    for category in ['rig', 'dslr']:
        for scene in sorted((args.data_root / f'multi_view_training_{category}_undistorted').iterdir()):
            if not scene.is_dir():
                continue
            name = category + '_' + scene.name
            split = 'development' if name in protocol['development_subsets'] else 'held_out_multiview'
            seeds = [22] + (protocol['repeat_seeds'] if split == 'held_out_multiview' else [])
            params = ['--views', '5', '--stride', '12'] if category == 'rig' else ['--views', '6']
            for seed in seeds:
                jobs.append((name, 'multi-view', scene, args.data_root / f'multi_view_training_{category}_scan_eval' / scene.name / f'{category}_scan_eval', params, seed, split))

    def run(job):
        name, mode, scene, gt, params, seed, split = job
        dest = args.output / f'{name}_s{seed}'
        dest.mkdir(parents=True, exist_ok=True)
        record_path = dest / 'record.json'
        if args.resume and record_path.is_file():
            existing = json.loads(record_path.read_text())
            if existing.get('protocol_sha256') == digest and existing.get('status') == 'success':
                return existing
        config = dict(protocol['sfm_config'], seed=seed, rectified_stereo=mode == 'two-view')
        config_file = dest / 'config.yaml'
        config_file.write_text(yaml.safe_dump(config))
        record = {'experiment': name, 'seed': seed, 'split': split, 'status': 'failed', 'protocol_sha256': digest, 'source_revision': revision,
                  'sfm_overrides': config, 'commands': []}
        steps = [[mode, str(scene), '--config', str(config_file), '--output', str(dest / 'baseline'), *params],
                 ['final-evaluate', str(dest / 'baseline'), '--scene', str(scene), '--ground-truth', str(gt), '--output', str(dest / 'evaluation')]]
        for i, step in enumerate(steps):
            module = 'timetravel3d.final_evaluation' if i else 'timetravel3d'
            argv = step[1:] if i else step
            command = [sys.executable, '-m', module, *argv]
            record['commands'].append(['python', '-m', module, *argv])
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            (dest / f'step_{i}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            if result.returncode:
                record['failure_stage'] = i
                record['error'] = result.stderr.splitlines()[-1] if result.stderr else 'nonzero exit'
                break
        else:
            report = json.loads((dest / 'evaluation/evaluation_report.json').read_text())
            baseline = json.loads((dest / 'baseline/report.json').read_text())
            record.update(status='success', rows=report['rows'], selected_images=baseline.get('selected_images', ['im0.png', 'im1.png']),
                registered_cameras=baseline['registered_cameras'], selected_cameras=baseline['selected_cameras'],
                versions=report['source_versions'], geometry_config=baseline['config'],
                runtime_seconds=baseline['runtime_seconds'], peak_memory_mb=baseline['peak_process_memory_mb'],
                evaluation_protocol=report['protocol'], bundle_adjustment=baseline.get('bundle_adjustment'))
        write_json(record_path, record)
        return record

    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run, job) for job in jobs]
        for future in as_completed(futures):
            r = future.result()
            records.append(r)
            print(f"{len(records)}/{len(jobs)} {r['status'].upper()} {r['experiment']} seed={r['seed']} cameras={r.get('registered_cameras',0)}/{r.get('selected_cameras',0)}", flush=True)
            write_json(args.output / 'progress.json', records)
    records.sort(key=lambda r: (r['experiment'], r['seed']))
    rows = []
    for record in records:
        for row in record.get('rows', []):
            rows.append(dict(row, experiment=record['experiment'], seed=record['seed'], split=record['split']))
    args.publish.mkdir(parents=True, exist_ok=True)
    write_json(args.publish / 'manifest.json', {'protocol': protocol, 'protocol_sha256': digest, 'experiments': records})
    write_json(args.publish / 'results.json', rows)
    write_csv(args.publish / 'results.csv', rows)
    print(f"Completed {sum(r['status']=='success' for r in records)}/{len(records)}; all failures recorded", flush=True)


if __name__ == '__main__':
    main()
