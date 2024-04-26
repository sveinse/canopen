import logging
from typing import Union
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

from canopen import objectdictionary

logger = logging.getLogger(__name__)


class Variable:

    def __init__(self, od: objectdictionary.ODVariable):
        self.od = od
        #: Description of this variable from Object Dictionary, overridable
        self.name = od.name
        if isinstance(od.parent, (objectdictionary.ODRecord,
                                  objectdictionary.ODArray)):
            # Include the parent object's name for subentries
            self.name = od.parent.name + "." + od.name
        #: Holds a local, overridable copy of the Object Index
        self.index = od.index
        #: Holds a local, overridable copy of the Object Subindex
        self.subindex = od.subindex

    def get_data(self) -> bytes:
        """Byte representation of the object as :class:`bytes`."""
        raise NotImplementedError("Variable is not readable")

    async def aget_data(self) -> bytes:
        """Byte representation of the object as :class:`bytes`. Async variant."""
        raise NotImplementedError("Variable is not readable")

    def set_data(self, data: bytes):
        raise NotImplementedError("Variable is not writable")

    async def aset_data(self, data: bytes):
        raise NotImplementedError("Variable is not writable")

    @property
    def data(self) -> bytes:
        """Byte representation of the object as :class:`bytes`."""
        return self.get_data()

    @data.setter
    def data(self, data: bytes):
        """Set the variable data."""
        self.set_data(data)

    @property
    def raw(self) -> Union[int, bool, float, str, bytes]:
        """Raw representation of the object."""
        return self.get_raw()

    def get_raw(self) -> Union[int, bool, float, str, bytes]:
        """Raw representation of the object.

        This table lists the translations between object dictionary data types
        and Python native data types.

        +---------------------------+----------------------------+
        | Data type                 | Python type                |
        +===========================+============================+
        | BOOLEAN                   | :class:`bool`              |
        +---------------------------+----------------------------+
        | UNSIGNEDxx                | :class:`int`               |
        +---------------------------+----------------------------+
        | INTEGERxx                 | :class:`int`               |
        +---------------------------+----------------------------+
        | REALxx                    | :class:`float`             |
        +---------------------------+----------------------------+
        | VISIBLE_STRING            | :class:`str` /             |
        |                           | ``unicode`` (Python 2)     |
        +---------------------------+----------------------------+
        | UNICODE_STRING            | :class:`str` /             |
        |                           | ``unicode`` (Python 2)     |
        +---------------------------+----------------------------+
        | OCTET_STRING              | :class:`bytes`             |
        +---------------------------+----------------------------+
        | DOMAIN                    | :class:`bytes`             |
        +---------------------------+----------------------------+

        Data types that this library does not handle yet must be read and
        written as :class:`bytes`.
        """
        return self._get_raw(self.get_data())

    async def aget_raw(self) -> Union[int, bool, float, str, bytes]:
        """Raw representation of the object, async variant"""
        return self._get_raw(await self.aget_data())

    def _get_raw(self, data: bytes) -> Union[int, bool, float, str, bytes]:
        value = self.od.decode_raw(data)
        text = "Value of %s (0x%X:%d) is %r" % (
            self.name, self.index,
            self.subindex, value)
        if value in self.od.value_descriptions:
            text += " (%s)" % self.od.value_descriptions[value]
        logger.debug(text)
        return value

    @raw.setter
    def raw(self, value: Union[int, bool, float, str, bytes]):
        """Set the raw value of the object"""
        self.set_raw(value)

    def set_raw(self, value: Union[int, bool, float, str, bytes]):
        """Set the raw value of the object"""
        self.set_data(self._set_raw(value))

    async def aset_raw(self, value: Union[int, bool, float, str, bytes]):
        """Set the raw value of the object, async variant"""
        await self.aset_data(self._set_raw(value))

    def _set_raw(self, value: Union[int, bool, float, str, bytes]):
        logger.debug("Writing %s (0x%X:%d) = %r",
                     self.name, self.index,
                     self.subindex, value)
        return self.od.encode_raw(value)

    @property
    def phys(self) -> Union[int, bool, float, str, bytes]:
        """Physical value scaled with some factor (defaults to 1)."""
        return self.get_phys()

    def get_phys(self) -> Union[int, bool, float, str, bytes]:
        """Physical value scaled with some factor (defaults to 1).

        On object dictionaries that support specifying a factor, this can be
        either a :class:`float` or an :class:`int`.
        Non integers will be passed as is.
        """
        return self._get_phys(self.get_raw())

    async def aget_phys(self) -> Union[int, bool, float, str, bytes]:
        """Physical value scaled with some factor (defaults to 1), async variant."""
        return self._get_phys(await self.aget_raw())

    def _get_phys(self, raw: Union[int, bool, float, str, bytes]):
        value = self.od.decode_phys(raw)
        if self.od.unit:
            logger.debug("Physical value is %s %s", value, self.od.unit)
        return value

    @phys.setter
    def phys(self, value: Union[int, bool, float, str, bytes]):
        """Set the physical value."""
        self.set_phys(value)

    def set_phys(self, value: Union[int, bool, float, str, bytes]):
        """Set the physical value."""
        self.set_raw(self.od.encode_phys(value))

    async def aset_phys(self, value: Union[int, bool, float, str, bytes]):
        """Set the physical value, async variant."""
        await self.aset_raw(self.od.encode_phys(value))

    @property
    def desc(self) -> str:
        """Converts to and from a description of the value as a string."""
        return self.get_desc()

    def get_desc(self) -> str:
        """Converts to and from a description of the value as a string."""
        value = self.od.decode_desc(self.get_raw())
        logger.debug("Description is '%s'", value)
        return value

    async def aget_desc(self) -> str:
        """Converts to and from a description of the value as a string, async variant."""
        value = self.od.decode_desc(await self.aget_raw())
        logger.debug("Description is '%s'", value)
        return value

    @desc.setter
    def desc(self, desc: str):
        """Set description."""
        self.set_desc(desc)

    def set_desc(self, desc: str):
        """Set description."""
        self.set_raw(self.od.encode_desc(desc))

    async def aset_desc(self, desc: str):
        """Set description, async variant."""
        await self.aset_raw(self.od.encode_desc(desc))

    @property
    def bits(self) -> "Bits":
        """Access bits using integers, slices, or bit descriptions."""
        return self.get_bits()

    def get_bits(self) -> "Bits":
        """Access bits using integers, slices, or bit descriptions."""
        return Bits(self)

    def read(self, fmt: str = "raw") -> Union[int, bool, float, str, bytes]:
        """Alternative way of reading using a function instead of attributes.

        May be useful for asynchronous reading.

        :param str fmt:
            How to return the value
             - 'raw'
             - 'phys'
             - 'desc'

        :returns:
            The value of the variable.
        """
        if fmt == "raw":
            return self.get_raw()
        elif fmt == "phys":
            return self.get_phys()
        elif fmt == "desc":
            return self.get_desc()

    async def aread(self, fmt: str = "raw") -> Union[int, bool, float, str, bytes]:
        """Alternative way of reading using a function instead of attributes. Async variant."""
        if fmt == "raw":
            return await self.aget_raw()
        elif fmt == "phys":
            return await self.aget_phys()
        elif fmt == "desc":
            return await self.aget_desc()

    def write(
        self, value: Union[int, bool, float, str, bytes], fmt: str = "raw"
    ) -> None:
        """Alternative way of writing using a function instead of attributes.

        May be useful for asynchronous writing.

        :param str fmt:
            How to write the value
             - 'raw'
             - 'phys'
             - 'desc'
        """
        if fmt == "raw":
            self.set_raw(value)
        elif fmt == "phys":
            self.set_phys(value)
        elif fmt == "desc":
            self.set_desc(value)

    async def awrite(
        self, value: Union[int, bool, float, str, bytes], fmt: str = "raw"
    ) -> None:
        """Alternative way of writing using a function instead of attributes. Async variant"""
        if fmt == "raw":
            await self.aset_raw(value)
        elif fmt == "phys":
            await self.aset_phys(value)
        elif fmt == "desc":
            await self.aset_desc(value)


class Bits(Mapping):

    def __init__(self, variable: Variable):
        self.variable = variable
        self.read()

    @staticmethod
    def _get_bits(key):
        if isinstance(key, slice):
            bits = range(key.start, key.stop, key.step)
        elif isinstance(key, int):
            bits = [key]
        else:
            bits = key
        return bits

    def __getitem__(self, key) -> int:
        return self.variable.od.decode_bits(self.raw, self._get_bits(key))

    def __setitem__(self, key, value: int):
        self.raw = self.variable.od.encode_bits(
            self.raw, self._get_bits(key), value)
        self.write()

    def __iter__(self):
        return iter(self.variable.od.bit_definitions)

    def __len__(self):
        return len(self.variable.od.bit_definitions)

    def read(self):
        self.raw = self.variable.get_raw()

    def write(self):
        self.variable.set_raw(self.raw)
