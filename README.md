# DATS Lab

App Streamlit locale per Dayton Audio DATS V3. Interfaccia in italiano.

Versione 0.1.0 · stadio Alpha · ramo di integrazione `main`. Standard: [GOLDEN_STD.md](GOLDEN_STD.md)
con addenda [Audio DSP](addenda/AUDIO_DSP_ACOUSTICS.md) e [Streamlit](addenda/STREAMLIT_SAAS.md).
Documentazione per modulo: [docs/INDEX.md](docs/INDEX.md) · [AGENTS.md](AGENTS.md) · [Changelog](CHANGELOG.md).

## Avvio

Python 3.11 o superiore. Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Su Linux installare anche PortAudio tramite il gestore di pacchetti della distribuzione
(ad esempio `sudo apt install libportaudio2` su Debian/Ubuntu).
Aprire l'indirizzo locale mostrato da Streamlit. Il dispositivo USB deve essere
collegato al computer che esegue Python, non necessariamente a quello del browser.
PyArrow è limitato alla versione 19: la versione 25.0.1 è stata bloccata dal
controllo applicazioni Windows su questo PC, mentre la 19.0.1 ha superato i test.

## Funzioni

- Importazione TXT DATS, ZMA a tre colonne e CSV Hz/ohm/gradi con punto decimale.
- Riferimenti originali caricabili dalla cartella `analysis`.
- Grafici di modulo e fase, sovrapposizione, confronto RMS nella banda comune.
- Esportazione CSV e ZMA. Le misure sono in memoria di sessione: scaricarle per conservarle.
- Enumerazione dispositivi e acquisizione audio stereo locale a 44100 Hz.
- Calibrazione sperimentale circuito aperto/cortocircuito/resistenza nota.
- Sweep estratto dalla cattura originale, oppure toni separati per diagnosi.
- Prova del segnale senza calibrazione, con esportazione del rapporto elettrico grezzo.

## Misure sperimentali

Chiudere il software DATS originale. Selezionare ingresso e uscita USB AUDIO CODEC
con la stessa API audio. Non collegare componenti connessi ad amplificatori,
altre apparecchiature o masse esterne. Nessun segnale viene emesso all'avvio.

Selezionare frequenze e livello, poi acquisire i tre standard. La resistenza da
1 kΩ integrata può fungere da riferimento. Acquisire infine il componente.
Cambiare un'impostazione nell'app invalida la calibrazione. Variazioni esterne
del volume, guadagno, dispositivo o cablaggio non sono rilevabili automaticamente:
in questi casi azzerare e ripetere la calibrazione.

Usare l'uscita **Entrambi (DATS)**: la cattura originale del driver mostra lo
stesso segnale sui due canali di uscita (correlazione circa 1). I canali singoli
restano disponibili per diagnosi. L'attesa di assestamento è almeno 500 ms.
Gli errori di qualità riportano frequenza, qualità e livello del tono per canale;
la soglia di 15 dB resta attiva. Queste modifiche richiedono una nuova calibrazione.

### Sweep originale

La modalità predefinita usa `analysis/original_stimulus.wav`, estratto da
`misura_driver_reale.pcapng` con `tools/extract_stimulus.py`. I pacchetti OUT
contengono 48 campioni stereo PCM16 per millisecondo, quindi il file estratto
è a 48 kHz. Viene ricampionato a 44,1 kHz mantenendo durata e frequenze.
La registrazione contiene 3,31 secondi inclusi silenzi, con circa 1,17 secondi
attivi sopra 100 conteggi PCM e picco 0,726. Non viene normalizzata.
Il livello predefinito è 0 dB rispetto a quella cattura; 0 dB mantiene
l'ampiezza digitale originale, ma non garantisce uguale tensione ai morsetti
se il mixer o i controlli hardware hanno impostazioni diverse.

I limiti di frequenza selezionano i punti analizzati, non la banda emessa dallo
sweep catturato. La curva usa 512 punti per default, selezionabili tra 96 e
2048 senza cambiare durata dello sweep. Una griglia più densa non aumenta la
risoluzione fisica: alle basse frequenze più punti possono ricadere negli stessi
bin FFT. Cambiare griglia invalida i riferimenti e richiede una nuova calibrazione.
I punti sweep sotto 15 dB vengono esclusi, senza interrompere tutta la scansione.
La misura usa solo le frequenze valide comuni ai tre riferimenti e al componente;
frequenze escluse e conteggio dei punti sono visibili nel risultato. Servono almeno
due punti validi comuni. Il CSV grezzo conserva anche i punti rifiutati con `valid=false`.
I limiti di frequenza selezionano i punti analizzati, non la banda emessa dallo
sweep catturato. La modalità sweep usa entrambi i canali indipendentemente dai
controlli dei toni, che sono disabilitati. L'analisi usa rapporti spettrali su tre
bin FFT vicini e rumore stimato dal silenzio iniziale: l'indicatore è un SNR
approssimato, non la qualità del fit sinusoidale usata per i toni. Non confrontare
numericamente i due indicatori. La calibrazione è invalidata cambiando modalità
o livello. L'equivalenza all'analisi proprietaria DATS resta da validare.

La prova hardware del 30/09/2026 a guadagno 0,25 ha acquisito tutti i 24 punti
20 Hz–20 kHz senza clipping, con picchi L/R 0,044/0,182. Dati e registrazione
in `analysis/live_sweep_0_25.json` e `.wav`. Questo conferma solo la risposta
elettrica acquisita, non l'audibilità del driver o l'accuratezza in ohm.
L'utente ha confermato l'audibilità della prova attenuata. La successiva prova a
guadagno 1 ha acquisito tutti i 24 punti senza clipping (picchi L/R 0,172/0,727).
Registrazione e risultati sono in `analysis/live_sweep_1_0.wav` e `.json`.
I rapporti cambiano tra i due livelli: la sola assenza di clipping non dimostra
linearità o accuratezza. Occorre validare la calibrazione a livello costante.

Il rapporto complesso H = canale 2 / canale 1 viene stimato con un fit sinusoidale.
Per un ponte lineare con risposta frazionaria, gli standard S (short), O (open),
L (resistenza R) danno Z = R (H-S)(L-O) / ((H-O)(L-S)). La procedura assume
standard ideali e circuito stabile. Sono rifiutati clipping, segnale insufficiente,
qualità sotto 15 dB e calibrazioni degeneri. La soglia di qualità non è una stima
dell'accuratezza assoluta. Una configurazione del ponte che rende un canale nullo
durante uno standard può essere incompatibile con questa procedura.

**Compatibilità hardware e accuratezza non ancora validate sul DATS reale.**
Gli export originali sono verificati, ma non è ancora ricostruito l'algoritmo
di calibrazione DATS dalle catture USB. Prima di usare risultati quantitativi,
confrontare resistenze indipendenti (ad esempio 8–10 Ω) e l'altoparlante con gli
export originali, nella stessa banda. Il formato TZZ non è decodificato e i
parametri Thiele/Small vengono solo mostrati se presenti nell'export, non calcolati.
Linux e macOS richiedono verifica pratica del dispositivo e del backend audio.

## Verifica software

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Documentazione: [Streamlit](https://docs.streamlit.io/),
[sounddevice](https://python-sounddevice.readthedocs.io/),
[manuale DATS V3](https://www.daytonaudio.com/images/resources/dats%20v3%20quick%20start.pdf).
