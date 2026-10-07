# dats_sweep

Sorgente: `dats_sweep.py`. Dipende da `dats_audio` (lock, sample rate), numpy, scipy
(`resample_poly`, unico uso di scipy) e `analysis/original_stimulus.wav` (48 kHz).

## API pubblica
- `stimulus(gain)`: sweep catturato, ricampionato a 44,1 kHz (147/160), gain in (0, 1].
- `record_sweep(in_id, out_id, gain)`: riproduce e registra; rifiuta clipping >= .98.
- `sweep_ratios(samples, freqs)`: rapporti da 3 bin FFT; rumore dal silenzio iniziale
  (primi 200 ms); punti sotto 15 dB → NaN. `ValueError` se < 2 punti validi.
- `acquire_sweep(...)`: registra + analizza.

## Invarianti
La registrazione dura quanto lo stimolo, che contiene silenzio iniziale e finale
(3,31 s); il margine >= 0,5 s richiesto dall'addendum Audio §3 non è verificato da test
(rischio dichiarato). Il rapporto spettrale è un SNR approssimato, non equivalente
alla qualità dei toni.

Test: `tests/test_sweep.py`.
