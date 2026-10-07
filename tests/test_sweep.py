import unittest
import numpy as np
from dats_sweep import stimulus, sweep_ratios


class SweepTests(unittest.TestCase):
    def test_resampling_and_gain(self):
        x = stimulus(.25)
        self.assertEqual(x.shape, (145971, 2))
        self.assertLess(np.max(np.abs(x)), .2)
        np.testing.assert_allclose(stimulus(.5), 2*x, atol=1e-7)
        with self.assertRaises(ValueError):
            stimulus(1.1)

    def test_spectral_ratio_with_common_latency_and_noise(self):
        tone = stimulus(.25)[:, 0]
        delayed = np.concatenate([np.zeros(4000), tone[:-4000]])
        rng = np.random.default_rng(123)
        samples = np.column_stack([delayed, delayed * 3]) + rng.normal(0, 1e-6, (len(tone), 2))
        ratio, quality = sweep_ratios(samples, np.geomspace(20, 20000, 24))
        np.testing.assert_allclose(ratio, 3, atol=.003)
        self.assertGreater(quality.min(), 15)

    def test_silent_input_rejected(self):
        with self.assertRaisesRegex(ValueError, 'insufficiente'):
            sweep_ratios(np.zeros((44100*3, 2)), [1000])

    def test_missing_high_frequency_does_not_discard_good_points(self):
        x = stimulus(.25).astype(float)
        spectrum = np.fft.rfft(x, axis=0)
        spectrum[np.fft.rfftfreq(len(x), 1/44100) > 15000] = 0
        filtered = np.fft.irfft(spectrum, n=len(x), axis=0)
        ratio, quality = sweep_ratios(filtered, [100, 1000, 20000])
        self.assertTrue(np.isfinite(ratio[:2]).all())
        self.assertFalse(np.isfinite(ratio[2]))
        self.assertLess(quality[2], 15)
