#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.constants import Time
from hwt.hwIOs.utils import addClkRstn
from hwt.hwModule import HwModule
from hwt.pyUtils.typingFuture import override
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.axi3 import Axi3
from hwtLib.amba.axi4 import Axi4


class AxiTestJunction(HwModule):

    def __init__(self, axiCls):
        self.axiCls = axiCls
        HwModule.__init__(self)

    @override
    def hwConfig(self) -> None:
        self.axiCls.hwConfig(self)

    @override
    def hwDeclr(self):
        addClkRstn(self)
        with self._hwParamsShared():
            self.s = self.axiCls()
            self.m = self.axiCls()._m()

    @override
    def hwImpl(self):
        self.m(self.s)


class Axi_ag_TC(SimTestCase):
    """
    Simple test of axi3/4 interfaces and agents for them
    """

    @override
    def tearDown(self):
        self.rmSim()
        SimTestCase.tearDown(self)

    def randAxi4A(self):
        """get random address transaction"""
        r = self._rand.getrandbits
        _id = r(6)
        addr = r(32)
        burst = r(2)
        cache = r(4)
        _len = r(8)
        lock = r(1)
        prot = r(3)
        size = r(3)
        qos = r(4)

        return (_id, addr, burst, cache, _len, lock, prot, size, qos)

    def randAxi3Au(self):
        """get random address transaction for axi 3 with user"""
        r = self._rand.getrandbits
        _id = r(6)
        addr = r(32)
        burst = r(2)
        cache = r(4)
        _len = r(4)
        lock = r(1)
        prot = r(3)
        size = r(3)
        user = r(3)

        return (_id, addr, burst, cache, _len, lock, prot, size, user)

    def randW(self, hasId=True):
        """get random data write transaction"""
        r = self._rand.getrandbits
        data = r(64)
        strb = r(64 // 8)
        last = r(1)
        if hasId:
            _id = r(6)
            return (_id, data, strb, last)
        else:
            return (data, strb, last)

    def randB(self):
        """get random data write acknowledge transaction"""
        r = self._rand.getrandbits
        _id = r(6)
        resp = r(2)
        return (_id, resp)

    def randR(self):
        """get random data read transaction"""
        r = self._rand.getrandbits
        _id = r(6)
        data = r(64)
        resp = r(2)
        last = r(1)
        return (_id, data, resp, last)

    def test_axi4_ag(self):
        """Test if axi4 agent can transmit and receive data on all channels"""
        assert self.rtl_simulator_cls is None, "Should have been removed in tearDown()"
        dut = AxiTestJunction(Axi4)
        self.compileSimAndStart(dut)
        N = 10

        aw = [self.randAxi4A() for _ in range(N)]
        ar = [self.randAxi4A() for _ in range(N)]
        w = [self.randW(False) for _ in range(N)]
        b = [self.randB() for _ in range(N)]
        r = [self.randR() for _ in range(N)]

        dut.s.aw._ag.data.extend(aw)
        dut.s.ar._ag.data.extend(ar)

        dut.s.w._ag.data.extend(w)

        dut.m.r._ag.data.extend(r)
        dut.m.b._ag.data.extend(b)

        self.runSim(20 * N * Time.ns)

        a = self.assertValSequenceEqual

        a(dut.m.aw._ag.data, aw)
        a(dut.m.ar._ag.data, ar)
        a(dut.m.w._ag.data, w)

        a(dut.s.r._ag.data, r)
        a(dut.s.b._ag.data, b)

    def test_axi3_withAddrUser_ag(self):
        """Test if axi3 agent can transmit and receive data on all channels"""
        assert self.rtl_simulator_cls is None, "Should have been removed in tearDown()"
        dut = AxiTestJunction(Axi3)
        dut.ADDR_USER_WIDTH = 10
        self.compileSimAndStart(dut)
        N = 10

        aw = [self.randAxi3Au() for _ in range(N)]
        ar = [self.randAxi3Au() for _ in range(N)]
        w = [self.randW() for _ in range(N)]
        b = [self.randB() for _ in range(N)]
        r = [self.randR() for _ in range(N)]

        dut.s.aw._ag.data.extend(aw)
        dut.s.ar._ag.data.extend(ar)

        dut.s.w._ag.data.extend(w)

        dut.m.r._ag.data.extend(r)
        dut.m.b._ag.data.extend(b)

        self.runSim(20 * N * Time.ns)

        a = self.assertValSequenceEqual

        a(dut.m.aw._ag.data, aw)
        a(dut.m.ar._ag.data, ar)
        a(dut.m.w._ag.data, w)

        a(dut.s.r._ag.data, r)
        a(dut.s.b._ag.data, b)


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Axi_ag_TC("test_axi4_ag")])
    suite = testLoader.loadTestsFromTestCase(Axi_ag_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
