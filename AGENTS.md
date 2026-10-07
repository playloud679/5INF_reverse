# Agent Instructions

Questo progetto aderisce a `GOLDEN_STD.md` (1.5.0). Addenda applicabili, letti prima del lavoro
di dominio: `addenda/AUDIO_DSP_ACOUSTICS.md`, `addenda/STREAMLIT_SAAS.md`.
Controllo aggiornamenti: `curl -s https://raw.githubusercontent.com/playloud679/dev_standards/refs/heads/main/VERSION`.

## Progetto
- Stadio: **Alpha** (`0.x.y`); uscita dall'Alpha solo con hardware DATS validato su resistenze
  indipendenti. Versione in `VERSION`.
- Ramo di integrazione: `main`. Lavorare su rami dedicati; commit Conventional Commits.
- Indice documentazione: `docs/INDEX.md`. Aggiornare il documento di modulo dopo ogni patch.

## Regole
0. Moduli coesi, commentati, con `docs/modules/<modulo>.md` e voce in `docs/INDEX.md` (§0, §2).
1. Validazione proporzionale (§7): `python -m unittest discover -s tests` e AppTest headless
   (comando in `docs/modules/app.md`). Solo documentazione: `git diff --check` e verifica link.
2. Ogni patch applicativa: bump di `VERSION`, `CHANGELOG.md`, versione nella UI (§8).
3. Sorgenti di verità: tutto a mano, tranne `analysis/original_stimulus.wav` (generato da
   `tools/extract_stimulus.py` dal pcapng) e gli export in `analysis/` (provenienti dal DATS).
   Non rigenerare né sovrascrivere senza richiesta esplicita (§16).
4. Stile antirez (§17). Dipendenze e motivo: streamlit/plotly (UI), numpy (DSP), scipy (solo
   `resample_poly`), pandas (CSV/tabelle), pyarrow (richiesto da Streamlit per le tabelle),
   sounddevice (I/O audio). Valutare la rimozione di scipy e pandas.
