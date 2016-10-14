#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hdl_toolkit.bitmask import mask
from hdl_toolkit.interfaces.std import Signal, HandshakeSync, VectSignal
from hdl_toolkit.interfaces.utils import log2ceil, propagateClkRstn
from hdl_toolkit.synthesizer.codeOps import If, Switch, connect
from hdl_toolkit.synthesizer.param import Param
from hwtLib.axi.axi_datapump_base import Axi_datapumpBase
from hwtLib.handshaked.fifo import HandshakedFifo
from hwtLib.interfaces.amba import (Axi4_r, AxiStream_withId)
from hwtLib.interfaces.amba_constants import RESP_OKAY
from hwtLib.handshaked.streamNode import streamSync


class TransEndInfo(HandshakeSync):
    def _config(self):
        self.DATA_WIDTH = Param(64)
    
    def _declr(self):
        # rem is number of bits in last word which is valid - 1
        self.rem = VectSignal(log2ceil(self.DATA_WIDTH // 8))

        self.propagateLast = Signal()
        HandshakeSync._declr(self)

class Axi_rDatapump(Axi_datapumpBase):
    """
    Foward req to axi ar channel 
    and collect data to data channel form axi r channel 
    
    This unit simplifies axi interface,
    blocks data channel when there is no request pending
    and contains frame merging logic if is required
    
    if req len is wider transaction is internally splited to multiple
    transactions, but read data are single packet as requested 
    
    errorRead stays high when there was error on axi r channel
    it will not affect unit functionality
    \n""" + Axi_datapumpBase.__doc__


    def _config(self):
        super()._config()
        
        self.DEFAULT_ID = Param(0)
        self.USER_WIDTH = Param(2)  # if 0 is used user signal completly disapears
        
    def _declr(self):
        super()._declr()  # add clk, rst, axi addr channel and req channel
        with self._asExtern():
            with self._paramsShared():
                self.r = Axi4_r()
                self.rOut = AxiStream_withId()
                
                self.errorRead = Signal()
        
        with self._paramsShared():
            f = self.sizeRmFifo = HandshakedFifo(TransEndInfo)
            f.DEPTH.set(self.MAX_TRANS_OVERLAP)
    
    
    def arIdHandler(self, lastReqDispatched):
        a = self.a
        req_idBackup = self._reg("req_idBackup", self.req.id._dtype)
        If(lastReqDispatched,
            req_idBackup ** self.req.id,
            a.id ** self.req.id 
        ).Else(
            a.id ** req_idBackup
        )
    
    def addrHandler(self, addRmSize):
        ar = self.a
        req = self.req
        
        self.axiAddrDefaults() 

        # if axi len is smaller we have to use transaction splitting
        if self.useTransSplitting(): 
            LEN_MAX = mask(ar.len._dtype.bit_length())
            ADDR_STEP = self.getBurstAddrOffset()
            
               
            lastReqDispatched = self._reg("lastReqDispatched", defVal=1) 
            lenDebth = self._reg("lenDebth", req.len._dtype)
            remBackup = self._reg("remBackup", req.rem._dtype)
            rAddr = self._reg("r_addr", req.addr._dtype)
                           
            reqLen = self._sig("reqLen", req.len._dtype)
            reqRem = self._sig("reqRem", req.rem._dtype)
            
            ack = self._sig("ar_ack")
            
            self.arIdHandler(lastReqDispatched)
            If(reqLen > LEN_MAX,
               ar.len ** LEN_MAX,
               addRmSize.rem ** 0,
               addRmSize.propagateLast ** 0
            ).Else(
               connect(reqLen, ar.len, fit=True),  # connect only lower bits of len
               addRmSize.rem ** reqRem,
               addRmSize.propagateLast ** 1
            )
             
            If(ack,
                If(reqLen > LEN_MAX,
                    lenDebth ** (reqLen - (LEN_MAX + 1)),
                    lastReqDispatched ** 0
                ).Else(
                    lastReqDispatched ** 1
                )
            )
            
            If(lastReqDispatched,
               ar.addr ** req.addr,
               rAddr ** (req.addr + ADDR_STEP),
               
               reqLen ** req.len,
               reqRem ** req.rem,
               remBackup ** req.rem,
               ack ** (req.vld & addRmSize.rd & ar.ready),
               streamSync(masters=[req],
                              slaves=[addRmSize, ar]),
            ).Else(
               req.rd ** 0,
               ar.addr ** rAddr,
               If(addRmSize.rd & ar.ready,
                  rAddr ** (rAddr + ADDR_STEP) 
               ),
               
               reqLen ** lenDebth,
               reqRem ** remBackup,
               ack ** (addRmSize.rd & ar.ready),
               streamSync(slaves=[addRmSize, ar]),
            )
        else:
            # if axi len is wider we can directly translate requests to axi
            ar.id ** req.id
            ar.addr ** req.addr

            connect(req.len, ar.len, fit=True)
            
            addRmSize.rem ** req.rem
            addRmSize.propagateLast ** 1
            
            streamSync(masters=[req],
                       slaves=[ar, addRmSize])
            
        
    
    def remSizeToStrb(self, remSize, strb):
        strbBytes = 2 ** self.getSizeAlignBits()
        
        return Switch(remSize)\
                .Case(0,
                      strb ** mask(strbBytes)
                ).addCases(
                 [ (i + 1, strb ** mask(i + 1)) 
                   for i in range(strbBytes - 1)]
                )
    
    def dataHandler(self, rmSizeOut): 
        r = self.r
        rOut = self.rOut
        
        rErrFlag = self._reg("rErrFlag", defVal=0)
        If(r.valid & rOut.ready & (r.resp != RESP_OKAY),
           rErrFlag ** 1
        )
        self.errorRead ** rErrFlag
        
        
        rOut.id ** r.id
        rOut.data ** r.data
        
        If(r.valid & r.last,
            self.remSizeToStrb(rmSizeOut.rem, rOut.strb)
        ).Else(
            rOut.strb ** mask(2 ** self.getSizeAlignBits())
        )
        rOut.last ** (r.last & rmSizeOut.propagateLast)
        
        streamSync(masters=[r, rmSizeOut],
                   slaves=[rOut],
                   extraConds={rmSizeOut: [r.last]})

        
    def _impl(self):
        propagateClkRstn(self)
        
        self.addrHandler(self.sizeRmFifo.dataIn)
        self.dataHandler(self.sizeRmFifo.dataOut)

if __name__ == "__main__":
    from hdl_toolkit.synthesizer.shortcuts import toRtl
    u = Axi_rDatapump()
    print(toRtl(u))
    
