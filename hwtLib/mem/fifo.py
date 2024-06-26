#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Tuple, List

from hwt.code import If
from hwt.hdl.types.bits import HBits
from hwt.hwIOs.std import HwIOFifoWriter, HwIOFifoReader, HwIOVectSignal
from hwt.hwIOs.utils import addClkRstn
from hwt.math import log2ceil
from hwt.serializer.mode import serializeParamsUniq
from hwt.hwParam import HwParam
from hwt.synthesizer.rtlLevel.rtlSignal import RtlSignal
from hwt.hwModule import HwModule
from hwt.constants import NOT_SPECIFIED
from hwt.pyUtils.typingFuture import override


# https://eewiki.net/pages/viewpage.action?pageId=20939499
@serializeParamsUniq
class Fifo(HwModule):
    """
    Generic FIFO usually mapped to BRAM.

    :ivar ~.EXPORT_SIZE: parameter, if true "size" signal will be exported
    :ivar ~.size: optional signal with count of items stored in this fifo
    :ivar ~.EXPORT_SPACE: parameter, if true "space" signal is exported
    :ivar ~.space: optional signal with count of items which can be added to this fifo

    .. hwt-autodoc:: _example_Fifo
    """

    @override
    def hwConfig(self):
        self.DATA_WIDTH = HwParam(64)
        self.DEPTH = HwParam(0)
        self.EXPORT_SIZE = HwParam(False)
        self.EXPORT_SPACE = HwParam(False)
        self.INIT_DATA: tuple = HwParam(())
        self.INIT_DATA_FIRST_WORD = HwParam(NOT_SPECIFIED)

    def _declr_size_and_space(self):
        if self.EXPORT_SIZE:
            self.size = HwIOVectSignal(log2ceil(self.DEPTH + 1), signed=False)._m()
        if self.EXPORT_SPACE:
            self.space = HwIOVectSignal(log2ceil(self.DEPTH + 1), signed=False)._m()

    @override
    def hwDeclr(self):
        assert self.DEPTH > 0, \
            "Fifo is disabled in this case, do not use it entirely"

        addClkRstn(self)
        with self._hwParamsShared():
            self.dataIn = HwIOFifoWriter()
            self.dataOut = HwIOFifoReader()._m()
        self._declr_size_and_space()

    def fifo_pointers(self, DEPTH: int,
                      write_en_wait: Tuple[RtlSignal, RtlSignal],
                      read_en_wait_list: List[Tuple[RtlSignal, RtlSignal]])\
                      ->List[Tuple[RtlSignal, RtlSignal]]:
        """
        Create fifo writer and reader pointers and enable/wait logic
        This functions supports multiple reader pointers

        :attention: writer pointer next logic check only last reader pointer
        :return: list, tule(en, ptr) for writer and each reader
        """
        index_t = HBits(log2ceil(DEPTH), signed=False)
        # assert isPow2(DEPTH), DEPTH
        MAX_DEPTH = DEPTH - 1
        s = self._sig
        r = self._reg
        fifo_write = s("fifo_write")
        write_ptr = _write_ptr = r("write_ptr", index_t, min(len(self.INIT_DATA), MAX_DEPTH))
        ack_ptr_list = [(fifo_write, write_ptr), ]
        # update writer (head) pointer as needed
        If(fifo_write,
            If(write_ptr._eq(MAX_DEPTH),
                write_ptr(0)
            ).Else(
                write_ptr(write_ptr + 1)
            )
        )

        write_en, _ = write_en_wait
        # instantiate all read pointers
        for i, (read_en, read_wait) in enumerate(read_en_wait_list):
            read_ptr = r(f"read_ptr{i:d}", index_t, 0)
            fifo_read = s(f"fifo_read{i:d}")
            ack_ptr_list.append((fifo_read, read_ptr))
            # update reader (tail) pointer as needed
            If(fifo_read,
                If(read_ptr._eq(MAX_DEPTH),
                    read_ptr(0)
                ).Else(
                    read_ptr(read_ptr + 1)
                )
            )

            looped = r(f"looped{i:d}", def_val=False if len(self.INIT_DATA) <= MAX_DEPTH else True)
            # looped logic
            If(write_en & write_ptr._eq(MAX_DEPTH),
                looped(True)
            ).Elif(read_en & read_ptr._eq(MAX_DEPTH),
                looped(False)
            )

            # Update Empty and Full flags
            read_wait(write_ptr._eq(read_ptr) & ~looped)
            fifo_read(read_en & (looped | (write_ptr != read_ptr)))
            # previous reader is next port writer (producer) as it next reader can continue only if previous reader did consume the item
            write_en, _ = read_en, read_wait
            write_ptr = read_ptr

        write_en, write_wait = write_en_wait
        write_ptr = _write_ptr
        # Update Empty and Full flags
        write_wait(write_ptr._eq(read_ptr) & looped)
        fifo_write(write_en & (~looped | (write_ptr != read_ptr)))

        return ack_ptr_list

    @override
    def hwImpl(self):
        DEPTH = self.DEPTH

        dout = self.dataOut
        din = self.dataIn

        s = self._sig
        r = self._reg
        ((fifo_write, wr_ptr), (fifo_read, rd_ptr),) = self.fifo_pointers(
            DEPTH, (din.en, din.wait), [(dout.en, dout.wait), ])

        init_data = self.INIT_DATA
        if not init_data:
            init_data_expanded = None
        else:
            init_data_expanded = list(init_data) + [None for _ in range(self.DEPTH - len(init_data))]

        if self.DATA_WIDTH:
            mem = self.mem = s("memory", HBits(self.DATA_WIDTH)[DEPTH], def_val=init_data_expanded)
            If(self.clk._onRisingEdge(),
                If(fifo_write,
                    # Write Data to Memory
                    mem[wr_ptr](din.data)
                )
            )

            If(self.clk._onRisingEdge(),
                If(fifo_read,
                    # Update data output
                    dout.data(mem[rd_ptr])
                )

                if self.INIT_DATA_FIRST_WORD == NOT_SPECIFIED else

                If(self.rst_n._isOn(),
                   dout.data(self.INIT_DATA_FIRST_WORD),
                ).Elif(fifo_read,
                    # Update data output
                    dout.data(mem[rd_ptr])
                )
            )

        if self.EXPORT_SIZE:
            size = r("size_reg", self.size._dtype, len(self.INIT_DATA))
            If(fifo_read,
                If(~fifo_write,
                   size(size - 1)
                )
            ).Else(
                If(fifo_write,
                   size(size + 1)
                )
            )
            self.size(size)

        if self.EXPORT_SPACE:
            space = r("space_reg", self.space._dtype, DEPTH - len(self.INIT_DATA))
            If(fifo_read,
                If(~fifo_write,
                   space(space + 1)
                )
            ).Else(
                If(fifo_write,
                   space(space - 1)
                )
            )
            self.space(space)


def _example_Fifo():
    m = Fifo()
    m.DATA_WIDTH = 8
    m.EXPORT_SIZE = True
    m.EXPORT_SPACE = True
    m.INIT_DATA = (1, 2, 3)
    m.INIT_DATA_FIRST_WORD = 0
    m.DEPTH = 16

    return m


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    
    m = _example_Fifo()
    print(to_rtl_str(m))
