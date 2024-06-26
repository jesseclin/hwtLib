#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import copy

from hwt.serializer.combLoopAnalyzer import CombLoopAnalyzer
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.amba.axiLite_comp.sim.utils import axi_randomize_per_channel
from hwtLib.amba.axi_comp.oooOp.utils import OutOfOrderCummulativeOpPipelineConfig
from hwtLib.amba.axi_comp.sim.ram import Axi4SimRam
from hwtLib.examples.axi.oooOp.counterHashTable import OooOpExampleCounterHashTable
from hwtLib.examples.axi.oooOp.testUtils import OutOfOrderCummulativeOp_dump_pipeline, \
    OutOfOrderCummulativeOp_dump_pipeline_html
from hwtLib.examples.errors.combLoops import freeze_set_of_sets
from hwtSimApi.constants import CLK_PERIOD


def MState(key, data):
    return (int(key is not None), key, data)


def TState(key, data, operation, match=0, reset=0):
    return (
        reset,
        MState(key, data),
        match,
        operation
    )


def in_trans(addr, reset, key, data, match, operation):
    return (
        addr,
        TState(key, data, operation, match, reset),
    )


OP = OooOpExampleCounterHashTable.OPERATION


class OooOpExampleCounterHashTable_4threads_TC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = OooOpExampleCounterHashTable()
        dut.ID_WIDTH = 2
        dut.ADDR_WIDTH = dut.ID_WIDTH + 3
        dut.PIPELINE_CONFIG = OutOfOrderCummulativeOpPipelineConfig.new_config(
                WRITE_TO_WRITE_ACK_LATENCY=1,
                WRITE_ACK_TO_READ_DATA_LATENCY=4
        )
        cls.compileSim(dut)

    def setUp(self):
        SimTestCase.setUp(self)
        dut = self.dut
        self.m = Axi4SimRam(axi=dut.m)

    def test_nop(self):
        dut = self.dut

        self.runSim(10 * CLK_PERIOD)
        self.assertEmpty(dut.dataOut._ag.data)
        self.assertEmpty(dut.m.aw._ag.data)
        self.assertEmpty(dut.m.w._ag.data)
        self.assertEmpty(dut.m.ar._ag.data)

    def _test_incr(self, inputs, randomize=False, mem_init={}):
        dut = self.dut
        ADDR_ITEM_STEP = 2 ** dut.ADDR_OFFSET_W
        for i in range(2 ** dut.ADDR_WIDTH // ADDR_ITEM_STEP):
            v = mem_init.get(i, 0)
            if v != 0:
                item_valid, key, value = v
                v = dut.MAIN_STATE_T.from_py({"item_valid": item_valid, "key": key, "value": value})
                v = v._reinterpret_cast(dut.m.w.data._dtype)
            self.m.data[i] = v

        dut.dataIn._ag.data.extend(inputs)

        t = (40 + len(inputs) * 3) * CLK_PERIOD
        if randomize:
            axi_randomize_per_channel(self, dut.m)
            self.randomize(dut.dataIn)
            self.randomize(dut.dataOut)
            t = int(t * 8)

        states = []
        self.procs.append(OutOfOrderCummulativeOp_dump_pipeline(self, dut, self.rtl_simulator.model, states))
        self.runSim(t)
        with open(f"tmp/{self.getTestName()}_pipeline.html", "w") as f:
            OutOfOrderCummulativeOp_dump_pipeline_html(f, dut, states)

        # check if pipeline registers are empty
        for i in range(dut.PIPELINE_CONFIG.WAIT_FOR_WRITE_ACK):
            valid = getattr(self.rtl_simulator.model.io, f"st{i:d}_valid")
            self.assertValEqual(valid.read(), 0, i)

        # check if main state fifo is empty
        ooo_fifo = self.rtl_simulator.model.ooo_fifo_inst.io
        self.assertValEqual(ooo_fifo.item_valid.read(), 0)
        self.assertValEqual(ooo_fifo.read_wait.read(), 1)

        # check if all transactions on AXI are finished
        self.assertEmpty(dut.m.b._ag.data)
        self.assertEmpty(dut.m.r._ag.data)

        # check output data itself
        dout = dut.dataOut._ag.data
        mem = copy(mem_init)
        for in_i, (_in, _out) in enumerate(zip(inputs, dout)):
            (
                addr,
                (
                    reset,
                    (key_vld, key, data),
                    _,
                    operation
                )  # transaction_state
            ) = _in
            (
                o_addr,
                (o_found_key_vld, o_found_key, o_found_data),  # main state
                (
                    o_reset,
                    (o_key_vld, o_key, o_data),  # orig item
                    o_match,
                    o_operation
                ),  # transaction_state
            ) = _out
            # None or tuple(item_valid, key, data)
            cur = mem.get(addr, None)

            def aeq(a, b):
                self.assertValEqual(a, b, ("pkt no", in_i, _in))

            aeq(o_addr, addr)
            was_found = cur is not None and cur[0] and int(cur[1]) == key
            if was_found and (operation == OP.LOOKUP or operation == OP.LOOKUP_OR_SWAP):
                # lookup and increment if found
                aeq(o_reset, 0)
                aeq(o_match, 1)
                aeq(o_found_key_vld, 1)
                aeq(o_found_key, key)
                aeq(o_found_data, cur[2] + 1)
                aeq(o_found_key_vld, 1)

                mem[addr] = (1, key, int(o_found_data))
            elif not was_found and operation == OP.LOOKUP:
                # lookup fail
                aeq(o_reset, 0)
                aeq(o_match, 0)
                # key remained same
                aeq(o_key_vld, key_vld)
                aeq(o_key, key)
                aeq(o_data, data)
                # there was nothing so nothig should have been found
                aeq(o_found_key_vld, int(cur is not None and cur[0]))

            elif (not was_found and operation == OP.LOOKUP_OR_SWAP) or operation == OP.SWAP:
                # swap
                # check returned item is the one which was at instr. input
                aeq(o_reset, 0)
                cur_key_vld = cur is not None and cur[0]
                if key_vld:
                    _o_match = cur_key_vld and int(cur[1]) == key
                    aeq(o_match, int(_o_match))
                aeq(o_found_key, key)
                aeq(o_found_key_vld, key_vld)
                aeq(o_found_data, data)

                # check orig item
                if cur is None:
                    aeq(o_key, None)
                    aeq(o_key_vld, None)
                    aeq(o_data, None)
                else:
                    aeq(o_key, cur[1])
                    aeq(o_key_vld, cur[0])
                    aeq(o_data, cur[2])

                mem[addr] = (int(key_vld), key, data)

            else:
                raise ValueError(operation)

            self.assertValEqual(o_operation, operation)

        self.assertEqual(len(dout), len(inputs))
        # for i in sorted(set(inputs)):
        #    self.assertValEqual(self.m.data[i], inputs.count(i), i)
        for i in range(2 ** dut.ADDR_WIDTH // ADDR_ITEM_STEP):
            v = self.m.getStruct(i * ADDR_ITEM_STEP, dut.MAIN_STATE_T)
            ref_v = mem.get(i, None)
            if ref_v is None or not ref_v[0]:
                aeq(v.item_valid, 0)
            else:
                aeq(v.item_valid, 1)
                aeq(v.key, ref_v[1])
                aeq(v.value, ref_v[2])

    def test_1x_not_found(self):
        self._test_incr([(0, TState(0, None, OP.LOOKUP)), ])

    def test_r_100x_not_found(self):
        index_pool = list(range(2 ** self.dut.ID_WIDTH))
        self._test_incr([
                (self._rand.choice(index_pool), TState(0, None, OP.LOOKUP))
                for _ in range(100)
            ],
            randomize=True)

    def test_1x_lookup_found(self):
        self._test_incr([(1, TState(99, None, OP.LOOKUP)), ], mem_init={1: MState(99, 20)})

    def test_r_100x_lookup_found(self):
        item_pool = [(i, MState(i + 1, 20 + i)) for i in range(2 ** self.dut.ID_WIDTH)]

        self._test_incr(
            [(i, TState(v[1], None, OP.LOOKUP)) for i, v in [
                    self._rand.choice(item_pool) for _ in range(100)
                ]
            ],
            mem_init={i: v for i, v in item_pool},
            randomize=True
        )

    def test_100x_lookup2_found(self, randomize=False):
        item_pool = [(i, MState(i + 1, 20 + i)) for i in range(2)]

        self._test_incr(
            [(i, TState(v[1], None, OP.LOOKUP)) for i, v in [
                    self._rand.choice(item_pool) for _ in range(100)
                ]
            ],
            mem_init={i: v for i, v in item_pool},
            randomize=randomize
        )
        
    def test_r_100x_lookup2_found(self):
        self.test_100x_lookup2_found(randomize=True)

    def test_100x_lookup_found_not_found_mix(self, randomize=False):
        N = 100
        max_id = 2 ** self.dut.ID_WIDTH
        item_pool = [(i % max_id, MState(i + 1, 20 + i)) for i in range(max_id * 2)]

        self._test_incr(
            [(i, TState(v[1], None, OP.LOOKUP)) for i, v in [
                    self._rand.choice(item_pool) for _ in range(N)
                ]
            ],
            # :attention: i is modulo mapped that means that
            #     mem_init actually contains only last "n" items from item_pool
            mem_init={i: v for i, v in item_pool},
            randomize=randomize
        )

    def test_r_100x_lookup_found_not_found_mix(self):
        self.test_100x_lookup_found_not_found_mix(randomize=True)

    def test_1x_lookup_or_swap_found(self):
        self._test_incr(
            [(1, TState(99, None, OP.LOOKUP_OR_SWAP)), ],
            mem_init={1: MState(99, 20)}
        )

    def test_1x_swap_delete(self):
        self._test_incr(
            [(1, TState(None, None, OP.SWAP)),
             # (1, TState(99, 123, OP.LOOKUP)), # [todo] write forwarding on original_state for swap ops.
              ],
            mem_init={1: MState(99, 20)}
        )

    def test_1x_swap_delete_unallocated(self):
        self._test_incr(
            [(1, TState(None, None, OP.SWAP)),  # delete of deleted
             (1, TState(99, 12, OP.LOOKUP)),  # search of non existing
             (1, TState(100, 33, OP.SWAP)),  # insert
             (1, TState(99, 12, OP.LOOKUP)),  # search of diffeent
             (1, TState(100, None, OP.LOOKUP)),  # search of existing
            ],
            mem_init={1: MState(None, None)}
        )

    def test_r_10x_swap_delete_unallocated(self):
        data = []
        for i in range(2):
            off = i * 10
            data.extend([
                (1, TState(None, None, OP.SWAP)),  # delete of deleted
                (1, TState(off + 1, None, OP.LOOKUP)),  # search of non existing
                (1, TState(off + 2, off + 1, OP.SWAP)),  # insert
                (1, TState(off + 1, None, OP.LOOKUP)),  # search of diffeent
                (1, TState(off + 2, None, OP.LOOKUP)),  # search of existing
            ])
        self._test_incr(
            data,
            mem_init={1: MState(None, None)},
            randomize=True
        )

    def test_no_comb_loops(self):
        s = CombLoopAnalyzer()
        s.visit_HwModule(self.dut)
        comb_loops = freeze_set_of_sets(s.report())
        # for loop in comb_loops:
        #     print(10 * "-")
        #     for s in loop:
        #         print(s.resolve()[1:])

        self.assertEqual(comb_loops, frozenset())


class OooOpExampleCounterHashTable_16threads_TC(OooOpExampleCounterHashTable_4threads_TC):

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = OooOpExampleCounterHashTable()
        dut.ID_WIDTH = 4
        dut.ADDR_WIDTH = dut.ID_WIDTH + 3
        dut.PIPELINE_CONFIG = OutOfOrderCummulativeOpPipelineConfig.new_config(
                WRITE_TO_WRITE_ACK_LATENCY=1,
                WRITE_ACK_TO_READ_DATA_LATENCY=16
        )
        cls.compileSim(dut)


class OooOpExampleCounterHashTable_16threads_2WtoB_TC(OooOpExampleCounterHashTable_4threads_TC):

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = OooOpExampleCounterHashTable()
        dut.ID_WIDTH = 4
        dut.ADDR_WIDTH = dut.ID_WIDTH + 3
        dut.PIPELINE_CONFIG = OutOfOrderCummulativeOpPipelineConfig.new_config(
                WRITE_TO_WRITE_ACK_LATENCY=2,
                WRITE_ACK_TO_READ_DATA_LATENCY=16
        )
        cls.compileSim(dut)


OooOpExampleCounterHashTable_TCs = [
    OooOpExampleCounterHashTable_4threads_TC,
    OooOpExampleCounterHashTable_16threads_TC,
    OooOpExampleCounterHashTable_16threads_2WtoB_TC,
]

if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([OooOpExampleCounterHashTable_4threads_TC("test_r_10x_swap_delete_unallocated")])
    loadedTcs = [testLoader.loadTestsFromTestCase(tc) for tc in OooOpExampleCounterHashTable_TCs]
    suite = unittest.TestSuite(loadedTcs)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
