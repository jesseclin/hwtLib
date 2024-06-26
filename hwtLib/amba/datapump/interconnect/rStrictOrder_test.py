#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.datapump.interconnect.rStricOrder import RStrictOrderInterconnect
from hwtLib.amba.datapump.sim_ram import AxiDpSimRam
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import mask


class RStrictOrderInterconnectTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = RStrictOrderInterconnect()

        dut.ID_WIDTH = 4

        cls.DRIVERS_CNT = 3
        dut.DRIVER_CNT = cls.DRIVERS_CNT

        cls.MAX_TRANS_OVERLAP = 4
        dut.MAX_TRANS_OVERLAP = cls.MAX_TRANS_OVERLAP

        dut.DATA_WIDTH = 64
        cls.compileSim(dut)

    def test_nop(self):
        dut = self.dut
        self.runSim(20 * CLK_PERIOD)

        for d in dut.drivers:
            self.assertEqual(len(d.r._ag.data), 0)

        self.assertEqual(len(dut.rDatapump.req._ag.data), 0)

    def test_passWithouData(self):
        dut = self.dut

        for i, driver in enumerate(dut.drivers):
            driver.req._ag.data.append((i + 1, i + 1, i + 1, 0))

        self.runSim((self.DRIVERS_CNT * 2) * CLK_PERIOD)

        for d in dut.drivers:
            self.assertEqual(len(d.r._ag.data), 0)

        self.assertEqual(len(dut.rDatapump.req._ag.data), self.DRIVERS_CNT)
        for i, req in enumerate(dut.rDatapump.req._ag.data):
            self.assertValSequenceEqual(req,
                                        (i + 1, i + 1, i + 1, 0))

    def test_passWithData(self):
        dut = self.dut

        for i, driver in enumerate(dut.drivers):
            _id = i + 1
            _len = i + 1
            driver.req._ag.data.append((_id, i + 1, _len, 0))
            for i2 in range(_len + 1):
                d = (_id, i + 1, mask(dut.DATA_WIDTH // 8), i2 == _len)
                dut.rDatapump.r._ag.data.append(d)

        self.runSim(20 * CLK_PERIOD)

        for i, d in enumerate(dut.drivers):
            self.assertEqual(len(d.r._ag.data), i + 1 + 1)

        self.assertEqual(len(dut.rDatapump.req._ag.data), self.DRIVERS_CNT)
        for i, req in enumerate(dut.rDatapump.req._ag.data):
            self.assertValSequenceEqual(req,
                                        (i + 1, i + 1, i + 1, 0))

    def test_randomized(self):
        dut = self.dut
        m = AxiDpSimRam(dut.DATA_WIDTH, dut.clk, dut.rDatapump)

        for d in dut.drivers:
            self.randomize(d.req)
            self.randomize(d.r)
        self.randomize(dut.rDatapump.req)
        self.randomize(dut.rDatapump.r)

        def prepare(driverIndex, addr, size, valBase=1, _id=1):
            driver = dut.drivers[driverIndex]
            driver.req._ag.data.append((_id, addr, size - 1, 0))
            expected = []
            _mask = mask(dut.DATA_WIDTH // 8)
            index = addr // (dut.DATA_WIDTH // 8)
            for i in range(size):
                v = valBase + i
                m.data[index + i] = v
                d = (_id, v, _mask, int(i == size - 1))
                expected.append(d)
            return expected

        def check(driverIndex, expected):
            driverData = dut.drivers[driverIndex].r._ag.data
            self.assertEqual(len(driverData), len(expected))
            for d, e in zip(driverData, expected):
                self.assertValSequenceEqual(d, e)

        d0 = prepare(0, 0x1000, 3, 99, _id=0)
        # + prepare(0, 0x2000, 1, 100, _id=0) + prepare(0, 0x3000, 16, 101)
        d1 = prepare(1, 0x4000, 3, 200, _id=1) + prepare(1, 0x5000, 1, 201, _id=1)
        # + prepare(1, 0x6000, 16, 202) #+ prepare(1, 0x7000, 16, 203)

        self.runSim(100 * CLK_PERIOD)

        check(0, d0)
        check(1, d1)

    def test_randomized2(self):
        dut = self.dut
        m = AxiDpSimRam(dut.DATA_WIDTH, dut.clk, dut.rDatapump)
        N = 17

        for d in dut.drivers:
            self.randomize(d.req)
            self.randomize(d.r)
        self.randomize(dut.rDatapump.req)
        self.randomize(dut.rDatapump.r)
        _mask = mask(dut.DATA_WIDTH // 8)

        expected = [[] for _ in dut.drivers]
        for _id, d in enumerate(dut.drivers):
            for i in range(N):
                size = self._rand.getrandbits(3) + 1
                magic = self._rand.getrandbits(16)
                values = [i + magic for i in range(size)]
                addr = m.calloc(size, dut.DATA_WIDTH // 8, initValues=values)

                d.req._ag.data.append((_id, addr, size - 1, 0))

                for i2, v in enumerate(values):
                    data = (_id, v, _mask, int(i2 == size - 1))
                    expected[_id].append(data)

        self.runSim(self.DRIVERS_CNT * N * 20 * CLK_PERIOD)

        for expect, driver in zip(expected, dut.drivers):
            self.assertValSequenceEqual(driver.r._ag.data, expect)


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([RStrictOrderInterconnectTC("test_passWithouData")])
    suite = testLoader.loadTestsFromTestCase(RStrictOrderInterconnectTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
