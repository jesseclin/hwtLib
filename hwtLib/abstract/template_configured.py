from copy import copy
from typing import Optional, List, Callable, Generator, Tuple

from hwt.hdl.frameTmpl import FrameTmpl
from hwt.hdl.transTmpl import TransTmpl
from hwt.hdl.types.bits import Bits
from hwt.hdl.types.hdlType import HdlType
from hwt.hdl.types.stream import HStream
from hwt.hdl.types.struct import HStruct
from hwt.pyUtils.arrayQuery import iter_with_last


class TemplateConfigured():
    """
    Class with functions for extracting metadata from frame template/HdlType.
    Used for resolving of data mapping between abstract type and physical interface.
    """
    def __init__(self,
                 structT: HdlType,
                 tmpl: Optional[TransTmpl]=None,
                 frames: Optional[List[FrameTmpl]]=None):
        """
        :param structT: instance of HStruct used as template for this frame
            If name is None no input port is generated and space
            is filled with invalid values, little-endian encoding,
            supported types of interfaces are: Handshaked, Signal
            can be also instance of FrameTmpl
        :param tmpl: instance of TransTmpl for this structT
        :param frames: list of FrameTmpl instances for this tmpl
        :note: if tmpl and frames are None they are resolved
            from structT parseTemplate
        """
        if tmpl is not None:
            assert frames is not None, \
                "tmpl and frames can be used only together"
        else:
            assert frames is None, "tmpl and frames can be used only together"

        self._structT = structT
        self._tmpl = tmpl
        self._frames = frames

    def parseTemplate(self):
        if self._tmpl is None:
            self._tmpl = TransTmpl(self._structT)

        if self._frames is None:
            DW = int(self.DATA_WIDTH)
            frames = FrameTmpl.framesFromTransTmpl(self._tmpl,
                                                   DW)
            self._frames = list(frames)

    def chainFrameWords(self):
        offset = 0
        for f in self._frames:
            wi = 0
            for last, (wi, w) in iter_with_last(f.walkWords(showPadding=True)):
                yield (offset + wi, w, last)
            offset += wi + 1


def HdlType_separate(t: HdlType, do_separate_query: Callable[[HdlType], bool])\
        -> Generator[Tuple[bool, HdlType], None, None]:
    """
    Split HStruct type hierachy on the specified fields to multiple
    type definitions.
    """
    sep = do_separate_query(t)
    if sep:
        yield (True, t)
    elif isinstance(t, HStruct):
        # fields which were generated by field spliting and are not yet in output HStruct
        leftovers = []
        any_split = False
        for f in t.fields:
            for separate_field, _t in HdlType_separate(f.dtype, do_separate_query):
                if t is f.dtype:
                    leftovers.append(f)
                else:
                    # the type was spltited somewhere
                    _f = copy(f)
                    _f.dtype = _t
                    if separate_field:
                        if leftovers:
                            new_t = HStruct(*leftovers, name=t.name)
                            yield (False, new_t)
                            leftovers.clear()
                        # create a new HStruct from previous fields
                        new_t = HStruct(_f, name=t.name)
                        leftovers.clear()
                        yield (True, new_t)
                        any_split = True
                    else:
                        leftovers.append(_f)
        if any_split:
            if leftovers:
                new_t = HStruct(*leftovers, name=t.name)
                yield (False, new_t)
        else:
            yield (False, t)

    else:
        yield (False, t)


def separate_streams(t: HdlType):
    """
    Split HStruct type hierarchy on the fields of HStream type.

    :note: e.g. in HStruct(
        (HStream(Bits(8)), "data"),
        (Bits(32), "fcs"),
        ) is split to HStruct((HStream(Bits(8)), "data"),) and
        HStruct((Bits(32), "fcs"),)
    """
    yield from HdlType_separate(t, lambda x: isinstance(x, HStream))


def to_primitive_stream_t(t: HdlType):
    """
    Convert type to a HStream of Bits
    With proper frame len, offset etc.
    """
    if isinstance(t, HStruct) and len(t.fields) == 1:
        return to_primitive_stream_t(t.fields[0].dtype)
    frame_len = (1, 1)
    start_offsets = [0, ]
    if isinstance(t, HStream):
        e_t = t.element_t
        if isinstance(e_t, Bits):
            return t
        else:
            frame_len = t.frame_len
            start_offsets = t.start_offsets
            t = e_t

    try:
        bit_len = t.bit_length()
    except TypeError:
        bit_len = None

    if bit_len is not None:
        return HStream(Bits(bit_len),
                       frame_len=frame_len,
                       start_offsets=start_offsets)
    else:
        raise NotImplementedError(t)
