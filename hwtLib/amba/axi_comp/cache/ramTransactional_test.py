#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.constants import NOP
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.axi_comp.cache.ramTransactional import RamTransactional
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import mask


class RamTransactionalTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        cls.u = u = RamTransactional()
        u.ID_WIDTH = 2
        u.DATA_WIDTH = 32
        u.ADDR_WIDTH = 16
        u.WORDS_WIDTH = 64
        u.ITEMS = 32
        u.MAX_BLOCK_DATA_WIDTH = 8

        cls.compileSim(u)

    def test_basic(self):
        u = self.u
        TEST_LEN = u.ITEMS
        RAM_WORDS = u.WORDS_WIDTH // u.DATA_WIDTH
        # Skip write phase
        u.r.addr._ag.data.extend([NOP for i in range(0, 10)])
        # Read during writing/flushing -> delays it after write
        u.r.addr._ag.data.extend([(0, i) for i in range(0, 10)])
        testAddr = [(0, i, 0) for i in range(0, TEST_LEN)]
        testInitData = [(i, mask(u.DATA_WIDTH // 8), int((i + 1) % RAM_WORDS == 0)) for i in range(0, TEST_LEN * RAM_WORDS)]
        u.w.addr._ag.data.extend(testAddr)
        u.w.data._ag.data.extend(testInitData)
        testSecondAddr = [(0, i, 1) for i in range(0, TEST_LEN)]
        testSecondData = [(i, mask(u.DATA_WIDTH // 8), int((i + 1) % RAM_WORDS == 0)) for i in reversed(range(0, TEST_LEN * RAM_WORDS))]
        u.w.addr._ag.data.extend(testSecondAddr)
        u.w.data._ag.data.extend(testSecondAddr)
        self.runSim((TEST_LEN + 20) * CLK_PERIOD)
        self.assertValSequenceEqual(u.r.data._ag.data, testSecondData, "Read data after flush mismatch")
        self.assertValSequenceEqual(u.flush_data.addr._ag.data, testAddr, "Flush addr mismatch")
        self.assertValSequenceEqual(u.flush_data.data._ag.data, testInitData, "Flush data mismatch")


RamTransactionalTCs = [
    RamTransactionalTC,
]

if __name__ == "__main__":
    import unittest
    suite = unittest.TestSuite()
    for tc in RamTransactionalTCs:
        suite.addTest(unittest.makeSuite(tc))
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
