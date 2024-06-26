#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.hwIOs.std import HwIOSignal
from hwt.hwModule import HwModule
from hwt.pyUtils.typingFuture import override


class ExampleChild(HwModule):
    @override
    def hwDeclr(self):
        self.c = HwIOSignal()
        self.d = HwIOSignal()._m()

    @override
    def hwImpl(self):
        self.d(self.c)


class UnusedSubunit(HwModule):
    @override
    def hwDeclr(self):
        self.a = HwIOSignal()
        self.b = HwIOSignal()._m()

        self.child = ExampleChild()

    @override
    def hwImpl(self):
        # self.child left unconnected -> error
        self.b(self.a)


class UnusedSubunit2(HwModule):
    @override
    def hwDeclr(self):
        self.a = HwIOSignal()
        self.b = HwIOSignal()._m()

        self.child0 = ExampleChild()
        self.child1 = ExampleChild()
        self.child2 = ExampleChild()

    @override
    def hwImpl(self):
        # chain of children is left unconnected -> error
        self.b(self.a)

        self.child1.c(self.child0.d)
        self.child2.c(self.child1.d)


if __name__ == "__main__":
    from hwt.synth import to_rtl_str
    
    m = UnusedSubunit2()
    # hwt.serializer.exceptions.SerializerException
    print(to_rtl_str(m))
