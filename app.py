"""Streamlit UI for DATS Lab. Docs: docs/modules/app.md"""
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dats_core import Measurement, parse_measurement, calibrated_impedance, resonance, inductance
from dats_audio import acquire, devices
from dats_sweep import acquire_sweep

ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / 'VERSION').read_text().strip()
st.set_page_config(page_title='DATS Lab', page_icon='📈', layout='wide')
st.title('DATS Lab')
st.caption(f'Impedenza, fase e confronto delle misure · Dayton Audio DATS V3 · v{VERSION}')
if 'measurements' not in st.session_state:
    st.session_state.measurements = {}
if 'calibration' not in st.session_state:
    st.session_state.calibration = {}


def load(data, name):
    try:
        st.session_state.measurements[name] = parse_measurement(data, name)
    except ValueError as exc:
        st.error(f'{name}: {exc}')


with st.sidebar:
    st.header('Archivio misure')
    uploads = st.file_uploader('Importa TXT, ZMA o CSV', type=['txt', 'zma', 'csv'], accept_multiple_files=True)
    if st.button('Importa file selezionati', disabled=not uploads):
        for file in uploads:
            load(file.getvalue(), file.name)
    if st.button('Carica i riferimenti DATS'):
        for filename, label in [('real drv.txt', 'DATS · altoparlante'),
                                ('shorted.txt', 'DATS · cortocircuito'),
                                ('Exported Impedance Data.txt', 'DATS · 1 kΩ')]:
            path = ROOT / 'analysis' / filename
            if path.exists():
                load(path.read_bytes(), label)
            else:
                st.warning(f'File mancante: {filename}')
    st.caption('I progetti binari TZZ non sono ancora importabili. Usare l’export di impedenza del software DATS.')
    if st.button('Svuota archivio della sessione'):
        st.session_state.measurements = {}
    st.caption('Le misure restano nella sessione: scaricarle prima di chiudere o ricaricare la pagina.')

curves, hardware, evidence = st.tabs(['Curve e confronto', 'Acquisizione DATS', 'Riferimenti USB'])
with curves:
    measurements = st.session_state.measurements
    if not measurements:
        st.info('Carica i riferimenti DATS dalla barra laterale oppure importa una misura.')
    else:
        selected = st.multiselect('Curve visibili', list(measurements), default=list(measurements))
        logarithmic = st.checkbox('Scala logaritmica dell’impedenza', value=False)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.09)
        for name in selected:
            m = measurements[name]
            fig.add_trace(go.Scatter(x=m.frequency, y=m.impedance, name=name, legendgroup=name), row=1, col=1)
            fig.add_trace(go.Scatter(x=m.frequency, y=m.phase, name=name, legendgroup=name, showlegend=False), row=2, col=1)
        fig.update_xaxes(type='log', title_text='Frequenza [Hz]', row=2, col=1)
        fig.update_xaxes(type='log', row=1, col=1)
        fig.update_yaxes(title_text='Impedenza [Ω]', type='log' if logarithmic else 'linear', row=1, col=1)
        fig.update_yaxes(title_text='Fase [°]', row=2, col=1)
        fig.update_layout(height=620, margin=dict(t=20), hovermode='x unified')
        st.plotly_chart(fig, width='stretch')
        detail = st.selectbox('Dettaglio ed esportazione', list(measurements))
        m = measurements[detail]
        a, b, c = st.columns(3)
        a.metric('Punti', len(m.frequency))
        res = resonance(m)
        b.metric('Risonanza fs / Zmax', f'{res[0]:.2f} Hz / {res[1]:.3f} Ω' if res else 'non trovata')
        le = [inductance(m, f) for f in (1000, 10000)]
        c.metric('Le a 1 kHz / 10 kHz', ' / '.join(f'{x * 1e3:.3f} mH' if x is not None else 'n/d' for x in le))
        st.caption('fs è il massimo locale interno con fase che passa per zero, non il massimo globale. '
                   'Le = Im(Z)/(2πf). Non sono parametri Thiele/Small completi.')
        if m.metadata.get('experimental'):
            st.warning('Misura sperimentale: accuratezza sul DATS non ancora validata.')
        if m.metadata:
            with st.expander('Parametri e provenienza'):
                st.json(m.metadata)
        a, b = st.columns(2)
        a.download_button('Scarica ZMA', m.zma(), 'misura.zma', 'text/plain')
        b.download_button('Scarica CSV', m.frame().to_csv(index=False), 'misura.csv', 'text/csv')
        with st.expander('Dati numerici'):
            st.dataframe(m.frame(), width='stretch')
        if len(measurements) > 1:
            st.subheader('Confronto numerico')
            reference_name = st.selectbox('Riferimento', [n for n in measurements if n != detail])
            ref = measurements[reference_name]
            mask = (m.frequency >= ref.frequency[0]) & (m.frequency <= ref.frequency[-1])
            if mask.any():
                expected = np.interp(np.log(m.frequency[mask]), np.log(ref.frequency), ref.impedance)
                error = m.impedance[mask] - expected
                st.metric('Errore RMS sul modulo nella banda comune', f'{np.sqrt(np.mean(error ** 2)):.5g} Ω')
                st.caption('Il riferimento viene interpolato rispetto al logaritmo della frequenza; nessuna estrapolazione.')
            else:
                st.info('Le curve non hanno frequenze in comune.')

