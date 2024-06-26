#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.types.defs import BIT
from hwt.hdl.types.struct import HStruct
from hwt.hwIOs.std import HwIOVectSignal, HwIOSignal, HwIORdVldSync
from hwt.hwIOs.utils import addClkRstn
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwtLib.abstract.busBridge import BusBridge
from hwtLib.cesnet.mi32.intf import Mi32
from hwtLib.handshaked.builder import HsBuilder


class Mi32AddrHs(HwIORdVldSync):
    """
    Equivalent of Mi32 address/write data channel
    with HwIORdVldSync compatible signal names

    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        Mi32.hwConfig(self)

    @override
    def hwDeclr(self):
        self.addr = HwIOVectSignal(self.ADDR_WIDTH)
        self.read = HwIOSignal()
        self.write = HwIOSignal()
        self.be = HwIOVectSignal(self.DATA_WIDTH // 8)
        self.dwr = HwIOVectSignal(self.DATA_WIDTH)
        super(Mi32AddrHs, self).hwDeclr()


class Mi32Buff(BusBridge):
    """
    Buffer for Mi32 interface

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        Mi32.hwConfig(self)
        self.ADDR_BUFF_DEPTH = HwParam(1)
        self.DATA_BUFF_DEPTH = HwParam(1)

    @override
    def hwDeclr(self):
        addClkRstn(self)
        with self._hwParamsShared():
            self.s = Mi32()
            self.m = Mi32()._m()

    def _Mi32_addr_to_Mi32AddrHs(self, mi32: Mi32, tmp_name):
        tmp = Mi32AddrHs()
        tmp._updateHwParamsFrom(mi32)
        setattr(self, tmp_name, tmp)
        tmp(mi32, exclude={
            tmp.vld, tmp.rd, tmp.read, tmp.write,
            mi32.ardy, mi32.rd, mi32.wr, mi32.drd, mi32.drdy})
        tmp.read(mi32.rd)
        tmp.write(mi32.wr)
        tmp.vld(mi32.rd | mi32.wr)
        mi32.ardy(tmp.rd)
        return tmp

    def _connect_Mi32AddrHs_to_Mi32(self, mi32ahs: Mi32AddrHs, mi32: Mi32):
        return [
            mi32(mi32ahs, exclude={
                mi32ahs.vld, mi32ahs.rd, mi32ahs.read, mi32ahs.write,
                mi32.ardy, mi32.rd, mi32.wr, mi32.drd, mi32.drdy}),
            mi32.rd(mi32ahs.vld & mi32ahs.read),
            mi32.wr(mi32ahs.vld & mi32ahs.write),
            mi32ahs.rd(mi32.ardy),
        ]

    @override
    def hwImpl(self):
        m = self._Mi32_addr_to_Mi32AddrHs(self.s, "addr_tmp")
        m = HsBuilder(self, m).buff(items=self.ADDR_BUFF_DEPTH).end
        self._connect_Mi32AddrHs_to_Mi32(m, self.m)

        data_t = HStruct(
            (self.m.drd._dtype, "drd"),  # read data
            (BIT, "drdy"),  # read data valid
        )
        m = (self.m.drd, self.m.drdy)

        for i in range(self.DATA_BUFF_DEPTH):
            reg = self._reg(f"read_data_reg{i:d}", data_t, def_val={"drdy": 0})
            reg.drd(m[0])
            reg.drdy(m[1])
            m = (reg.drd, reg.drdy)

        self.s.drd(m[0])
        self.s.drdy(m[1])


if __name__ == "__main__":
    from hwt.synth import to_rtl_str

    m = Mi32Buff()
    print(to_rtl_str(m))
