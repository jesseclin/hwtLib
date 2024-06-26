from hwt.constants import DIRECTION
from hwt.hwIOs.std import HwIOVectSignal, HwIOSignal
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwt.serializer.ip_packager import IpPackager
from hwtLib.amba.axi3Lite import Axi3Lite_addr, Axi3Lite, Axi3Lite_r, Axi3Lite_b, \
    IP_Axi3Lite
from hwtLib.amba.axi4s import Axi4Stream, Axi4StreamAgent
from hwtLib.amba.axi_common import AxiMap, Axi_id, Axi_hs, Axi_strb
from hwtLib.amba.constants import BYTES_IN_TRANS, BURST_INCR, CACHE_DEFAULT, \
    LOCK_DEFAULT, PROT_DEFAULT
from hwtLib.amba.sim.agentCommon import BaseAxiAgent
from hwtSimApi.hdlSimulator import HdlSimulator
from ipCorePackager.component import Component


_DEFAULT = object()


#####################################################################
class Axi3_addr(Axi3Lite_addr, Axi_id):
    """
    Axi3 address channel interface

    .. hwt-autodoc::
    """
    LEN_WIDTH = 4
    LOCK_WIDTH = 2

    @override
    def hwConfig(self):
        Axi3Lite_addr.hwConfig(self)
        Axi_id.hwConfig(self, default_id_width=6)
        self.USER_WIDTH = HwParam(0)

    @override
    def hwDeclr(self):
        Axi3Lite_addr.hwDeclr(self)
        Axi_id.hwDeclr(self)
        self.burst = HwIOVectSignal(2)
        self.cache = HwIOVectSignal(4)
        self.len = HwIOVectSignal(self.LEN_WIDTH)
        self.lock = HwIOVectSignal(self.LOCK_WIDTH)
        self.prot = HwIOVectSignal(3)
        self.size = HwIOVectSignal(3)
        if self.USER_WIDTH:
            self.user = HwIOVectSignal(self.USER_WIDTH)

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        self._ag = Axi3_addrAgent(sim, self)


class Axi3_addrAgent(Axi4StreamAgent):
    """
    Simulation agent for :class:`.Axi3_addr` interface

    input/output data stored in list under "data" property
    data contains tuples (id, addr, burst, cache, len, lock,
    prot, size, qos, optionally user)
    """

    def __init__(self, sim: HdlSimulator, hwIO: Axi3_addr, allowNoReset=False):
        BaseAxiAgent.__init__(self, sim, hwIO, allowNoReset=allowNoReset)

        signals = [
            hwIO.id,
            hwIO.addr,
            hwIO.burst,
            hwIO.cache,
            hwIO.len,
            hwIO.lock,
            hwIO.prot,
            hwIO.size,
        ]
        if hasattr(hwIO, "user"):
            signals.append(hwIO.user)
        self._signals = tuple(signals)
        self._sigCnt = len(signals)

    def create_addr_req(self, addr, _len,
                        _id=0,
                        burst=BURST_INCR,
                        cache=CACHE_DEFAULT,
                        lock=LOCK_DEFAULT,
                        prot=PROT_DEFAULT,
                        size=_DEFAULT,
                        user=None):
        """
        Create a default AXI address transaction
        :note: transaction is created and returned but it is not added to a agent data
        """
        if size is _DEFAULT:
            D_B = self.hwIO._parent.DATA_WIDTH // 8
            size = BYTES_IN_TRANS(D_B)
        if self.hwIO.USER_WIDTH:
            return (_id, addr, burst, cache, _len, lock, prot, size, user)
        else:
            assert user is None
            return (_id, addr, burst, cache, _len, lock, prot, size)


#####################################################################
class Axi3_w(Axi_hs, Axi_strb):
    """
    Axi3 write channel interface (simplified  Axi4Stream)

    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        self.ID_WIDTH = HwParam(0)
        self.DATA_WIDTH = HwParam(64)

    @override
    def hwDeclr(self):
        if self.ID_WIDTH:
            self.id = HwIOVectSignal(self.ID_WIDTH)
        self.data = HwIOVectSignal(self.DATA_WIDTH)
        Axi_strb.hwDeclr(self)
        self.last = HwIOSignal()
        Axi_hs.hwDeclr(self)

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        Axi4Stream._initSimAgent(self, sim)


#####################################################################
class Axi3_r(Axi3Lite_r, Axi_id):
    """
    Axi 3 read channel interface

    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        Axi_id.hwConfig(self, default_id_width=6)
        Axi3Lite_r.hwConfig(self)

    @override
    def hwDeclr(self):
        Axi_id.hwDeclr(self)
        Axi3Lite_r.hwDeclr(self)
        self.last = HwIOSignal()

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        self._ag = Axi3_rAgent(sim, self)


