#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.simulator.simTestCase import SimTestCase
from hwtLib.peripheral.usb.constants import USB_VER
from hwtLib.peripheral.usb.descriptors.cdc import get_default_usb_cdc_vcp_descriptors
from hwtLib.peripheral.usb.usb2.device_cdc_vcp import Usb2CdcVcp
from hwtLib.peripheral.usb.usb2.ulpi_agent_test import UlpiAgentBaseTC
from hwtLib.peripheral.usb.usb2.utmi_usb_agent import UtmiUsbAgent
from hwtSimApi.utils import freq_to_period


class Usb2CdcVcpTC(UlpiAgentBaseTC):

    @classmethod
    def setUpClass(cls):
        cls.dut = dut = Usb2CdcVcp()
        dut.PRE_NEGOTIATED_TO = USB_VER.USB2_0  # to avoid waiting at the begin of sim
        cls.compileSim(dut)

    def setUp(self):
        SimTestCase.setUp(self)
        dut = self.dut
        dut.phy._ag = UtmiUsbAgent(dut.phy._ag.sim, dut.phy)
        dut.phy._ag.RETRY_CNTR_MAX = 100

    def test_descriptor_download(self):
        dut = self.dut
        CLK_PERIOD = int(freq_to_period(dut.CLK_FREQ))
        self.runSim(600 * CLK_PERIOD)

        self.assertUlpiAgFinished(dut.phy._ag)
        host = dut.phy._ag.usb_driver

        # self.assertEqual(dev.addr, 1)
        self.assertEqual(len(host.descr), 1)
        self.assertSequenceEqual(host.descr[1],
                                 get_default_usb_cdc_vcp_descriptors(productStr="Usb2CdcVcp",
                                                                     bMaxPacketSize=512))


if __name__ == '__main__':
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Usb2CdcVcpTC("test_phy_to_link")])
    suite = testLoader.loadTestsFromTestCase(Usb2CdcVcpTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
