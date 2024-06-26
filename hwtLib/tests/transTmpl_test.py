#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from hwt.hdl.transTmpl import TransTmpl
from hwt.hdl.types.stream import HStream
from hwt.hdl.types.struct import HStruct
from hwt.hdl.types.union import HUnion
from hwtLib.types.ctypes import uint8_t, uint16_t


union0 = HUnion(
            (HStruct(
                (uint8_t, "a0"),
                (uint8_t, "a1"),
             ), "a"),
            (uint16_t, "b"),
            )
union0_str = """\
<TransTmpl start:0, end:16
    <TransTmpl name:a, start:0, end:16
        <TransTmpl name:a0, start:0, end:8>
        <TransTmpl name:a1, start:8, end:16>
    >
    <OR>
    <TransTmpl name:b, start:0, end:16>
>"""

stream_const_len = HStruct(
    (uint8_t, "a0"),
    (HStream(uint8_t, frame_len=(1, 1)), "f0"),
    (uint8_t, "a1"),
)

stream_const_len_str = """\
<TransTmpl start:0, end:24
    <TransTmpl name:a0, start:0, end:8>
    <TransTmpl name:f0, start:8, end:16, itemCnt:1
        <TransTmpl name:f0, start:0, end:8>
    >
    <TransTmpl name:a1, start:16, end:24>
>"""

stream_const_len2 = HStruct(
    (uint8_t, "a0"),
    (HStream(uint8_t, frame_len=(2, 2)), "f0"),
    (uint8_t, "a1"),
)
stream_const_len2_str = """\
<TransTmpl start:0, end:32
    <TransTmpl name:a0, start:0, end:8>
    <TransTmpl name:f0, start:8, end:24, itemCnt:2
        <TransTmpl name:f0, start:0, end:8>
    >
    <TransTmpl name:a1, start:24, end:32>
>"""


class TransTmpl_TC(unittest.TestCase):
    def test_walkFlatten_struct(self):
        t = HStruct((uint8_t, "a"),
                    (uint8_t, "b"),
                    (uint8_t, "c"))
        trans = TransTmpl(t)
        self.assertEqual(len(list(trans.HwIO_walkFlatten())), 3)

    def test_walkFlatten_stream_const_len(self):
        trans = TransTmpl(stream_const_len)
        self.assertEqual(len(list(trans.HwIO_walkFlatten())), 3)

    def test__repr__stream_const_len(self):
        trans = TransTmpl(stream_const_len)
        s = repr(trans)
        self.assertEqual(s, stream_const_len_str)

    def test_walkFlatten_stream_const_len2(self):
        trans = TransTmpl(stream_const_len2)
        self.assertEqual(len(list(trans.HwIO_walkFlatten())), 4)

    def test__repr__stream_const_len2(self):
        trans = TransTmpl(stream_const_len2)
        s = repr(trans)
        self.assertEqual(s, stream_const_len2_str)

    def test_walkFlatten_arr(self):
        t = HStruct((uint8_t[4], "a"))
        trans = TransTmpl(t)
        self.assertEqual(len(list(trans.HwIO_walkFlatten())), 4)

    def test__repr__union(self):
        s = repr(TransTmpl(union0))
        self.assertEqual(s, union0_str)

    def test_walkFlatten_union(self):
        trans = TransTmpl(union0)
        fl = list(trans.HwIO_walkFlatten())
        self.assertEqual(len(fl), 1)
        children = list(fl[0].walkFlattenChilds())
        self.assertEqual(len(children), 2)

        self.assertEqual(len(list(children[0])), 2)
        self.assertEqual(len(list(children[1])), 1)


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([TransTmpl_TC("test_walkFlatten_arr")])
    suite = testLoader.loadTestsFromTestCase(TransTmpl_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)