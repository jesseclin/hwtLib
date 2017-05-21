#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hwt.code import  If, Concat, sll
from hwt.hdlObjects.typeShortcuts import vecT 
from hwt.interfaces.std import Signal, VectSignal
from hwt.interfaces.utils import addClkRstn
from hwt.synthesizer.interfaceLevel.unit import Unit
from hwt.synthesizer.param import Param, evalParam
from hwtLib.clocking.clkBuilder import ClkBuilder
from hwtLib.handshaked.intfBiDirectional import HandshakedBiDirectional, \
    HandshakedBiDirectionalAgent
from hwtLib.logic.binToOneHot import BinToOneHot
from hwtLib.spi.intf import Spi


class SpiCntrlDataAgent(HandshakedBiDirectionalAgent):
    def doRead(self, s):
        """extract data from interface"""
        intf = self.intf
        r = s.read

        return r(intf.slave), r(intf.dout), r(intf.last)

    def doWrite(self, s, data):
        """write data to interface"""
        w = s.write 
        intf = self.intf
        slave, d, last = data
        w(slave, intf.slave)
        w(d, intf.dout)
        w(last, intf.last)


class SpiCntrlData(HandshakedBiDirectional):
    """
    HandshakedBiDirectional interface with last and slave signal added.
    If last=1 slave will be deselected and initial slave select wait will be.
    Slave selects the slave where data should be read from and written to. 
    """
    def _declr(self):
        self.slave = VectSignal(1)
        HandshakedBiDirectional._declr(self)
        self.last = Signal()
    
    def _getSimAgent(self):
        return SpiCntrlDataAgent


class SpiMaster(Unit):
    """
    Master for SPI interface

    :ivar SPI_FREQ_PESCALER: frequency prescaler to get SPI clk from main clk (Param)
    :ivar SS_WAIT_CLK_TICKS: number of SPI ticks to wait with SPI clk activation after slave select 
    :ivar HAS_TX: if set true write part will be instantiated
    :ivar HAS_RX: if set true read part will be instantiated

    :attention: this implementation expects that slaves are reading data on rising edge of SPI clk
        and data from slaves are ready on risign edge as well
        and SPI clk is kept high in idle
        (most of them does but there are some exceptions)
    """
    def _config(self):
        self.SPI_FREQ_PESCALER = Param(32)
        self.SS_WAIT_CLK_TICKS = Param(4)
        self.HAS_TX = Param(True)
        self.HAS_RX = Param(True)
        self.SPI_DATA_WIDTH = Param(1)
        Spi._config(self)
         
    def _declr(self):
        addClkRstn(self)
        
        self.spi = Spi()
        self.HAS_RX = evalParam(self.HAS_RX).val
        self.HAS_TX = evalParam(self.HAS_TX).val
        assert self.HAS_RX or self.HAS_TX 
        
        with self._paramsShared():
            self.DATA_WIDTH = evalParam(self.SPI_DATA_WIDTH).val * 8
            self.data = SpiCntrlData()
            self.data.DATA_WIDTH.set(self.DATA_WIDTH)
            
        self.csDecoder = BinToOneHot()
        self.csDecoder.DATA_WIDTH.set(self.SLAVE_CNT)

    def writePart(self, writeTick, isLastTick, data):
        txReg = self._reg("rxReg", vecT(self.DATA_WIDTH))
        txInitialized = self._reg("txInitialized", defVal=0)
        If(writeTick,
            If(txInitialized,
                txReg ** sll(txReg, 1),
                If(isLastTick,
                   txInitialized ** 0,
                )
            ).Else(
               txInitialized ** 1,
               txReg ** data 
            )
        )
        self.spi.mosi ** txReg[self.DATA_WIDTH - 1]

    def readPart(self, readTick):
        rxReg = self._reg("rxReg", vecT(self.DATA_WIDTH))
        If(readTick,
           rxReg ** Concat(rxReg[:1], self.spi.miso)
        )
        return rxReg

    def spiClkGen(self, requiresInitWait, en):
        """
        create clock generator for SPI 
        writeTick is 1 on falling edge of spi clk
        readTick is 1 on rising edge of spi clk
        
        :return: tuple of tick signals (if data should be send, if data should be read)  
        """
        builder = ClkBuilder(self, self.clk)
        timersRst = self._sig("timersRst")
        
        PESCALER = self.SPI_FREQ_PESCALER
        SPI_HALF_PERIOD = PESCALER // 2
        spiClkHalfTick, initWaitDone, endOfWord = builder.timers(
            [("spiClkHalfTick", SPI_HALF_PERIOD),
             ("initWait", SPI_HALF_PERIOD * self.SS_WAIT_CLK_TICKS * 2),
             ("endOfWord", SPI_HALF_PERIOD * 8 * 2)
            ],
            enableSig=en,
            rstSig=timersRst)
        
        timersRst ** (~en | (requiresInitWait & initWaitDone))
        
        clkOut = self._reg("clkOut", defVal=1)
        If(spiClkHalfTick,
           clkOut ** ~clkOut
        )
        
        self.spi.clk ** (clkOut | requiresInitWait)  # clk idle value is high

        clkRisign, clkFalling = builder.edgeDetector(clkOut, rise=True, fall=True, initVal=1)
        
        rdEn = clkRisign & ~requiresInitWait
        wrEn = clkFalling & ~requiresInitWait
        
        return (wrEn, rdEn, initWaitDone, endOfWord)
        
    def _impl(self):
        
        d = self.data
        slaveSelectWaitRequired = self._reg("slaveSelectWaitRequired", defVal=1)
        
        writeTick, readTick, initWaitDone, endOfWord = self.spiClkGen(
            slaveSelectWaitRequired,
            self.data.vld)
        
        if self.HAS_RX:
            d.din ** self.readPart(readTick)
        else:
            d.din ** None
            
        if self.HAS_TX:
            self.writePart(writeTick, endOfWord, d.dout)
        
        If(initWaitDone,
           slaveSelectWaitRequired ** 0
        ).Elif(endOfWord,
           slaveSelectWaitRequired ** d.last
        )
        
        csD = self.csDecoder
        csD.din ** d.slave
        csD.en ** d.vld
        
        self.spi.cs ** csD.dout 
        d.rd ** endOfWord


if __name__ == "__main__":
    from hwt.synthesizer.shortcuts import toRtl
    u = SpiMaster()
    print(toRtl(u))