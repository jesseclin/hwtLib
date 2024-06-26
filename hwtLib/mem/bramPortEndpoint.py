#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import SwitchLogic, Switch, If
from hwt.hdl.types.bits import HBits
from hwt.hwIOs.std import HwIOBramPort_noClk
from hwt.math import log2ceil
from hwtLib.abstract.busEndpoint import BusEndpoint


class BramPortEndpoint(BusEndpoint):
    """
    Delegate transaction from BrapmPort interface to interfaces
    for fields of specified structure.

    :attention: Interfaces are dynamically generated from names
        of fields in structure template.

    .. hwt-autodoc:: _example_BramPortEndpoint
    """
    _getWordAddrStep = HwIOBramPort_noClk._getWordAddrStep
    _getAddrStep = HwIOBramPort_noClk._getAddrStep

    def __init__(self, structTemplate, hwIOCls=HwIOBramPort_noClk,
                 shouldEnterFn=None):
        BusEndpoint.__init__(self, structTemplate,
                             hwIOCls=hwIOCls, shouldEnterFn=shouldEnterFn)

    def hwImpl(self):
        self._parseTemplate()
        bus = self.bus

        ADDR_STEP = self._getAddrStep()
        if self._directly_mapped_words:
            readReg = self._reg("readReg", dtype=bus.dout._dtype)
            # tuples (condition, assign statements)
            If(bus.en,
               self.connect_directly_mapped_read(bus.addr, readReg, [])
            )
            self.connect_directly_mapped_write(bus.addr, bus.din, bus.en & bus.we)
        else:
            readReg = None

        if self._bramPortMapped:
            BRAMS_CNT = len(self._bramPortMapped)
            bramIndxCases = []
            readBramIndx = self._reg("readBramIndx", HBits(
                log2ceil(BRAMS_CNT + 1), False))
            outputSwitch = Switch(readBramIndx)

            for i, ((_, _), t) in enumerate(self._bramPortMapped):
                # if we can use prefix instead of addr comparing do it
                _addr = t.bitAddr // ADDR_STEP
                _addrEnd = t.bitAddrEnd // ADDR_STEP
                port = self.getPort(t)

                _addrVld, _ = self.propagateAddr(bus.addr,
                                                 ADDR_STEP,
                                                 port.addr,
                                                 port.dout._dtype.bit_length(),
                                                 t)

                port.we(bus.en & bus.we & _addrVld)
                port.en(bus.en & _addrVld)
                port.din(bus.din)

                bramIndxCases.append((_addrVld, readBramIndx(i)))
                outputSwitch.Case(i, bus.dout(port.dout))

            outputSwitch.Default(bus.dout(readReg))
            SwitchLogic(bramIndxCases,
                        default=readBramIndx(BRAMS_CNT))
        else:
            bus.dout(readReg)


def _example_BramPortEndpoint():
    from hwt.hdl.types.struct import HStruct
    from hwtLib.types.ctypes import uint32_t

    m = BramPortEndpoint(
        HStruct(
            (uint32_t, "reg0"),
            (uint32_t, "reg1"),
            (uint32_t[1024], "segment0"),
            (uint32_t[1024], "segment1"),
            (uint32_t[1024 + 4], "nonAligned0")
        )
    )
    m.DATA_WIDTH = 32
    return m


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    
    m = _example_BramPortEndpoint()
    print(to_rtl_str(m))
