from collections import deque

from hwt.constants import NOP
from hwt.simulator.agentBase import SyncAgentBase
from hwtLib.peripheral.usb.constants import USB_LINE_STATE
from hwtLib.peripheral.usb.usb2.ulpi import ulpi_reg_otg_control_t_reset_defaults, \
    ulpi_reg_function_control_t_reset_default
from hwtLib.peripheral.usb.usb2.utmi import Utmi_8b_rx, Utmi_8b, utmi_interrupt_t
from hwtSimApi.agents.base import AgentBase
from hwtSimApi.hdlSimulator import HdlSimulator
from hwtSimApi.triggers import WaitCombStable, WaitCombRead, WaitWriteOnly
from pyMathBitPrecise.bit_utils import ValidityError


class Utmi_8b_rxAgent(SyncAgentBase):
    """
    Simulation agent for :class:`hwtLib.peripheral.usb.usb2.utmi.Utmi_8b_rx` interface.

    :attention: "active" signal acts as a valid, "valid" signal acts as a mask
    :ivar data: Deque[Deque[Tuple[int, int]]] (internal deque represents packets, tuple represents data, error)

    .. figure:: ./_static/utmi_rx.png
    """
    USB_ERROR = "ERROR"

    def __init__(self, sim:HdlSimulator, hwIO: Utmi_8b_rx, allowNoReset=False):
        SyncAgentBase.__init__(self, sim, hwIO, allowNoReset=allowNoReset)
        self._last_active = 0
        self.data = deque()
        self.actual_packet = None

    def get_data(self):
        i = self.hwIO
        if i.error.read():
            d = self.USB_ERROR
        else:
            d = int(i.data.read())
        return d

    def set_active(self, val):
        self.hwIO.active.write(val)
        self._last_active = val

    def set_data(self, data):
        if data is None:
            d = None
            e = None
        else:
            if data is self.USB_ERROR:
                e = 1
                d = None
            else:
                e = 0
                d = data

        i = self.hwIO
        i.data.write(d)
        i.error.write(e)

    def monitor(self):
        yield WaitCombStable()
        if self.notReset():
            hwIO = self.hwIO
            active = int(hwIO.active.read())
            if active:
                if not self._last_active:
                    # start of packet
                    assert self.actual_packet is None
                    self.actual_packet = deque()

                vld = int(hwIO.valid.read())
                if vld:
                    d = self.get_data()
                    if self._debugOutput is not None:
                        self._debugOutput.write("%s, read, %d: %r\n" % (
                            hwIO._getFullName(),
                            self.sim.now, d))
                    self.actual_packet.append(d)

            elif self._last_active:
                # end of packet
                assert self.actual_packet, (self.sim.now, hwIO._getFullName())
                self.data.append(self.actual_packet)
                self.actual_packet = None

            self._last_active = active

    def driver(self):
        yield WaitCombRead()
        d = NOP
        active = 0
        if self.notReset():
            if self.actual_packet:
                d = self.actual_packet.popleft()
                active = 1
            elif self._last_active == 1:
                # end of packet, need to have at least one clk tick with active=0
                active = 0
                d = NOP

            elif self.data and self._last_active == 0:
                self.actual_packet = self.data.popleft()
                # first beat of packet (active=1, valid=0)
                active = 1
                d = NOP

        yield WaitWriteOnly()
        hwIO = self.hwIO
        if d is NOP:
            self.set_data(None)
            hwIO.valid.write(0)
        else:
            self.set_data(d)
            hwIO.valid.write(1)

        self.set_active(active)
        if active and self._debugOutput is not None:
            self._debugOutput.write("%s, wrote, %d: %r\n" % (
                hwIO._getFullName(),
                self.sim.now, self.actualData))


