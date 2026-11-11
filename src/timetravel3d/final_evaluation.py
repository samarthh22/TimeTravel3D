"""V2 selections are fixed before independent GT evaluation is invoked."""
import argparse
import json
from pathlib import Path

import numpy as np

from .evaluation import run as evaluate
from .output import write_json, write_ply
from .uncertainty import variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reconstruction', type=Path)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--ground-truth', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=Path('configs/final_protocol.json'))
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    with np.load(args.reconstruction / 'reconstruction.npz') as archive:
        data = dict(archive)
    risk, masks = variants(data, protocol['retention_fraction'], protocol['noise_floor_px'])
    args.output.mkdir(parents=True, exist_ok=True)
    # Save selection before evaluation can read any ground-truth data.
    np.savez_compressed(args.output / 'selection.npz', uncertainty=risk, **masks)
    for method in ['baseline', 'coverage_uncertainty']:
        write_ply(args.output / f'{method}.ply', data['points'][masks[method]], data['colors'][masks[method]])
    report = evaluate(args.reconstruction, args.scene, args.ground_truth, args.output,
                      max_scan_points=protocol['max_scan_points'], masks_override=masks)
    report['selection_protocol'] = protocol
    write_json(args.output / 'evaluation_report.json', report)
    print(json.dumps({method: row['median_point_error_m'] for method, row in zip(masks, report['rows'])}))


if __name__ == '__main__':
    main()
