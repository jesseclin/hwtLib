#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.types.bits import HBits
from hwt.synthesizer.rtlLevel.netlist import RtlNetlist
from hwtLib.examples.rtlLvl.netlistToRtl import netlistToVhdlStr
from ipCorePackager.constants import DIRECTION


def SimpleRegister():
    t = HBits(8)

    n = RtlNetlist()

    s_out = n.sig("s_out", t)
    s_in = n.sig("s_in", t)
    clk = n.sig("clk")
    syncRst = n.sig("rst")

    val = n.sig("val", t, clk, syncRst, 0)
    val(s_in)
    s_out(val)

    interf = {clk: DIRECTION.IN, syncRst: DIRECTION.IN,
              s_in: DIRECTION.IN, s_out: DIRECTION.OUT}
    return n, interf


if __name__ == "__main__":
    netlist, interfaces = SimpleRegister()
    print(netlistToVhdlStr("SimpleRegister", netlist, interfaces))
