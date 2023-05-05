#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.constants import Time
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.examples.statements.forLoopCntrl import StaticForLoopCntrl


class StaticForLoopCntrlTC(SimTestCase):
    ITERATIONS = 5

    @classmethod
    def setUpClass(cls):
        u = StaticForLoopCntrl()
        u.ITERATIONS = cls.ITERATIONS
        cls.compileSim(u)

    def test_simple(self):
        u = self.u
        u.bodyBreak._ag.data.append(0)
        u.cntrl._ag.data.extend([1 for _ in range(10)])

        self.runSim(110 * Time.ns)

        self.assertValSequenceEqual(u.index._ag.data,
                                    (2 * [4, 3, 2, 1, 0]))


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([StaticForLoopCntrlTC("test_nothingEnable")])
    suite = testLoader.loadTestsFromTestCase(StaticForLoopCntrlTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
