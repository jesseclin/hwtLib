#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import copy
import unittest

from hwt.constants import NOP
from hwt.hwIOs.std import HwIODataRdVld
from hwtLib.handshaked.fifo import HandshakedFifo
from hwtLib.mem.fifo_test import FifoTC


class HsFifoTC(FifoTC):

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = HandshakedFifo(HwIODataRdVld)
        dut.DEPTH = cls.ITEMS
        dut.DATA_WIDTH = 64
        dut.EXPORT_SIZE = True
        cls.compileSim(dut)

    def getFifoItems(self):
        m = self.rtl_simulator.model
        mem = m.fifo_inst.io.memory
        items = set([int(x.read()) for x in mem])
        items.add(int(m.io.dataOut_data.read()))
        return items

    def getUnconsumedInput(self):
        d = copy(self.dut.dataIn._ag.data)
        ad = self.dut.dataIn._ag.actualData
        if ad != NOP:
            d.appendleft(ad)
        return d

    def test_stuckedData(self):
        super(HsFifoTC, self).test_stuckedData()
        self.assertValEqual(self.rtl_simulator.io.dataOut_data, 1)

    def test_tryMore2(self, capturedOffset=1):
        # capturedOffset=1 because handshaked aget can act in same clk
        super(HsFifoTC, self).test_tryMore2(capturedOffset=capturedOffset)


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([HsFifoTC("test_passdata")])
    suite = testLoader.loadTestsFromTestCase(HsFifoTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
