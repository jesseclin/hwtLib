from hdl_toolkit.intfLvl import Param
from hdl_toolkit.synthesizer.codeOps import And
from hdl_toolkit.interfaces.std import Handshaked
from hwtLib.handshaked.compBase import HandshakedCompBase
from hdl_toolkit.interfaces.utils import addClkRstn

class HandshakedFork(HandshakedCompBase):
    """
    Clone input stream to n identical output streams
    transaction is made in all interfaces or none of them
    
    combinational
    """
    def _config(self):
        self.OUTPUTS = Param(2)
        super()._config()
        
    def _declr(self):
        with self._asExtern(), self._paramsShared():
            addClkRstn(self)  # this is just for reference, not actualy used inside
            self.dataIn = self.intfCls()
            self.dataOut = self.intfCls(multipliedBy=self.OUTPUTS)

    def _impl(self):
        rd = self.getRd
        vld = self.getVld
        data = self.getData
        
        for io in self.dataOut:
            for i, o in zip(data(self.dataIn), data(io)):
                o ** i 
        
        outRd = And(*[rd(i) for i in self.dataOut])
        rd(self.dataIn) ** outRd 

        for o in self.dataOut:
            # everyone else is ready and input is valid
            deps = [vld(self.dataIn)]
            for otherO in self.dataOut:
                if otherO is o:
                    continue
                deps.append(rd(otherO))
            _vld = And(*deps)
            
            vld(o) ** _vld  
        
        
if __name__ == "__main__":
    from hdl_toolkit.synthesizer.shortcuts import toRtl
    u = HandshakedFork(Handshaked)
    print(toRtl(u))
