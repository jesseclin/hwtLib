# -*- coding: utf-8 -*-

from math import ceil

from hwt.hwIO import HwIO
from hwt.hwIOs.std import HwIOSignal, HwIOVectSignal
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwtSimApi.agents.base import AgentBase
from hwtSimApi.hdlSimulator import HdlSimulator
from hwtSimApi.triggers import WaitTimeslotEnd, Edge
from pyMathBitPrecise.bit_utils import get_bit, mask, get_bit_range


class HwIOHd44780(HwIO):
    """
    HD44780 is an old but comonly used driver for character LCDs.
    It is commonly used for 16x2 character displays but does also supports
    a different number of characters.

    :note: if DATA_WIDTH == 4 the .d signal has 4bits and its bits
        whould be connected to bits 7-4 on physical device

    .. hwt-autodoc::
    """

    # for f_osc = 270KHz, which is deaut clock used by most of the LCDs
    # 37 us, dealy or rest of the commands
    DELAY_CMD = 10
    # 1.52 ms, also for clear display command
    DELAY_RETURN_HOME = 41 * DELAY_CMD
    # ROM code: A00
    CHAR_MAP = {
        **{chr(c): c for c in range(ord(' '), ord('}') + 1)},
        **{
            '¥': 0b01011100,  # replaces \\ glyph in ASCII range above
            '←': 0b01111110,
            '→': 0b01111111,
            # 'ヲ': 0b10100110,
            '⌜': 0b10100010,
            '⌟': 0b10100011,
            # maybe not exactly \\ but looks very similar and there is nothing
            # like \\
            '\\': 0b10100100,
            '·': 0b10100101,

            '°': 0b11011111,
            'α': 0b11100000,
            'ä': 0b11100001,
            'β': 0b11100010,
            'ε': 0b11100011,
            'μ': 0b11100100,
            'σ': 0b11100101,
            'ρ': 0b11100111,

            '√': 0b11101000,

            '¢': 0b11101100,
            'Ⱡ': 0b11101101,
            'ñ': 0b11101110,
            'ö': 0b11101111,

            'θ': 0b11110010,
            '∞': 0b11110011,
            'Ω': 0b11110100,
            'ü': 0b11110101,
            'Σ': 0b11110110,
            'π': 0b11110111,
            'x̅': 0b11110000,

            '÷': 0b11101011,

            '█': 0b11111111,
        },
    }
    INCR = 1
    DECR = 0
    SC_DISPLAY_SHIFT = 1
    SC_CURSOR_MOVE = 0
    SHIFT_RIGHT = 1
    SHIFT_LEFT = 0
    BUSY = 1
    RS_CONTROL = 0
    RS_DATA = 1
    RW_READ = 1
    RW_WRITE = 0

    CMD_CLEAR_DISPLAY = 1  # (long command)
    CMD_RETURN_HOME = 2  # (long command)

    @staticmethod
    def CMD_ENTRY_MODE_SET(incr_decr: int, shift_en: int):
        """
        specifies how the cursor should be modified after char write
        """
        return 0b00000100 | (incr_decr << 1) | (shift_en)

    @staticmethod
    def CMD_DISPLAY_CONTROL(display_on_off, cursor_on_off, cursor_blink):
        return 0b00001000 | (display_on_off << 2)\
             | (cursor_on_off << 1) | cursor_blink

    @staticmethod
    def CMD_CURSOR_OR_DISPLAY_SHIFT(shift_or_cursor, right_left):
        return 0b00010000 | (shift_or_cursor << 3) | (right_left << 2)

    # depends on physical wires
    DATA_LEN_4b = 0
    DATA_LEN_8b = 1
    # depens on LCD type
    LINES_1 = 0
    LINES_2 = 1
    FONT_5x8 = 0  # deault
    FONT_5x10 = 1

    @staticmethod
    def CMD_FUNCTION_SET(data_len, lines, font):
        assert data_len in (HwIOHd44780.DATA_LEN_4b, HwIOHd44780.DATA_LEN_8b)
        assert lines in (HwIOHd44780.LINES_1, HwIOHd44780.LINES_2)
        assert font in (HwIOHd44780.FONT_5x8, HwIOHd44780.FONT_5x8)
        return 0b00100000 | (data_len << 4) | (lines << 3) | (font << 2)

    @staticmethod
    def CMD_DDRAM_ADDR_SET(addr):
        """set cursor position"""
        assert addr & mask(7) == addr, addr
        return 0b10000000 | addr

    @override
    def hwConfig(self):
        self.FREQ = int(270e3)
        self.DATA_WIDTH = HwParam(8)
        self.ROWS = HwParam(2)
        self.COLS = HwParam(16)

    @override
    def hwDeclr(self):
        self.en = HwIOSignal()
        self.rs = HwIOSignal()  # register select
        self.rw = HwIOSignal()
        self.d = HwIOVectSignal(self.DATA_WIDTH)

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        self._ag = HD44780InterfaceAgent(sim, self)


