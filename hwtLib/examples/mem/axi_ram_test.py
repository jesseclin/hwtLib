#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwtLib.amba.axiLite_comp.sim.utils import axi_randomize_per_channel
from hwtLib.amba.axi_comp.to_axiLite_test import Axi_to_AxiLite_TC, split_frames
from hwtLib.amba.constants import RESP_OKAY
from hwtLib.examples.mem.axi_ram import Axi4BRam
from hwtSimApi.constants import CLK_PERIOD


class Axi4BRam_TC(Axi_to_AxiLite_TC):
    TRANSACTION_CNT = 32
    MAX_LEN = 4

    @classmethod
    def setUpClass(cls):
        cls.dut = Axi4BRam()
        cls.dut.DATA_WIDTH = 64
        cls.compileSim(cls.dut)

    def randomize_all(self):
        axi_randomize_per_channel(self, self.dut.s)

    def test_nop(self):
        self.randomize_all()
        self.runSim(10 * CLK_PERIOD)
        m = self.dut.s
        self.assertEmpty(m.r._ag.data)
        self.assertEmpty(m.b._ag.data)

    def test_read(self):
        N = 0
        dut = self.dut
        self.randomize_all()
        # dut.m.ar._ag._debugOutput = sys.stdout
        # dut.s.ar._ag._debugOutput = sys.stdout

        expected_frames = []
        addr = 0
        memory_init = []
        for _ in range(self.TRANSACTION_CNT):
            id_ = self._rand.getrandbits(dut.ID_WIDTH)
            len_ = self.get_rand_in_range(self.MAX_LEN)
            N += len_ + 1 + 1
            rand_data = [self._rand.getrandbits(dut.DATA_WIDTH)
                         for _ in range(len_ + 1)]
            memory_init.extend(rand_data)
            # rand_data = [i + 1 for i in range(len_ + 1)]
            # print(f"{id_:d}, 0x{addr:x}, {len_:d}", rand_data)
            a_t = dut.s.ar._ag.create_addr_req(addr, len_, id_)
            dut.s.ar._ag.data.append(a_t)
            expected_frames.append((addr, id_, rand_data))
            addr += len(rand_data) * dut.DATA_WIDTH // 8

        mem = self.rtl_simulator.model.ram_inst.io.ram_memory
        mem.val = mem.def_val = mem._dtype.from_py({i: v for i, v in enumerate(memory_init)})

        self.runSim(N * 3 * CLK_PERIOD)
        r_data = split_frames(dut.s.r._ag.data)
        self.assertEqual(len(expected_frames), len(r_data), msg=[
            # expected id, len, seen id, len
            ((d0[1], len(d0[2])), (int(d1[0][0]), len(d1[0])))
            for d0, d1 in zip(expected_frames, r_data)])

        for (_, id_, expected), data in zip(expected_frames, r_data):
            expected_data = [(id_, d, RESP_OKAY) for d in expected]
            self.assertValSequenceEqual(
                data,
                expected_data
            )

    def test_write(self):
        N = self.TRANSACTION_CNT
        dut = self.dut

        expected_data = []
        addr = 0
        for _ in range(self.TRANSACTION_CNT):
            id_ = self._rand.getrandbits(dut.ID_WIDTH)
            len_ = self.get_rand_in_range(self.MAX_LEN)
            N += len_ + 3
            # rand_data = [self._rand.getrandbits(dut.DATA_WIDTH)
            #             for _ in range(len_ + 1)]
            rand_data = [i + 1 for i in range(len_ + 1)]
            # print(f"{id_:d}, 0x{addr:x}, {len_:d}", rand_data)
            a_t = dut.s.aw._ag.create_addr_req(addr, len_, id_)
            dut.s.aw._ag.data.append(a_t)

            w_frame = self.create_w_frame(rand_data)
            dut.s.w._ag.data.extend(w_frame)

            word_i = addr // (dut.DATA_WIDTH // 8)
            for i, d in enumerate(rand_data):
                expected_data.append((word_i + i, d))
            addr += len(rand_data) * dut.DATA_WIDTH // 8

        self.runSim(N * 3 * CLK_PERIOD)

        for word_i, expected in expected_data:
            d = self.rtl_simulator.model.ram_inst.io.ram_memory.val.val.get(word_i, None)
            self.assertValEqual(d, expected, ("word ", word_i))


if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Axi4BRam_TC("test_read")])
    suite = testLoader.loadTestsFromTestCase(Axi4BRam_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
