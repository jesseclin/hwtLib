from hdl_toolkit.intfLvl import Param, connect, Unit, EmptyUnit
from hdl_toolkit.interfaces.amba import AxiStream, AxiLite
from hdl_toolkit.synthesizer.interfaceLevel.emptyUnit import setOut

class HeadFieldExtractor(EmptyUnit):
    def _declr(self):
        with self._asExtern():
            self.din = AxiStream()
            self.dout = AxiStream()
            self.headers = AxiStream()
    
    def _impl(self):
        setOut(self.dout, self.headers)
    
class PatternMatch(EmptyUnit):
    def _declr(self):
        with self._asExtern():
            self.din = AxiStream()
            self.match = AxiStream()
            self.cfg = AxiLite()
    
    def _impl(self):
        setOut(self.match)
    
    
class Filter(EmptyUnit):
    def _declr(self):
        with self._asExtern():
            self.headers = AxiStream()
            self.match = AxiStream()
            self.din = AxiStream()
            self.dout = AxiStream()
            self.cfg = AxiLite()
    
    def _impl(self):
        setOut(self.match, self.dout)


class AxiStreamFork(EmptyUnit):
    def _declr(self):
        with self._asExtern():
            self.din = AxiStream()
            self.dout0 = AxiStream()
            self.dout1 = AxiStream()

    def _impl(self):
        setOut(self.dout0, self.dout1)

class Exporter(EmptyUnit):
    def _declr(self):
        with self._asExtern():
            self.din = AxiStream()
            self.dout = AxiStream()
    def _impl(self):
        setOut(self.dout)


class NetFilter(Unit):
    """
    This unit has actually no functionality it is just example of hierarchical design.
    """
    def _config(self):
        self.DATA_WIDTH = Param(64)
    
    def _declr(self):
        with self._paramsShared():
            with self._asExtern():
                self.din = AxiStream()
                self.export = AxiStream()
                # self.cfg = AxiLite(isExtern=True)
    
            self.hfe = HeadFieldExtractor()
            self.pm = PatternMatch()
            self.filter = Filter()
            self.exporter = Exporter()
    
            self.forkHfe = AxiStreamFork()
        
    def _impl(self):
        s = self
        s.hfe.din ** s.din 
        s.forkHfe.din ** s.hfe.dout
        s.pm.din ** s.forkHfe.dout0 
        s.filter.din ** s.forkHfe.dout1
        s.filter.headers ** s.hfe.headers 
        s.filter.match ** s.pm.match 
        s.exporter.din ** s.filter.dout 
        s.export ** s.exporter.dout 


if __name__ == "__main__":
    from hdl_toolkit.synthesizer.shortcuts import toRtl
    from cli_toolkit.ip_packager.packager import Packager
    print(toRtl(NetFilter))
    
    # s = NetFilter()
    # p = Packager(s)
    # p.createPackage("project/ip/")

    
