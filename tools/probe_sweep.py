"""Explicit live probe: emits captured sweep on the selected DATS only."""
import argparse
import json
from pathlib import Path
import sys
import wave
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dats_audio import devices, SAMPLE_RATE
from dats_sweep import record_sweep, sweep_ratios

parser = argparse.ArgumentParser()
parser.add_argument('--gain', type=float, default=.25)
args = parser.parse_args()
items = devices()
ins = [d for d in items if 'USB AUDIO' in d['name'].upper() and d['api'] == 'MME' and d['max_input_channels'] >= 2]
outs = [d for d in items if 'USB AUDIO' in d['name'].upper() and d['api'] == 'MME' and d['max_output_channels'] >= 2]
if len(ins) != 1 or len(outs) != 1:
    raise RuntimeError('Serve una sola coppia DATS stereo MME identificabile.')
recording = record_sweep(ins[0]['id'], outs[0]['id'], args.gain)
root = Path(__file__).resolve().parents[1] / 'analysis'
tag = str(args.gain).replace('.', '_')
with wave.open(str(root / f'live_sweep_{tag}.wav'), 'wb') as out:
    out.setnchannels(2)
    out.setsampwidth(2)
    out.setframerate(SAMPLE_RATE)
    out.writeframes((np.clip(recording, -1, 1) * 32767).astype('<i2').tobytes())
report = {'gain_relative_original': args.gain, 'sample_rate_hz': SAMPLE_RATE,
          'peak_input_channels': np.max(np.abs(recording), axis=0).tolist(),
          'duration_s': len(recording)/SAMPLE_RATE,
          'note': 'Electrical response only; audibility and impedance accuracy not validated.'}
try:
    frequencies = np.geomspace(20, 20000, 24)
    ratios, quality = sweep_ratios(recording, frequencies)
    report.update(frequency_hz=frequencies.tolist(), ratio_real=ratios.real.tolist(),
                  ratio_imag=ratios.imag.tolist(), quality_db=quality.tolist())
except ValueError as exc:
    report['analysis_error'] = str(exc)
(root / f'live_sweep_{tag}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
