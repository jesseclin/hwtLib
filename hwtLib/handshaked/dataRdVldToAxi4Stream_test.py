#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hwIOs.std import HwIODataRdVld
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.handshaked.dataRdVldToAxi4Stream import DataRdVldToAxi4Stream
from hwtSimApi.constants import CLK_PERIOD


class DataRdVldToAxi4Stream_MAX_FRAME_WORDS_TC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        dut = DataRdVldToAxi4Stream(HwIODataRdVld)
        dut.MAX_FRAME_WORDS = 5
        cls.dut = dut
        cls.compileSim(dut)

    def test_basic(self, N=10, randomized=True):
        dut:DataRdVldToAxi4Stream = self.dut
        MAX_FRAME_WORDS = dut.MAX_FRAME_WORDS
        expected = []
        for i in range(N * MAX_FRAME_WORDS):
            dut.dataIn._ag.data.append(i)
            last = (i + 1) % MAX_FRAME_WORDS == 0
            expected.append((i, int(last)))

        t = (N * MAX_FRAME_WORDS + 10) * CLK_PERIOD
        if randomized:
            self.randomize(dut.dataIn)
            self.randomize(dut.dataOut)
            t *= 4
        self.runSim(t)
        self.assertValSequenceEqual(dut.dataOut._ag.data, expected)


class DataRdVldToAxi4Stream_IN_TIMEOUT_TC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        dut = DataRdVldToAxi4Stream(HwIODataRdVld)
        dut.IN_TIMEOUT = 3
        cls.dut = dut
        cls.compileSim(dut)

    def test_basic_no_timeout(self, N=100, randomized=False, expected_frame_lens={100}):
        self.test_basic(N=N, randomized=randomized, expected_frame_lens=expected_frame_lens)

    def test_basic(self, N=100, randomized=True, expected_frame_lens={1, 2, 3, 4, 5, 6}):
        dut: DataRdVldToAxi4Stream = self.dut
        for i in range(N):
            dut.dataIn._ag.data.append(i)

        t = (N + 10) * CLK_PERIOD
        if randomized:
            self.randomize(dut.dataIn)
            self.randomize(dut.dataOut)
            t *= 4
        self.runSim(t)
        data = []
        frame_lens = set()
        actual_len = 0
        for (d, last) in dut.dataOut._ag.data:
            d = int(d)
            data.append(d)

            last = bool(last)
            actual_len += 1
            if last:
                frame_lens.add(actual_len)
                actual_len = 0
        expected_data = list(range(N))

        self.assertSequenceEqual(data, expected_data)
        self.assertSetEqual(frame_lens, expected_frame_lens)  # N dependent


class DataRdVldToAxi4Stream_IN_TIMEOUT_AND_MAX_FRAME_WORDS_TC(DataRdVldToAxi4Stream_IN_TIMEOUT_TC):

    @classmethod
    def setUpClass(cls):
        dut = DataRdVldToAxi4Stream(HwIODataRdVld)
        dut.IN_TIMEOUT = 3
        dut.MAX_FRAME_WORDS = 4
        cls.dut = dut
        cls.compileSim(dut)

    def test_basic(self, N=100, randomized=True, expected_frame_lens={1, 2, 3, 4}):
        super(DataRdVldToAxi4Stream_IN_TIMEOUT_AND_MAX_FRAME_WORDS_TC, self).test_basic(
            N=N, randomized=randomized, expected_frame_lens=expected_frame_lens)

    def test_basic_no_timeout(self, N=101, randomized=False, expected_frame_lens={1, 4}):
        super(DataRdVldToAxi4Stream_IN_TIMEOUT_AND_MAX_FRAME_WORDS_TC, self).test_basic_no_timeout(
            N=N, randomized=randomized, expected_frame_lens=expected_frame_lens)


DataRdVldToAxi4StreamTCs = [
    DataRdVldToAxi4Stream_MAX_FRAME_WORDS_TC,
    DataRdVldToAxi4Stream_IN_TIMEOUT_TC,
    DataRdVldToAxi4Stream_IN_TIMEOUT_AND_MAX_FRAME_WORDS_TC,
]


if __name__ == "__main__":
    import unittest

    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([DataRdVldToAxi4Stream_MAX_FRAME_WORDS_TC("test_stuckedData")])
    loadedTcs = [testLoader.loadTestsFromTestCase(tc) for tc in DataRdVldToAxi4StreamTCs]
    suite = unittest.TestSuite(loadedTcs)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
