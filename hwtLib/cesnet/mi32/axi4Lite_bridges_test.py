#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hwIOs.utils import propagateClkRstn, addClkRstn
from hwt.hwModule import HwModule
from hwt.pyUtils.typingFuture import override
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.axi4Lite import Axi4Lite
from hwtLib.amba.axiLite_comp.sim.ram import Axi4LiteSimRam
from hwtLib.amba.axiLite_comp.sim.utils import axi_randomize_per_channel
from hwtLib.amba.axi_comp.builder import AxiBuilder
from hwtLib.amba.constants import PROT_DEFAULT, RESP_OKAY
from hwtLib.cesnet.mi32.axi4Lite_to_mi32 import Axi4Lite_to_Mi32
from hwtLib.cesnet.mi32.intf import Mi32
from hwtLib.cesnet.mi32.to_axi4Lite import Mi32_to_Axi4Lite
from hwtSimApi.constants import CLK_PERIOD


class Axi4LiteMi32Bridges(HwModule):
    """
    :class:`hwt.hwModule.HwModule` with AxiLiteEndpoint + AxiLiteReg + AxiLite2Mi32 + Mi32_2AxiLite
    """

    @override
    def hwConfig(self):
        Mi32.hwConfig(self)

    @override
    def hwDeclr(self):
        addClkRstn(self)
        with self._hwParamsShared():
            self.s = Axi4Lite()
            self.toMi32 = Axi4Lite_to_Mi32()
            self.toAxi = Mi32_to_Axi4Lite()
            self.m = Axi4Lite()._m()

    @override
    def hwImpl(self):
        propagateClkRstn(self)
        toMi32 = self.toMi32
        toAxi = self.toAxi

        m = AxiBuilder(self, self.s).buff().end
        toMi32.s(m)
        toAxi.s(toMi32.m)
        self.m(AxiBuilder(self, toAxi.m).buff().end)


class Mi32Axi4LiteBrigesTC(SimTestCase):
    @classmethod
    @override
    def setUpClass(cls):
        dut = cls.dut = Axi4LiteMi32Bridges()
        cls.compileSim(dut)

    def randomize_all(self):
        dut = self.dut
        for i in [dut.m, dut.s]:
            axi_randomize_per_channel(self, i)

    @override
    def setUp(self):
        SimTestCase.setUp(self)
        dut = self.dut
        self.memory = Axi4LiteSimRam(axi=dut.m)

    def test_nop(self):
        self.randomize_all()
        self.runSim(10 * CLK_PERIOD)
        dut = self.dut
        for i in [dut.m, dut.s]:
            self.assertEmpty(i.ar._ag.data)
            self.assertEmpty(i.aw._ag.data)
            self.assertEmpty(i.r._ag.data)
            self.assertEmpty(i.w._ag.data)
            self.assertEmpty(i.b._ag.data)

    def test_read(self):
        dut = self.dut
        N = 10
        a_trans = [(i * 0x4, PROT_DEFAULT) for i in range(N)]
        for i in range(N):
            self.memory.data[i] = i + 1
        dut.s.ar._ag.data.extend(a_trans)
        #self.randomize_all()
        self.runSim(N * 10 * CLK_PERIOD)
        dut = self.dut
        for i in [dut.s, dut.m]:
            self.assertEmpty(i.aw._ag.data)
            self.assertEmpty(i.w._ag.data)
            self.assertEmpty(i.b._ag.data)

        r_trans = [(i + 1, RESP_OKAY) for i in range(N)]
        self.assertValSequenceEqual(dut.s.r._ag.data, r_trans)


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Mi32Axi4LiteBrigesTC("test_singleLong")])
    suite = testLoader.loadTestsFromTestCase(Mi32Axi4LiteBrigesTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
