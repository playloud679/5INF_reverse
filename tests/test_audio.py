import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from dats_audio import acquire, DEVICE_LOCK


class AudioTests(unittest.TestCase):
    def test_stream_failure_releases_device(self):
        audio = MagicMock()
        audio.query_devices.return_value = {'hostapi': 0}
        audio.playrec.side_effect = RuntimeError('device disconnected')
        with patch.dict(sys.modules, {'sounddevice': audio}):
            with self.assertRaisesRegex(RuntimeError, 'disconnected'):
                acquire([100], 1, 2, .02, 0)
        self.assertFalse(DEVICE_LOCK.locked())
        audio.stop.assert_called_once()

    def test_duplex_pipeline(self):
        audio = MagicMock()
        audio.query_devices.return_value = {'hostapi': 0}
        audio.get_status.return_value = False
        def record(signal, **kwargs):
            t = np.arange(len(signal)) / kwargs['samplerate']
            return np.column_stack([.1*np.sin(2*np.pi*100*t), .05*np.sin(2*np.pi*100*t + .2)])
        audio.playrec.side_effect = record
        with patch.dict(sys.modules, {'sounddevice': audio}):
            ratio, quality = acquire([100], 1, 2, .02, 0)
        np.testing.assert_allclose(ratio, [.5*np.exp(.2j)], atol=1e-10)
        self.assertFalse(DEVICE_LOCK.locked())
        self.assertGreater(quality[0], 100)

    def test_dats_drives_both_outputs_identically(self):
        audio = MagicMock()
        audio.query_devices.return_value = {'hostapi': 0}
        audio.get_status.return_value = False
        def record(signal, **kwargs):
            np.testing.assert_array_equal(signal[:, 0], signal[:, 1])
            self.assertGreater(np.max(np.abs(signal[:, 0])), .019)
            return signal * np.array([1., .5])
        audio.playrec.side_effect = record
        with patch.dict(sys.modules, {'sounddevice': audio}):
            ratio, _ = acquire([100], 1, 2, .02, 2)
        np.testing.assert_allclose(ratio, [.5], atol=1e-8)
