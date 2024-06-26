#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from _collections import deque
import unittest

from hwt.simulator.simTestCase import SimTestCase
from hwtLib.peripheral.i2c.intf import I2cAgent
from hwtLib.peripheral.i2c.masterBitCntrl import I2cMasterBitCtrl, \
    NOP, START, READ, WRITE
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import get_bit


class I2CMasterBitCntrlTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        cls.dut = I2cMasterBitCtrl()
        cls.compileSim(cls.dut)

    def test_nop(self):
        dut = self.dut
        dut.cntrl._ag.data.append((NOP, 0))
        dut.clk_cnt_initVal._ag.data.append(4)
        self.runSim(20 * CLK_PERIOD)

        self.assertFalse(dut.i2c._ag.hasTransactionPending())

    def test_startbit(self):
        dut = self.dut
        dut.cntrl._ag.data.extend([(START, 0), (NOP, 0)])
        dut.clk_cnt_initVal._ag.data.append(4)
        self.runSim(60 * CLK_PERIOD)

        self.assertEqual(dut.i2c._ag.bit_cntrl_rx, deque([I2cAgent.START]))

    def test_7bitAddr(self):
        dut = self.dut
        addr = 13
        mode = I2cAgent.READ
        dut.cntrl._ag.data.extend(
            [(START, 0), ] +
            [(WRITE, get_bit(addr, 7 - i - 1)) for i in range(7)] +
            [(WRITE, mode),
             (READ, 0),
             (NOP, 0)
            ])
        dut.clk_cnt_initVal._ag.data.append(4)
        self.runSim(70 * CLK_PERIOD)

        self.assertValSequenceEqual(
            dut.i2c._ag.bit_cntrl_rx,
            [I2cAgent.START] +
            [get_bit(addr, 7 - i - 1)
             for i in range(7)] +
            [mode])


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([I2CMasterBitCntrlTC("test_nop")])
    suite = testLoader.loadTestsFromTestCase(I2CMasterBitCntrlTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
