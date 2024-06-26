#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwtLib.amba.axi_comp.oooOp.outOfOrderCummulativeOp import OutOfOrderCummulativeOp
from hwtLib.amba.axi_comp.oooOp.utils import OOOOpPipelineStage


class OooOpExampleCounterArray(OutOfOrderCummulativeOp):
    """
    This components uses array of counters accessible through axi interface.
    These counters are incremented using "dataIn" interface in a coherent way.
    The operation may finish out of order but the data on "dataOut" and in the memory
    will be correct.

    .. hwt-autodoc::
    """

    def hwConfig(self):
        OutOfOrderCummulativeOp.hwConfig(self)
        # the transaction always just increments the counter
        # so there is no need for transaction state
        self.TRANSACTION_STATE_T = None

    def main_op(self,  dst_main_state: OOOOpPipelineStage, src_main_state: OOOOpPipelineStage):
        return dst_main_state.data(src_main_state.data + 1)


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    
    # m = _example_OutOfOrderCummulativeOp()
    m = OooOpExampleCounterArray()
    m.ID_WIDTH = 2
    m.ADDR_WIDTH = 2 + 3
    m.DATA_WIDTH = m.MAIN_STATE_T.bit_length()

    print(to_rtl_str(m))
