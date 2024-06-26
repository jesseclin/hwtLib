#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.simulator.simTestCase import SimTestCase
from hwtLib.examples.builders.hwException import HwExceptionCatch
from hwtSimApi.constants import CLK_PERIOD
from hwtSimApi.triggers import WaitWriteOnly


class HwExceptionCatch_TC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        cls.dut = HwExceptionCatch()
        cls.compileSim(cls.dut)

    def test_non_error(self):
        data = [i + 3 for i in range(100)]
        dut = self.dut
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.randomize(dut.raise_ExampleHwException1_0)

        dut.dataIn._ag.data.extend(data)

        self.runSim(CLK_PERIOD * 6 * len(data))

        self.assertValSequenceEqual(dut.dataOut._ag.data, data)

    def test_handled_err(self):
        data = [1, 5, 3, 4, 5, 1, 3, 4, 5]
        dut = self.dut
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.randomize(dut.raise_ExampleHwException1_0)

        dut.dataIn._ag.data.extend(data)

        self.runSim(CLK_PERIOD * 12 * len(data))

        self.assertValSequenceEqual(dut.dataOut._ag.data, [d for d in data if d != 1])

    def test_err_dissabled_handling(self):
        data = [43, 1, 5, 3, 4, 5, 1, 3, 4, 5]
        dut = self.dut
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)

        def dissableErrHandling():
            yield WaitWriteOnly()
            dut.raise_ExampleHwException1_0._ag.setEnable(False)

        self.procs.append(dissableErrHandling())
        dut.dataIn._ag.data.extend(data)

        self.runSim(CLK_PERIOD * 12 * len(data))

        self.assertValSequenceEqual(dut.dataOut._ag.data, [43])

    def test_err_causing_stall(self):
        data = [43, 1, 5, 3, 4, 5, 1, 0, 3, 4, 5]
        dut = self.dut
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.randomize(dut.raise_ExampleHwException1_0)
        dut.dataIn._ag.data.extend(data)

        self.runSim(CLK_PERIOD * 12 * len(data))

        self.assertValSequenceEqual(dut.dataOut._ag.data, [43, 5, 3, 4, 5])


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([HwExceptionCatch_TC("test_reply1x")])
    suite = testLoader.loadTestsFromTestCase(HwExceptionCatch_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
