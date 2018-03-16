from hwt.code import FsmBuilder, If, connect
from hwt.hdl.types.bits import Bits
from hwt.hdl.types.defs import BIT
from hwt.hdl.types.enum import HEnum
from hwt.hdl.types.struct import HStruct
from hwt.interfaces.utils import addClkRstn, propagateClkRstn
from hwt.synthesizer.param import Param
from hwt.synthesizer.unit import Unit
from hwtLib.amba.axi3 import Axi3
from hwtLib.amba.axi4 import Axi4
from hwtLib.amba.axiLite import AxiLite, Axi4Lite
from hwtLib.amba.axiLite_comp.endpoint import AxiLiteEndpoint


SEND_AW, SEND_W, RECV_B, SEND_AR, RECV_R = range(1, 6)


class AxiTester(Unit):
    """
    Tester for AXI3/4 interfaces

    Can precisely control order and timing
    of read address/write address/read/write/write response transactions
    Allows to read and specify values of controls signals like cache/lock/burst
    etc...
    """

    def __init__(self, axiCls=Axi4, cntrlCls=Axi4Lite):
        self._axiCls = axiCls
        self._cntrlCls = cntrlCls
        super(AxiTester, self).__init__()

    def _config(self):
        self._axiCls._config(self)
        self.CNTRL_DATA_WIDTH = Param(32)
        self.CNTRL_ADDR_WIDTH = Param(32)

    def _declr(self):
        addClkRstn(self)
        with self._paramsShared():
            self.axi = self._axiCls()

        c = self.cntrl = self._cntrlCls()
        c._replaceParam("DATA_WIDTH", self.CNTRL_DATA_WIDTH)
        c._replaceParam("ADDR_WIDTH", self.CNTRL_ADDR_WIDTH)

        # r = self.ram = Ram_dp()
        # r.ADDR_WIDTH.set(log2ceil(4096))
        # r._replaceParam("DATA_WIDTH", self.DATA_WIDTH)
        self._add_ep()

    def _add_ep(self):
        strb_w = self.DATA_WIDTH // 8
        # [TODO] hotfix, should be self.DATA_WIDTH
        data_field_w = self.CNTRL_DATA_WIDTH
        if isinstance(self.axi, Axi4):
            len_width = 8
        elif isinstance(self.axi, Axi3):
            len_width = 4
        else:
            raise NotImplementedError()

        mem_space = HStruct(
            (Bits(32), "id_reg"),
            (Bits(32), "cmd_and_status"),
            (Bits(self.ADDR_WIDTH), "addr"),
            # a or w id
            (Bits(self.ID_WIDTH), "ar_aw_w_id"),
            (Bits(32 - int(self.ID_WIDTH)), None),

            (Bits(2), "burst"),
            (Bits(32 - 2), None),
            (Bits(4), "cache"),
            (Bits(32 - 4), None),
            (Bits(len_width), "len"),
            (Bits(32 - len_width), None),
            (Bits(self.LOCK_WIDTH), "lock"),
            (Bits(32 - int(self.LOCK_WIDTH)), None),
            (Bits(3), "prot"),
            (Bits(32 - 3), None),
            (Bits(3), "size"),
            (Bits(32 - 3), None),
            (Bits(4), "qos"),
            (Bits(32 - 4), None),

            (Bits(self.ID_WIDTH), "r_id"),
            (Bits(32 - int(self.ID_WIDTH)), None),
            (Bits(data_field_w), "r_data"),
            (Bits(2), "r_resp"),
            (Bits(32 - 2), None),
            (BIT, "r_last"),
            (Bits(32 - 1), None),

            (Bits(self.ID_WIDTH), "b_id"),
            (Bits(32 - int(self.ID_WIDTH)), None),
            (Bits(2), "b_resp"),
            (Bits(32 - 2), None),

            (Bits(data_field_w), "w_data"),
            (BIT, "w_last"),
            (Bits(32 - 1), None),
            (Bits(strb_w), "w_strb"),
            (Bits(32 - int(strb_w)), None),
        )

        ep = self.axi_ep = AxiLiteEndpoint(mem_space)
        ep.DATA_WIDTH.set(self.CNTRL_DATA_WIDTH)
        ep.ADDR_WIDTH.set(self.CNTRL_ADDR_WIDTH)

    def _impl(self):
        propagateClkRstn(self)
        exclude = set()
        for ch in [self.cntrl.aw, self.cntrl.ar]:
            if hasattr(ch, "prot"):
                exclude.add(ch.prot)

        connect(self.cntrl, self.axi_ep.bus, exclude=exclude)

        ep = self.axi_ep.decoded
        id_reg_val = int.from_bytes("test".encode(), byteorder="little")
        ep.id_reg.din(id_reg_val)

        def connected_reg(name, input_=None, inputEn=None, fit=False):
            port = getattr(ep, name)
            reg = self._reg(name, Bits(port.din._dtype.bit_length()))
            e = If(port.dout.vld,
                   connect(port.dout.data, reg, fit=fit)
                )
            if input_ is not None:
                e.Elif(inputEn,
                    connect(input_, reg, fit=fit)
                )
            port.din(reg)
            return reg

        cmdIn = ep.cmd_and_status.dout
        cmd = self._reg("reg_cmd", Bits(cmdIn.data._dtype.bit_length()), defVal=0)
        cmdVld = self._reg("reg_cmd_vld", defVal=0)
        If(cmdIn.vld,
           connect(cmdIn.data, cmd, fit=True)
        )
        partDone = self._sig("partDone")
        If(partDone,
           cmdVld(0)
        ).Elif(cmdIn.vld,
           cmdVld(1)
        )

        def cmd_en(cmd_code):
            return cmdVld & cmd._eq(cmd_code)

        state_t = HEnum("state_t",
                        ["ready", "wait_ar", "wait_aw",
                         "wait_w", "wait_b", "wait_r"])

        axi = self.axi
        st = FsmBuilder(self, state_t)\
            .Trans(state_t.ready,
                   (cmd_en(SEND_AW) & ~axi.aw.ready, state_t.wait_aw),
                   (cmd_en(SEND_AR) & ~axi.ar.ready, state_t.wait_ar),
                   (cmd_en(SEND_W) & ~axi.w.ready, state_t.wait_w),
                   (cmd_en(RECV_R) & ~axi.r.valid, state_t.wait_r),
                   (cmd_en(RECV_B) & ~axi.b.valid, state_t.wait_b),
            ).Trans(state_t.wait_aw,
                (axi.aw.ready, state_t.ready)
            ).Trans(state_t.wait_ar,
                (axi.ar.ready, state_t.ready)
            ).Trans(state_t.wait_w,
                (axi.w.ready, state_t.ready)
            ).Trans(state_t.wait_r,
                (axi.r.valid, state_t.ready)
            ).Trans(state_t.wait_b,
                (axi.b.valid, state_t.ready)
            ).stateReg

        partDone((st._eq(state_t.wait_aw) & axi.aw.ready) |
                 (st._eq(state_t.wait_ar) & axi.ar.ready) |
                 (st._eq(state_t.wait_w) & axi.w.ready) |
                 (st._eq(state_t.wait_r) & axi.r.valid) |
                 (st._eq(state_t.wait_b) & axi.b.valid))

        ready = st._eq(state_t.ready)
        tmp = self._sig("tmp")
        tmp(st._eq(state_t.ready) & ~ep.cmd_and_status.dout.vld)
        connect(tmp, ep.cmd_and_status.din, fit=True)

        a_w_id = connected_reg("ar_aw_w_id")
        addr = connected_reg("addr")
        burst = connected_reg("burst")
        cache = connected_reg("cache")
        len_ = connected_reg("len")
        lock = connected_reg("lock")
        prot = connected_reg("prot")
        size = connected_reg("size")
        qos = connected_reg("qos")

        # aw/ar
        for p in [axi.aw, axi.ar]:
            p.id(a_w_id)
            p.addr(addr)
            p.burst(burst)
            p.cache(cache)
            p.len(len_)
            p.lock(lock)
            p.prot(prot)
            p.size(size)
            p.qos(qos)

        aw_vld = (ready & cmd_en(SEND_AW)) | st._eq(state_t.wait_aw)
        axi.aw.valid(aw_vld)
        ar_vld = (ready & cmd_en(SEND_AR)) | st._eq(state_t.wait_ar)
        axi.ar.valid(ar_vld)

        r = axi.r
        r_rd = (ready & cmd_en(RECV_R)) | st._eq(state_t.wait_r)
        r_en = r.valid & r_rd
        connected_reg("r_id", r.id, r_en)
        connected_reg("r_data", r.data, r_en, fit=True)
        connected_reg("r_resp", r.resp, r_en)
        connected_reg("r_last")
        r.ready(r_rd)

        w = axi.w
        w_data = connected_reg("w_data", fit=True)
        w_last = connected_reg("w_last")
        w_strb = connected_reg("w_strb")
        w.id(a_w_id)
        connect(w_data, w.data, fit=True)
        w.strb(w_strb)
        w.last(w_last)
        w_vld = (ready & cmd_en(SEND_W)) | st._eq(state_t.wait_w)
        w.valid(w_vld)

        b = axi.b
        b_rd = (ready & cmd_en(RECV_B)) | st._eq(state_t.wait_b)
        connected_reg("b_id", b.id, b.valid & b_rd)
        connected_reg("b_resp")
        b.ready(b_rd)


if __name__ == "__main__":
    from hwt.synthesizer.utils import toRtl
    from hwt.serializer.ip_packager.packager import Packager
    from os.path import expanduser

    u = AxiTester(Axi4)
    # print(toRtl(u))
    p = Packager(u)
    p.createPackage(expanduser("~"))
