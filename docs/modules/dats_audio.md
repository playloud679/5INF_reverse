# dats_audio

Sorgente: `dats_audio.py`. Dipende da `dats_core.channel_ratio`; `sounddevice` è caricato
solo all'uso. Nessun suono all'avvio o durante l'enumerazione.

## API pubblica
- `devices()`: elenco dispositivi con `id` e nome API.
- `acquire(freqs, in_id, out_id, amplitude, channel, progress)`: toni separati.
  Ampiezza in (0, .1], 10–20000 Hz, stessa host API, 44100 Hz stereo float32.

## Invarianti
- `DEVICE_LOCK` (condiviso con `dats_sweep`) impedisce acquisizioni concorrenti.
- Assestamento >= 500 ms prima della finestra di analisi (addendum Audio §3).
- Errori di flusso audio interrompono la misura, nessun fallback silenzioso.

Test: `tests/test_audio.py` (dispositivi simulati).
