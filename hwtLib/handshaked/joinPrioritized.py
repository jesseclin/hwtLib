#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import And, Or, SwitchLogic
from hwt.hObjList import HObjList
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwtLib.handshaked.compBase import HandshakedCompBase


class HsJoinPrioritized(HandshakedCompBase):
    """
    Join input stream to single output stream
    inputs with lower number has higher priority

    :note: combinational

    .. hwt-autodoc:: _example_HsJoinPrioritized
    """

    @override
    def hwConfig(self):
        self.INPUTS = HwParam(2)
        super().hwConfig()

    @override
    def hwDeclr(self):
        with self._hwParamsShared():
            self.dataIn = HObjList(
                self.hwIOCls() for _ in range(int(self.INPUTS))
            )
            self.dataOut = self.hwIOCls()._m()

    def dataConnectionExpr(self, dIn, dOut):
        """Create connection between input and output interface"""
        data = self.get_data
        dataConnectExpr = []
        outDataSignals = list(data(dOut))

        if dIn is None:
            dIn = [None for _ in outDataSignals]
        else:
            dIn = data(dIn)

        for _din, _dout in zip(dIn, outDataSignals):
            dataConnectExpr.append(_dout(_din))

        return dataConnectExpr

    @override
    def hwImpl(self):
        rd = self.get_ready_signal
        vld = self.get_valid_signal
        dout = self.dataOut

        vldSignals = [vld(d) for d in self.dataIn]

        # data out mux
        dataCases = []
        for i, din in enumerate(self.dataIn):
            allLowerPriorNotReady = map(lambda x: ~x, vldSignals[:i])
            rd(din)(And(rd(dout), *allLowerPriorNotReady))

            cond = vld(din)
            dataConnectExpr = self.dataConnectionExpr(din, dout)
            dataCases.append((cond, dataConnectExpr))

        dataDefault = self.dataConnectionExpr(None, dout)
        SwitchLogic(dataCases, dataDefault)

        vld(dout)(Or(*vldSignals))


def _example_HsJoinPrioritized():
    from hwt.hwIOs.std import HwIODataRdVld
    
    m = HsJoinPrioritized(HwIODataRdVld)
    return m


if __name__ == "__main__":
    from hwt.synth import to_rtl_str

    m = _example_HsJoinPrioritized()
    print(to_rtl_str(m))
