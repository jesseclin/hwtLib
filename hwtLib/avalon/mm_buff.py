#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Union

from hwt.hwIOs.std import HwIODataRdVld
from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwt.serializer.mode import serializeParamsUniq
from hwt.synthesizer.interfaceLevel.utils import HwIO_pack, \
    HwIO_connectPacked
from hwtLib.abstract.busBridge import BusBridge
from hwtLib.avalon.mm import AvalonMM
from hwtLib.handshaked.fifo import HandshakedFifo
from hwtLib.handshaked.reg import HandshakedReg
from hwtLib.handshaked.streamNode import StreamNode


@serializeParamsUniq
class AvalonMmBuff(BusBridge):
    """
    Transaction buffer for Avalon MM interface

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        AvalonMM.hwConfig(self)
        self.ADDR_BUFF_DEPTH = HwParam(4)
        self.DATA_BUFF_DEPTH = HwParam(4)

    @override
    def hwDeclr(self):
        addClkRstn(self)

        with self._hwParamsShared():
            self.s = AvalonMM()

        with self._hwParamsShared():
            self.m: AvalonMM = AvalonMM()._m()

        assert self.ADDR_BUFF_DEPTH > 0 or self.DATA_BUFF_DEPTH > 0, (
            "This buffer is completely disabled,"
            " it should not be instantiated at all",
            self.ADDR_BUFF_DEPTH, self.DATA_BUFF_DEPTH)

    def _mk_buff(self, DEPTH: int, DATA_WIDTH: int) -> Union[HandshakedFifo, HandshakedReg]:
        if DEPTH == 1:
            b = HandshakedReg(HwIODataRdVld)
        else:
            b = HandshakedFifo(HwIODataRdVld)
            b.DEPTH = self.DATA_BUFF_DEPTH

        b.DATA_WIDTH = DATA_WIDTH

        return b

    @override
    def hwImpl(self):
        s: AvalonMM = self.s
        m: AvalonMM = self.m

        r_data = self._mk_buff(self.DATA_BUFF_DEPTH, self.DATA_WIDTH)
        self.r_data = r_data

        r_data.dataIn.data(m.readData)
        r_data.dataIn.vld(m.readDataValid)

        s.readData(r_data.dataOut.data)
        s.readDataValid(r_data.dataOut.vld)
        r_data.dataOut.rd(1)

        w_resp = self._mk_buff(self.DATA_BUFF_DEPTH, m.response._dtype.bit_length())
        self.w_resp = w_resp

        w_resp.dataIn.data(m.response)
        w_resp.dataIn.vld(m.writeResponseValid)

        s.response(w_resp.dataOut.data)
        s.writeResponseValid(w_resp.dataOut.vld)
        w_resp.dataOut.rd(1)

        addr_data = HwIO_pack(s, exclude=[s.readData, s.readDataValid, s.response, s.writeResponseValid, s.waitRequest])
        addr = self._mk_buff(self.ADDR_BUFF_DEPTH, addr_data._dtype.bit_length())
        self.addr = addr

        addr.dataIn.data(addr_data)
        StreamNode(
            [(s.read | s.write, ~s.waitRequest), ],
            [addr.dataIn],
        ).sync()

        m_tmp = AvalonMM()
        m_tmp._updateHwParamsFrom(m)
        self.m_tmp = m_tmp
        non_addr_signals = [
            m_tmp.readData,
            m_tmp.readDataValid,
            m_tmp.response,
            m_tmp.writeResponseValid,
            m_tmp.waitRequest
        ]
        HwIO_connectPacked(addr.dataOut.data, m_tmp, exclude=non_addr_signals)
        m(m_tmp, exclude=non_addr_signals + [m_tmp.read, m_tmp.write])
        m.read(m_tmp.read & addr.dataOut.vld)
        m.write(m_tmp.write & addr.dataOut.vld)
        addr.dataOut.rd(~m.waitRequest)

        propagateClkRstn(self)


if __name__ == "__main__":
    from hwt.synth import to_rtl_str

    m = AvalonMmBuff()
    print(to_rtl_str(m))
