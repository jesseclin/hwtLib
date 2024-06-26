#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.constants import Time
from hwt.hdl.types.bits import HBits
from hwt.hdl.types.hdlType import HdlType
from hwt.hdl.types.struct import HStruct
from hwt.hdl.types.structUtils import field_path_get_type
from hwt.pyUtils.arrayQuery import flatten
from hwt.synthesizer.typePath import TypePath
from hwtLib.amba.axiLite_comp.endpoint import AxiLiteEndpoint
from hwtLib.amba.axiLite_comp.endpoint_test import AxiLiteEndpointTC, \
    AxiLiteEndpointDenseStartTC, AxiLiteEndpointDenseTC
from hwtLib.amba.constants import RESP_OKAY, RESP_SLVERR
from hwtLib.types.ctypes import uint32_t
from pyMathBitPrecise.bit_utils import mask

structTwoArr = HStruct(
                       (uint32_t[4], "field0"),
                       (uint32_t[4], "field1")
                       )
structTwoArr_str = """\
struct {
    <HBits, 32bits, unsigned>[4] field0 // start:0x0(bit) 0x0(byte)
    <HBits, 32bits, unsigned>[4] field1 // start:0x80(bit) 0x10(byte)
}"""

structTwoArr2 = HStruct(
                       (uint32_t[3], "field0"),
                       (uint32_t[4], "field1")
                       )
structTwoArr2_str = """\
struct {
    <HBits, 32bits, unsigned>[3] field0 // start:0x0(bit) 0x0(byte)
    <HBits, 32bits, unsigned>[4] field1 // start:0x60(bit) 0xc(byte)
}"""

structStructsInArray = HStruct(
                        (HStruct(
                                (uint32_t, "field0"),
                                (uint32_t, "field1")
                                )[4],
                         "arr"),
                        )
structStructsInArray_str = """\
struct {
    struct {
        <HBits, 32bits, unsigned> field0 // start:0x0(bit) 0x0(byte)
        <HBits, 32bits, unsigned> field1 // start:0x20(bit) 0x4(byte)
    }[4] arr // start:0x0(bit) 0x0(byte)
}"""


class AxiLiteEndpointArrayTC(AxiLiteEndpointTC):
    STRUCT_TEMPLATE = structTwoArr
    FIELD_ADDR = [0x0, 0x10]

    def test_nop(self):
        dut = self.mySetUp(32)
        MAGIC = 100

        for i in range(8):
            dut.decoded.field0._ag.mem[i] = MAGIC + 1
            dut.decoded.field1._ag.mem[i] = 2 * MAGIC + 1

        self.randomizeAll()
        self.runSim(100 * Time.ns)

        self.assertEmpty(dut.bus._ag.r.data)
        for i in range(8):
            self.assertValEqual(dut.decoded.field0._ag.mem[i], MAGIC + 1)
            self.assertValEqual(dut.decoded.field1._ag.mem[i], 2 * MAGIC + 1)

    def test_read(self):
        dut = self.mySetUp(32)
        regs = self.regs
        MAGIC = 100

        for i in range(4):
            dut.decoded.field0._ag.mem[i] = MAGIC + i + 1
            dut.decoded.field1._ag.mem[i] = 2 * MAGIC + i + 1
            regs.field0[i].read()
            regs.field1[i].read()

        self.randomizeAll()
        self.runSim(2 * 8 * 100 * Time.ns)

        self.assertValSequenceEqual(dut.bus._ag.r.data, [
            (MAGIC + 1, RESP_OKAY),
            (2 * MAGIC + 1, RESP_OKAY),
            (MAGIC + 2, RESP_OKAY),
            (2 * MAGIC + 2, RESP_OKAY),
            (MAGIC + 3, RESP_OKAY),
            (2 * MAGIC + 3, RESP_OKAY),
            (MAGIC + 4, RESP_OKAY),
            (2 * MAGIC + 4, RESP_OKAY),
            ])

    def test_write(self):
        dut = self.mySetUp(32)
        regs = self.regs
        MAGIC = 100

        for i in range(4):
            dut.decoded.field0._ag.mem[i] = None
            dut.decoded.field1._ag.mem[i] = None
            regs.field0[i].write(MAGIC + i + 1)
            regs.field1[i].write(2 * MAGIC + i + 1)

        self.randomizeAll()
        self.runSim(2 * 8 * 100 * Time.ns)

        self.assertEmpty(dut.bus._ag.r.data)
        for i in range(4):
            self.assertValEqual(dut.decoded.field0._ag.mem[i],
                                MAGIC + i + 1, f"index={i:d}")
            self.assertValEqual(dut.decoded.field1._ag.mem[i],
                                2 * MAGIC + i + 1, f"index={i:d}")

    def test_registerMap(self):
        self.mySetUp(32)
        s = self.addrProbe.discovered.__repr__(withAddr=0, expandStructs=True)
        self.assertEqual(s, structTwoArr_str)


