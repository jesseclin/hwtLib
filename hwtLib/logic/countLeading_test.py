from hwt.simulator.simTestCase import SimTestCase
from hwtLib.logic.countLeading import CountLeadingZeros, CountLeadingOnes
from hwtSimApi.constants import CLK_PERIOD


class CountLeadingTC(SimTestCase):

    def tearDown(self):
        self.rmSim()
        SimTestCase.tearDown(self)

    def test_CountLeadingZeros(self):
        dut = CountLeadingZeros()
        dut.DATA_WIDTH = 4
        self.compileSimAndStart(dut)

        test_values = list(range(2 ** dut.DATA_WIDTH))
        dut.data_in._ag.data.extend(test_values)

        ref = []
        for v in test_values:
            leading = dut.DATA_WIDTH
            while v:
                v >>= 1
                leading -= 1
            ref.append(leading)

        self.runSim((len(ref) + 1) * CLK_PERIOD)
        ref.append(0)

        self.assertValSequenceEqual(dut.data_out._ag.data, ref)

    def test_CountLeadingOnes(self):
        dut = CountLeadingOnes()
        dut.DATA_WIDTH = 4
        self.compileSimAndStart(dut)

        test_values = list(range(2 ** dut.DATA_WIDTH))
        dut.data_in._ag.data.extend(test_values)

        ref = []
        for v in test_values:
            x = 1 << dut.DATA_WIDTH - 1
            leading = 0
            while v & x:
                x >>= 1
                leading += 1
            ref.append(leading)

        self.runSim((len(ref) + 1) * CLK_PERIOD)
        ref.append(4)

        self.assertValSequenceEqual(dut.data_out._ag.data, ref)


if __name__ == '__main__':
    import sys
    import unittest

    testLoader = unittest.TestLoader()
    suite = testLoader.loadTestsFromTestCase(CountLeadingTC)
    runner = unittest.TextTestRunner(verbosity=3)
    sys.exit(not runner.run(suite).wasSuccessful())
