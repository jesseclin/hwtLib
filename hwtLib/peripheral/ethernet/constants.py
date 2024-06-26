from hwt.hdl.types.bits import HBits
from hwt.math import log2ceil


class ETH:
    PREAMBLE_1B = HBits(8).from_py(0x55)
    PREAMBLE = HBits(7 * 8).from_py(0x55555555555555)  # (7* 0x55)
    SFD = HBits(8).from_py(0xD5)  # frame delimiter


ETH_ZLEN = 60  # Min. octets in frame sans FCS
ETH_DATA_LEN = 1500  # Max. octets in payload
ETH_FRAME_LEN = 1514  # Max. octets in frame sans FCS


class ETH_BITRATE:
    M_10M = 0
    M_100M = 1
    M_1G = 2
    M_2_5G = 3
    M_10G = 4
    M_25G = 5
    M_100G = 6
    M_200G = 7
    M_400G = 8
    M_1T = 9

    def get_siganl_width(self, max_mode: int):
        return log2ceil(max_mode)
