"""Check published budgets, result accounting and local documentation links."""
import csv
import json
import re
from pathlib import Path

import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'benchmarks/final/manifest.json').read_text())
    records = manifest['experiments']
    rows = json.loads((root / 'benchmarks/final/results.json').read_text())
    summary = json.loads((root / 'benchmarks/final/summary.json').read_text())
    assert len(records) == summary['attempted_runs'] == 69
    successes = [r for r in records if r['status'] == 'success']
    assert len(successes) == summary['successful_runs'] == 66
    assert len(rows) == len(successes) * 8
    assert len([r for r in records if r['seed'] == 22]) == 45
    for record in successes:
        baseline = next(r for r in record['rows'] if r['method'] == 'baseline')
        budget = int(np.ceil(baseline['retained_points'] * .8))
        for row in record['rows']:
            if row['method'] != 'baseline':
                assert row['retained_points'] == budget, (record['experiment'], row['method'])
            assert 0 <= row['grid_coverage_retention'] <= 1
    with (root / 'benchmarks/final/results.csv').open(newline='', encoding='utf-8') as f:
        assert len(list(csv.DictReader(f))) == len(rows)
    for filename in ['README.md']:
        path = root / filename
        content = path.read_text(encoding='utf-8')
        assert content.count('```') % 2 == 0
        for target in re.findall(r'\]\(([^)]+)\)', content):
            if not target.startswith(('http:', 'https:', '#')):
                assert (path.parent / target).exists(), (filename, target)
    print(f'Validated {len(rows)} rows, 69 attempts, 45 primary subsets, matched budgets and local README links.')


if __name__ == '__main__':
    main()
