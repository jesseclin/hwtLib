#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.axi_comp.oooOp.reorder_buffer import ReorderBuffer
from hwtLib.types.ctypes import uint8_t
from hwtSimApi.constants import CLK_PERIOD


class ReorderBufferTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        cls.dut = ReorderBuffer()
        cls.dut.ID_WIDTH = 4
        cls.dut.T = uint8_t        
        cls.compileSim(cls.dut)
        
    def test_reverse(self):
        dut = self.dut
        no_ids = 2 ** dut.ID_WIDTH
        in_req = [(no_ids - i - 1, i) for i in range(no_ids)]
        dut.dataIn._ag.data.extend(in_req + in_req)
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.runSim(no_ids * 8 * CLK_PERIOD + 20 * CLK_PERIOD)
        in_req.sort(key=lambda x: x[0])
        self.assertValSequenceEqual(dut.dataOut._ag.data, list(map(lambda x: x[1], in_req + in_req)))

    def test_sequence(self):
        dut = self.dut
        reps = 2
        no_ids = 2 ** dut.ID_WIDTH
        
        seq = [0, 6, 3, 13, 10, 5, 14, 7, 15, 11, 9, 8, 4, 2, 1, 12]
        in_req = []
        for i in range(no_ids):
            in_req.append((seq[i % len(seq)], i))
        
        in_data = []
        for i in range(reps):
            in_data = in_data + in_req
            
        dut.dataIn._ag.data.extend(in_data)
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.runSim(len(in_data) * 4 * CLK_PERIOD + 20 * CLK_PERIOD)
        in_req.sort(key=lambda x: x[0])
        
        out_data = []
        for i in range(reps):
            out_data = out_data + in_req
                        
        self.assertValSequenceEqual(dut.dataOut._ag.data, list(map(lambda x: x[1], out_data)))


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    suite = testLoader.loadTestsFromTestCase(ReorderBufferTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
