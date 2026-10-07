"""Local audio acquisition; no audio is emitted during discovery or app startup.

Docs: docs/modules/dats_audio.md
"""
import threading
import numpy as np
from dats_core import channel_ratio

DEVICE_LOCK = threading.Lock()
SAMPLE_RATE = 44100


def devices():
    import sounddevice as sd
    apis = sd.query_hostapis()
    return [dict(d, id=i, api=apis[d['hostapi']]['name']) for i, d in enumerate(sd.query_devices())]


def acquire(frequencies, input_id, output_id, amplitude, output_channel, progress=None):
    import sounddevice as sd
    if not 0 < amplitude <= .1:
        raise ValueError('Ampiezza fuori intervallo.')
    if output_channel not in (0, 1, 2):
        raise ValueError('Canale di uscita non valido.')
    frequencies = np.asarray(frequencies, dtype=float)
    if not len(frequencies) or not np.isfinite(frequencies).all() or np.any((frequencies < 10) | (frequencies > 20000)):
        raise ValueError('Intervallo consentito: 10–20000 Hz.')
    if not DEVICE_LOCK.acquire(blocking=False):
        raise ValueError('Dispositivo già in uso da un’altra sessione.')
    ratios, qualities = [], []
    try:
        if sd.query_devices(input_id)['hostapi'] != sd.query_devices(output_id)['hostapi']:
            raise ValueError('Selezionare ingresso e uscita con la stessa API audio.')
        sd.check_input_settings(device=input_id, channels=2, samplerate=SAMPLE_RATE, dtype='float32')
        sd.check_output_settings(device=output_id, channels=2, samplerate=SAMPLE_RATE, dtype='float32')
        for index, frequency in enumerate(frequencies):
            # Allow the two device buffers and the analog path to settle.
            settle = max(.50, 8 / frequency)
            duration = max(.15, 12 / frequency)
            count = int(np.ceil((settle + duration + .05) * SAMPLE_RATE))
            t = np.arange(count) / SAMPLE_RATE
            tone = amplitude * np.sin(2 * np.pi * frequency * t)
            fade = min(int(.02 * SAMPLE_RATE), count // 4)
            tone[:fade] *= np.linspace(0, 1, fade)
            tone[-fade:] *= np.linspace(1, 0, fade)
            signal = np.zeros((count, 2), dtype=np.float32)
            if output_channel == 2:
                signal[:] = tone[:, None]
            else:
                signal[:, output_channel] = tone
            recorded = sd.playrec(signal, samplerate=SAMPLE_RATE, channels=2,
                                  dtype='float32', device=(input_id, output_id), blocking=True)
            status = sd.get_status()
            if status:
                raise ValueError(f'Errore nel flusso audio: {status}')
            start = int(settle * SAMPLE_RATE)
            end = start + int(duration * SAMPLE_RATE)
            try:
                ratio, quality = channel_ratio(recorded[start:end], frequency, SAMPLE_RATE)
            except ValueError as exc:
                raise ValueError(f'{frequency:.2f} Hz: {exc}') from exc
            ratios.append(ratio)
            qualities.append(quality)
            if progress:
                progress((index + 1) / len(frequencies))
    finally:
        try:
            sd.stop()
        finally:
            DEVICE_LOCK.release()
    return np.asarray(ratios), np.asarray(qualities)
