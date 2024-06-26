#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwt.constants import Time
from hwt.hdl.types.struct import HStruct
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.datapump.sim_ram import AxiDpSimRam
from hwtLib.structManipulators.structWriter import StructWriter
from hwtLib.types.ctypes import uint64_t


class StructWriter_TC(SimTestCase):

    def tearDown(self):
        self.rmSim()
        SimTestCase.tearDown(self)

    def buildEnv(self, structT):
        dut = self.dut = StructWriter(structT)
        dut.DATA_WIDTH = 64
        self.compileSimAndStart(dut)
        m = AxiDpSimRam(int(dut.DATA_WIDTH), dut.clk, wDatapumpHwIO=dut.wDatapump)
        return m

    def test_singleField(self):
        MAGIC = 54
        MAGIC2 = 0x1000
        s = HStruct(
                    (uint64_t, "field0")
                   )

        m = self.buildEnv(s)
        self.dut.dataIn.field0._ag.data.append(MAGIC)
        self.dut.set._ag.data.append(MAGIC2)
        self.runSim(100 * Time.ns)

        s_got = m.getStruct(MAGIC2, s)
        self.assertValEqual(s_got.field0, MAGIC)

    def test_doubleField(self):
        MAGIC = 54
        MAGIC2 = 0x1000
        s = HStruct(
                    (uint64_t, "field0"),
                    (uint64_t, "field1")
                   )

        m = self.buildEnv(s)
        dut = self.dut
        dut.dataIn.field0._ag.data.append(MAGIC)
        dut.dataIn.field1._ag.data.append(MAGIC + 1)
        dut.set._ag.data.append(MAGIC2)

        self.runSim(100 * Time.ns)

        self.assertEmpty(dut.dataIn.field0._ag.data)
        self.assertEmpty(dut.dataIn.field1._ag.data)
        self.assertEmpty(dut.set._ag.data)

        s_got = m.getStruct(MAGIC2, s)
        self.assertValEqual(s_got.field0, MAGIC)
        self.assertValEqual(s_got.field1, MAGIC + 1)

    def test_tripleField(self):
        MAGIC = 54
        MAGIC2 = 0x1000
        s = HStruct(
                     (uint64_t, "field0"),
                     (uint64_t, "field1"),
                     (uint64_t, "field2")
                     )

        m = self.buildEnv(s)
        dut = self.dut
        dIn = dut.dataIn

        dIn.field0._ag.data.append(MAGIC)
        dIn.field1._ag.data.append(MAGIC + 1)
        dIn.field2._ag.data.append(MAGIC + 2)
        dut.set._ag.data.append(MAGIC2)

        self.runSim(100 * Time.ns)

        self.assertEmpty(dIn.field0._ag.data)
        self.assertEmpty(dIn.field1._ag.data)
        self.assertEmpty(dIn.field2._ag.data)
        self.assertEmpty(dut.set._ag.data)

        s_got = m.getStruct(MAGIC2, s)
        self.assertValEqual(s_got.field0, MAGIC)
        self.assertValEqual(s_got.field1, MAGIC + 1)
        self.assertValEqual(s_got.field2, MAGIC + 2)

    def test_holeOnStart(self):
        MAGIC = 54
        MAGIC2 = 0x1000
        s = HStruct(
                    (uint64_t, None),
                    (uint64_t, None),
                    (uint64_t, None),
                    (uint64_t, None),
                    (uint64_t, "field0"),
                    (uint64_t, "field1"),
                    (uint64_t, "field2")
                   )

        m = self.buildEnv(s)
        dut = self.dut
        dIn = dut.dataIn

        dIn.field0._ag.data.append(MAGIC)
        dIn.field1._ag.data.append(MAGIC + 1)
        dIn.field2._ag.data.append(MAGIC + 2)
        dut.set._ag.data.append(MAGIC2)

        self.runSim(100 * Time.ns)

        self.assertEmpty(dIn.field0._ag.data)
        self.assertEmpty(dIn.field1._ag.data)
        self.assertEmpty(dIn.field2._ag.data)
        self.assertEmpty(dut.set._ag.data)

        s_got = m.getStruct(MAGIC2, s)
        self.assertValEqual(s_got.field0, MAGIC)
        self.assertValEqual(s_got.field1, MAGIC + 1)
        self.assertValEqual(s_got.field2, MAGIC + 2)

    def test_holeInMiddle(self):
        MAGIC = 54
        MAGIC2 = 0x1000
        s = HStruct(
                    (uint64_t, "field0"),
                    (uint64_t, None),
                    (uint64_t, None),
                    (uint64_t, None),
                    (uint64_t, None),
                    (uint64_t, "field1"),
                    (uint64_t, "field2")
                   )

        m = self.buildEnv(s)
        dut = self.dut
        dIn = dut.dataIn

        dIn.field0._ag.data.append(MAGIC)
        dIn.field1._ag.data.append(MAGIC + 1)
        dIn.field2._ag.data.append(MAGIC + 2)
        dut.set._ag.data.append(MAGIC2)

        self.runSim(100 * Time.ns)

        self.assertEmpty(dIn.field0._ag.data)
        self.assertEmpty(dIn.field1._ag.data)
        self.assertEmpty(dIn.field2._ag.data)
        self.assertEmpty(dut.set._ag.data)

        s_got = m.getStruct(MAGIC2, s)
        self.assertValEqual(s_got.field0, MAGIC)
        self.assertValEqual(s_got.field1, MAGIC + 1)
        self.assertValEqual(s_got.field2, MAGIC + 2)


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([StructWriter_TC("test_doubleField")])
    suite = testLoader.loadTestsFromTestCase(StructWriter_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
