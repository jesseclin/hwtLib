from hdl_toolkit.hdlObjects.typeShortcuts import vecT
from hdl_toolkit.interfaces.std import Signal, VectSignal
from hdl_toolkit.interfaces.utils import addClkRstn, log2ceil
from hdl_toolkit.synthesizer.interfaceLevel.unit import Unit
from hdl_toolkit.synthesizer.param import Param, evalParam
from hdl_toolkit.synthesizer.codeOps import If
from hdl_toolkit.synthesizer.shortcuts import toRtl


class StaticForLoopCntrl(Unit):
    def _config(self):
        self.ITERATIONS = Param(15)
    
    def _declr(self):
        addClkRstn(self)
        self.counterW = log2ceil(self.ITERATIONS)
    
        self.cntrlVld = Signal()
        self.cntrlRd = Signal()
        
        self.index = VectSignal(self.counterW) 
        self.bodyVld = Signal()
        self.bodyRd = Signal()
        self.bodyBreak = Signal()
        
    def _impl(self):
        ITERATIONS = evalParam(self.ITERATIONS).val
        """
        Iterates from ITERATIONS -1 to 0 body is enabled by bodyVld and if bodyRd 
        then counter is decremented for next iteration
        break causes reset of counter
        """
        
        counter = self._reg("counter", vecT(self.counterW + 1), 0)
        
        If(counter._eq(0),
            If(self.cntrlVld,
               counter ** ITERATIONS
            )
        ).Else(
            If(self.bodyRd,
                If(self.bodyBreak,
                    counter ** 0 
                ).Else(
                    counter ** (counter - 1)
                )
            )  
        )
            
        self.cntrlRd ** counter._eq(0)
        self.bodyVld ** (counter != 0) 
        self.index ** (counter[self.counterW:0] - 1)

        
if __name__ == "__main__":
    u = StaticForLoopCntrl()
    print(toRtl(u))

