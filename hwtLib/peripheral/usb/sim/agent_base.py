from typing import List, Union, Deque

from hwt.code import Concat
from hwt.hdl.types.bitsVal import BitsVal
from hwt.hdl.value import HValue
from hwt.synthesizer.rtlLevel.constants import NOT_SPECIFIED
from hwtLib.logic.crcPoly import CRC_5_USB, CRC_16_USB
from hwtLib.logic.crc_test_utils import NaiveCrcAccumulator
from hwtLib.peripheral.usb.constants import packet_token_t, USB_PID
from hwtLib.peripheral.usb.descriptors.bundle import UsbDescriptorBundle
from hwtLib.types.ctypes import uint8_t
from pyMathBitPrecise.bit_utils import reverse_bits


class UsbPacketToken():
    """
    :note: bits of individual items are sent in LSB first but the items of the packet are sent
        in the oreder defined by structure of the packet
    """

    def __init__(self, pid: USB_PID, addr: int, endp: int):
        self.pid = pid
        self.addr = addr
        self.endp = endp

    def crc5(self):
        r = NaiveCrcAccumulator(CRC_5_USB)
        r.takeWord(self.addr, 7)
        r.takeWord(self.endp, 4)
        return r.getFinalValue()

    def pack(self):
        return packet_token_t.from_py({
            "pid": reverse_bits(self.pid, 4),
            "addr": reverse_bits(self.addr, 7),
            "endp": reverse_bits(self.endp, 4),
            "crc5": self.crc5(),
        })

    @classmethod
    def unpack(cls, v: Union[BitsVal, List[BitsVal]]):
        if isinstance(v, (list, tuple)):
            v = Concat(*reversed(v))

        _v = v._reinterpret_cast(packet_token_t)
        pid = reverse_bits(int(_v.pid), 4)
        addr = reverse_bits(int(_v.addr), 7)
        endp = reverse_bits(int(_v.endp), 4)
        self = cls(pid, addr, endp)
        assert self.crc5() == int(_v.crc5)
        return self

    def __repr__(self):
        return "<%s %s, 0x%x>" % (self.__class__.__name__, self.pid, self.addr)


class UsbPacketData():

    def __init__(self, pid: int, data: List[int]):
        self.pid = pid
        if isinstance(data, HValue):
            data = UsbDescriptorBundle.pack_descriptor(data)
        else:
            assert isinstance(data, list), data
        self.data = data

    def crc16(self):
        r = NaiveCrcAccumulator(CRC_16_USB)
        for d in self.data:
            r.takeWord(d, 8)
        return r.getFinalValue()

    def unpack(self, t):
        assert len(self.data) == t.bit_length() // 8
        data = [d if isinstance(d, HValue) else uint8_t.from_py(d) for d in self.data]
        return Concat(*reversed(data))._reinterpret_cast(t)

    def __repr__(self):
        pid = self.pid
        if pid == USB_PID.DATA_0:
            pid = "0"
        elif pid == USB_PID.DATA_1:
            pid = "1"
        elif pid == USB_PID.DATA_2:
            pid = "2"
        elif pid == USB_PID.DATA_M:
            pid = "M"
        else:
            pid = "<invalid>(%r)" % pid

        return "<%s %s, %r>" % (self.__class__.__name__, pid, self.data)


class UsbPacketHandshake():

    def __init__(self, pid: USB_PID):
        self.pid = pid

    def __repr__(self):
        pid = self.pid
        if pid == USB_PID.HS_ACK:
            pid = "ACK"
        elif pid == USB_PID.HS_NACK:
            pid = "NACK"
        elif pid == USB_PID.HS_NYET:
            pid = "NYET"
        elif pid == USB_PID.HS_STALL:
            pid = "STALL"
        else:
            pid = "<invalid>(%r)" % pid

        return "<%s %s>" % (self.__class__.__name__, pid)


class UsbAgent():

    def __init__(self,
                 rx: Deque[Union[UsbPacketToken, UsbPacketData]],
                 tx: Deque[Union[UsbPacketToken, UsbPacketData]]):
        self.rx = rx
        self.tx = tx
        self.RETRY_CNTR_MAX = 100

    def receive(self, packet_cls):
        rx = self.rx
        i = self.RETRY_CNTR_MAX
        while not rx and i:
            i -= 0
            yield None

        t = rx.popleft()

        if packet_cls is not NOT_SPECIFIED:
            assert isinstance(t, packet_cls), t

        # print(self, t)
        return t

    def wait_on_ack(self):
        i = self.RETRY_CNTR_MAX
        while not self.rx and i:
            i -= 1
            yield None

        d = self.rx.popleft()
        assert isinstance(d, UsbPacketHandshake) and d.pid == USB_PID.HS_ACK, d

    def send(self, p):
        "send and wait until other side consumes the data"
        tx = self.tx
        tx.append(p)
        while tx:
            yield None

    def send_ack(self):
        yield from self.send(UsbPacketHandshake(USB_PID.HS_ACK))

