#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import If
from hwt.constraints import set_max_delay
from hwt.hObjList import HObjList
from hwt.hwIOs.std import HwIOSignal, HwIODataRdVld
from hwt.hwIOs.utils import addClkRst
from hwt.hwModule import HwModule
from hwt.hwParam import HwParam
from hwt.pyUtils.typingFuture import override
from hwt.serializer.mode import serializeParamsUniq
from hwtLib.clocking.cdc import CdcPulseGen
from hwtLib.clocking.vldSynced_cdc import VldSyncedCdc
from hwtLib.handshaked.compBase import HandshakedCompBase


@serializeParamsUniq
class HandshakeFSM(HwModule):
    """
    .. hwt-autodoc::
    """

    @override
    def hwDeclr(self):
        addClkRst(self)
        self.ack = HwIOSignal()
        self.vld = HwIOSignal()
        self.rd = HwIOSignal()._m()

    @override
    def hwImpl(self):
        rd = self._reg("rd", def_val=1)
        If(rd,
           rd(~self.vld)
        ).Else(
           rd(self.ack)
        )
        self.rd(rd)


@serializeParamsUniq
class HandshakedCdc(HandshakedCompBase):
    """
    CDC (Clock Domain Crossing) for handshaked interface

    :note: This component uses syncrhorization by pulse CDCs which means it's throughput is significantly limited
        (eta slowest clk / 3)

    .. hwt-autodoc:: example_HandshakedCdc
    """

    @override
    def hwConfig(self):
        HandshakedCompBase.hwConfig(self)
        self.DATA_RESET_VAL = HwParam(None)
        self.IN_FREQ = HwParam(int(100e6))
        self.OUT_FREQ = HwParam(int(100e6))

    @override
    def hwDeclr(self):
        VldSyncedCdc.hwDeclr(self)

        ipg = self.in_ack_pulse_gen = CdcPulseGen()
        ipg.IN_FREQ = self.OUT_FREQ
        ipg.OUT_FREQ = self.IN_FREQ

        opg = self.out_en_pulse_gen = CdcPulseGen()
        opg.IN_FREQ = self.IN_FREQ
        opg.OUT_FREQ = self.OUT_FREQ

        self.tx_fsm = HandshakeFSM()
        self.rx_fsm = HandshakeFSM()

    def propagate_clk(self, m: CdcPulseGen, reverse=False):
        if reverse:
            m.dataIn_clk(self.dataOut_clk)
            m.dataIn_rst(~self.dataOut_rst_n)
            m.dataOut_clk(self.dataIn_clk)
            m.dataOut_rst(~self.dataIn_rst_n)
        else:
            m.dataIn_clk(self.dataIn_clk)
            m.dataIn_rst(~self.dataIn_rst_n)
            m.dataOut_clk(self.dataOut_clk)
            m.dataOut_rst(~self.dataOut_rst_n)

    def propagate_in_clk(self, u):
        u.clk(self.dataIn_clk)
        u.rst(~self.dataIn_rst_n)

    def propagate_out_clk(self, u):
        u.clk(self.dataOut_clk)
        u.rst(~self.dataOut_rst_n)

    def create_data_reg(self, name_prefix, clk=None, rst=None):
        """
        Create a registers for data signals with default values
        from :class:`hwt.hwModule.HwModule` parameters and with specified clk/rst
        """
        regs = HObjList()
        def_vals = self.DATA_RESET_VAL
        d_sigs = self.get_data(self.dataIn)

        if def_vals is None or isinstance(def_vals, (int)):
            def_vals = [def_vals for _ in d_sigs]

        for d, def_val in zip(d_sigs, def_vals):
            r = self._reg(name_prefix + d._name,
                          d._dtype,
                          def_val=def_val,
                          clk=clk, rst=rst)
            regs.append(r)

        return regs

    @override
    def hwImpl(self):
        vld, rd = self.get_valid_signal, self.get_ready_signal
        din = self.dataIn
        dout = self.dataOut
        din_clk = {
            "clk": self.dataIn_clk,
            "rst": self.dataIn_rst_n
        }
        dout_clk = {
            "clk": self.dataOut_clk,
            "rst": self.dataOut_rst_n
        }
        din_en = self._reg("din_en", def_val=0, **din_clk)
        dout_ack = self._reg("dout_ack", def_val=0, **dout_clk)
        din_data = self.create_data_reg("din_", **din_clk)

        tx_fsm = self.tx_fsm
        self.propagate_in_clk(tx_fsm)
        tx_fsm.vld(vld(din))
        in_ready = tx_fsm.rd
        rd(din)(in_ready)

        out_en_gen = self.out_en_pulse_gen
        self.propagate_clk(out_en_gen, reverse=False)
        dout_en = out_en_gen.dataOut_en
        rx_fsm = self.rx_fsm
        self.propagate_out_clk(rx_fsm)
        rx_fsm.ack(rd(dout))
        rx_fsm.vld(dout_en)
        dout_vld_n = rx_fsm.rd

        next_dataIn = vld(din) & in_ready
        If(next_dataIn,
            din_data(HObjList(self.get_data(din)))
        )
        din_en(din_en ^ next_dataIn)
        out_en_gen.dataIn(din_en)
        dout_data = self.create_data_reg("dout_", **dout_clk)
        dout_load_data = ~dout_vld_n & rd(dout)
        If(dout_load_data,
           dout_data(din_data)
        )
        FAST_CLK_PERIOD_NS = 1e9 / max(self.dataIn_clk.FREQ, self.dataOut_clk.FREQ)
        for d_in, d_out in zip(din_data, dout_data):
            set_max_delay(d_in, d_out, FAST_CLK_PERIOD_NS)

        HObjList(self.get_data(dout))(dout_data)

        dout_vld = ~dout_vld_n
        dout_vld_delayed = self._reg("dout_vld_delayed", def_val=0, **dout_clk)
        dout_vld_delayed(dout_vld)
        dout_vld = dout_vld_delayed
        vld(dout)(dout_vld)

        dout_ack(dout_ack ^ dout_load_data)

        in_ack_gen = self.in_ack_pulse_gen
        self.propagate_clk(in_ack_gen, reverse=True)
        in_ack_gen.dataIn(dout_ack)
        din_ack = in_ack_gen.dataOut_en
        tx_fsm.ack(din_ack)


def example_HandshakedCdc():
    m = HandshakedCdc(HwIODataRdVld)
    m.IN_FREQ = int(100e6)
    m.OUT_FREQ = int(200e6)
    return m


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    
    m = example_HandshakedCdc()
    print(to_rtl_str(m))
