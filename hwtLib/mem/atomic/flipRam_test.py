#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwt.constants import Time, NOP, WRITE, READ
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.mem.atomic.flipRam import FlipRam


class FlipRamTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        cls.dut = FlipRam()
        cls.compileSim(cls.dut)

    def test_basic(self):
        dut = self.dut
        MAGIC0 = 80
        MAGIC1 = 30
        N = 10

        dut.select_sig._ag.data.append(0)
        dut.firstA._ag.requests.extend([(WRITE, i, MAGIC0 + i)
                                      for i in range(N)])
        dut.secondA._ag.requests.extend([(WRITE, i, MAGIC1 + i)
                                       for i in range(N)])

        dut.firstA._ag.requests.extend([(READ, i) for i in range(N)])
        dut.secondA._ag.requests.extend([(READ, i) for i in range(N)])

        self.runSim(N * 40 * Time.ns)

        self.assertValSequenceEqual(dut.firstA._ag.r_data, [MAGIC0 + i
                                                          for i in range(N)])
        self.assertValSequenceEqual(dut.secondA._ag.r_data, [MAGIC1 + i
                                                           for i in range(N)])

    def test_flip(self):
        dut = self.dut
        MAGIC0 = 80
        MAGIC1 = 30
        N = 3

        dut.select_sig._ag.data.extend(
            [0 for _ in range(N)]
            + [1 for _ in range(2 * N)])
        dut.firstA._ag.requests.extend(
            [(WRITE, i, MAGIC0 + i) for i in range(N)]
            + [NOP for _ in range(2 * N)])
        dut.secondA._ag.requests.extend(
            [(WRITE, i, MAGIC1 + i) for i in range(N)]
            + [NOP for _ in range(2 * N)])

        dut.firstA._ag.requests.extend([(READ, i % N) for i in range(N)])
        dut.secondA._ag.requests.extend([(READ, i % N) for i in range(N)])

        self.runSim(3 * N * 40 * Time.ns)

        self.assertValSequenceEqual(dut.firstA._ag.r_data, [MAGIC1 + i
                                                          for i in range(N)])
        self.assertValSequenceEqual(dut.secondA._ag.r_data, [MAGIC0 + i
                                                           for i in range(N)])


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([FlipRamTC("test_withStops")])
    suite = testLoader.loadTestsFromTestCase(FlipRamTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
