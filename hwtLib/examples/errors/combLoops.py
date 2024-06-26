#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwt.code import If
from hwt.hObjList import HObjList
from hwt.hdl.statements.statement import HwtSyntaxError
from hwt.hwIOs.std import HwIOVectSignal, HwIORdVldSync, HwIOSignal
from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.hwModule import HwModule
from hwt.pyUtils.typingFuture import override
from hwt.serializer.combLoopAnalyzer import CombLoopAnalyzer
from hwt.serializer.combLoopAnalyzer.tarjan import StronglyConnectedComponentSearchTarjan
from hwt.synth import synthesised, to_rtl_str
from hwtLib.handshaked.reg import HandshakedReg


def freeze_set_of_sets(obj):
    return frozenset(map(frozenset, obj))


class CntrCombLoop(HwModule):
    """
    A direct combinational loop which is detected  immediately
    """

    @override
    def hwDeclr(self):
        self.a = HwIOSignal()
        self.c = HwIOVectSignal(8, signed=False)._m()

    @override
    def hwImpl(self) -> None:
        b = self._sig("b", self.c._dtype, def_val=0)
        If(self.a,
           b(b + 1)
        )
        self.c(b)


class HandshakeWire0(HwModule):

    @override
    def hwDeclr(self):
        addClkRstn(self)
        self.dataIn = HwIORdVldSync()
        self.dataOut = HwIORdVldSync()._m()

    @override
    def hwImpl(self) -> None:
        self.dataOut(self.dataIn)


class HandshakeWire1(HandshakeWire0):
    """
    HandshakeWire0 with register on rd signal
    """

    @override
    def hwImpl(self) -> None:
        self.dataOut.vld(self.dataIn.vld)

        rd = self._reg("rd", def_val=1)
        rd(self.dataOut.rd)
        self.dataIn.rd(rd)


class WrongHandshakeCheckExample0(HandshakeWire0):

    @override
    def hwImpl(self):
        dataIn, dataOut = self.dataIn, self.dataOut

        dataIn.rd(dataIn.vld & dataOut.rd)
        dataOut.vld(dataIn.vld)


class WrongHandshakeCheckExample1(HandshakeWire0):

    @override
    def hwImpl(self):
        dataIn, dataOut = self.dataIn, self.dataOut

        dataIn.rd(dataIn.vld & dataOut.rd)
        dataOut.vld(dataIn.vld & dataOut.rd)


class HandshakeRegLoop(HwModule):

    def __init__(self, loop_connector_cls):
        self.loop_connector_cls = loop_connector_cls
        super(HandshakeRegLoop, self).__init__()

    @override
    def hwDeclr(self):
        addClkRstn(self)
        self.rd, self.vld = HwIOSignal()._m(), HwIOSignal()._m()

    @override
    def hwImpl(self) -> None:
        r = HandshakedReg(HwIORdVldSync)
        # r.DELAY = 1
        # r.LATENCY = 2 # to break ready signal chain
        self.reg = r
        if self.loop_connector_cls == HandshakedReg:
            c = self.loop_connector_cls(HwIORdVldSync)
        else:
            c = self.loop_connector_cls()

        self.con = c

        # circle  r <-> c
        r.dataIn(c.dataOut)
        c.dataIn(r.dataOut)

        self.rd(r.dataOut.rd)
        self.vld(r.dataOut.vld)

        propagateClkRstn(self)


class DoubleHandshakeReg(HandshakeWire0):

    @override
    def hwImpl(self) -> None:
        regs = self.regs = HObjList(HandshakedReg(HwIORdVldSync) for _ in range(2))
        regs[0].dataIn(self.dataIn)
        regs[1].dataIn(regs[0].dataOut)
        self.dataOut(regs[1].dataOut)
        propagateClkRstn(self)


class CombLoopAnalysisTC(unittest.TestCase):

    def test_tarjan(self):
        g = {1:[2], 2:[1, 5], 3:[4], 4:[3, 5], 5:[6], 6:[7], 7:[8], 8:[6, 9], 9:[]}
        scc_search = StronglyConnectedComponentSearchTarjan(g)
        res = scc_search.search_strongly_connected_components()

        res = freeze_set_of_sets(res)
        self.assertEqual(res, freeze_set_of_sets([[9], [8, 7, 6], [5], [2, 1], [4, 3]]))

    def test_CntrCombLoop(self):
        m = CntrCombLoop()
        with self.assertRaises(HwtSyntaxError):
            to_rtl_str(m)

    def get_comb_loops(self, m: HwModule):
        s = CombLoopAnalyzer()
        synthesised(m)
        s.visit_HwModule(m)
        return freeze_set_of_sets(
            set(str(member.resolve()[1:]) for member in loop)
            for loop in s.report()
        )

    def test_HandshakeWire0(self):
        m = HandshakeWire0()
        comb_loops = self.get_comb_loops(m)
        self.assertEqual(comb_loops, frozenset())

    def test_HandshakeWire1(self):
        m = HandshakeWire1()
        comb_loops = self.get_comb_loops(m)
        self.assertEqual(comb_loops, frozenset())

    def test_HandshakeRegLoop_HandshakeWire0(self):
        m = HandshakeRegLoop(HandshakeWire0)
        comb_loops = self.get_comb_loops(m)
        self.assertEqual(comb_loops,
            freeze_set_of_sets([
               [
                    'sig_con_dataIn_rd',
                    'reg/dataOut_rd',
                    'sig_con_dataOut_rd',
                    'sig_reg_dataOut_rd',
                    'con/dataOut_rd',
                    'con/dataIn_rd',
                    'reg/dataIn_rd',
                    'sig_reg_dataIn_rd',
                ],
            ]))

    def test_HandshakeRegLoop_HandshakeWire1(self):
        m = HandshakeRegLoop(HandshakeWire1)
        comb_loops = self.get_comb_loops(m)
        self.assertEqual(comb_loops, frozenset())

    def test_shared_component_instance_no_comb_loops(self):
        m = DoubleHandshakeReg()
        comb_loops = self.get_comb_loops(m)
        self.assertEqual(comb_loops, frozenset())

    def test_shared_component_instance_with_comb_loops(self):
        m = HandshakeRegLoop(HandshakedReg)
        comb_loops = self.get_comb_loops(m)
        ref = [
               [
                    'sig_con_dataIn_rd',
                    'reg/dataOut_rd',
                    'sig_con_dataOut_rd',
                    'sig_reg_dataOut_rd',
                    'con/dataOut_rd',
                    'con/dataIn_rd',
                    'reg/dataIn_rd',
                    'sig_reg_dataIn_rd',
                ],
            ]
        #    print([m for m in loop if m not in ref[0]])
        #    print([m for m in ref[0] if m not in loop])
        #for loop in comb_loops:

        self.assertSetEqual(comb_loops,
            freeze_set_of_sets(ref))


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    suite = testLoader.loadTestsFromTestCase(CombLoopAnalysisTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)

    # m = HandshakeRegLoop(HandshakeCheckExample)
    # m = HandshakeRegLoop(HandshakeWire1)
    # m = HandshakeCheckExample()
    # print(to_rtl_str(m))
    # s = CombLoopAnalyzer()
    # synthesised(m)
    # s.visit_HwModule(u)

    # for k, v in s.comb_connection_matrix.items():
    #    print(to_set_of_names(k), "\t", list(to_set_of_names(_v) for _v in v))

    # print("tarjan")
    # for scc in s.report():
    #    print(len(scc), list(to_set_of_names(_v) for _v in scc))
