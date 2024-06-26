#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from math import ceil

from hwt.simulator.simTestCase import SimTestCase
from hwtLib.xilinx.primitive.examples.dsp48e1Add import Dsp48e1Add
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import mask


class Dsp48e1Add_48b_noRegsTC(SimTestCase):
    DATA_WIDTH = 48
    REG_IN = False
    REG_OUT = False

    @classmethod
    def setUpClass(cls):
        cls.dut = dut = Dsp48e1Add()
        dut.DATA_WIDTH = cls.DATA_WIDTH
        dut.REG_IN = cls.REG_IN
        dut.REG_OUT = cls.REG_OUT
        cls.compileSim(dut)

    def test_3x_exact(self):
        dut = self.dut
        dut.data_in._ag.data.extend([(7, 16), (21, 19), (1, 2)])
        ref = [7 + 16, 21 + 19, 1 + 2]

        self.runSim((8 + ceil(self.DATA_WIDTH / 48)) * CLK_PERIOD)

        self.assertValSequenceEqual(dut.data_out._ag.data, ref)

    def test_40x_random(self, N=40, randomize=True):
        dut = self.dut
        r = self._rand
        din = []
        ref = []
        m = mask(self.DATA_WIDTH)
        for _ in range(N):
            a = r.randint(0, m)
            b = r.randint(0, m)
            res = (a + b) & m
            din.append((a, b))
            ref.append(res)

        dut.data_in._ag.data.extend(din)

        if randomize:
            self.randomize(dut.data_in)
            self.randomize(dut.data_out)

        self.runSim((5 * N + 10) * CLK_PERIOD)

        self.assertValSequenceEqual(dut.data_out._ag.data, ref)


class Dsp48e1Add_48b_inRegsTC(Dsp48e1Add_48b_noRegsTC):
    REG_IN = True


class Dsp48e1Add_48b_outRegsTC(Dsp48e1Add_48b_noRegsTC):
    REG_OUT = True


class Dsp48e1Add_48b_inOutRegsTC(Dsp48e1Add_48b_noRegsTC):
    REG_IN = True
    REG_OUT = True


class Dsp48e1Add_96b_noRegsTC(Dsp48e1Add_48b_noRegsTC):
    DATA_WIDTH = 96


class Dsp48e1Add_96b_inRegsTC(Dsp48e1Add_48b_inRegsTC):
    DATA_WIDTH = 96


class Dsp48e1Add_96b_outRegsTC(Dsp48e1Add_48b_outRegsTC):
    DATA_WIDTH = 96


class Dsp48e1Add_96b_inOutRegsTC(Dsp48e1Add_48b_inOutRegsTC):
    DATA_WIDTH = 96


class Dsp48e1Add_256b_noRegsTC(Dsp48e1Add_48b_noRegsTC):
    DATA_WIDTH = 256


class Dsp48e1Add_256b_inRegsTC(Dsp48e1Add_48b_inRegsTC):
    DATA_WIDTH = 256


class Dsp48e1Add_256b_outRegsTC(Dsp48e1Add_48b_outRegsTC):
    DATA_WIDTH = 256


class Dsp48e1Add_256b_inOutRegsTC(Dsp48e1Add_48b_inOutRegsTC):
    DATA_WIDTH = 256


Dsp48e1Add_TCs = [
    Dsp48e1Add_48b_noRegsTC,
    Dsp48e1Add_48b_inRegsTC,
    Dsp48e1Add_48b_outRegsTC,
    Dsp48e1Add_48b_inOutRegsTC,
    Dsp48e1Add_96b_noRegsTC,
    Dsp48e1Add_96b_inRegsTC, # 1-clk cascade
    Dsp48e1Add_96b_outRegsTC, # cascade, in reg merged for non-first dsp
    Dsp48e1Add_96b_inOutRegsTC, # cascade
    Dsp48e1Add_256b_noRegsTC, # only part of last DSP used
    Dsp48e1Add_256b_inRegsTC, # 1-clk cascade, only part of last DSP used
    Dsp48e1Add_256b_outRegsTC, # cascade, in reg merged for non-first dsp, only part of last DSP used
    Dsp48e1Add_256b_inOutRegsTC, # cascade, only part of last DSP used
]

if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Dsp48e1Add_48b_noRegsTC("test_3_exact_values")])
    loadedTcs = [testLoader.loadTestsFromTestCase(tc) for tc in Dsp48e1Add_TCs]
    suite = unittest.TestSuite(loadedTcs)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
