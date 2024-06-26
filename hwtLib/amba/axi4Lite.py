from hwt.hwIOs.std import HwIOVectSignal
from hwt.pyUtils.typingFuture import override
from hwtLib.amba.axi3Lite import IP_Axi3Lite, Axi3Lite, Axi3Lite_r, \
    Axi3Lite_b, Axi3Lite_w, Axi3Lite_addr, Axi3Lite_addrAgent
from hwtLib.amba.axi_common import AxiMap
from hwtLib.amba.constants import PROT_DEFAULT
from hwtSimApi.hdlSimulator import HdlSimulator


class Axi4Lite_addr(Axi3Lite_addr):
    """
    :class:`~.Axi3Lite_addr` with "prot" signal added.

    .. hwt-autodoc::
    """

    @override
    def hwDeclr(self):
        super(Axi4Lite_addr, self).hwDeclr()
        self.prot = HwIOVectSignal(3)

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        self._ag = Axi4Lite_addrAgent(sim, self)


class Axi4Lite_addrAgent(Axi3Lite_addrAgent):
    """
    :ivar ~.data: iterable of addr
    """

    @override
    def get_data(self):
        return self.hwIO.addr.read(), self.hwIO.prot.read()

    @override
    def set_data(self, data):
        if data is None:
            addr, prot = None, None
        else:
            addr, prot = data

        self.hwIO.addr.write(addr)
        self.hwIO.prot.write(prot)

    @override
    def create_addr_req(self, addr, prot=PROT_DEFAULT):
        return (addr, prot)


class Axi4Lite_w(Axi3Lite_w):
    """
    (Same as :class:`~.Axi3Lite_w`)

    .. hwt-autodoc::
    """

class Axi4Lite_b(Axi3Lite_b):
    """
    (Same as :class:`~.Axi3Lite_b`)

    .. hwt-autodoc::
    """

class Axi4Lite_r(Axi3Lite_r):
    """
    (Same as :class:`~.Axi3Lite_r`)

    .. hwt-autodoc::
    """

class Axi4Lite(Axi3Lite):
    """
    Axi4-lite bus interface
    (Same as :class:`~.Axi3Lite` just address channels do have "prot" signal)

    .. hwt-autodoc::
    """
    AW_CLS = Axi4Lite_addr
    AR_CLS = Axi4Lite_addr
    W_CLS = Axi4Lite_w
    R_CLS = Axi4Lite_r
    B_CLS = Axi4Lite_b

    @override
    def _getIpCoreIntfClass(self):
        return IP_Axi4Lite


class IP_Axi4Lite(IP_Axi3Lite):
    """
    IP core meta description for Axi4-lite interface
    """

    def __init__(self):
        super().__init__()
        self.quartus_name = "axi4lite"
        a_sigs = ['addr', 'prot', 'valid', 'ready']
        self.map = {'aw': AxiMap('aw', a_sigs),
                    'w': AxiMap('w', ['data', 'strb', 'valid', 'ready']),
                    'ar': AxiMap('ar', a_sigs),
                    'r': AxiMap('r', ['data', 'resp', 'valid', 'ready']),
                    'b': AxiMap('b', ['valid', 'ready', 'resp'])
                    }
