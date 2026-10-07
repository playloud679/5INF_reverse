"""Summarize USB capture evidence without modifying source captures."""
import collections
import json
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
tshark = shutil.which('tshark') or r'C:\Program Files\Wireshark\tshark.exe'
fields = ['frame.number', 'frame.time_relative', 'frame.len', 'frame.cap_len',
          'usb.device_address', 'usb.endpoint_address', 'usb.transfer_type',
          'usb.iso.data']
report = {}
for path in sorted(root.glob('*.pcapng')):
    command = [tshark, '-r', str(path), '-T', 'fields']
    for field in fields:
        command += ['-e', field]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    streams = collections.defaultdict(lambda: {'urbs_with_payload': 0, 'bytes': 0, 'nonzero_bytes': 0})
    rows = [line.split('\t') for line in result.stdout.splitlines()]
    for row in rows:
        if row[4] != '2' or row[6] != '0x00' or not row[7]:
            continue
        payload = bytes.fromhex(row[7].replace(',', '').replace(':', ''))
        entry = streams[row[5]]
        entry['urbs_with_payload'] += 1
        entry['bytes'] += len(payload)
        entry['nonzero_bytes'] += sum(byte != 0 for byte in payload)
    report[path.name] = {
        'frames': len(rows),
        'duration_seconds': float(rows[-1][1]) if rows else 0,
        'truncated_frames': sum(row[2] != row[3] for row in rows),
        'device_address_2_isochronous_payloads': dict(streams),
    }
out = root / 'analysis'
out.mkdir(exist_ok=True)
(out / 'capture_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
