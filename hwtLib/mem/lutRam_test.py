#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.constants import WRITE, READ
from hwt.simulator.simTestCase import SimTestCase
from hwt.simulator.utils import HConstSequenceToInts
from hwtLib.mem.lutRam import RAM64X1S
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import get_bit


def applyRequests(ram, requests):
    """
    request has to be tuple (WRITE, addr, data) or (READ, addr)
    data can be only 0 or 1 (because width of data port is 1)
    """
    for req in requests:
        m = req[0]
        if m == WRITE:
            data = req[2]
            assert data == 1 or data == 0
            ram.d._ag.data.append(data)
            ram.we._ag.data.append(1)
        elif m == READ:
            ram.we._ag.data.append(0)
        else:
            raise Exception(f"invalid mode {req[0]}")

        addr = req[1]
        # ram addr has 6 bits
        for i in range(6):
            addrbit = getattr(ram, f"a{i:d}")
            addrBitval = get_bit(addr, i)
            addrbit._ag.data.append(addrBitval)


class LutRamTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        dut = RAM64X1S()
        cls.compileSim(dut)

    def test_writeAndRead(self):
        dut = self.dut

        requests = [(WRITE, 0, 0), (WRITE, 1, 1),
                    (READ, 0), (READ, 1),
                    (READ, 2), (READ, 3), (READ, 2)]
        applyRequests(dut, requests)

        self.runSim(8 * CLK_PERIOD)
        self.assertSequenceEqual(HConstSequenceToInts(dut.o._ag.data),
                                 [0, 0, 0, 1, 0, 0, 0, 0])


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([LutRamTC("test_withStops")])
    suite = testLoader.loadTestsFromTestCase(LutRamTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
