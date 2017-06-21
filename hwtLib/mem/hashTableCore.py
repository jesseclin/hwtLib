from hwt.code import log2ceil, If, connect, Concat
from hwt.interfaces.std import Handshaked
from hwt.interfaces.utils import propagateClkRstn, addClkRstn
from hwt.synthesizer.interfaceLevel.unit import Unit
from hwt.synthesizer.param import Param, evalParam
from hwtLib.handshaked.ramAsHs import RamAsHs
from hwtLib.handshaked.reg import HandshakedReg
from hwtLib.handshaked.streamNode import streamSync
from hwtLib.logic.crcComb import CrcComb
from hwtLib.logic.crcPoly import CRC_32
from hwtLib.mem.hashTable_intf import InsertIntf, LookupKeyIntf, \
    LookupResultIntf
from hwtLib.mem.ram import RamSingleClock


CHT_FOUND = 1
INSERT_FAIL = 0
INSERT_DONE = 1


# https://web.stanford.edu/class/cs166/lectures/13/Small13.pdf
class HashTableCore(Unit):
    """
    Generic hash table, in block RAM
    there is a input key which is hashed ad this has is used as an index into memory
    item on this place is checked and returned on "lookupRes" interface 
    (item does have to be found, see "found" flag in LookupResultIntf)
    
    memory is an array of items in format 
    
    .. code-block:: c

        struct item {
            bool vldFlag;
            data_t data;
            key_t key;
        };

    :ivar ITEMS_CNT: number of items in memory of hash table
    :ivar KEY_WIDTH: width of the key used by hash table
    :ivar LOOKUP_HASH: flag if this interface should have hash signal
    :ivar LOOKUP_KEY: flag if this interface should have hash signal
    :ivar DATA_WIDTH: width of data, can be zero and then no data interface is instantiated
    """
    def __init__(self, polynom):
        super(HashTableCore, self).__init__()
        self.POLYNOM = polynom

    def _config(self):
        self.ITEMS_CNT = Param(32)
        self.DATA_WIDTH = Param(8)
        self.KEY_WIDTH = Param(16)
        self.LOOKUP_HASH = Param(False)
        self.LOOKUP_KEY = Param(False)
        
    def _declr(self):
        addClkRstn(self)
        assert int(self.KEY_WIDTH) > 0
        assert int(self.DATA_WIDTH) >= 0
        assert int(self.ITEMS_CNT) > 1
        
        self.HASH_WITH = log2ceil(self.ITEMS_CNT).val

        assert self.HASH_WITH < int(self.KEY_WIDTH), "It makes no sense to use hash table when you can use key directly as index"
        
        with self._paramsShared():
            self.insert = InsertIntf()
            self.insert.HASH_WIDTH.set(self.HASH_WITH)

            self.lookup = LookupKeyIntf()

            self.lookupRes = LookupResultIntf()
            self.lookupRes.HASH_WIDTH.set(self.HASH_WITH)

        t = self.table = RamSingleClock()
        t.PORT_CNT.set(1)
        t.ADDR_WIDTH.set(log2ceil(self.ITEMS_CNT))
        t.DATA_WIDTH.set(self.KEY_WIDTH + self.DATA_WIDTH + 1)  # +1 for vldFlag

        tc = self.tableConnector = RamAsHs()
        tc.ADDR_WIDTH.set(t.ADDR_WIDTH.get())
        tc.DATA_WIDTH.set(t.DATA_WIDTH.get())
        
        hashWidth = max(evalParam(self.KEY_WIDTH).val, self.HASH_WITH)
        h = self.hash = CrcComb()
        h.DATA_WIDTH.set(hashWidth)
        h.POLY.set(self.POLYNOM)
        h.POLY_WIDTH.set(hashWidth)

    def parseKeyRec(self, sig):
        """
        Parse data stored in hash table
        """
        DW = int(self.DATA_WIDTH)
        KW = int(self.KEY_WIDTH)
        
        vldFlag = sig[0]

        dataLow = 1
        dataHi = dataLow + DW
        if dataHi > dataLow: 
            data = sig[dataHi:dataLow]
        else:
            data = None
        
        keyLow = dataHi
        keyHi = keyLow + KW
        # assert keyHi > keyLow
        
        key = sig[keyHi:keyLow]
        
        return (key, data, vldFlag)
    
    def lookupLogic(self, ramR):
        h = self.hash
        l = self.lookup
        res = self.lookupRes
        
        # tmp storage for original key and hash for later check
        origKeyReg = HandshakedReg(LookupKeyIntf)
        origKeyReg.KEY_WIDTH.set(self.KEY_WIDTH)
        self.origKeyReg = origKeyReg
        origKeyReg.dataIn.key ** l.key
        origKeyReg.clk ** self.clk
        origKeyReg.rst_n ** self.rst_n
        
        origKey = origKeyReg.dataOut
        

        # hash key and address with has in table
        h.dataIn ** l.key
        # has can be wider
        connect(h.dataOut, ramR.addr.data, fit=True) 

        inputSlaves = [ramR.addr, origKeyReg.dataIn]
        outputMasters = [origKey, ramR.data, ]

        if self.LOOKUP_HASH:
            origHashReg = HandshakedReg(Handshaked)
            origHashReg.DATA_WIDTH.set(self.HASH_WITH)

            self.origHashReg = origHashReg
            origHashReg.clk ** self.clk
            origHashReg.rst_n ** self.rst_n
            connect(h.dataOut, origHashReg.dataIn.data, fit=True)
            
            inputSlaves.append(origHashReg.dataIn)
            outputMasters.append(origHashReg.dataOut)

        streamSync(masters=[l],
                   slaves=inputSlaves)

        # propagate loaded data
        streamSync(masters=outputMasters,
                   slaves=[res])
            
        key, data, vldFlag = self.parseKeyRec(ramR.data.data)

        if self.LOOKUP_HASH:
            res.hash ** origHashReg.dataOut.data

        if self.LOOKUP_KEY:
            res.key ** origKey.key
            
        if self.DATA_WIDTH:
            res.data ** data

        res.found ** (origKey.key._eq(key) & vldFlag) 
        
    def insertLogic(self, ramW):
        In = self.insert
        
        if self.DATA_WIDTH:
            rec = Concat(In.key, In.data, In.vldFlag)
        else:
            rec = Concat(In.key, In.vldFlag)

        ramW.data ** rec
        ramW.addr ** In.hash 
        streamSync(masters=[In], slaves=[ramW])

    def _impl(self):
        propagateClkRstn(self)

        table = self.tableConnector
        self.table.a ** table.ram
        self.lookupLogic(table.r)
        self.insertLogic(table.w)


if __name__ == "__main__":
    from hwt.synthesizer.shortcuts import toRtl
    u = HashTableCore(CRC_32)
    print(toRtl(u))  
