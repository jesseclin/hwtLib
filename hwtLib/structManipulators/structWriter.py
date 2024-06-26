#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import StaticForEach
from hwt.hdl.types.struct import HStruct
from hwt.hwIOs.std import HwIODataRdVld, HwIORdVldSync
from hwt.hwIOs.hwIOStruct import HwIOStruct
from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.hwParam import HwParam
from hwtLib.amba.axis_comp.frame_deparser import Axi4S_frameDeparser
from hwtLib.amba.datapump.intf import HwIOAxiWDatapump
from hwtLib.handshaked.builder import HsBuilder
from hwtLib.handshaked.fifo import HandshakedFifo
from hwtLib.handshaked.reg import HandshakedReg
from hwtLib.handshaked.streamNode import StreamNode
from hwtLib.structManipulators.structReader import StructReader
from hwt.pyUtils.typingFuture import override

SKIP = 1
PROPAGATE = 0


class StructWriter(StructReader):
    """
    Write struct specified in constructor over wDatapump interface on address
    specified over set interface

    :ivar ~.MAX_OVERLAP: parameter which specifies the maximum number of concurrent transaction
    :ivar ~.WRITE_ACK: HwParam, if true ready on "set" will be set only
        when component is in idle (if false "set"
        is regular handshaked interface)

    .. figure:: ./_static/StructWriter.png

    :note: names in the picture are just illustrative

    .. hwt-autodoc:: _example_StructWriter
    """

    @override
    def hwConfig(self):
        StructReader.hwConfig(self)
        self.MAX_OVERLAP = HwParam(2)
        self.WRITE_ACK = HwParam(False)

    def _createInterfaceForField(self, parent, structField):
        return Axi4S_frameDeparser._mkFieldHwIO(self, parent, structField)

    @override
    def hwDeclr(self):
        addClkRstn(self)
        self.parseTemplate()
        self.dataIn = HwIOStruct(self._structT, tuple(),
                                 self._createInterfaceForField)

        s = self.set = HwIODataRdVld()  # data signal is addr of structure to write
        s.DATA_WIDTH = self.ADDR_WIDTH
        # write ack from slave
        self.writeAck: HwIORdVldSync = HwIORdVldSync()._m()

        with self._hwParamsShared():
            # interface for communication with datapump
            self.wDatapump = HwIOAxiWDatapump()._m()
            self.wDatapump.MAX_BYTES = self.maxBytesInTransaction()

            self.frameAssember = Axi4S_frameDeparser(
                self._structT,
                tmpl=self._tmpl,
                frames=self._frames
            )

    @override
    def hwImpl(self):
        req = self.wDatapump.req
        w = self.wDatapump.w
        ack = self.wDatapump.ack

        # multi frame
        if self.MAX_OVERLAP > 1:
            ackPropageteInfo = HandshakedFifo(HwIODataRdVld)
            ackPropageteInfo.DEPTH = self.MAX_OVERLAP
        else:
            ackPropageteInfo = HandshakedReg(HwIODataRdVld)
        ackPropageteInfo.DATA_WIDTH = 1
        self.ackPropageteInfo = ackPropageteInfo

        if self.WRITE_ACK:
            _set = self.set
        else:
            _set = HsBuilder(self, self.set).buff().end

        if self.ID_WIDTH:
            req.id(self.ID)

        def propagateRequest(frame, indx):
            inNode = StreamNode(slaves=[req, ackPropageteInfo.dataIn])
            ack = inNode.ack()
            isLastFrame = indx == len(self._frames) - 1
            statements = [
                req.addr(_set.data + frame.startBitAddr // 8),
                req.len(frame.getWordCnt() - 1),
                self.driveReqRem(req, frame.parts[-1].endOfPart - frame.startBitAddr),
                ackPropageteInfo.dataIn.data(SKIP if  indx != 0 else PROPAGATE),
                inNode.sync(_set.vld),
                _set.rd(ack if isLastFrame else 0),
            ]

            return statements, ack & _set.vld

        StaticForEach(self, self._frames, propagateRequest)

        # connect write channel
        w(self.frameAssember.dataOut)

        # propagate ack
        StreamNode(
            masters=[ack, ackPropageteInfo.dataOut],
            slaves=[self.writeAck],
            skipWhen={
                self.writeAck: ackPropageteInfo.dataOut.data._eq(PROPAGATE)
            }
        ).sync()

        # connect fields to assembler
        for _, transTmpl in self._tmpl.HwIO_walkFlatten():
            f = transTmpl.getFieldPath()
            hwIO = self.frameAssember.dataIn._fieldsToHwIOs[f]
            hwIO(self.dataIn._fieldsToHwIOs[f])

        propagateClkRstn(self)


def _example_StructWriter():
    from hwtLib.types.ctypes import uint16_t, uint32_t, uint64_t

    s = HStruct(
            (uint64_t, "item0"),  # tuples (type, name) where type has to be instance of Bits type
            (uint64_t, None),  # name = None means this field will be ignored
            (uint64_t, "item1"),
            (uint64_t, None),
            (uint16_t, "item2"),
            (uint16_t, "item3"),
            (uint32_t, "item4"),
            (uint32_t, None),
            (uint64_t, "item5"),  # this word is split on two bus words
            (uint32_t, None),
            (uint64_t, None),
            (uint64_t, None),
            (uint64_t, None),
            (uint64_t, "item6"),
            (uint64_t, "item7"),
        )

    m = StructWriter(s)
    return m


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    m = _example_StructWriter()
    print(to_rtl_str(m))
