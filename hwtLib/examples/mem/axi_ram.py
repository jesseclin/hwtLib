#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.types.struct import HStruct
from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.math import log2ceil
from hwt.hwModule import HwModule
from hwtLib.amba.axi4 import Axi4
from hwtLib.amba.axi4Lite import Axi4Lite
from hwtLib.amba.axiLite_comp.endpoint import AxiLiteEndpoint
from hwtLib.amba.axi_comp.builder import AxiBuilder
from hwtLib.mem.ram import RamSingleClock


class Axi4BRam(HwModule):
    """
    .. hwt-autodoc::
    """

    def hwConfig(self) -> None:
        Axi4.hwConfig(self)
        self.DATA_WIDTH = 512
        self.ADDR_WIDTH = 10

    def hwDeclr(self) -> None:
        addClkRstn(self)

        with self._hwParamsShared():
            self.s = Axi4()
            self.ram = RamSingleClock()
            self.ram.ADDR_WIDTH = self.ADDR_WIDTH - log2ceil(self.DATA_WIDTH // 8 - 1)

    def hwImpl(self) -> None:
        ram = self.ram
        al = AxiBuilder(self, self.s).to_axi(Axi4Lite).end
        with self._hwParamsShared():
            dec = self.decoder = AxiLiteEndpoint(HStruct(
                    (ram.port[0].dout._dtype[2 ** ram.ADDR_WIDTH], "ram")
                ))

        dec.bus(al)
        ram.port[0](dec.decoded.ram)

        propagateClkRstn(self)


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    m = Axi4BRam()
    print(to_rtl_str(m))
