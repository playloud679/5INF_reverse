# app

Sorgente: `app.py`. Interfaccia Streamlit in italiano; tre schede: Curve e confronto,
Acquisizione DATS, Riferimenti USB. Dipende da tutti i moduli `dats_*`.

## Contratti UI (addendum Streamlit §1)
- Parametri persistenti: `measurements`, `calibration` (session_state).
- Pulsanti di azione con chiavi `btn_*` (es. `btn_cal_open`); mai condivise con i parametri.
- La firma delle impostazioni audio (`audio_signature`) invalida la calibrazione se cambia.
- La versione mostrata nel sottotitolo viene da `VERSION`.
- Risonanza e Le (1/10 kHz) usano `dats_core.resonance`/`inductance`.

## Validazione
```
python -c 'from streamlit.testing.v1 import AppTest; at = AppTest.from_file("app.py", default_timeout=30); at.run(); assert not at.exception, at.exception'
python -m unittest tests.test_app
```
