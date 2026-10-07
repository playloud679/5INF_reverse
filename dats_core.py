"""Text references, resonance/Le extraction and experimental three-standard calibration.

Docs: docs/modules/dats_core.md
"""
from dataclasses import dataclass, field
import io
import numpy as np
import pandas as pd


@dataclass
class Measurement:
    name: str
    frequency: np.ndarray
    impedance: np.ndarray
    phase: np.ndarray
    metadata: dict = field(default_factory=dict)

    def frame(self):
        return pd.DataFrame({'frequency_hz': self.frequency,
                             'impedance_ohm': self.impedance, 'phase_deg': self.phase})

    def zma(self):
        stream = io.StringIO()
        stream.write('* ' + self.name.replace('\n', ' ') + '\n')
        if self.metadata.get('experimental'):
            stream.write('* EXPERIMENTAL: hardware accuracy not validated\n')
        np.savetxt(stream, self.frame().to_numpy(), fmt='%.9g', delimiter='\t')
        return stream.getvalue()


def parse_measurement(data: bytes, name: str) -> Measurement:
    text = data.decode('utf-8-sig', errors='replace')
    rows, metadata = [], {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if line.startswith(('*', '#', ';')):
            if '=' in line:
                key, value = line.lstrip('*#; ').split('=', 1)
                metadata[key.strip()] = value.strip()
            continue
        if line.lower().startswith(('freq', 'frequency_hz')):
            continue
        parts = line.replace(',', ' ').split()
        try:
            if len(parts) != 3:
                raise ValueError()
            rows.append([float(x) for x in parts])
        except ValueError:
            raise ValueError(f'Riga {number}: attese tre colonne numeriche (Hz, ohm, gradi).') from None
    values = np.asarray(rows, dtype=float)
    if len(values) < 2:
        raise ValueError('Servono almeno due punti di misura.')
    if not np.isfinite(values).all():
        raise ValueError('La curva contiene valori NaN o infiniti.')
    if np.any(values[:, 0] <= 0) or np.any(np.diff(values[:, 0]) <= 0):
        raise ValueError('Le frequenze devono essere positive e strettamente crescenti.')
    if np.any(values[:, 1] < 0):
        raise ValueError('Il modulo di impedenza non può essere negativo.')
    return Measurement(name, *values.T, metadata)


def calibrated_impedance(h, short, opened, load, resistance):
    """Invert an unknown fractional-linear bridge response using O/S/L standards.

    Assumes a stable linear bridge, ideal open/short and a resistive known load.
    Does not claim to reproduce the manufacturer's calibration algorithm.
    """
    if not np.isfinite(resistance) or resistance <= 0:
        raise ValueError('Resistenza di riferimento non valida.')
    h, short, opened, load = np.broadcast_arrays(h, short, opened, load)
    for a, b in [(load, short), (load, opened), (short, opened), (h, opened)]:
        if np.any(np.abs(a - b) <= 1e-8 * np.maximum(1, np.maximum(np.abs(a), np.abs(b)))):
            raise ValueError('Calibrazione degenere o carico vicino al circuito aperto. Controllare collegamenti e canali.')
    result = resistance * (h - short) * (load - opened) / ((h - opened) * (load - short))
    if not np.isfinite(result).all():
        raise ValueError('Impedenza non finita: ripetere la calibrazione.')
    return result


def channel_ratio(samples, frequency, samplerate):
    """Least-squares sinusoidal phasors, cancelling common acquisition delay."""
    samples = np.asarray(samples)
    if samples.ndim != 2 or samples.shape[1] != 2 or not np.isfinite(samples).all():
        raise ValueError('Acquisizione stereo non valida.')
    if np.max(np.abs(samples)) >= .98:
        raise ValueError('Ingresso in clipping: ridurre il livello e ricalibrare.')
    t = np.arange(len(samples)) / samplerate
    angle = 2 * np.pi * frequency * t
    basis = np.column_stack([np.cos(angle), np.sin(angle), np.ones(len(t))])
    coefficients = np.linalg.lstsq(basis, samples, rcond=None)[0]
    phasors = coefficients[0] - 1j * coefficients[1]
    if np.min(np.abs(phasors)) < 1e-5:
        raise ValueError('Segnale insufficiente su uno dei canali: verificare il dispositivo e il collegamento.')
    residual = samples - basis @ coefficients
    quality = 20 * np.log10(np.abs(phasors) / np.maximum(np.sqrt(2) * np.std(residual, axis=0), 1e-12))
    if np.min(quality) < 15:
        levels = 20 * np.log10(np.maximum(np.abs(phasors), 1e-12))
        raise ValueError('Segnale troppo rumoroso o instabile per una misura affidabile. '
                         f'Qualità L/R: {quality[0]:.1f}/{quality[1]:.1f} dB; '
                         f'livello del tono L/R: {levels[0]:.1f}/{levels[1]:.1f} dBFS. '
                         'Verificare uscita stereo, collegamento e volume di sistema.')
    return phasors[1] / phasors[0], float(np.min(quality))


def resonance(m):
    """Return (fs, zmax) of the first internal local maximum of |Z| where the
    phase crosses zero from inductive to capacitive, else None.

    A global argmax is wrong here: above ~5 kHz the voice-coil inductance can
    exceed the mechanical peak (addenda/AUDIO_DSP_ACOUSTICS.md section 2).
    """
    z, ph = m.impedance, m.phase
    for i in range(1, len(z) - 1):
        if z[i] >= z[i - 1] and z[i] > z[i + 1] and ph[i - 1] > 0 >= ph[i + 1]:
            return float(m.frequency[i]), float(z[i])
    return None


def inductance(m, frequency):
    """Le(f) = Im(Z)/(2 pi f) in henry, interpolated on log f; None if out of range."""
    if not m.frequency[0] <= frequency <= m.frequency[-1]:
        return None
    im = m.impedance * np.sin(np.radians(m.phase))
    return float(np.interp(np.log(frequency), np.log(m.frequency), im) / (2 * np.pi * frequency))