class AxiLiteEndpointArray2TC(AxiLiteEndpointTC):
    STRUCT_TEMPLATE = structTwoArr2
    FIELD_ADDR = [0x0, 3 * 0x04]

    def test_nop(self):
        dut = self.mySetUp(32)
        MAGIC = 100

        for i in range(4):
            if i < 3:
                dut.decoded.field0._ag.mem[i] = MAGIC + 1
            dut.decoded.field1._ag.mem[i] = 2 * MAGIC + 1

        self.randomizeAll()
        self.runSim(100 * Time.ns)

        self.assertEmpty(dut.bus._ag.r.data)
        for i in range(4):
            if i < 3:
                self.assertValEqual(dut.decoded.field0._ag.mem[i], MAGIC + 1)
            self.assertValEqual(dut.decoded.field1._ag.mem[i], 2 * MAGIC + 1)

    def test_read(self):
        dut = self.mySetUp(32)
        regs = self.regs
        MAGIC = 100

        for i in range(4):
            if i < 3:
                dut.decoded.field0._ag.mem[i] = MAGIC + i + 1
                regs.field0[i].read()

            dut.decoded.field1._ag.mem[i] = 2 * MAGIC + i + 1
            regs.field1[i].read()

        self.randomizeAll()
        self.runSim(2 * 8 * 100 * Time.ns)

        self.assertValSequenceEqual(dut.bus._ag.r.data, [
            (MAGIC + 1, RESP_OKAY),
            (2 * MAGIC + 1, RESP_OKAY),
            (MAGIC + 2, RESP_OKAY),
            (2 * MAGIC + 2, RESP_OKAY),
            (MAGIC + 3, RESP_OKAY),
            (2 * MAGIC + 3, RESP_OKAY),
            (2 * MAGIC + 4, RESP_OKAY),
        ])

    def test_write(self):
        dut = self.mySetUp(32)
        regs = self.regs
        MAGIC = 100

        for i in range(4):
            if i < 3:
                dut.decoded.field0._ag.mem[i] = None
                regs.field0[i].write(MAGIC + i + 1)

            dut.decoded.field1._ag.mem[i] = None
            regs.field1[i].write(2 * MAGIC + i + 1)

        self.randomizeAll()
        self.runSim(2 * 8 * 100 * Time.ns)

        self.assertEmpty(dut.bus._ag.r.data)
        for i in range(4):
            if i < 3:
                self.assertValEqual(dut.decoded.field0._ag.mem[i],
                                    MAGIC + i + 1, f"index={i:d}")
            self.assertValEqual(dut.decoded.field1._ag.mem[i],
                                2 * MAGIC + i + 1, f"index={i:d}")

    def test_registerMap(self):
        self.mySetUp(32)
        s = self.addrProbe.discovered.__repr__(withAddr=0, expandStructs=True)
        self.assertEqual(s, structTwoArr2_str)


