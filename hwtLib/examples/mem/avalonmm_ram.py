#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.types.struct import HStruct
from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.math import log2ceil
from hwt.hwModule import HwModule
from hwtLib.amba.axi4Lite import Axi4Lite
from hwtLib.amba.axiLite_comp.endpoint import AxiLiteEndpoint
from hwtLib.avalon.mm import AvalonMM
from hwtLib.mem.ram import RamSingleClock
from hwtLib.avalon.builder import AvalonMmBuilder


class AvalonMmBRam(HwModule):
    """
    .. hwt-autodoc::
    """

    def hwConfig(self) -> None:
        AvalonMM.hwConfig(self)

    def hwDeclr(self) -> None:
        addClkRstn(self)

        with self._hwParamsShared():
            self.s = AvalonMM()
            self.ram = RamSingleClock()
            self.ram.ADDR_WIDTH = self.ADDR_WIDTH - log2ceil(self.DATA_WIDTH // 8 - 1)

    def hwImpl(self) -> None:
        ram = self.ram
        al = AvalonMmBuilder(self, self.s).to_axi(Axi4Lite).end
        with self._hwParamsShared():
            dec = self.decoder = AxiLiteEndpoint(HStruct(
                    (ram.port[0].dout._dtype[2 ** ram.ADDR_WIDTH], "ram")
                ))

        dec.bus(al)
        ram.port[0](dec.decoded.ram)

        propagateClkRstn(self)


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    m = AvalonMmBRam()
    m.DATA_WIDTH = 256
    m.ADDR_WIDTH = 26 + log2ceil(256 // 8 - 1)
    m.MAX_BURST = 2 ** 7
    print(to_rtl_str(m))