class HD44780InterfaceAgent(AgentBase):
    """
    Agent which emulates HD44780 LCD

    :ivar ~.screen: character present on screen
    """
    REV_CHAR_MAP = {v: k for k, v in HwIOHd44780.CHAR_MAP.items()}

    def __init__(self, sim: HdlSimulator, hwIO: HwIOHd44780):
        super(HD44780InterfaceAgent, self).__init__(sim, hwIO)
        self.screen = [
            [' ' for _ in range(hwIO.COLS)]
            for _ in range(hwIO.ROWS)
        ]
        self.busy = False
        self.cursor = [0, 0]  # left upper corner, [row, line]
        self.cursor_on = None
        self.cursor_blink = None
        self.display_on = None
        # speciies how the cursor should be modified after char write
        self.shift = None
        self.lines = None
        self.data_len = None
        self.font = None

    def get_str(self):
        return "\n".join(["".join(line) for line in self.screen])

    @override
    def monitor(self):
        i = self.hwIO
        while True:
            # print(self.sim.now // Time.ns)
            yield Edge(i.en)
            yield WaitTimeslotEnd()
            if i.en.read():
                rs = int(i.rs.read())
                rw = int(i.rw.read())
                d = int(i.d.read())
                if rs == HwIOHd44780.RS_CONTROL:
                    # command processing
                    if rw == HwIOHd44780.RW_WRITE:
                        if d & 0b10000000:
                            # cursor position set (DDRAM addr)
                            d = get_bit_range(d, 0, 7)
                            self.cursor[0] = ceil(d / i.COLS)
                            assert self.cursor[0] < i.ROWS, self.cursor[0]
                            self.cursor[1] = d % i.ROWS
                        elif d & 0b01000000:
                            raise NotImplementedError()
                        elif d & 0b00100000:
                            # CMD_FUNCTION_SET
                            self.data_len = get_bit(d, 4)
                            self.lines = get_bit(d, 3)
                            self.font = get_bit(d, 2)
                        elif d & 0b00010000:
                            # CMD_CURSOR_OR_DISPLAY_SHIFT
                            shift_or_cursor = get_bit(d, 3)
                            right_left = get_bit(d, 2)
                            if shift_or_cursor == HwIOHd44780.SC_CURSOR_MOVE:
                                c = self.cursor
                                if right_left == HwIOHd44780.SHIFT_RIGHT:
                                    c[1] += 1
                                    if c[1] == i.COLS:
                                        c[1] = 0
                                        c[0] += 1
                                        if c[0] == i.ROWS:
                                            c[0] = 0
                            else:
                                raise NotImplementedError()
                        elif d & 0b00001000:
                            # CMD_DISPLAY_CONTROL
                            self.display_on = get_bit(d, 2)
                            self.cursor_on = get_bit(d, 1)
                            self.cursor_blink = get_bit(d, 0)
                        elif d & 0b00000100:
                            # CMD_ENTRY_MODE_SET
                            shift_en = get_bit(d, 0)
                            incr_decr = get_bit(d, 1)
                            if shift_en:
                                self.shift = 1 if incr_decr == HwIOHd44780.INCR else -1
                            else:
                                self.shift = 0
                        elif d & HwIOHd44780.CMD_RETURN_HOME:
                            raise NotImplementedError()
                        elif d == HwIOHd44780.CMD_CLEAR_DISPLAY:
                            for line in self.screen:
                                for x in range(i.COLS):
                                    line[x] = ' '
                            self.cursor = [0, 0]
                        else:
                            raise NotImplementedError("{0:8b}".format(d))
                    else:
                        assert rw == HwIOHd44780.RW_READ, rw
                        raise NotImplementedError()
                else:
                    # data processing
                    assert rs == HwIOHd44780.RS_DATA, rs
                    if self.data_len == HwIOHd44780.DATA_LEN_8b:
                        d = int(d)
                        d = self.REV_CHAR_MAP.get(d, " ")
                        cur = self.cursor
                        self.screen[cur[0]][cur[1]] = d
                        cur[1] += self.shift
                    else:
                        raise NotImplementedError()
