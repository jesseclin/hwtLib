#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hwIOs.utils import addClkRstn, propagateClkRstn
from hwt.hwModule import HwModule
from hwt.pyUtils.typingFuture import override
from hwtLib.peripheral.usb.usb2.ulpi import Ulpi, ULPI_TX_CMD
from hwtLib.peripheral.usb.usb2.ulpi_agent_test import UlpiAgentTC
from hwtLib.peripheral.usb.usb2.utmi import Utmi_8b
from hwtLib.peripheral.usb.usb2.utmi_to_ulpi import Utmi_to_Ulpi


class Utmi_to_UlpiWrap(HwModule):

    @override
    def hwDeclr(self):
        addClkRstn(self)
        self.host = Ulpi()
        self.dev = Utmi_8b()._m()
        self.core = Utmi_to_Ulpi()

    @override
    def hwImpl(self):
        c = self.core
        c.ulpi(self.host)
        self.dev(c.utmi)
        propagateClkRstn(self)


class Utmi_to_UlpiTC(UlpiAgentTC):

    @classmethod
    @override
    def setUpClass(cls):
        cls.dut = Utmi_to_UlpiWrap()
        cls.compileSim(cls.dut)

    def format_pid_before_tx(self, pid: int):
        return int(pid)

    def format_link_to_phy_packets(self, packets):
        for p in packets:
            pid = p[0]
            assert ULPI_TX_CMD.is_USB_PID(pid)
            p[0] = ULPI_TX_CMD.get_USB_PID(pid)
        return packets

if __name__ == '__main__':
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Utmi_to_UlpiTC("test_link_to_phy")])
    suite = testLoader.loadTestsFromTestCase(Utmi_to_UlpiTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
