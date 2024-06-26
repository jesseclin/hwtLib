from hwt.hwIOs.agents.rdVldSync import HwIODataRdVldAgent
from hwt.hwIOs.std import HwIOVectSignal, HwIOSignal, HwIODataRdVld
from hwt.hwParam import HwParam
from hwtSimApi.hdlSimulator import HdlSimulator
from hwt.pyUtils.typingFuture import override


class HwIODataMaskLastRdVld(HwIODataRdVld):
    """
    HwIODataRdVld interface with data, mask, last signal.

    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        self.MASK_GRANULARITY = HwParam(8)
        HwIODataRdVld.hwConfig(self)

    @override
    def hwDeclr(self):
        super(HwIODataMaskLastRdVld, self).hwDeclr()
        assert self.DATA_WIDTH % self.MASK_GRANULARITY == 0, (
            self.DATA_WIDTH, self.MASK_GRANULARITY)
        self.USE_MASK = self.MASK_GRANULARITY != self.DATA_WIDTH
        if self.USE_MASK:
            self.mask = HwIOVectSignal(self.DATA_WIDTH // self.MASK_GRANULARITY)
        self.last = HwIOSignal()

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        self._ag = HwIODataMaskRdVldAgent(sim, self)


class HwIODataMaskRdVldAgent(HwIODataRdVldAgent):
    """
    Simulation agent for :class:`.HwIODataMaskLastRdVld` interface.
    """

    @override
    def set_data(self, data):
        i = self.hwIO
        if data is None:
            d, m, last = None, None, None
        else:
            d, m, last = data

        i.mask.write(m)
        i.data.write(d)
        i.last.write(last)

    @override
    def get_data(self):
        i = self.hwIO
        return i.data.read(), i.mask.read(), i.last.read()
