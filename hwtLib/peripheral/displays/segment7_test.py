#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwtLib.examples.base_serialization_TC import BaseSerializationTC
from hwtLib.peripheral.displays.segment7 import Segment7


class Segment7TC(BaseSerializationTC):
    __FILE__ = __file__

    def test_toVhdl(self):
        self.assert_serializes_as_file(Segment7(), "Segment7.vhd")


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Segment7TC("test_basic")])
    suite = testLoader.loadTestsFromTestCase(Segment7TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
