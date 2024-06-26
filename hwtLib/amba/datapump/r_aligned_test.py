#!/usr/bin/env python3e
# -*- coding: utf-8 -*-

from hwtLib.amba.axi3 import Axi3
from hwtLib.amba.axi3Lite import Axi3Lite
from hwtLib.amba.axi4 import Axi4
from hwtLib.amba.axi4Lite import Axi4Lite
from hwtLib.amba.axiLite_comp.sim.ram import Axi4LiteSimRam
from hwtLib.amba.axi_comp.sim.ram import Axi4SimRam
from hwtLib.amba.constants import RESP_OKAY
from hwtLib.amba.datapump.r import Axi_rDatapump
from hwtLib.amba.datapump.test import Axi_datapumpTC
from hwtSimApi.constants import CLK_PERIOD
from pyMathBitPrecise.bit_utils import mask


class Axi4_rDatapumpTC(Axi_datapumpTC):
    LEN_MAX_VAL = 255
    DATA_WIDTH = 64
    CHUNK_WIDTH = DATA_WIDTH
    ALIGNAS = DATA_WIDTH

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = Axi_rDatapump(axiCls=Axi4)
        dut.DATA_WIDTH = cls.DATA_WIDTH
        dut.CHUNK_WIDTH = cls.CHUNK_WIDTH
        assert cls.CHUNK_WIDTH == cls.DATA_WIDTH
        dut.MAX_CHUNKS = cls.LEN_MAX_VAL + 1
        dut.ALIGNAS = cls.ALIGNAS
        cls.compileSim(dut)

    def test_nop(self):
        dut = self.dut
        self.runSim(20 * CLK_PERIOD)

        self.assertEmpty(dut.axi.ar._ag.data)
        self.assertEmpty(dut.driver.r._ag.data)

    def test_notSplitedReq(self):
        dut = self.dut

        req = dut.driver._ag.req

        # download one word from addr 0x100
        req.data.append(self.mkReq(0x100, 0))
        self.runSim((self.LEN_MAX_VAL + 3) * CLK_PERIOD)

        self.assertEqual(len(req.data), 0)
        self.assertEqual(len(dut.axi.ar._ag.data), 1)
        self.assertEqual(len(dut.driver._ag.r.data), 0)

    def test_notSplitedReqWithData(self):
        dut = self.dut
        r = dut.axi.r._ag

        ar_ref, driver_r_ref = self.spotReadMemcpyTransactions(0x100, 0, None)
        # extra data without any request
        for i in range(2):
            r.data.append(self.rTrans(i + 78))

        self.runSim((self.LEN_MAX_VAL + 7) * CLK_PERIOD)

        self.assertValSequenceEqual(dut.axi.ar._ag.data, ar_ref)
        self.assertValSequenceEqual(dut.driver.r._ag.data, driver_r_ref)
        # 2. is now beeing sended (but it should not finish as there is not a request for it)
        self.assertEqual(len(r.data), 2 - 1)

    def test_maxNotSplitedReqWithData(self):
        dut = self.dut

        req = dut.driver.req._ag
        r = dut.axi.r._ag

        ar_ref, driver_r_ref = self.spotReadMemcpyTransactions(0x100, self.LEN_MAX_VAL, None)

        # dummy data after the transaction
        r.data.extend([
            self.rTrans(11),
            self.rTrans(12),
        ])
        self.runSim((self.LEN_MAX_VAL + 6) * CLK_PERIOD)

        self.assertEmpty(req.data)
        self.assertValSequenceEqual(dut.axi.ar._ag.data, ar_ref)
        self.assertValSequenceEqual(dut.driver.r._ag.data, driver_r_ref)

        # 2. is now beeing sended (but it should not finish as there is not a request for it)
        self.assertEqual(len(r.data), 2 - 1)

    def test_maxReq(self):
        ar_ref, driver_r_ref = self.spotReadMemcpyTransactions(0x100, 2 * self.LEN_MAX_VAL + 1, None, addData=False)
        self.runSim((2 * self.LEN_MAX_VAL + 3) * CLK_PERIOD)

        self.check_r_trans(ar_ref, driver_r_ref)

    def test_maxOverlap(self):
        dut = self.dut
        MAX_TRANS_OVERLAP = dut.MAX_TRANS_OVERLAP

        ar_ref, _ = self.spotReadMemcpyTransactions(0x100, 2 * MAX_TRANS_OVERLAP, 0, addData=False)

        self.runSim((2 * MAX_TRANS_OVERLAP + 6) * CLK_PERIOD)

        self.assertEqual(len(dut.driver._ag.req.data), MAX_TRANS_OVERLAP)
        self.assertEqual(len(dut.driver.r._ag.data), 0)
        self.assertValSequenceEqual(dut.axi.ar._ag.data, ar_ref[:16])
        self.assertEqual(len(dut.axi.r._ag.data), 0)

    def test_multipleShortest(self, N=64):
        ar_ref, driver_r_ref = self.spotReadMemcpyTransactions(0x0, N - 1, 0)
        self.runSim((N + 5) * CLK_PERIOD)
        self.check_r_trans(ar_ref, driver_r_ref)

    def test_endstrb(self, FRAME_LEN=0):
        ar_ref, driver_r_ref = [], []
        addr_step = self.DATA_WIDTH // 8
        for i in range(0, addr_step, self.CHUNK_WIDTH // 8):  # for all possible end offsets
            _ar_ref, _driver_r_ref = self.spotReadMemcpyTransactions((i + FRAME_LEN + 1) * addr_step,
                                                                 FRAME_LEN,
                                                                 None,
                                                                 lastWordByteCnt=i + self.CHUNK_WIDTH // 8)
            ar_ref.extend(_ar_ref)
            driver_r_ref.extend(_driver_r_ref)

        self.runSim((len(driver_r_ref) + 5) * 2 * CLK_PERIOD)

        self.check_r_trans(ar_ref, driver_r_ref)

    def test_endstrbMultiFrame(self):
        self.test_endstrb(self.LEN_MAX_VAL)

    def test_multipleSplited(self, FRAMES=4):
        ar_ref, driver_r_ref = self.spotReadMemcpyTransactions(0x100, FRAMES * (self.LEN_MAX_VAL + 1) - 1, None)
        self.runSim((len(driver_r_ref) + 5) * CLK_PERIOD)
        self.check_r_trans(ar_ref, driver_r_ref)

    def test_randomized(self, N=24):
        dut = self.dut

        if dut.AXI_CLS in (Axi3Lite, Axi4Lite):
            m = Axi4LiteSimRam(axi=dut.axi)
        else:
            m = Axi4SimRam(axi=dut.axi)

        MAGIC = 99
        self.randomize(dut.driver.r)
        self.randomize(dut.driver.req)

        self.randomize(dut.axi.ar)
        self.randomize(dut.axi.r)

        r_ref = []
        for _ in range(N):
            size = int(self._rand.random() * self.LEN_MAX_VAL) + 1
            data = [MAGIC + i2 for i2 in range(size)]
            a = m.calloc(size, dut.DATA_WIDTH // 8, initValues=data)
            _, _r_ref = self.spotReadMemcpyTransactions(a, size - 1, None, data=data)
            r_ref.extend(_r_ref)
            MAGIC += size

        self.runSim(len(r_ref) * 5 * CLK_PERIOD)

        self.assertEmpty(dut.driver.req._ag.data)
        self.assertValSequenceEqual(dut.driver.r._ag.data, r_ref)

    def test_simpleUnalignedWithData(self, N=1, WORDS=1, OFFSET_B=None, randomize=False):
        dut = self.dut

        req = dut.driver._ag.req
        if randomize:
            self.randomize(dut.driver.req)
            self.randomize(dut.driver.r)
            self.randomize(dut.axi.ar)
            self.randomize(dut.axi.r)

        if dut.AXI_CLS in (Axi3Lite, Axi4Lite):
            m = Axi4LiteSimRam(axi=dut.axi)
        else:
            m = Axi4SimRam(axi=dut.axi)

        if OFFSET_B is None:
            if self.ALIGNAS == self.DATA_WIDTH:
                # to trigger an alignment error
                OFFSET_B = 1
            else:
                OFFSET_B = self.ALIGNAS // 8

        addr_step = dut.DATA_WIDTH // 8
        offset = 8
        ref_r_frames = []
        for i in range(N):
            data = [ (i + i2) & 0xff for i2 in range((WORDS + 1) * addr_step)]
            a = m.calloc((WORDS + 1) * addr_step, 1, initValues=data)
            rem = (self.CHUNK_WIDTH % self.DATA_WIDTH) // 8
            req.data.append(self.mkReq(a + OFFSET_B, WORDS - 1, rem=rem))
            if rem == 0:
                rem = self.DATA_WIDTH
            ref_r_frames.append(data[OFFSET_B:((WORDS - 1) * addr_step) + rem + OFFSET_B])

        t = (10 + N) * CLK_PERIOD
        if randomize:
            t *= 6
        self.runSim(t)
        if dut.ALIGNAS == dut.DATA_WIDTH:
            # unsupported alignment check if error is set
            self.assertValEqual(dut.errorAlignment._ag.data[-1], 1)

        else:
            if dut.ALIGNAS != 8:
                # if alignment is on 1B the but the errorAlignment can not happen
                self.assertValEqual(dut.errorAlignment._ag.data[-1], 0)

            ar_ref = []
            if dut.axi.LEN_WIDTH == 0:
                for i in range(N):
                    for w_i in range(WORDS + 1):
                        ar_ref.append(
                            self.aTrans(0x100 + (i + w_i) * addr_step, WORDS, 0)
                        )
            else:
                for i in range(N):
                    ar_ref.append(
                        self.aTrans(0x100 + i * addr_step, WORDS, 0)
                    )

            driver_r = dut.driver.r._ag.data
            for ref_frame in ref_r_frames:
                offset = None
                r_data = []
                for w_i in range(WORDS):
                    data, strb, last = driver_r.popleft()
                    self.assertValEqual(last, int(w_i == WORDS - 1))

                    for B_i in range(addr_step):
                        if strb[B_i]:
                            if offset is None:
                                offset = B_i + (addr_step * w_i)
                            B = int(data[(B_i + 1) * 8: B_i * 8])
                            r_data.append(B)

                self.assertEqual(offset, 0)
                self.assertSequenceEqual(r_data, ref_frame)

        self.assertEmpty(dut.axi.ar._ag.data)
        self.assertEmpty(dut.axi.r._ag.data)


class Axi3_rDatapumpTC(Axi4_rDatapumpTC):
    LEN_MAX_VAL = 15

    @classmethod
    def setUpClass(cls):
        dut = Axi_rDatapump(axiCls=Axi3)
        dut.DATA_WIDTH = cls.DATA_WIDTH
        dut.CHUNK_WIDTH = cls.CHUNK_WIDTH
        assert cls.CHUNK_WIDTH == cls.DATA_WIDTH
        dut.MAX_CHUNKS = cls.LEN_MAX_VAL + 1
        dut.ALIGNAS = cls.ALIGNAS
        cls.compileSim(dut)


class Axi3Lite_rDatapumpTC(Axi4_rDatapumpTC):
    LEN_MAX_VAL = 3
    MAX_CHUNKS = 1
    CHUNK_WIDTH = Axi4_rDatapumpTC.DATA_WIDTH
    ALIGNAS = Axi4_rDatapumpTC.ALIGNAS

    @classmethod
    def setUpClass(cls):
        dut = Axi_rDatapump(axiCls=Axi3Lite)
        dut.DATA_WIDTH = cls.DATA_WIDTH
        dut.CHUNK_WIDTH = cls.CHUNK_WIDTH
        assert cls.CHUNK_WIDTH == cls.DATA_WIDTH
        dut.MAX_CHUNKS = cls.LEN_MAX_VAL + 1
        dut.ALIGNAS = cls.ALIGNAS
        cls.compileSim(dut)

    def rTrans(self, data, _id=0, resp=RESP_OKAY, last=True):
        assert last
        assert _id == 0
        return (data, resp)

    def rDriverTrans(self, data, last, strb=mask(64 // 8), id_=0):
        assert id_ == 0
        return (data, strb, int(last))


Axi_rDatapump_alignedTCs = [
    Axi3_rDatapumpTC,
    Axi4_rDatapumpTC,
    Axi3Lite_rDatapumpTC,
]

if __name__ == "__main__":
    import unittest
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Axi4Lite_rDatapump_16b_from_64bTC("test_notSplitedReqWithData")])
    loadedTcs = [testLoader.loadTestsFromTestCase(tc) for tc in Axi_rDatapump_alignedTCs]
    suite = unittest.TestSuite(loadedTcs)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
