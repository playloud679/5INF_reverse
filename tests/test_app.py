import unittest
import numpy as np
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_successive_measurements_are_preserved(self):
        device = {'id': 1, 'name': 'USB AUDIO CODEC', 'api': 'Test', 'hostapi': 0,
                  'max_input_channels': 2, 'max_output_channels': 2}
        with patch('dats_audio.devices', return_value=[device]), patch('dats_sweep.acquire_sweep',
                side_effect=lambda f, *args: (np.full(len(f), .5+0j), np.full(len(f), 30.))):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
            next(c for c in app.checkbox if 'Ho selezionato' in c.label).check().run()
            app.session_state['calibration'] = {'open': np.full(512, 2+0j),
                'short': np.zeros(512, dtype=complex), 'load': np.ones(512, dtype=complex)}
            app.run()
            for _ in range(2):
                next(b for b in app.button if b.label == 'Misura componente').click().run(timeout=30)
                self.assertEqual(len(app.exception), 0)
                self.assertFalse(next(b for b in app.button if b.label == 'Misura componente').disabled)
            names = list(app.session_state['measurements'])
            self.assertEqual(len(names), 2)
            self.assertEqual(names[1], names[0] + ' (2)')
            self.assertEqual(app.session_state['live_result'], names[1])
            self.assertEqual(len(app.session_state['calibration']), 3)

    def test_calibration_confirmation_survives_rerun(self):
        device = {'id': 1, 'name': 'USB AUDIO CODEC', 'api': 'Test', 'hostapi': 0,
                  'max_input_channels': 2, 'max_output_channels': 2}
        with patch('dats_audio.devices', return_value=[device]), patch('dats_sweep.acquire_sweep',
                side_effect=lambda frequencies, *args: (np.ones(len(frequencies), dtype=complex), np.full(len(frequencies), 30.))):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
            next(c for c in app.checkbox if 'Ho selezionato' in c.label).check().run()
            next(b for b in app.button if b.label == 'Prova segnale senza calibrazione').click().run(timeout=30)
            self.assertEqual(app.session_state['calibration'], {})
            self.assertEqual(app.session_state['measurements'], {})
            self.assertEqual(len(app.exception), 0)
            next(b for b in app.button if b.label == 'Acquisisci aperto').click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertIn('open', app.session_state['calibration'])
            self.assertTrue(any('Circuito aperto: riferimento acquisito' in s.value for s in app.success))
            app.run()
            self.assertTrue(any('Circuito aperto: riferimento acquisito' in s.value for s in app.success))
            next(b for b in app.button if b.label == 'Acquisisci corto / zero').click().run(timeout=30)
            self.assertIn('short', app.session_state['calibration'])
            next(b for b in app.button if b.label == 'Acquisisci resistenza nota').click().run(timeout=30)
            self.assertIn('load', app.session_state['calibration'])
            self.assertFalse(next(b for b in app.button if b.label == 'Misura componente').disabled)
            self.assertEqual(len(app.exception), 0)

    def test_offline_reference_workflow(self):
        with patch('dats_audio.devices', return_value=[]):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            next(b for b in app.button if b.label == 'Carica i riferimenti DATS').click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.session_state['measurements']), 3)
            self.assertEqual(app.metric[0].value, '344')
            next(b for b in app.button if b.label == 'Svuota archivio della sessione').click().run(timeout=30)
            self.assertEqual(len(app.session_state['measurements']), 0)
            self.assertEqual(len(app.exception), 0)

    def test_audio_backend_error(self):
        with patch('dats_audio.devices', side_effect=OSError('PortAudio unavailable')):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any('Audio non disponibile' in e.value for e in app.error))

    def test_calibration_invalidated_on_level_change(self):
        device = {'id': 1, 'name': 'USB AUDIO CODEC', 'api': 'Test', 'hostapi': 0,
                  'max_input_channels': 2, 'max_output_channels': 2}
        with patch('dats_audio.devices', return_value=[device]):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            app.session_state['calibration'] = {'open': [1], 'short': [2], 'load': [3]}
            next(s for s in app.slider if s.label == 'Livello rispetto allo sweep originale [dB]').set_value(-18).run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.session_state['calibration'], {})
            self.assertTrue(next(b for b in app.button if b.label == 'Misura componente').disabled)


if __name__ == '__main__':
    unittest.main()