class AxiLiteEndpointStructsInArrayTC(AxiLiteEndpointTC):
    STRUCT_TEMPLATE = structStructsInArray

    def mySetUp(self, data_width=32):

        def shouldEnterFn(root: HdlType, field_path: TypePath):
            return (True, isinstance(field_path_get_type(root, field_path), HBits))

        dut = AxiLiteEndpoint(self.STRUCT_TEMPLATE,
                            shouldEnterFn=shouldEnterFn)
        self.dut = dut

        self.DATA_WIDTH = data_width
        dut.DATA_WIDTH = self.DATA_WIDTH

        self.compileSimAndStart(self.dut, onAfterToRtl=self.mkRegisterMap)
        return dut

    def test_nop(self):
        dut = self.mySetUp(32)

        self.randomizeAll()
        self.runSim(100 * Time.ns)

        self.assertEmpty(dut.bus._ag.r.data)
        for item in dut.decoded.arr:
            self.assertEmpty(item.field0._ag.dout)
            self.assertEmpty(item.field1._ag.dout)

    def test_registerMap(self):
        self.mySetUp(32)
        s = self.addrProbe.discovered.__repr__(withAddr=0, expandStructs=True)
        self.assertEqual(s, structStructsInArray_str)

    def test_read(self):
        dut = self.mySetUp(32)
        MAGIC = 100
        MAGIC2 = 300

        a = dut.bus.ar._ag.create_addr_req
        dut.bus.ar._ag.data.extend([a(i * 0x4) for i in range(4 * 2 + 1)])

        for i, a in enumerate(dut.decoded.arr):
            a.field0._ag.din.extend([MAGIC + i])
            a.field1._ag.din.extend([MAGIC2 + i])

        self.randomizeAll()
        self.runSim(500 * Time.ns)
        expected = list(flatten([[(MAGIC + i, RESP_OKAY),
                                  (MAGIC2 + i, RESP_OKAY)]
                                 for i in range(4)], level=1)
                        ) + [(None, RESP_SLVERR)]
        self.assertValSequenceEqual(dut.bus.r._ag.data, expected)

    def test_write(self):
        dut = self.mySetUp(32)
        MAGIC = 100
        MAGIC2 = 300
        m = mask(32 // 8)
        N = 4

        a = dut.bus.ar._ag.create_addr_req
        dut.bus.aw._ag.data.extend([a(i * 0x4) for i in range(N * 2 + 1)])

        expected = [
            [(MAGIC + i + 1, m) for i in range(N)],
            [(MAGIC2 + i + 1, m) for i in range(N)]
        ]

        dut.bus.w._ag.data.extend(flatten(zip(expected[0], expected[1]),
                                        level=1))
        dut.bus.w._ag.data.append((123, m))

        self.randomizeAll()
        self.runSim(800 * Time.ns)

        for i, a in enumerate(dut.decoded.arr):
            # [index of field][index in arr][data index]
            self.assertValSequenceEqual(a.field0._ag.dout, [expected[0][i][0]])
            self.assertValSequenceEqual(a.field1._ag.dout, [expected[1][i][0]])

        self.assertValSequenceEqual(dut.bus.b._ag.data,
                                    [RESP_OKAY for _ in range(2 * N)]
                                    +[RESP_SLVERR])


AxiLiteEndpointArrTCs = [
    AxiLiteEndpointArrayTC,
    AxiLiteEndpointArray2TC,
    AxiLiteEndpointStructsInArrayTC,
]

if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    _ALL_TCs = [
        AxiLiteEndpointTC,
        AxiLiteEndpointDenseStartTC,
        AxiLiteEndpointDenseTC,
        *AxiLiteEndpointArrTCs,
    ]
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([AxiLiteEndpointTC("test_read")])
    loadedTcs = [testLoader.loadTestsFromTestCase(tc) for tc in _ALL_TCs]
    suite = unittest.TestSuite(loadedTcs)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)

    # m = AxiLiteEndpoint(structStructsInArray,
    #                     shouldEnterFn=lambda tmpl: True)
    # m.DATA_WIDTH = 32
    # print(to_rtl_str(m))
