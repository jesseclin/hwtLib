#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwt.code import If
from hwt.hdl.assignment import Assignment
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.typeShortcuts import hBit
from hwt.serializer.vhdl.serializer import VhdlSerializer
from hwt.synthesizer.rtlLevel.netlist import RtlNetlist
from hwtLib.samples.rtlLvl.indexOps import IndexOps


class TestCaseSynthesis(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.n = RtlNetlist()

    def test_opRisingEdgeMultipletimesSameObj(self):
        clk = self.n.sig("ap_clk")
        self.assertEqual(clk._onRisingEdge(), clk._onRisingEdge())

    def test_syncSig(self):
        n = self.n
        clk = n.sig("ap_clk")
        a = n.sig("a", clk=clk)

        self.assertEqual(len(a.drivers), 1)
        _if = a.drivers[0]
        self.assertIsInstance(_if, If)

        self.assertEqual(len(_if.cond), 1)
        self.assertEqual(len(_if.ifTrue), 1)
        self.assertEqual(_if.ifFalse, None)
        self.assertEqual(len(_if.elIfs), 0)

        assig = _if.ifTrue[0]
        self.assertEqual(assig.src, a.next)
        self.assertEqual(assig.dst, a)

        onRisE = _if.cond.pop()
        self.assertEqual(onRisE.origin.operator, AllOps.RISING_EDGE)
        self.assertEqual(onRisE.origin.operands[0], clk)

    def test_syncSigWithReset(self):
        c = self.n
        clk = c.sig("ap_clk")
        rst = c.sig("ap_rst")
        a = c.sig("a", clk=clk, syncRst=rst, defVal=0)

        self.assertEqual(len(a.drivers), 1)

        _if = a.drivers[0]
        self.assertIsInstance(_if, If)

        self.assertEqual(len(_if.cond), 1)
        self.assertEqual(len(_if.ifTrue), 1)
        self.assertEqual(_if.ifFalse, None)
        self.assertEqual(len(_if.elIfs), 0)

        if_reset = _if.ifTrue[0]

        self.assertEqual(len(if_reset.cond), 1)
        rst_eq1 = rst._eq(1)
        self.assertIs(if_reset.cond[0], rst_eq1)
        self.assertEqual(len(if_reset.ifTrue), 1)
        self.assertEqual(len(if_reset.ifFalse), 1)
        self.assertEqual(len(if_reset.elIfs), 0)

        a_reset = if_reset.ifTrue[0]
        a_next = if_reset.ifFalse[0]
        self.assertIsInstance(a_reset, Assignment)
        self.assertEqual(a_reset.src, hBit(0))

        self.assertIsInstance(a_next, Assignment)
        self.assertEqual(a_next.src, a.next)

    def test_indexOps(self):
        c, interf = IndexOps()
        _, arch = list(c.synthesize("indexOps", interf))

        s = VhdlSerializer.Architecture(arch, VhdlSerializer.getBaseContext())

        self.assertNotIn("sig_", s)


if __name__ == '__main__':
    unittest.main()
