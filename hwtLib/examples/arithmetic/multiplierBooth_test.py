from hwt.simulator.simTestCase import SimTestCase
from hwtLib.examples.arithmetic.multiplierBooth import MultiplierBooth
from hwtSimApi.constants import CLK_PERIOD


class MultiplierBoothTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        cls.dut = dut = MultiplierBooth()
        dut.DATA_WIDTH = 4
        cls.compileSim(dut)

    def test_possitive(self):
        dut = self.dut
        din = dut.dataIn._ag.data
        ref = []
        for a, b in [
                (0, 0), (0, 1), (1, 0),
                (1, 1),
                (1, 2),
                (1, 2),
                (2, 2),
                (3, 2), (2, 3), (3, 3),
                (7, 3),
                (4, 5),
                (5, 4),
                (7, 7),
                ]:
            din.append((a, b))
            ref.append(a * b)

        self.runSim(CLK_PERIOD * (len(din) * dut.RESULT_WIDTH + 15))

        self.assertValSequenceEqual(dut.dataOut._ag.data, ref)


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([MultiplierBoothTC("test_possitive")])
    suite = testLoader.loadTestsFromTestCase(MultiplierBoothTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)

