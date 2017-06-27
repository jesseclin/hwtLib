import socket
import unittest

from hwt.code import iterBits
from hwt.simulator.simTestCase import SimTestCase
from hwtLib.samples.iLvl.builders.pingResponder import PingResponder, \
    echoFrame_t
from hwtLib.types.net.eth import parse_eth_addr, ETHER_TYPE
from hwtLib.types.net.icmp import ICMP_TYPE, ICMP_echo_header_t
from hwtLib.types.net.ip import IPv4, IHL_DEFAULT, IPv4Header_t, IP_PROTOCOL
from hwtLib.amba.axis_comp.frameParser_test import packAxiSFrame
from hwt.hdlObjects.constants import Time
from hwtLib.amba.axis import unpackAxiSFrame
from hwt.simulator.agentConnector import valToInt
from hwt.hdlObjects.types.structUtils import HStruct_unpack


def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)


def checksum(msg):
    s = 0
    for i in range(0, len(msg), 2):
        w = msg[i] + (msg[i + 1] << 8)
        s = carry_around_add(s, w)

    return ~s & 0xffff


def hstruct_checksum(structVal):
    """
    Checksum of values in StructValue instance
    """
    valAsShorts = iterBits(structVal, bitsInOne=8)
    valAsShorts = list(map(lambda x: x.val, valAsShorts))
    return checksum(valAsShorts)


def pingResponder_model(packetStructVal):
    """
    Modify ICMP Echo Request to an ICMP Echo Reply packet.

    :param packet: struct val of packet
    """
    print(packetStructVal._dtype)
    packet = iterBits(packetStructVal, bitsInOne=8, skipPadding=False)
    packet = list(map(valToInt, packet))
    eth = 0
    # swap eht addr
    packet[(eth + 0):(eth + 6)], packet[(eth + 6):(eth + 12)] = packet[(eth + 6):(eth + 12)], packet[(eth + 0):(eth + 6)]
    
    
    ip = 2 * 6 + 2
    # Swap source and destination address.
    packet[(ip + 12):(ip + 16)], packet[(ip + 16):(ip + 20)] = packet[(ip + 16):(ip + 20)], packet[(ip + 12):(ip + 16)]

    icmp = ip + 20
    # Change ICMP type code to Echo Reply (0).
    packet[icmp] = ICMP_TYPE.ECHO_REPLY

    # Calculate new  ICMP Checksum field.
    checksum = 0
    # for every 16-bit of the ICMP payload:
    for i in range(icmp, len(packet), 2):
        half_word = (packet[i] << 8) + (packet[i + 1])
        checksum += half_word
    # Get one's complement of the checksum.
    checksum = ~(checksum + 4) & 0xffff
    # Put the new checksum back into the packet. (bigendian)
    packet[icmp + 2] = checksum >> 8
    packet[icmp + 3] = checksum & ((1 << 8) - 1)

    return bytes(packet)


class PingResponderTC(SimTestCase):
    def setUp(self):
        self.DATA_WIDTH = 32

        SimTestCase.setUp(self)
        u = self.u = PingResponder()
        u.DATA_WIDTH.set(self.DATA_WIDTH)

        self.prepareUnit(u)



    def create_ICMP_echo_frame(self,
                               ethSrc="00:1:2:3:4:5", ethDst="6:7:8:9:10:11",
                               ipSrc="192.168.0.1", ipDst="192.168.0.2"):

        v = echoFrame_t.fromPy({
                "eth": {
                    "src": parse_eth_addr(ethSrc),
                    "dst": parse_eth_addr(ethDst),
                    "type": ETHER_TYPE.IPv4,
                },
                "ip": {
                    "version": IPv4,
                    "ihl": IHL_DEFAULT,
                    "dscp": 0,
                    "ecn": 0,
                    "totalLen": IPv4Header_t.sizeof() + ICMP_echo_header_t.sizeof(),
                    "id": 0,
                    "flags": 0,
                    "fragmentOffset": 0,
                    "ttl": 100,
                    "protocol": IP_PROTOCOL.ICMP,
                    "headerChecksum": 0,
                    "src": socket.inet_aton(ipSrc),
                    "dst": socket.inet_aton(ipDst)
                },
                "icmp": {
                    "type": ICMP_TYPE.ECHO_REQUEST,
                    "code": 0,
                    "checksum": 0,
                    "identifier": 0,
                    "seqNo": 0,
                    "payload": int.from_bytes(b"abcd", byteorder="big")
                }
            })

        v.ip.headerChecksum.val = hstruct_checksum(v.ip)
        v.icmp.checksum.val = hstruct_checksum(v.icmp)

        return v

    def test_struct_packUnpack(self):
        f = self.create_ICMP_echo_frame()
        asBytes = iterBits(f, bitsInOne=8, skipPadding=False)
        asBytes = list(map(valToInt, asBytes))
        
        f_out = HStruct_unpack(echoFrame_t, asBytes, dataWidth=8)

        self.assertEqual(f, f_out)

        _f = f
        f = f_out
        asBytes = iterBits(f, bitsInOne=8, skipPadding=False)
        asBytes = list(map(valToInt, asBytes))
        
        f_out = HStruct_unpack(echoFrame_t, asBytes, dataWidth=8)
        
        self.assertEqual(_f, f_out)
        
    
    def test_reply1x(self):
        u = self.u
        f = self.create_ICMP_echo_frame()

        u.rx._ag.data.extend(packAxiSFrame(self.DATA_WIDTH, f, withStrb=True))
        u.myIp._ag.data.append(int.from_bytes(socket.inet_aton("192.168.0.2"), byteorder="little"))
        self.doSim(500 * Time.ns)
        
        res = unpackAxiSFrame(echoFrame_t, u.tx._ag.data)
        model_res = pingResponder_model(f)
        
        _res = iterBits(res, bitsInOne=8, skipPadding=False)
        _res = bytes(map(valToInt, _res))
        print("")
        print("f", f)
        print("res", res)
        print("model_res", HStruct_unpack(echoFrame_t, model_res, dataWidth=8))

        self.assertEqual(_res, model_res)


if __name__ == "__main__":
    suite = unittest.TestSuite()

    suite.addTest(PingResponderTC('test_reply1x'))

    # suite.addTest(unittest.makeSuite(PingResponderTC))
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)