class Utmi_8b_txAgent(SyncAgentBase):
    """
    Simulation agent for :class:`hwtLib.peripheral.usb.usb2.utmi.Utmi_8b_tx` interface.

    :ivar data: Deque[Deque[int]] (internal deque represents packets)

    .. figure:: ./_static/utmi_rx.png
    """

    def __init__(self, sim:HdlSimulator, hwIO, allowNoReset=False):
        SyncAgentBase.__init__(
            self, sim, hwIO, allowNoReset=allowNoReset)
        self.data = deque()
        self.actual_packet = None
        self._last_ready = 0
        self._last_valid = 0

    def driver(self):
        yield WaitCombRead()
        if self.notReset():
            d = NOP
            if self.actual_packet:
                d = self.actual_packet[0]
            elif self._last_valid == 1:
                # end of packet, need to have at least one clk tick with active=0
                d = NOP
                self.actual_packet = None

            elif self.data and self._last_ready == 0:
                self.actual_packet = self.data.popleft()
                # first beat of packet (active=1, valid=0)
                d = self.actual_packet[0]

            yield WaitWriteOnly()
            hwIO = self.hwIO

            if d is NOP:
                hwIO.data.write(None)
                hwIO.vld.write(0)
            else:
                hwIO.data.write(d)
                hwIO.vld.write(1)

            yield WaitCombStable()

            try:
                rd = int(hwIO.rd.read())
            except ValidityError:
                raise AssertionError(self.sim.now, hwIO._getFullName(), "invalid rd (would cause desynchronization of the channel)")

            if d is NOP:
                if self._last_valid == 1:
                    assert rd == 1, (self.sim.now, hwIO._getFullName(), rd, "Ready must be 1 or 1 clk tick after end of packet (EOP state)")

            if rd and self.actual_packet:
                self.actual_packet.popleft()

        else:
            rd = 0
            d = NOP

        self._last_ready = rd
        self._last_valid = int(d is not NOP)

    def monitor(self):
        yield WaitCombRead()
        if self.notReset():
            yield WaitWriteOnly()
            yield WaitCombRead()
            hwIO = self.hwIO
            try:
                vld = int(hwIO.vld.read())
            except ValidityError:
                    raise AssertionError(self.sim.now, hwIO._getFullName(), "invalid vld, this would case desynchronization")
            if self._last_valid and not vld:
                # end of packet
                self.data.append(self.actual_packet)
                self.actual_packet = None
            elif not self._last_valid and vld:
                # start of packet
                self.actual_packet = deque()

            if vld:
                try:
                    d = int(hwIO.data.read())
                except ValidityError:
                    raise AssertionError(self.sim.now, hwIO._getFullName(), "invalid data")
                self.actual_packet.append(d)

            if vld or self._last_valid:
                rd = 1
            else:
                rd = 0

            yield WaitWriteOnly()
            hwIO.rd.write(rd)

            self._last_ready = rd
            self._last_valid = vld

        else:
            self._last_ready = 0
            self._last_valid = 0


class Utmi_8bAgent(AgentBase):
    """
    Simulation agent for :class:`hwtLib.peripheral.usb.usb2.utmi.Utmi_8b` interface.
    """

    def __init__(self, sim:HdlSimulator, hwIO: Utmi_8b):
        AgentBase.__init__(self, sim, hwIO)
        for i in [hwIO.function_control, hwIO.otg_control, hwIO.interrupt, hwIO.rx, hwIO.tx]:
            i._initSimAgent(sim)

    @property
    def link_to_phy_packets(self):
        return self.hwIO.tx._ag.data

    @link_to_phy_packets.setter
    def link_to_phy_packets_setter(self, v):
        self.hwIO.tx._ag.data = v

    @property
    def actual_link_to_phy_packet(self):
        return self.hwIO.tx._ag.actual_packet

    @actual_link_to_phy_packet.setter
    def actual_link_to_phy_packet_setter(self, v):
        self.hwIO.tx._ag.actual_packet = v

    @property
    def phy_to_link_packets(self):
        return self.hwIO.rx._ag.data

    @phy_to_link_packets.setter
    def phy_to_link_packets_setter(self, v):
        self.hwIO.rx._ag.data = v

    @property
    def actual_phy_to_link_packet(self):
        return self.hwIO.tx._ag.actual_packet

    @actual_phy_to_link_packet.setter
    def actual_phy_to_link_packet_setter(self, v):
        self.hwIO.rx._ag.actual_packet = v

    def getMonitors(self):
        yield from self.hwIO.tx._ag.getDrivers()
        yield from self.hwIO.rx._ag.getMonitors()
        yield self.monitor()

    def monitor(self):
        yield WaitWriteOnly()
        hwIO = self.hwIO
        for cHwIO in hwIO.function_control._hwIOs:
            d = ulpi_reg_function_control_t_reset_default[cHwIO._name]
            cHwIO.write(d)

        for cHwIO in hwIO.otg_control._hwIOs:
            d = ulpi_reg_otg_control_t_reset_defaults[cHwIO._name]
            cHwIO.write(d)
        hwIO.tx.vld.write(0)

    def getDrivers(self):
        yield from self.hwIO.tx._ag.getMonitors()
        yield from self.hwIO.rx._ag.getDrivers()
        yield self.driver()

    def driver(self):
        yield WaitWriteOnly()
        hwIO = self.hwIO
        hwIO.LineState.write(USB_LINE_STATE.J)
        hwIO.interrupt._ag.set_data(tuple(0 for _ in range(len(utmi_interrupt_t.fields) - 1)))
        hwIO.tx.rd.write(0)
        hwIO.rx.valid.write(0)
        hwIO.rx.active.write(0)

