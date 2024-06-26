#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.constants import Time
from hwt.pyUtils.arrayQuery import take, iter_with_last
from hwt.simulator.simTestCase import SimTestCase, \
    simpleRandomizationProcess
from hwtLib.amba.axis_comp.fifoMeasuring import Axi4S_fifoMeasuring
from pyMathBitPrecise.bit_utils import mask, mask_bytes
from hwtSimApi.constants import CLK_PERIOD
from hwtSimApi.triggers import Timer


class Axi4S_fifoMeasuringTC(SimTestCase):

    @classmethod
    def setUpClass(cls):
        dut = cls.dut = Axi4S_fifoMeasuring()
        dut.USE_STRB = True
        cls.DATA_WIDTH = 64
        cls.MAX_LEN = 15

        dut.MAX_LEN = cls.MAX_LEN
        dut.SIZES_BUFF_DEPTH = 4
        dut.DATA_WIDTH = cls.DATA_WIDTH
        cls.compileSim(dut)

    def test_nop(self):
        dut = self.dut
        self.runSim(20 * CLK_PERIOD)

        self.assertEqual(len(dut.sizes._ag.data), 0)
        self.assertEqual(len(dut.dataOut._ag.data), 0)

    def test_singleWordPacket(self):
        dut = self.dut

        dut.dataIn._ag.data.extend([
            (2, mask(8), 1),
        ])

        self.runSim(20 * CLK_PERIOD)
        self.assertValSequenceEqual(dut.sizes._ag.data, [8, ])
        self.assertValSequenceEqual(dut.dataOut._ag.data, [(2, mask(8), 1), ])

    def test_singleWordPacketWithDelay(self):
        dut = self.dut

        dut.dataIn._ag.data.extend([(2, mask(8), 1),
                                  ])
        dut.dataOut._ag._enabled = False

        self.runSim(20 * CLK_PERIOD)
        self.assertValSequenceEqual(dut.sizes._ag.data, [8, ])
        self.assertEmpty(dut.dataOut._ag.data, 0)
        self.assertValEqual(self.rtl_simulator.model.io.dataOut_last.read(), 1)

    def test_multiplePackets(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data

        goldenData = [(1, mask(8), 1),
                      (2, mask(8), 1),
                      (3, mask(8), 1)
                      ]

        dut.dataIn._ag.data.extend(goldenData)

        self.runSim(20 * CLK_PERIOD)
        self.assertValSequenceEqual(data, goldenData)
        self.assertValSequenceEqual(sizes, [8, 8, 8])

    def test_doubleWordPacket(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data

        goldenData = [(1, mask(8), 0),
                      (2, mask(8), 1)
                      ]
        dut.dataIn._ag.data.extend(goldenData)

        self.runSim(20 * CLK_PERIOD)
        self.assertValSequenceEqual(data, goldenData)
        self.assertValSequenceEqual(sizes, (16,))

    def test_withPause(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data

        goldenData = [
            (i + 1, 255, int(i == 5)) for i in range(6)
        ]
        dut.dataIn._ag.data.extend(goldenData)

        def pause():
            yield Timer(3 * CLK_PERIOD)
            dut.dataOut._ag.setEnable_asMonitor(False)
            yield Timer(3 * CLK_PERIOD)
            dut.dataOut._ag.setEnable_asMonitor(True)

        self.procs.append(pause())

        self.runSim(20 * CLK_PERIOD)

        self.assertValSequenceEqual(data, goldenData)
        self.assertValSequenceEqual(sizes, [6 * 8])

    def test_unalignedPacket(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data

        goldenData = [
            (1, mask(8), 0),
            (2, mask(1), 1)
        ]
        dut.dataIn._ag.data.extend(goldenData)

        self.runSim(20 * CLK_PERIOD)

        self.assertValSequenceEqual(data, goldenData)
        self.assertValSequenceEqual(sizes, (9,))

    def test_unalignedPacket1Word(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data

        goldenData = [(2, 1, 1), ]
        dut.dataIn._ag.data.extend(goldenData)

        self.runSim(20 * CLK_PERIOD)

        self.assertValSequenceEqual(data, goldenData)
        self.assertValSequenceEqual(sizes, (1,))

    def test_randomized(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data
        N = 30

        for i in range(N):
            dut.dataIn._ag.data.extend([
                (i + 1, mask(8), i == 5) for i in range(6)
            ])
        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.randomize(dut.sizes)

        self.runSim(N * 6 * 10 * 3 * Time.ns)

        self.assertEqual(len(sizes), N)
        self.assertEqual(len(data), N * 6)
        for s in sizes:
            self.assertValEqual(s, 6 * 8)

    def test_randomized10(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data
        N = 10
        expectedData = []
        expectedLen = []

        for i in range(N):
            _l = int(self._rand.random() * (self.MAX_LEN + 1 + 1))
            d = [(i + 1, mask(8), int(i == (_l - 1))) for i in range(_l)]
            dut.dataIn._ag.data.extend(d)

            expectedData.extend(d)
            expectedLen.append(_l * 8)

        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        self.randomize(dut.sizes)

        self.runSim(len(expectedData) * 3 * CLK_PERIOD)

        self.assertEqual(len(sizes), N)
        self.assertEqual(len(data), len(expectedData))

        for exp, d in zip(expectedData, data):
            self.assertValSequenceEqual(d, exp)

        for el, l in zip(expectedLen, sizes):
            self.assertValEqual(l, el)

    def test_withSizeBrake(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = dut.dataOut._ag.data
        N = 30
        SIZE_BUFF_SIZE = 16
        L = 6
        expectedLen = []

        for i in range(N):
            d = [(i + 1, 255, int(i == (L - 1))) for i in range(L)]
            dut.dataIn._ag.data.extend(d)
            expectedLen.append(L * 8)

        self.randomize(dut.dataIn)
        self.randomize(dut.dataOut)
        dut.sizes._ag.enable = False

        def sizesEn():
            yield Timer((SIZE_BUFF_SIZE + 5) * CLK_PERIOD)
            yield from simpleRandomizationProcess(self, dut.sizes._ag)()

        self.procs.append(sizesEn())

        self.runSim(N * 6 * 10 * 3 * Time.ns)

        self.assertEqual(len(sizes), N)
        self.assertEqual(len(data), N * 6)
        for el, l in zip(expectedLen, sizes):
            self.assertValEqual(l, el)

    def sendFrame(self, data):
        dut = self.dut
        _mask = mask(self.DATA_WIDTH // 8)
        _d = [(d, _mask, int(i == (len(data) - 1)))
              for i, d in enumerate(data)]
        dut.dataIn._ag.data.extend(_d)

    def getFrames(self):
        dut = self.dut
        sizes = dut.sizes._ag.data
        data = iter(dut.dataOut._ag.data)
        size_of_word = self.DATA_WIDTH // 8

        frames = []
        for s in sizes:
            _s = int(s)
            words = _s // size_of_word
            if _s / size_of_word - words > 0.0:
                words += 1

            frame = []
            for last, (_d, _mask, _last) in iter_with_last(take(data, words)):
                self.assertValEqual(_last, last)
                _mask = int(_mask)
                _d.val = mask_bytes(_d.val, _mask, size_of_word)
                _d.vld_mask = mask_bytes(_d.vld_mask, _mask, size_of_word)
                frame.append(int(_d))
            frames.append(frame)

        return frames

    def test_overflow(self):
        MAX_LEN = self.MAX_LEN
        data = [i for i in range(MAX_LEN + 4)]
        self.sendFrame(data)

        self.runSim((MAX_LEN + 10) * CLK_PERIOD)
        f = self.getFrames()
        self.assertEqual(f,
                         [[i for i in range(MAX_LEN + 1)],
                          [MAX_LEN + 1, MAX_LEN + 2, MAX_LEN + 3]])


if __name__ == "__main__":
    import unittest

    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Axi4S_fifoMeasuringTC("test_singleWordPacket")])
    suite = testLoader.loadTestsFromTestCase(Axi4S_fifoMeasuringTC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
