import unittest
from pathlib import Path
import numpy as np
from dats_core import Measurement, parse_measurement, calibrated_impedance, channel_ratio, resonance, inductance


class CoreTests(unittest.TestCase):
    def test_original_exports_and_roundtrip(self):
        root = Path(__file__).resolve().parents[1] / 'analysis'
        for name in ['real drv.txt', 'shorted.txt', 'Exported Impedance Data.txt']:
            m = parse_measurement((root / name).read_bytes(), name)
            self.assertEqual(len(m.frequency), 344)
            np.testing.assert_allclose(parse_measurement(m.zma().encode(), name).impedance, m.impedance)
            np.testing.assert_allclose(parse_measurement(m.frame().to_csv(index=False).encode(), name).phase, m.phase)

    def test_invalid_curves(self):
        for data in [b'1 2 3\n1 3 4', b'1 nan 0\n2 3 0', b'1 -2 0\n2 3 0', b'garbage']:
            with self.assertRaises(ValueError):
                parse_measurement(data, 'bad')

    def test_unknown_bridge_calibration(self):
        # Independent synthetic fractional-linear analog bridge.
        a, b, c, d = 2 + .1j, 3 - .4j, .02 + .001j, 7 + .2j
        bridge = lambda z: (a * z + b) / (c * z + d)
        expected = np.array([4 + 0j, 8 + 3j, 30 - 12j])
        actual = calibrated_impedance(bridge(expected), bridge(0), a / c, bridge(1000), 1000)
        np.testing.assert_allclose(actual, expected, rtol=1e-10)
        with self.assertRaises(ValueError):
            calibrated_impedance(1, 0, 2, 0, 1000)

    def test_channel_phase(self):
        rate, frequency = 44100, 137.5
        t = np.arange(10000) / rate
        signal = np.column_stack([.1 * np.cos(2*np.pi*frequency*t + .4),
                                  .03 * np.cos(2*np.pi*frequency*t + .9)])
        ratio, quality = channel_ratio(signal, frequency, rate)
        np.testing.assert_allclose(ratio, .3 * np.exp(.5j), atol=1e-10)
        self.assertGreater(quality, 100)
        with self.assertRaises(ValueError):
            channel_ratio(signal * 20, frequency, rate)

    def test_resonance_ignores_inductive_rise_and_le(self):
        f = np.geomspace(20, 20000, 600)
        w = 2 * np.pi * f
        motional = 1 / (1 / 40 + 1j * w * 1e-3 + 1 / (1j * w * 0.01))  # parallel RLC, fs ~50 Hz
        z = 6 + 1j * w * 2e-3 + motional
        m = Measurement('x', f, np.abs(z), np.angle(z, deg=True))
        self.assertGreater(np.abs(z[-1]), np.abs(z).max() * .99)  # global max is the HF rise
        fs, zmax = resonance(m)
        self.assertLess(fs, 100)
        self.assertGreater(zmax, 6)
        self.assertAlmostEqual(inductance(m, 10000) * 1e3, 2, delta=.05)
        self.assertIsNone(inductance(m, 30000))


if __name__ == '__main__':
    unittest.main()
