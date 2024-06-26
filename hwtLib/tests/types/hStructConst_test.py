#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwtLib.types.net.dpdk import rte_mbuf
from hwtLib.types.net.udp import UDP_header_t


class HStructConstTC(unittest.TestCase):

    def test_structFromPy(self):
        v = rte_mbuf.from_py({
                         "buf_len": 10,
                         "seqn": 1,
                         })
        self.assertEqual(int(v.buf_len), 10)
        self.assertEqual(int(v.seqn), 1)

    def test_tryToSetNonExistingDefVal(self):
        with self.assertRaises(AssertionError):
            UDP_header_t.from_py({
                                 "wrong": 10
                                 })

    def test_tryToSetNonExistingAttribute(self):
        v = rte_mbuf.from_py({
                         "buf_len": 10,
                         "seqn": 1,
                         })

        with self.assertRaises(AttributeError):
            v.nonExisting = None


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([HStructConstTC("test_sWithStartPadding")])
    suite = testLoader.loadTestsFromTestCase(HStructConstTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
