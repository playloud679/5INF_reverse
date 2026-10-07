"""Captured DATS excitation and experimental simultaneous spectral ratios.

Docs: docs/modules/dats_sweep.md
"""
from pathlib import Path
import wave
import numpy as np
from scipy.signal import resample_poly
from dats_audio import DEVICE_LOCK, SAMPLE_RATE

STIMULUS = Path(__file__).resolve().parent / 'analysis' / 'original_stimulus.wav'


def stimulus(gain=.25):
    if not 0 < gain <= 1:
        raise ValueError('Il guadagno deve essere tra 0 e 1 rispetto alla cattura originale.')
    with wave.open(str(STIMULUS), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (2, 2, 48000):
            raise ValueError('Formato della cattura sweep inatteso.')
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').reshape(-1, 2).astype(float) / 32768
    # Preserve physical duration/frequencies when the audio API operates at 44.1 kHz.
    return (resample_poly(samples, 147, 160, axis=0) * gain).astype('float32')


def record_sweep(input_id, output_id, gain=.25):
    import sounddevice as sd
    signal = stimulus(gain)
    if not DEVICE_LOCK.acquire(blocking=False):
        raise ValueError('Dispositivo già in uso da un’altra sessione.')
    try:
        if sd.query_devices(input_id)['hostapi'] != sd.query_devices(output_id)['hostapi']:
            raise ValueError('Ingresso e uscita devono usare la stessa API audio.')
        sd.check_input_settings(device=input_id, channels=2, samplerate=SAMPLE_RATE, dtype='float32')
        sd.check_output_settings(device=output_id, channels=2, samplerate=SAMPLE_RATE, dtype='float32')
        captured = sd.playrec(signal, samplerate=SAMPLE_RATE, channels=2, dtype='float32',
                              device=(input_id, output_id), blocking=True)
        status = sd.get_status()
        if status:
            raise ValueError(f'Errore nel flusso audio: {status}')
        if not np.isfinite(captured).all():
            raise ValueError('Campioni non finiti.')
        if np.max(np.abs(captured)) >= .98:
            raise ValueError('Clipping in ingresso: ridurre il livello relativo allo sweep originale.')
        return captured
    finally:
        try:
            sd.stop()
        finally:
            DEVICE_LOCK.release()


def sweep_ratios(samples, frequencies, rate=SAMPLE_RATE):
    """Ratios from neighboring FFT bins; noise estimated from initial silence.

    Quality is an approximate spectral SNR, not coherence or absolute accuracy.
    The entire response must lie inside the recording, away from its boundaries.
    """
    samples = np.asarray(samples)
    frequencies = np.asarray(frequencies)
    if samples.ndim != 2 or samples.shape[1] != 2 or len(samples) < rate:
        raise ValueError('Registrazione sweep stereo troppo breve.')
    if not np.isfinite(samples).all() or not np.isfinite(frequencies).all():
        raise ValueError('Dati non finiti.')
    if np.any((frequencies < 10) | (frequencies > 20000)):
        raise ValueError('Banda supportata: 10–20000 Hz.')
    x = samples - samples.mean(axis=0)
    spectrum = np.fft.rfft(x, axis=0)
    noise = np.maximum(samples[:int(.2 * rate)].std(axis=0), 1e-7) ** 2 * len(samples)
    ratios, qualities = [], []
    for frequency in frequencies:
        center = int(round(frequency * len(samples) / rate))
        bins = spectrum[max(1, center-1):center+2]
        power = np.mean(np.abs(bins)**2, axis=0)
        quality = 10 * np.log10(np.maximum(power, 1e-30) / noise)
        if np.min(quality) < 15:
            ratios.append(complex(float('nan'), float('nan')))
            qualities.append(float(quality.min()))
            continue
        ratios.append(np.sum(bins[:, 1] * bins[:, 0].conj()) / np.sum(np.abs(bins[:, 0])**2))
        qualities.append(float(quality.min()))
    ratios, qualities = np.asarray(ratios), np.asarray(qualities)
    if np.count_nonzero(np.isfinite(ratios)) < 2:
        raise ValueError('Sweep insufficiente: meno di due frequenze valide. Verificare livello e collegamento.')
    return ratios, qualities


def acquire_sweep(frequencies, input_id, output_id, gain=.25, progress=None):
    if progress:
        progress(.05)
    captured = record_sweep(input_id, output_id, gain)
    result = sweep_ratios(captured, frequencies)
    if progress:
        progress(1.)
    return result
