#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import Or, If
from hwtLib.amba.axis_comp.base import Axi4SCompBase
from hwtLib.handshaked.joinPrioritized import HsJoinPrioritized
from hwt.hwIOs.utils import addClkRstn


class Axi4SJoinPrioritized(Axi4SCompBase, HsJoinPrioritized):
    """
    Join input stream to single output stream
    inputs with lower number has higher priority

    :note: The frame from each interface is always taken as a whole.

    :see: :class:`hwtLib.handshaked.joinPrioritized.HsJoinPrioritized`

    .. hwt-autodoc::
    """

    def hwDeclr(self) -> None:
        addClkRstn(self)
        HsJoinPrioritized.hwDeclr(self)

    def hwImpl(self) -> None:
        join = HsJoinPrioritized(self.HWIO_CLS)
        join._updateHwParamsFrom(self)
        join.get_valid_signal = self.get_valid_signal
        join.get_ready_signal = self.get_ready_signal

        self.join = join

        # en override
        ens = [self._reg(f"en{i:d}", def_val=0) for i in range(len(self.dataIn))]
        all_0 = ~Or(*ens)
        for en_flag, din, c_din in zip(ens, self.dataIn, self.join.dataIn):
            en = (all_0 | en_flag)
            vld = self.get_valid_signal(c_din)
            vld(en & self.get_valid_signal(din))
            rd = self.get_ready_signal(din)
            rd(en & self.get_ready_signal(c_din))
            self.dataConnectionExpr(din, c_din)
            If(rd & vld,
               en_flag(~din.last)
            )
        self.dataOut(join.dataOut)


if __name__ == "__main__":
    from hwt.synth import to_rtl_str

    m = Axi4SJoinPrioritized()
    print(to_rtl_str(m))
