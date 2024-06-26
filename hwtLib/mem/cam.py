#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import If, Concat
from hwt.hObjList import HObjList
from hwt.hdl.types.bits import HBits
from hwt.hdl.types.defs import BIT
from hwt.hwIOs.std import HwIODataRdVld
from hwt.hwIOs.utils import addClkRstn
from hwt.hwModule import HwModule
from hwt.hwParam import HwParam
from hwt.math import log2ceil
from hwt.pyUtils.typingFuture import override
from hwt.serializer.mode import serializeParamsUniq
from hwtLib.commonHwIO.addr_data import HwIOAddrDataVldRdVld, HwIOAddrDataRdVld
from hwtLib.handshaked.streamNode import StreamNode


@serializeParamsUniq
class Cam(HwModule):
    """
    Content addressable memory.
    MATCH_LATENCY = 1

    :note: a combinational version

    :ivar USE_VLD_BIT: if true the validity bit is a part of the CAM record

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        self.KEY_WIDTH = HwParam(15)
        self.ITEMS = HwParam(32)
        self.USE_VLD_BIT = HwParam(True)

    def _declr_match_io(self):
        self.match = m = HwIODataRdVld()
        m.DATA_WIDTH = self.KEY_WIDTH
        # one hot encoded
        self.out = o = HwIODataRdVld()._m()
        o.DATA_WIDTH = self.ITEMS

    @override
    def hwDeclr(self):
        addClkRstn(self)
        self._declr_match_io()

        # address is index of CAM cell, data is key to store
        if self.USE_VLD_BIT:
            w = HwIOAddrDataVldRdVld()
        else:
            w = HwIOAddrDataRdVld()
        w.DATA_WIDTH = self.KEY_WIDTH
        w.ADDR_WIDTH = log2ceil(self.ITEMS - 1)
        self.write = w

    def writeHandler(self, mem):
        w = self.write
        w.rd(1)

        key_data = w.data
        if self.USE_VLD_BIT:
            key_data = Concat(w.data, w.vld_flag)

        If(self.clk._onRisingEdge(),
           If(w.vld,
              mem[w.addr](key_data)
           )
        )

    def matchHandler(self, mem, key: HwIODataRdVld, match_res: HwIODataRdVld):

        key_data = key.data
        if self.USE_VLD_BIT:
            key_data = Concat(key.data, BIT.from_py(1))

        out_one_hot = []
        for i in range(self.ITEMS):
            b = mem[i]._eq(key_data)
            out_one_hot.append(b)

        match_res.data(Concat(*reversed(out_one_hot)))
        StreamNode([key], [match_res]).sync()

    @override
    def hwImpl(self):
        KEY_WIDTH = self.KEY_WIDTH
        if self.USE_VLD_BIT:
            # +1 bit to validity check
            KEY_WIDTH += 1

        self._mem = self._sig("cam_mem",
                              HBits(KEY_WIDTH)[self.ITEMS],
                              [0 for _ in range(self.ITEMS)]
                              )
        self.writeHandler(self._mem)
        self.matchHandler(self._mem, self.match, self.out)


@serializeParamsUniq
class CamMultiPort(Cam):
    """
    A variant of :class:`~.Cam` with multiple ports for lookup

    :ivar MATCH_PORT_CNT: number of CAM ports for matching, if None there is only as single port
        otherwise there is an array of such a ports of specified size

    .. hwt-autodoc:: _example_CamMultiPort
    """

    @override
    def hwConfig(self):
        Cam.hwConfig(self)
        self.MATCH_PORT_CNT = HwParam(None)

    def _declr_match_io(self):
        if self.MATCH_PORT_CNT is None:
            # single port version
            Cam._declr_match_io(self)
        else:
            # muliport version
            self.match = HObjList([HwIODataRdVld() for _ in range(self.MATCH_PORT_CNT)])
            for m in self.match:
                m.DATA_WIDTH = self.KEY_WIDTH

            self.out = HObjList([HwIODataRdVld()._m() for _ in range(self.MATCH_PORT_CNT)])
            for o in self.out:
                o.DATA_WIDTH = self.ITEMS

    def matchHandler(self, mem, key:HwIODataRdVld, match_res:HwIODataRdVld):
        if self.MATCH_PORT_CNT is None:
            Cam.matchHandler(self, mem, key, match_res)
        else:
            # multiport version
            for _match, _match_res in zip(self.match, self.out):
                Cam.matchHandler(self, mem, _match, _match_res)

def _example_CamMultiPort():
    m = CamMultiPort()
    m.MATCH_PORT_CNT = 2
    return m

if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    m = _example_CamMultiPort()
    print(to_rtl_str(m))
