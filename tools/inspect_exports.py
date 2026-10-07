"""Inspect DATS text exports and record binary project facts (not a TZZ decoder)."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import math

root = Path(__file__).resolve().parents[1] / 'analysis'
source = root / 'real drv.txt'
rows = []
metadata = []
for line in source.read_text(encoding='utf-8-sig').splitlines():
    if line.startswith('*'):
        metadata.append(line.lstrip('* ').strip())
        continue
    parts = line.split()
    if len(parts) == 3:
        try:
            rows.append(tuple(map(float, parts)))
        except ValueError:
            pass
assert rows and all(a[0] < b[0] for a, b in zip(rows, rows[1:]))
with (root / 'driver_reference.csv').open('w', newline='', encoding='utf-8') as stream:
    writer = csv.writer(stream)
    writer.writerow(['frequency_hz', 'impedance_ohm', 'phase_deg'])
    writer.writerows(rows)
projects = {}
for path in sorted(root.glob('*.tzz')):
    data = path.read_bytes()
    projects[path.name] = {
        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
        'first_8_bytes_as_float64_le': struct.unpack_from('<d', data)[0],
        'offset_100_as_uint32_le': struct.unpack_from('<I', data, 100)[0],
        'note': 'Raw interpretations only; field meanings and binary layout unverified.',
    }
report = {
    'source': source.name, 'points': len(rows),
    'frequency_range_hz': [rows[0][0], rows[-1][0]],
    'maximum_sampled_impedance': dict(zip(['frequency_hz', 'impedance_ohm', 'phase_deg'], max(rows, key=lambda r: r[1]))),
    'original_header': metadata, 'projects': projects,
    'validation': 'Reference export only. USB-derived impedance has not yet been reconstructed or compared.',
}
(root / 'export_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))

# Compare all three references on their original frequency grids.
references = {}
grids = []
for filename, label in [('real drv.txt', 'driver'), ('shorted.txt', 'shorted'),
                        ('Exported Impedance Data.txt', 'resistor_1k')]:
    points = []
    for line in (root / filename).read_text(encoding='utf-8-sig').splitlines():
        parts = line.split()
        if not parts or parts[0] == '*' or parts[0] == 'Freq':
            continue
        if len(parts) != 3:
            raise ValueError(f'{filename}: unexpected data row: {line}')
        point = tuple(map(float, parts))
        if not all(map(math.isfinite, point)) or point[0] <= 0 or point[1] < 0:
            raise ValueError(f'{filename}: invalid data: {line}')
        points.append(point)
    if not points or not all(a[0] < b[0] for a, b in zip(points, points[1:])):
        raise ValueError(f'{filename}: empty or unordered frequency grid')
    grids.append([p[0] for p in points])
    with (root / f'{label}_reference.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['frequency_hz', 'impedance_ohm', 'phase_deg'])
        writer.writerows(points)
    references[label] = {
        'source': filename, 'points': len(points),
        'frequency_range_hz': [points[0][0], points[-1][0]],
        'impedance_range_ohm': [min(p[1] for p in points), max(p[1] for p in points)],
        'phase_range_deg': [min(p[2] for p in points), max(p[2] for p in points)],
        'nearest_1khz': dict(zip(['frequency_hz', 'impedance_ohm', 'phase_deg'],
                                min(points, key=lambda p: abs(p[0] - 1000)))),
    }
comparison = {'references': references, 'identical_frequency_grids': all(g == grids[0] for g in grids),
              'note': 'The 1k association is inferred from the export header Re=1000 Ohms. Capture correspondence and USB calibration are not yet validated.'}
(root / 'reference_comparison.json').write_text(json.dumps(comparison, indent=2), encoding='utf-8')
print(json.dumps(comparison, indent=2))
