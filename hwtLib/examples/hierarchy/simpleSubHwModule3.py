#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.hwModule import HwModule
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwtLib.amba.axi4s import Axi4Stream
from hwtLib.examples.hierarchy.simpleSubHwModule2 import SimpleSubModule2TC
from hwtLib.examples.simpleHwModuleAxi4Stream import SimpleHwModuleAxi4Stream


class SimpleSubHwModule3(HwModule):
    """
    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        self.DATA_WIDTH = HwParam(128)
        self.USE_STRB = HwParam(True)

    @override
    def hwDeclr(self):
        addClkRstn(self)
        with self._hwParamsShared():
            self.submodule0 = SimpleHwModuleAxi4Stream()

            self.a0 = Axi4Stream()
            self.b0 = Axi4Stream()._m()

    @override
    def hwImpl(self):
        propagateClkRstn(self)
        m = self.submodule0
        m.a(self.a0)
        self.b0(m.b)


class SimpleSubModule3TC(SimpleSubModule2TC):

    @classmethod
    @override
    def setUpClass(cls):
        cls.dut = SimpleSubHwModule3()
        cls.compileSim(cls.dut)

if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    print(to_rtl_str(SimpleSubHwModule3()))
