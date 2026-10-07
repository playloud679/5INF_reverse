# dats_core

Sorgente: `dats_core.py`. Nessuna dipendenza interna; usa numpy e pandas.

## API pubblica
- `Measurement` (nome, frequenza, |Z|, fase, metadata): `frame()`, `zma()`.
- `parse_measurement(bytes, name)`: TXT/ZMA/CSV a tre colonne. `ValueError` se
  < 2 punti, valori non finiti, frequenze non crescenti, |Z| negativo.
- `calibrated_impedance(h, short, open, load, R)`: Z = R(H-S)(L-O)/((H-O)(L-S)).
  `ValueError` per calibrazioni degeneri o risultato non finito.
- `channel_ratio(samples, f, rate)`: fasore canale2/canale1 con fit ai minimi quadrati;
  rifiuta clipping (>= .98), segnale < 1e-5, qualità < 15 dB.
- `resonance(m)`: (fs, Zmax) del primo massimo locale interno con fase che passa da
  positiva a negativa; `None` se assente. Non usa l'argmax globale (addendum Audio §2).
- `inductance(m, f)`: Le = Im(Z)/(2πf) interpolata su log f; `None` fuori banda.

## Invarianti e test
`tests/test_core.py`: import/roundtrip degli export originali, curve non valide,
calibrazione, rapporto di canale, `resonance`/`inductance` su modello RLC sintetico
(il massimo globale è la salita induttiva). Comando: `python -m unittest tests.test_core`.
