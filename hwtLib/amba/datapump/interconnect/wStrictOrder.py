#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import Or, Switch
from hwt.hwIOs.std import HwIODataRdVld
from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.math import log2ceil
from hwt.serializer.mode import serializeParamsUniq
from hwt.hObjList import HObjList
from hwt.hwParam import HwParam
from hwtLib.amba.axi_comp.interconnect.base import AxiInterconnectBase
from hwtLib.amba.datapump.intf import HwIOAxiWDatapump
from hwtLib.handshaked.fifo import HandshakedFifo
from hwt.pyUtils.typingFuture import override


@serializeParamsUniq
class WStrictOrderInterconnect(AxiInterconnectBase):
    """
    Strict order interconnect for HwIOAxiWDatapump (N-to-1)
    ensures that response on request is delivered to driver which asked for it
    while transactions can overlap

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        self.DRIVER_CNT = HwParam(2)
        self.MAX_TRANS_OVERLAP = HwParam(16)
        HwIOAxiWDatapump.hwConfig(self)

    def getDpHwIO(self, unit):
        return unit.wDatapump

    @override
    def hwDeclr(self):
        addClkRstn(self)
        with self._hwParamsShared():
            self.drivers = HObjList(
                HwIOAxiWDatapump()
                for _ in range(int(self.DRIVER_CNT)))
            self.wDatapump = HwIOAxiWDatapump()._m()

        self.DRIVER_INDEX_WIDTH = log2ceil(self.DRIVER_CNT)

        fW = self.orderInfoFifoW = HandshakedFifo(HwIODataRdVld)
        fAck = self.orderInfoFifoAck = HandshakedFifo(HwIODataRdVld)
        for f in [fW, fAck]:
            f.DEPTH = self.MAX_TRANS_OVERLAP
            f.DATA_WIDTH = self.DRIVER_INDEX_WIDTH

    def wHandler(self):
        w = self.wDatapump.w
        fWOut = self.orderInfoFifoW.dataOut
        fAckIn = self.orderInfoFifoAck.dataIn

        driversW = [d.w for d in self.drivers]

        selectedDriverVld = self._sig("selectedDriverWVld")
        selectedDriverVld(Or(*map(lambda d: fWOut.data._eq(d[0]) & d[1].valid,
                                  enumerate(driversW))
                            ))
        selectedDriverLast = self._sig("selectedDriverLast")
        selectedDriverLast(Or(*map(lambda d: fWOut.data._eq(d[0]) & d[1].last,
                                   enumerate(driversW))
                             ))

        Switch(fWOut.data).add_cases(
            [(i, w(d, exclude=[d.valid, d.ready]))
               for i, d in enumerate(driversW)]

        ).Default(
            w.data(None),
            w.strb(None),
            w.last(None)
        )

        fAckIn.data(fWOut.data)

        # handshake logic
        fWOut.rd(selectedDriverVld & selectedDriverLast & w.ready & fAckIn.rd)
        for i, d in enumerate(driversW):
            d.ready(fWOut.data._eq(i) & w.ready & fWOut.vld & fAckIn.rd)
        w.valid(selectedDriverVld & fWOut.vld & fAckIn.rd)
        fAckIn.vld(selectedDriverVld & selectedDriverLast & w.ready & fWOut.vld)

        #extraConds = {
        #    fAckIn: selectedDriverLast
        #    }
        #for i, d in enumerate(driversW):
        #    extraConds[d] = fWOut.data._eq(i)
        #
        #StreamNode(masters=[w, fWOut],
        #           slaves=driversW+[fAckIn],
        #           extraConds=extraConds).sync()

    def ackHandler(self):
        ack = self.wDatapump.ack
        fAckOut = self.orderInfoFifoAck.dataOut
        driversAck = [d.ack for d in self.drivers]

        selectedDriverAckReady = self._sig("selectedDriverAckReady")
        selectedDriverAckReady(Or(*map(lambda d: fAckOut.data._eq(d[0]) & d[1].rd,
                                       enumerate(driversAck))
                                 ))

        ack.rd(fAckOut.vld & selectedDriverAckReady)
        fAckOut.rd(ack.vld & selectedDriverAckReady)

        for i, d in enumerate(driversAck):
            d(ack, exclude=[d.vld, d.rd])
            d.vld(ack.vld & fAckOut.vld & fAckOut.data._eq(i))

    @override
    def hwImpl(self):
        assert int(self.DRIVER_CNT) > 1, "It makes no sense to use interconnect in this case"
        propagateClkRstn(self)
        self.reqHandler(self.wDatapump.req, self.orderInfoFifoW.dataIn)
        self.wHandler()
        self.ackHandler()


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    m = WStrictOrderInterconnect()
    print(to_rtl_str(m))