with hardware:
    st.subheader('Acquisizione locale · sperimentale')
    st.write('Il DATS deve essere collegato al computer che esegue Streamlit. Chiudere il software DATS originale prima dell’acquisizione.')
    st.warning('Collegare soltanto componenti scollegati da amplificatori, altre apparecchiature e masse esterne. La conversione in ohm richiede una nuova calibrazione in questa app.')
    try:
        available = devices()
        inputs = [d for d in available if d['max_input_channels'] >= 2]
        outputs = [d for d in available if d['max_output_channels'] >= 2]
    except Exception as exc:
        st.error(f'Audio non disponibile: {exc}')
        inputs, outputs = [], []
    if inputs and outputs:
        def label(d):
            return f"{d['id']} · {d['name']} · {d['api']}"
        def preferred(items):
            return next((i for i, d in enumerate(items) if 'USB AUDIO' in d['name'].upper()), 0)
        a, b = st.columns(2)
        inp = a.selectbox('Ingresso stereo', inputs, index=preferred(inputs), format_func=label)
        out = b.selectbox('Uscita stereo', outputs, index=preferred(outputs), format_func=label)
        excitation = st.selectbox('Segnale di misura', ['Sweep dalla cattura DATS', 'Toni separati (diagnostica)'])
        sweep_db = st.slider('Livello rispetto allo sweep originale [dB]', -24, 0, 0)
        st.caption('Lo sweep riproduce i campioni estratti dalla cattura, ricampionati da 48 a 44,1 kHz. '
                   '0 dB mantiene l’ampiezza digitale catturata; il volume di sistema può cambiarne il livello effettivo. '
                   'I limiti di frequenza sotto definiscono i punti analizzati, non tagliano lo sweep emesso.')
        a, b, c = st.columns(3)
        low = a.number_input('Frequenza iniziale [Hz]', 10.0, 19000.0, 20.0)
        high = b.number_input('Frequenza finale [Hz]', 20.0, 20000.0, 20000.0)
        if excitation == 'Sweep dalla cattura DATS':
            count = c.select_slider('Punti della curva', options=[96, 256, 512, 1024, 2048], value=512, key='sweep_points')
            st.caption('Più punti rendono la curva più dettagliata senza allungare lo sweep. '
                       'Alle frequenze basse alcuni punti possono condividere gli stessi campioni spettrali: '
                       'la risoluzione fisica resta limitata dalla durata del segnale. '
                       'Cambiare il numero di punti richiede una nuova calibrazione.')
        else:
            count = c.select_slider('Numero di frequenze', options=[12, 24, 48, 96], value=24, key='tone_points')
        a, b, c = st.columns(3)
        db = a.slider('Livello digitale [dBFS]', -50, -20, -34, disabled=excitation == 'Sweep dalla cattura DATS')
        channel = b.selectbox('Canale di uscita', ['Entrambi (DATS)', 'Sinistro', 'Destro'], disabled=excitation == 'Sweep dalla cattura DATS')
        resistance = c.number_input('Resistenza di riferimento [Ω]', .1, 100000.0, 1000.0)
        st.caption('Il livello digitale non indica la tensione ai morsetti. Mantenere invariati volume di sistema, guadagni e collegamenti audio durante calibrazione e misura.')
        frequencies = np.geomspace(low, high, count)
        signature = ('sweep-v3', excitation, sweep_db, inp['id'], inp['name'], inp['api'], out['id'], out['name'], out['api'], low, high, count, db, channel, resistance)
        if st.session_state.get('audio_signature') != signature:
            st.session_state.calibration = {}
            st.session_state.pop('acquisition_notice', None)
            st.session_state.audio_signature = signature
        confirmed = st.checkbox('Ho selezionato il DATS in ingresso e uscita e verificato che il componente sia scollegato da altre apparecchiature.')
        st.subheader('1. Calibrazione')
        ready = confirmed and high > low and inp['hostapi'] == out['hostapi']
        if not confirmed:
            st.info('Spunta la conferma del dispositivo e dei collegamenti qui sopra per abilitare i pulsanti.')
        elif high <= low:
            st.error('La frequenza finale deve essere maggiore di quella iniziale.')
        elif inp['hostapi'] != out['hostapi']:
            st.error('Scegli ingresso e uscita con la stessa API audio.')
        mode = 'Componente da misurare'
        calibration_clicked = False
        keys = {'Circuito aperto': 'open', 'Cortocircuito': 'short', 'Resistenza nota': 'load'}
        calibration = st.session_state.calibration
        st.caption('Riferimenti acquisiti: ' + (', '.join(k for k, v in keys.items() if v in calibration) or 'nessuno'))
        instructions = {'open': 'Lascia i morsetti separati, senza componente.',
                        'short': 'Unisci saldamente i due morsetti per acquisire lo zero dei cavetti.',
                        'load': f'Collega la resistenza di riferimento da {resistance:g} Ω.'}
        buttons = {'open': 'Acquisisci aperto', 'short': 'Acquisisci corto / zero', 'load': 'Acquisisci resistenza nota'}
        for column, (title, key) in zip(st.columns(3), keys.items()):
            column.metric(title, 'Acquisito' if key in calibration else 'Da acquisire')
            column.write(instructions[key])
            if column.button(buttons[key], key=f'btn_cal_{key}', disabled=not ready):
                mode = title
                calibration_clicked = True
        if st.session_state.get('acquisition_notice'):
            st.success(st.session_state.acquisition_notice)
        st.caption('I riferimenti di calibrazione non generano una curva nell’archivio. '
                   'La curva viene creata solo acquisendo il componente dopo tutti e tre i riferimenti.')
        st.caption('Ogni pulsante acquisisce il riferimento indicato. La prova del segnale non salva lo zero. '
                   'La cancellazione sotto elimina solo i riferimenti memorizzati.')
        if st.button('Cancella riferimenti di calibrazione'):
            st.session_state.calibration = {}
            st.session_state.pop('acquisition_notice', None)
            st.rerun()
        st.subheader('2. Misura del componente')
        st.write('Dopo i tre riferimenti, collega il componente ai morsetti.')
        name = st.text_input('Nome della nuova misura', 'DATS · misura sperimentale')
        st.caption('Puoi ripetere Misura componente senza rifare la calibrazione finché le impostazioni restano invariate. '
                   'Le acquisizioni con lo stesso nome vengono numerate e conservate separatamente.')
        diagnostic = st.button('Prova segnale senza calibrazione', disabled=not ready)
        st.caption('La prova emette il segnale selezionato e acquisisce i due ingressi; non produce un’impedenza in ohm.')
        measurement_ready = ready and all(k in calibration for k in ('open', 'short', 'load')) and bool(name.strip())
        if not all(k in calibration for k in ('open', 'short', 'load')):
            st.info('Per misurare in ohm, acquisisci prima aperto, corto e resistenza nota con i pulsanti sopra.')
        if st.button('Misura componente', type='primary', disabled=not measurement_ready) or diagnostic or calibration_clicked:
            st.session_state.pop('acquisition_notice', None)
            progress = st.progress(0.0, text='Acquisizione in corso…')
            try:
                if excitation == 'Sweep dalla cattura DATS':
                    ratio, quality = acquire_sweep(frequencies, inp['id'], out['id'],
                                                  10 ** (sweep_db / 20), progress.progress)
                else:
                    ratio, quality = acquire(frequencies, inp['id'], out['id'], 10 ** (db / 20),
                                             {'Sinistro': 0, 'Destro': 1, 'Entrambi (DATS)': 2}[channel], progress.progress)
                import pandas as pd
                valid = np.isfinite(ratio)
                rejected = int(np.count_nonzero(~valid))
                quality_note = (f' {rejected} punti esclusi perché sotto la soglia di qualità.' if rejected else '')
                st.session_state['last_raw'] = pd.DataFrame({
                    'frequency_hz': frequencies, 'ratio_real': ratio.real,
                    'ratio_imag': ratio.imag, 'quality_db': quality, 'valid': valid})
                st.session_state['last_raw_mode'] = 'Prova senza calibrazione' if diagnostic else mode
                if diagnostic:
                    st.session_state.acquisition_notice = ('Prova completata: segnali elettrici acquisiti. '
                        'Questo non conferma l’emissione acustica né l’accuratezza dell’impedenza. '
                        f'Indicatore di qualità minimo sui punti validi: {quality[valid].min():.1f} dB.' + quality_note)
                elif mode in keys:
                    calibration[keys[mode]] = ratio
                    st.session_state.acquisition_notice = f'{mode}: riferimento acquisito. Punti validi: {valid.sum()}/{len(valid)}.' + quality_note
                else:
                    for reference in calibration.values():
                        valid &= np.isfinite(reference)
                    if np.count_nonzero(valid) < 2:
                        raise ValueError('Meno di due punti validi comuni alla misura e ai tre riferimenti. Ripetere la calibrazione.')
                    z = calibrated_impedance(ratio[valid], calibration['short'][valid], calibration['open'][valid], calibration['load'][valid], resistance)
                    saved_name = name.strip()
                    suffix = 2
                    while saved_name in st.session_state.measurements:
                        saved_name = f'{name.strip()} ({suffix})'
                        suffix += 1
                    st.session_state.measurements[saved_name] = Measurement(saved_name, frequencies[valid], np.abs(z), np.angle(z, deg=True),
                        {'experimental': True, 'calibration': 'open/short/load', 'reference_ohm': resistance,
                         'excluded_frequency_hz': frequencies[~valid].tolist(), 'requested_points': len(frequencies),
                         'sample_rate_hz': 44100, 'level_dbfs': db if excitation.startswith('Toni') else None, 'quality_min_db': float(quality[valid].min()),
                         'excitation': excitation, 'sweep_relative_db': sweep_db if excitation.startswith('Sweep') else None,
                         'input': label(inp), 'output': label(out), 'output_channel': 'Entrambi' if excitation.startswith('Sweep') else channel})
                    st.session_state.live_result = saved_name
                    st.session_state.acquisition_notice = (f'{saved_name}: acquisita, {valid.sum()}/{len(valid)} punti validi comuni alla calibrazione. '
                        'Impedenza e fase sono visualizzate qui sotto e nella scheda Curve e confronto.')
                st.rerun()
            except Exception as exc:
                st.error(f'Acquisizione interrotta: {exc}')
            finally:
                progress.empty()
        if 'last_raw' in st.session_state:
            st.download_button('Scarica ultima acquisizione grezza (CSV)',
                st.session_state.last_raw.to_csv(index=False), 'acquisizione_grezza.csv', 'text/csv')
            st.caption('Ultima acquisizione grezza: ' + st.session_state.last_raw_mode)
    else:
        st.info('Nessuna coppia di dispositivi stereo disponibile. È possibile usare importazione e confronto senza hardware.')

    live_measurements = {key: value for key, value in st.session_state.measurements.items()
                         if value.metadata.get('experimental')}
    st.subheader('Risultato: impedenza e fase')
    if live_measurements:
        if st.session_state.get('live_result') not in live_measurements:
            st.session_state.live_result = list(live_measurements)[-1]
        result_name = st.selectbox('Misura acquisita da visualizzare', list(live_measurements),
                                   index=None, key='live_result')
        result = live_measurements[result_name]
        excluded = result.metadata.get('excluded_frequency_hz', [])
        if excluded:
            st.warning(f'{len(excluded)} frequenze escluse: segnale insufficiente nella misura o in almeno un riferimento. '
                       'Le linee del grafico collegano i punti validi; non rappresentano misure nelle frequenze escluse.')
            with st.expander('Frequenze escluse [Hz]'):
                st.write(excluded)
        result_fig = make_subplots(specs=[[{'secondary_y': True}]])
        result_fig.add_trace(go.Scatter(x=result.frequency, y=result.impedance, name='Impedenza [Ω]',
                                       line=dict(color='#2684ff')), secondary_y=False)
        result_fig.add_trace(go.Scatter(x=result.frequency, y=result.phase, name='Fase [°]',
                                       line=dict(color='#ef553b')), secondary_y=True)
        result_fig.update_xaxes(type='log', title_text='Frequenza [Hz]')
        result_fig.update_yaxes(title_text='Impedenza [Ω]', secondary_y=False)
        result_fig.update_yaxes(title_text='Fase [°]', secondary_y=True)
        result_fig.update_layout(height=480, hovermode='x unified', margin=dict(t=30))
        st.plotly_chart(result_fig, width='stretch', key='live_impedance_phase')
        st.caption('Blu: modulo dell’impedenza, asse sinistro. Rosso: fase, asse destro. '
                   'Misura sperimentale: accuratezza ancora da validare.')
        st.download_button('Esporta questa misura ZMA', result.zma(), 'misura.zma', 'text/plain', key='live_zma')
    else:
        st.info('Dopo la calibrazione, collega il driver e premi Misura componente: il grafico apparirà qui. '
                'Le acquisizioni dei riferimenti e la prova del segnale non generano una curva di impedenza.')

with evidence:
    st.subheader('Catture e riferimenti disponibili')
    st.write('Le catture identificano USB AUDIO CODEC (08bb:29c0), uscita 0x02 e ingresso 0x84. I payload sono presenti; la conversione delle catture in curve di impedenza non è ancora validata.')
    st.write('L’app può riprodurre lo sweep estratto dalla cattura oppure toni separati per diagnosi. '
             'La calibrazione a tre riferimenti e l’analisi spettrale sono sperimentali; non replicano l’algoritmo proprietario DATS.')
    for filename in ['reference_comparison.json', 'capture_summary.json']:
        path = ROOT / 'analysis' / filename
        if path.exists():
            with st.expander(filename):
                st.json(path.read_text(encoding='utf-8'))
