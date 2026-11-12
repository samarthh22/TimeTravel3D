"""One-command offline demo, reusing the final courtyard experiment when available."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from timetravel3d.uncertainty import variants
from timetravel3d.viewer import save_viewer
from timetravel3d.output import plot_cloud


def main():
    if sys.prefix == sys.base_prefix:
        raise SystemExit('Use .venv/Scripts/python.exe scripts/run_demo.py')
    folder = Path('results/final/dslr_courtyard_s22')
    baseline = folder / 'baseline'
    if not (baseline / 'reconstruction.npz').is_file():
        folder.mkdir(parents=True, exist_ok=True)
        import yaml
        protocol = json.loads(Path('configs/final_protocol.json').read_text())
        (folder / 'config.yaml').write_text(yaml.safe_dump(protocol['sfm_config']))
        subprocess.run([sys.executable, '-m', 'timetravel3d', 'multi-view', '../multi_view_training_dslr_undistorted/courtyard',
            '--views', '6', '--config', str(folder / 'config.yaml'), '--output', str(baseline)], check=True)
    with np.load(baseline / 'reconstruction.npz') as archive:
        data = dict(archive)
    _, masks = variants(data)
    path = Path('results/demo/viewer.html')
    save_viewer(path, data, masks['coverage_uncertainty'], 'TimeTravel3D: courtyard reconstruction')
    plot_cloud(path.parent / 'point_cloud.png', data['points'], data['colors'])
    print('Open in your browser:', path.resolve())
    print('Baseline points:', len(data['points']), 'Proposed:', int(masks['coverage_uncertainty'].sum()))
    print('Rotate with mouse drag. Toggle baseline/proposed. No server or internet required.')


if __name__ == '__main__':
    main()