class Axi3_rAgent(BaseAxiAgent):
    """
    Simulation agent for :class:`.Axi4_r` interface

    input/output data stored in list under "data" property
    data contains tuples (id, data, resp, last)
    """

    @override
    def get_data(self):
        hwIO = self.hwIO

        _id = hwIO.id.read()
        data = hwIO.data.read()
        resp = hwIO.resp.read()
        last = hwIO.last.read()

        return (_id, data, resp, last)

    @override
    def set_data(self, data):
        hwIO = self.hwIO

        if data is None:
            data = [None for _ in range(4)]

        _id, data, resp, last = data

        hwIO.id.write(_id)
        hwIO.data.write(data)
        hwIO.resp.write(resp)
        hwIO.last.write(last)


#####################################################################
class Axi3_b(Axi3Lite_b, Axi_id):
    """
    Axi3 write response channel interface

    .. hwt-autodoc::
    """
    @override
    def hwConfig(self):
        Axi_id.hwConfig(self)
        Axi3Lite_b.hwConfig(self)

    @override
    def hwDeclr(self):
        Axi_id.hwDeclr(self)
        Axi3Lite_b.hwDeclr(self)

    @override
    def _initSimAgent(self, sim: HdlSimulator):
        self._ag = Axi3_bAgent(sim, self)


class Axi3_bAgent(BaseAxiAgent):
    """
    Simulation agent for :class:`.Axi3_b` interface

    input/output data stored in list under "data" property
    data contains tuples (id, resp)
    """

    @override
    def get_data(self):
        hwIO = self.hwIO

        return hwIO.id.read(), hwIO.resp.read()

    @override
    def set_data(self, data):
        hwIO = self.hwIO

        if data is None:
            data = [None for _ in range(2)]

        _id, resp = data

        hwIO.id.write(_id)
        hwIO.resp.write(resp)


#####################################################################
class Axi3(Axi3Lite):
    """
    AMBA Axi3 bus interface

    https://static.docs.arm.com/ihi0022/d/IHI0022D_amba_axi_protocol_spec.pdf

    .. hwt-autodoc::
    """
    LOCK_WIDTH = Axi3_addr.LOCK_WIDTH
    LEN_WIDTH = Axi3_addr.LEN_WIDTH
    AW_CLS = Axi3_addr
    AR_CLS = Axi3_addr
    W_CLS = Axi3_w
    R_CLS = Axi3_r
    B_CLS = Axi3_b

    @override
    def hwConfig(self):
        Axi3Lite.hwConfig(self)
        Axi_id.hwConfig(self, default_id_width=6)
        self.ADDR_USER_WIDTH = HwParam(0)
        # self.DATA_USER_WIDTH = HwParam(0)

    @override
    def hwDeclr(self):
        with self._hwParamsShared():
            if self.HAS_R:
                self.ar = self.AR_CLS()
                self.ar.USER_WIDTH = self.ADDR_USER_WIDTH
                self.r = self.R_CLS(masterDir=DIRECTION.IN)

            if self.HAS_W:
                self.aw = self.AW_CLS()
                self.aw.USER_WIDTH = self.ADDR_USER_WIDTH
                self.w = self.W_CLS()
                self.b = self.B_CLS(masterDir=DIRECTION.IN)
            # for d in [self.w, self.r, self.b]:
            #     d.USER_WIDTH = self.DATA_USER_WIDTH

    @override
    def _getIpCoreIntfClass(self):
        return IP_Axi3


class IP_Axi3(IP_Axi3Lite):
    """
    IP core interface meta for Axi3 interface
    """
    def __init__(self,):
        super(IP_Axi3, self).__init__()
        self.quartus_name = "axi"
        self.xilinx_protocol_name = "AXI3"
        A_SIGS = ['id', 'burst', 'cache', 'len', 'lock',
                  'prot', 'size', 'qos', 'user']
        AxiMap('ar', A_SIGS, self.map['ar'])
        AxiMap('r', ['id', 'last'], self.map['r'])
        AxiMap('aw', A_SIGS, self.map['aw'])
        AxiMap('w', ['id', 'last'], self.map['w'])
        AxiMap('b', ['id'], self.map['b'])

    @override
    def postProcess(self,
                    component: Component,
                    packager: IpPackager,
                    thisIf: Axi3):
        self.endianness = "little"
        thisIntfName = packager.getInterfaceLogicalName(thisIf)

        def param(name, val):
            return self.addSimpleParam(thisIntfName, name, str(val))

        # [TODO] width as expression instead of int
        param("ADDR_WIDTH", thisIf.aw.addr._dtype.bit_length())
        param("MAX_BURST_LENGTH", int(2 ** thisIf.aw.len._dtype.bit_length()))
        param("NUM_READ_OUTSTANDING", 5)
        param("NUM_WRITE_OUTSTANDING", 5)
        param("PROTOCOL", self.xilinx_protocol_name)
        param("READ_WRITE_MODE", "READ_WRITE")
        param("SUPPORTS_NARROW_BURST", 0)

        A_U_W = int(thisIf.ADDR_USER_WIDTH)
        if A_U_W:
            param("AWUSER_WIDTH", A_U_W)
            param("ARUSER_WIDTH", A_U_W)
