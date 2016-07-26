from hdl_toolkit.synthetisator.interfaceLevel.unit import Unit
from hdl_toolkit.synthetisator.param import Param, evalParam
from hdl_toolkit.interfaces.utils import addClkRstn, log2ceil
from hdl_toolkit.interfaces.std import ReqDoneSync, Signal
from hdl_toolkit.hdlObjects.typeShortcuts import vecT
from hdl_toolkit.hdlObjects.types.enum import Enum
from hdl_toolkit.synthetisator.codeOps import FsmBuilder, c, If


class DelayMs(Unit):
    def _config(self):
        self.FREQ = Param(int(100e6)) # [hz]
        self.MAX_DELAY = Param(100) # [ms]
    
    def _declr(self):
        with self._asExtern():
            addClkRstn(self)
            self.delayTime = Signal(dtype=vecT(log2ceil(self.MAX_DELAY)))
            self.acivate = ReqDoneSync()
            
    def _impl(self):
        
        stT = Enum("stT", ["idle", 'hold', 'done'])
        clksPerMs = evalParam(self.FREQ) // 1000
        
        cntrClk = self._reg("cntrClk", vecT( log2ceil(clksPerMs)))
        cntrMs = self._reg("cntrMs", self.delayTime._dtype) 
        
        stFsm = FsmBuilder(self, stT)
        st = stFsm.stateReg
        act = self.acivate
        
        
        c(act.req & st._eq(stT.done), act.done)
        
        stFsm\
        .Trans(stT.idle, 
            (act.req,                  stT.hold)
        ).Trans(stT.hold,
            (cntrMs._eq(self.delayTime), stT.done)
        ).Default(#stT.done,
            (~act.req,                 stT.idle)
        )
        
        
        # Creates ms_counter that counts at 1KHz
        If(st._eq(stT.hold),
            If(cntrClk._eq(clksPerMs),
                c(0, cntrClk),
                c(cntrMs+1, cntrMs)
            ).Else(
                c(cntrClk+1, cntrClk),
                cntrMs._same()
            )
        ).Else(
            c(0, cntrClk),
            c(0, cntrMs)  
        )
        
if __name__ == "__main__":
    from hdl_toolkit.synthetisator.shortcuts import toRtl
    # there is more of synthesis methods. toRtl() returns formated vhdl string
    u = DelayMs()
    print(toRtl(u))