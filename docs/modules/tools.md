# tools

Sorgenti: `tools/extract_stimulus.py`, `inspect_captures.py`, `inspect_exports.py`,
`probe_sweep.py`. Script a riga di comando, fuori dall'app.

- `extract_stimulus.py`: estrae i payload OUT da `misura_driver_reale.pcapng`
  (richiede tshark) e genera `analysis/original_stimulus.wav`. Non invia audio.
- `inspect_captures.py`, `inspect_exports.py`: riassunti in sola lettura di catture ed export.
- `probe_sweep.py`: **emette** lo sweep sul DATS selezionato; solo su richiesta esplicita.
