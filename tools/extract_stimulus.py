"""Extract OUT payloads from the driver capture; never send audio to hardware."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import shutil
import subprocess
import wave
import numpy as np

root = Path(__file__).resolve().parents[1]
tshark = shutil.which('tshark') or r'C:\Program Files\Wireshark\tshark.exe'
cmd = [tshark, '-r', str(root / 'misura_driver_reale.pcapng'), '-Y',
       'usb.device_address == 2 && usb.endpoint_address == 0x02 && usb.transfer_type == 0 && usb.data_len > 0',
       '-T', 'fields', '-e', 'frame.number', '-e', 'usb.iso.data']
rows = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()
payloads = [bytes.fromhex(line.split('\t')[1].replace(',', '').replace(':', '')) for line in rows]
x = np.frombuffer(b''.join(payloads), dtype='<i2').reshape(-1, 2)
# USB OUT packets contain 48 stereo PCM16 samples per 1 ms frame.
rate = 48000
dest = root / 'analysis' / 'original_stimulus.wav'
with wave.open(str(dest), 'wb') as out:
    out.setnchannels(2)
    out.setsampwidth(2)
    out.setframerate(rate)
    out.writeframes(x.tobytes())
active = np.flatnonzero(np.max(np.abs(x.astype(float)), axis=1) > 100)
segments = []
for start in np.arange(0, len(x), 4800):
    block = x[start:start + 4800, 0].astype(float)
    if len(block) < 128:
        continue
    spectrum = np.abs(np.fft.rfft(block * np.hanning(len(block))))
    segments.append({'time_s': float(start / rate), 'rms': float(np.sqrt(np.mean(block**2))/32768),
                     'dominant_hz': float(np.fft.rfftfreq(len(block), 1/rate)[np.argmax(spectrum)])})
report = {'source': 'misura_driver_reale.pcapng', 'sample_rate_hz': rate,
          'rate_basis': '48 PCM16 stereo samples per full-speed 1ms USB frame; verify timing before metrology',
          'frames': len(x), 'duration_s': len(x)/rate,
          'peak': float(np.max(np.abs(x.astype(float)))/32768),
          'active_range_s': [float(active[0]/rate), float(active[-1]/rate)],
          'output_channel_correlation': float(np.corrcoef(x.T)[0, 1]), 'blocks': segments}
(root / 'analysis' / 'stimulus_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
