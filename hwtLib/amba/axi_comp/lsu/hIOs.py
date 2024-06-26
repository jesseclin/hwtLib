from hwt.hwIO import HwIO
from hwt.hwIOs.std import HwIODataRdVld, HwIOVectSignal, HwIOSignal
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwtLib.amba.axi3Lite import Axi3Lite_addr, Axi3Lite_r
from hwtLib.amba.axi4s import Axi4Stream
from hwtSimApi.hdlSimulator import HdlSimulator
from ipCorePackager.constants import DIRECTION


class HwIOAxiWriteAggregatorWriteTmp(Axi4Stream):
    """
    HwIO for tmp input register on store buffer write input

    :ivar cam_lookup: HwIOVectSignal with value of lookup from item cam
        (1 if cacheline present in store buffer)
    :ivar mask_byte_unaligned: HwIOSignal 1 if any byte of mask is 0 or all 1

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        Axi4Stream.hwConfig(self)
        self.USE_STRB = True
        self.ADDR_WIDTH = HwParam(32)
        self.ITEMS = HwParam(64)

    @override
    def hwDeclr(self):
        self.addr = HwIOVectSignal(self.ADDR_WIDTH)
        Axi4Stream.hwDeclr(self)
        self.colides_with_last_addr = HwIOSignal()
        self.cam_lookup = HwIOVectSignal(self.ITEMS)
        self.mask_byte_unaligned = HwIOSignal()

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        raise NotImplementedError()


class HwIOAxiWriteAggregatorRead(HwIO):
    """
    An interface which is used to speculatively read data from AxiWriteAggregator

    .. hwt-autodoc::
    """

    @override
    def hwConfig(self):
        self.ADDR_WIDTH = HwParam(32)
        self.DATA_WIDTH = HwParam(64)

    @override
    def hwDeclr(self):
        self.a = Axi3Lite_addr()
        self.r_data_available = HwIODataRdVld()
        self.r_data_available.DATA_WIDTH = 1
        self.r = Axi3Lite_r()

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        raise NotImplementedError()
