#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hdl.types.bits import HBits
from hwt.serializer.combLoopAnalyzer import CombLoopAnalyzer
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.axiLite_comp.sim.utils import axi_randomize_per_channel
from hwtLib.amba.axi_comp.cache.cacheWriteAllocWawOnlyWritePropagating import AxiCacheWriteAllocWawOnlyWritePropagating
from hwtLib.amba.constants import RESP_OKAY
from hwtLib.examples.errors.combLoops import freeze_set_of_sets
from hwtLib.mem.sim.segmentedArrayProxy import SegmentedArrayProxy
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import set_bit_range, mask, int_list_to_int
from hwt.hdl.types.bitsConst import HBitsConst


class AxiCacheWriteAllocWawOnlyWritePropagatingTC(SimTestCase):
    # number of words in transaction - 1
    LEN = 0

    @classmethod
    def setUpClass(cls):
        cls.dut = dut = AxiCacheWriteAllocWawOnlyWritePropagating()
        dut.IS_PREINITIALIZED = True
        dut.DATA_WIDTH = 32
        dut.CACHE_LINE_SIZE = 4 * (cls.LEN + 1)
        dut.CACHE_LINE_CNT = 16
        dut.MAX_BLOCK_DATA_WIDTH = 8
        dut.WAY_CNT = 2
        cls.ADDR_STEP = dut.CACHE_LINE_SIZE
        cls.WAY_CACHELINES = dut.CACHE_LINE_CNT // dut.WAY_CNT
        cls.compileSim(dut)

    def setUp(self):
        SimTestCase.setUp(self)
        m = self.rtl_simulator.model
        dut = self.dut
        self.TAGS = SegmentedArrayProxy([
                getattr(m.tag_array_inst.tag_mem_inst, f"children_{i:d}_inst").io.ram_memory
                for i in range(dut.tag_array.tag_record_t.bit_length() * dut.WAY_CNT // 8)
            ],
        )
        self.DATA = SegmentedArrayProxy([
                getattr(m.data_array_inst.data_array_inst, f"children_{i:d}_inst").io.ram_memory
                for i in range(dut.DATA_WIDTH // 8)
            ],
            words_per_item=self.LEN + 1
        )

    def set_data(self, index: int, way: int, data: HBitsConst):
        dut = self.dut
        WAY_CACHELINES = dut.CACHE_LINE_CNT // dut.WAY_CNT
        self.DATA[way * WAY_CACHELINES + index] = data

    def build_cacheline(self, cacheline_words):
        return int_list_to_int(cacheline_words, self.dut.DATA_WIDTH)

    def get_data(self, index, way):
        return self.DATA[way * self.WAY_CACHELINES + index]

    def set_tag(self, addr, way):
        dut = self.dut
        tag, index, offset = dut.parse_addr_int(addr)
        assert offset == 0, addr
        tag_t = dut.tag_array.tag_record_t
        tag_t_w = tag_t.bit_length()
        v = tag_t.from_py({"tag": tag, "valid": 1})._reinterpret_cast(HBits(tag_t_w))

        cur_v = self.TAGS[index]
        assert cur_v._is_full_valid(), (cur_v, index)
        val = set_bit_range(cur_v.val, way * tag_t_w, tag_t_w, v.val)
        self.TAGS[index] = val

        return index

    def cacheline_insert(self, addr: int, way: int, data: HBitsConst):
        index = self.set_tag(addr, way)
        self.set_data(index, way, data)

    def get_cachelines(self):
        dut = self.dut
        res = {}
        tags_t = dut.tag_array.tag_record_t[dut.WAY_CNT]
        tags_raw_t = HBits(tags_t.bit_length())
        for index in range(2 ** dut.INDEX_W):
            tags = self.TAGS[index]
            tags = tags_raw_t.from_py(tags.val, tags.vld_mask)._reinterpret_cast(tags_t)
            for way, t in enumerate(tags):
                if t.valid:
                    data = self.get_data(index, way)
                    addr = dut.deparse_addr(t.tag, index, 0)
                    if data._is_full_valid():
                        data = int(data)
                    res[int(addr)] = data
        return res

    def randomize_all(self):
        dut = self.dut
        axi_randomize_per_channel(self, dut.s)
        axi_randomize_per_channel(self, dut.m)

    def test_utils(self):
        self.TAGS.clean()
        self.DATA.clean()
        self.assertDictEqual(self.get_cachelines(), {})

        expected = {}
        MAGIC = 99
        for w in range(self.dut.WAY_CNT):
            a = (w * self.WAY_CACHELINES + 3) * self.ADDR_STEP
            self.cacheline_insert(a, w, MAGIC + w)
            expected[a] = MAGIC + w
            self.assertDictEqual(self.get_cachelines(), expected)

    def test_no_comb_loops(self):
        s = CombLoopAnalyzer()
        s.visit_HwModule(self.dut)
        comb_loops = freeze_set_of_sets(s.report())
        # for loop in comb_loops:
        #     print(10 * "-")
        #     for s in loop:
        #         print(s.resolve()[1:])

        self.assertEqual(comb_loops, frozenset())

    def test_nop(self):
        dut = self.dut
        self.randomize_all()
        self.runSim(50 * CLK_PERIOD)
        for x in [dut.m.ar, dut.m.aw, dut.m.w, dut.s.r, dut.s.b]:
            self.assertEmpty(x._ag.data)

    def test_read_through(self, N=10, randomized=False):
        # Every transaction should be checked if present in cache, should not be found and should
        # be forwarded on axi "m" port
        dut = self.dut
        self.TAGS.clean()
        ref = [
            dut.s.ar._ag.create_addr_req(addr=i * self.ADDR_STEP, _len=self.LEN, _id=i)
            for i in range(N)
        ]
        dut.s.ar._ag.data.extend(ref)
        t = (N * (self.LEN + 1) + 5) * CLK_PERIOD
        if randomized:
            self.randomize_all()
            t *= 3

        self.runSim(t)
        self.assertValSequenceEqual(dut.m.ar._ag.data, ref)
        for x in [dut.m.aw, dut.m.w, dut.s.r, dut.s.b]:
            self.assertEmpty(x._ag.data)

    def test_read_from_everywhere(self, N_PER_WAY=10, MAGIC=99, randomized=False):
        # Every transaction should be read from the cache
        dut = self.dut
        self.TAGS.clean()
        self.DATA.clean()
        ID_MAX = 2 ** dut.ID_WIDTH
        WAY_CACHELINES = self.WAY_CACHELINES
        expected_r = []
        for w in range(dut.WAY_CNT):
            for i in range(N_PER_WAY):
                i = i % WAY_CACHELINES
                addr = (i + w * WAY_CACHELINES) * self.ADDR_STEP
                _id = i % ID_MAX
                req = dut.s.ar._ag.create_addr_req(addr=addr, _len=self.LEN, _id=_id)
                dut.s.ar._ag.data.append(req)
                d_list = []
                for w_i in range(self.LEN + 1):
                    d = w * MAGIC + i + w_i
                    expected_r.append((_id, d, RESP_OKAY, int(w_i == self.LEN)))
                    d_list.append(d)

                self.cacheline_insert(addr, w, self.build_cacheline(d_list))

        t = (10 + dut.WAY_CNT * N_PER_WAY * (self.LEN + 1)) * CLK_PERIOD
        if randomized:
            self.randomize_all()
            t *= 3
        self.runSim(t)
        for x in [dut.s.ar, dut.m.ar, dut.m.aw, dut.m.w, dut.s.b]:
            self.assertEmpty(x._ag.data, x)

        self.assertValSequenceEqual(dut.s.r._ag.data, expected_r)

    def test_read_from_everywhere_r(self, N_PER_WAY=50, MAGIC=99):
        self.test_read_from_everywhere(
            N_PER_WAY=N_PER_WAY,
            MAGIC=MAGIC,
            randomized=True)

    def _test_write_to(self, N_PER_WAY=8, MAGIC=99, preallocate=False, randomized=False):
        # Every cacheline should be stored in cache as there is plenty of space
        dut = self.dut
        self.TAGS.clean()
        self.DATA.clean()

        WAY_CACHELINES = self.WAY_CACHELINES
        ID_MAX = 2 ** dut.ID_WIDTH
        aw = dut.s.aw._ag
        expected = {}
        b_expected = []
        M = mask(dut.DATA_WIDTH // 8)
        for w in range(dut.WAY_CNT):
            for i in range(N_PER_WAY):
                i = i % WAY_CACHELINES
                addr = (i + w * WAY_CACHELINES) * self.ADDR_STEP

                if preallocate:
                    self.cacheline_insert(addr, w, 0)

                _id = i % ID_MAX
                req = aw.create_addr_req(addr=addr, _len=self.LEN, _id=_id)
                aw.data.append(req)
                d_list = []
                for w_i in range(self.LEN + 1):
                    d = w * MAGIC + i + w_i
                    dut.s.w._ag.data.append((d, M, int(w_i == self.LEN)))
                    d_list.append(d)
                expected[addr] = self.build_cacheline(d_list)

                b_expected.append((_id, RESP_OKAY))
        if preallocate:
            self.assertDictEqual(self.get_cachelines(), {k: 0 for k in expected.keys()})
        t = (dut.WAY_CNT * N_PER_WAY * (self.LEN + 1) + 10) * CLK_PERIOD
        if randomized:
            t *= 3
            self.randomize_all()

        self.runSim(t)
        for x in [dut.s.aw, dut.s.r, dut.m.ar, dut.m.aw, dut.m.w]:
            self.assertEmpty(x._ag.data, x)

        self.assertDictEqual(self.get_cachelines(), expected)
        self.assertValSequenceEqual(dut.s.b._ag.data, b_expected)

    def test_write_to_empty(self, N_PER_WAY=8, MAGIC=99, preallocate=False, randomized=False):
        self._test_write_to(N_PER_WAY, MAGIC, preallocate, randomized)

    def test_write_to_preallocated(self, N_PER_WAY=8, MAGIC=99):
        self._test_write_to(N_PER_WAY=N_PER_WAY, MAGIC=MAGIC, preallocate=True)

    def test_write_to_empty_r(self, N_PER_WAY=50, MAGIC=99):
        self._test_write_to(N_PER_WAY=N_PER_WAY, MAGIC=MAGIC, preallocate=False, randomized=True)

    def test_write_to_preallocated_r(self, N_PER_WAY=50, MAGIC=99):
        self._test_write_to(N_PER_WAY=N_PER_WAY, MAGIC=MAGIC, preallocate=True, randomized=True)

    def test_read_write_to_different_sets(self, N_PER_WAY=5, MAGIC=99, randomized=False):
        dut = self.dut
        self.TAGS.clean()
        self.DATA.clean()

        WAY_CACHELINES = self.WAY_CACHELINES
        ID_MAX = 2 ** dut.ID_WIDTH
        aw = dut.s.aw._ag
        expected = {}
        b_expected = []
        M = mask(dut.DATA_WIDTH // 8)
        expected_r = []
        for w in range(dut.WAY_CNT):
            for i in range(N_PER_WAY):
                i = i % WAY_CACHELINES
                addr = (i + w * WAY_CACHELINES) * self.ADDR_STEP

                _id = i % ID_MAX
                req = aw.create_addr_req(addr=addr, _len=0, _id=_id)

                dut.s.ar._ag.data.append(req)

                aw.data.append(req)
                r_d_list = []
                w_d_list = []
                for w_i in range(self.LEN + 1):
                    last = int(w_i == self.LEN)

                    write_d = (dut.WAY_CNT + w) * MAGIC + i + w_i
                    dut.s.w._ag.data.append((write_d, M, last))
                    w_d_list.append(write_d)

                    read_d = w * MAGIC + i + w_i
                    expected_r.append((_id, read_d, RESP_OKAY, last))
                    r_d_list.append(read_d)

                expected[addr] = self.build_cacheline(w_d_list)
                self.cacheline_insert(addr, w, self.build_cacheline(r_d_list))

                b_expected.append((_id, RESP_OKAY))

        t = (dut.WAY_CNT * N_PER_WAY * (self.LEN + 1) + 10) * CLK_PERIOD
        if randomized:
            t *= 3
            self.randomize_all()

        self.runSim(t)
        for x in [dut.s.aw, dut.m.ar, dut.m.aw, dut.m.w]:
            self.assertEmpty(x._ag.data, x)

        self.assertDictEqual(self.get_cachelines(), expected)
        self.assertValSequenceEqual(dut.s.b._ag.data, b_expected)
        self.assertValSequenceEqual(dut.s.r._ag.data, expected_r)

    # write victim flush


class AxiCacheWriteAllocWawOnlyWritePropagating_len1TC(AxiCacheWriteAllocWawOnlyWritePropagatingTC):
    LEN = 1


AxiCacheWriteAllocWawOnlyWritePropagatingTCs = [
    AxiCacheWriteAllocWawOnlyWritePropagatingTC,
    AxiCacheWriteAllocWawOnlyWritePropagating_len1TC,
]

if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([AxiCacheWriteAllocWawOnlyWritePropagatingTC("test_write_to_empty")])
    loadedTcs = [testLoader.loadTestsFromTestCase(tc) for tc in AxiCacheWriteAllocWawOnlyWritePropagatingTCs]
    suite = unittest.TestSuite(loadedTcs)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
