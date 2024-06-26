from math import ceil

from hwt.code import If, Switch
from hwt.hdl.types.bits import HBits
from hwt.hwIOs.std import HwIODataRdVld
from hwt.hwIOs.utils import addClkRstn
from hwt.math import log2ceil
from hwt.pyUtils.arrayQuery import iter_with_last
from hwt.hwModule import HwModule
from hwt.hwParam import HwParam
from hwtLib.amba.axi4s import Axi4Stream
from hwtLib.handshaked.streamNode import StreamNode
from hwt.pyUtils.typingFuture import override


class Axi4S_eq(HwModule):
    """
    Comparator of const size value provided as a Axi4Stream

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        Axi4Stream.hwConfig(self)
        self.VAL = HwParam(HBits(64).from_py(0))

    @override
    def hwDeclr(self):
        addClkRstn(self)
        with self._hwParamsShared():
            self.dataIn = Axi4Stream()
        self.dataOut = HwIODataRdVld()._m()
        self.dataOut.DATA_WIDTH = 1

    @override
    def hwImpl(self):
        V = self.VAL
        VAL_W = self.VAL._dtype.bit_length()
        D_W = self.DATA_WIDTH
        if not V._is_full_valid():
            raise NotImplementedError()
        din = self.dataIn
        dout = self.dataOut
        if VAL_W <= D_W:
            # do comparison in single word
            dout.data(din.data[VAL_W:]._eq(V))
            StreamNode([din], [dout]).sync()
        else:
            # build fsm for comparing
            word_cnt = ceil(VAL_W / D_W)
            word_index = self._reg("word_index", HBits(log2ceil(word_cnt - 1)),
                                   def_val=0)
            # true if all previous words were matching
            state = self._reg("state", def_val=1)
            offset = 0
            word_cases = []
            for is_last_word, i in iter_with_last(range(word_cnt)):
                val_low = offset
                val_high = min(offset + D_W, VAL_W)
                in_high = val_high - val_low
                state_update = din.data[in_high:]._eq(V[val_high:val_low])
                if is_last_word:
                    dout.data(state & state_update)
                else:
                    word_cases.append((i, state(state & state_update)))
                offset = val_high

            If(StreamNode([din], [dout]).ack(),
                If(din.last,
                   word_index(0),
                   state(1),
                ).Else(
                   word_index(word_index + 1),
                   Switch(word_index)\
                   .add_cases(word_cases)
                )
            )

            StreamNode([din],
                       [dout],
                       extraConds={dout: din.valid & din.last},
                       skipWhen={dout: ~(din.valid & din.last)}
            ).sync()

