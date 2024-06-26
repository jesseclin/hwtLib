from hwt.hdl.types.bits import HBits
from hwt.hdl.types.defs import BIT, BIT_N
from hwt.hdl.types.struct import HStruct
from hwt.hwIOs.std import HwIOVectSignal, HwIOSignal, HwIODataRdVld, HwIODataVld
from hwt.hwIOs.hwIOStruct import HdlType_to_HwIO
from hwt.hwIO import HwIO
from hwt.hwParam import HwParam
from hwtSimApi.hdlSimulator import HdlSimulator
from ipCorePackager.constants import DIRECTION
from hwt.pyUtils.typingFuture import override


class Utmi_8b_rx(HwIODataVld):
    """
    :attention: The "active" signal marks for the presense of some data. It has to be asserted 1 before valid is set.
        And it has to be 1 whenever the "vld" signal is 1. Because of this the "active" signal behaves as a valid in :class:`hwt.hwIOs.std.HwIODataVld` interface
        and "vld" signal behaves as a mask.
    :note: The drop to 0 on "active" signal marks for the end of packet.


    .. figure:: ./_static/utmi_rx.png

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        self.DATA_WIDTH = HwParam(8)

    @override
    def hwDeclr(self):
        self.data = HwIOVectSignal(self.DATA_WIDTH)
        self.valid = HwIOSignal()
        # end of packet is recognized by active going low
        self.active = HwIOSignal()
        self.error = HwIOSignal()

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        from hwtLib.peripheral.usb.usb2.utmi_agent import Utmi_8b_rxAgent
        self._ag = Utmi_8b_rxAgent(sim, self)


class Utmi_8b_tx(HwIODataRdVld):
    """
    :note: Same signals as handshaked interface, but the protocol is slightly different

    .. figure:: ./_static/utmi_tx.png

    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        HwIODataRdVld.hwConfig(self)
        self.DATA_WIDTH = 8

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        from hwtLib.peripheral.usb.usb2.utmi_agent import Utmi_8b_txAgent
        self._ag = Utmi_8b_txAgent(sim, self)


utmi_function_control_t = HStruct(
    (HBits(2), "XcvrSelect"),
    (BIT, "TermSelect"),
    (HBits(2), "OpMode"),
    (BIT, "Reset"),
    (BIT_N, "SuspendM"),
    (BIT, None),
)

utmi_interface_control_t = HStruct(
    (BIT, "FsLsSerialMode_6pin"),
    (BIT, "FsLsSerialMode_3pin"),
    (BIT, "CarkitMode"),
    (BIT_N, "ClockSuspendM"),
    (BIT, "AutoResume"),
    (BIT, "IndicatorComplement"),
    (BIT, "IndicatorPassThru"),
    (BIT, "InterfaceProtectDisable"),
)

utmi_otg_control_t = HStruct(
    (BIT, "IdPullup"),
    (BIT, "DpPulldown"),
    (BIT, "DmPulldown"),
    (BIT, "DischrgVbus"),
    (BIT, "ChrgVbus"),
    (BIT, "DrvVbus"),
    (BIT, "DrvVbusExternal"),
    (BIT, "UseExternalVbusIndicator"),
)

utmi_interrupt_t = HStruct(
    (BIT, "HostDisconnect"),
    (BIT, "VbusValid"),
    (BIT, "SessValid"),
    (BIT, "SessEnd"),
    (BIT, "IdGnd"),
    (HBits(3), None),
)


class Utmi_8b(HwIO):
    """
    UTMI+ (USB 2.0 Transceiver Macrocell Interace) Level 3, 8b variant only

    https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/usb2-transceiver-macrocell-interface-specification.pdf
    http://ww1.microchip.com/downloads/en/DeviceDoc/00002142A.pdf

    .. hwt-autodoc::
    """

    class XCVR_SELECT():
        HS = 0
        FS = 1

    class TERM_SELECT():
        HS = 0
        FS = 1

    class OP_MODE():
        NORMAL = 0b00
        NON_DRIVING = 0b01
        DISABLE_BIT_STUFFING_AND_NRZI = 0b10
        # 0b11 is reserved

    class LINE_STATE_BIT():
        DP = 0  # data + pin
        DM = 1  # data - pin

    @override
    def hwDeclr(self):
        self.LineState = HwIOVectSignal(2)
        self.function_control = HdlType_to_HwIO().apply(utmi_function_control_t, masterDir=DIRECTION.IN)
        self.otg_control = HdlType_to_HwIO().apply(utmi_otg_control_t, masterDir=DIRECTION.IN)
        self.interrupt = HdlType_to_HwIO().apply(utmi_interrupt_t)

        # end of packet is signalized by tx.vld going low, the tx.rd is 0 in idle and tx.vld has to be asserted 1 firts
        self.tx = Utmi_8b_tx(masterDir=DIRECTION.IN)
        self.rx = Utmi_8b_rx()
        for c in [self.rx, self.tx]:
            c.DATA_WIDTH = 8

    @override
    def _initSimAgent(self, sim:HdlSimulator):
        from hwtLib.peripheral.usb.usb2.utmi_agent import Utmi_8bAgent
        self._ag = Utmi_8bAgent(sim, self)

