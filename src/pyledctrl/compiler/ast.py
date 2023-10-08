"""Implementation of the abstract syntax tree into which the ``.led`` source
files are parsed before they are turned into bytecode.

The API of this module is inspired by (but is not an exact replica of) the
``ast`` module in Python.

The grammar modelled by this syntax tree can roughly be described in EBNF
syntax as follows (where the ``CommandCode.`` constants are considered
terminals and therefore are enclosed in quotes)::

    program = statement-sequence;
    statement-sequence = { statement | statement-sequence };
    statement = command
              | comment
              | loop-block;
    command = end-command
            | nop-command
            | sleep-command
            | wait-until-command
            | set-color-command
            | set-gray-command
            | set-black-command
            | set-white-command
            | fade-to-color-command
            | fade-to-gray-command
            | fade-to-black-command
            | fade-to-white-command
            | reset-timer-command
            | set-color-from-channels-command
            | fade-to-color-from-channels-command
            | jump-command
            | pyro-set-command
            | pyro-set-all-command;

    (* Declaration of a comment block *)
    comment = "";            (* resolves to empty bytecode *)

    (* Declarations of specific commands *)
    end-command = "CommandCode.END";
    nop-command = "CommandCode.NOP";
    sleep-command = "CommandCode.SLEEP", duration;
    wait-until-command = "CommandCode.WAIT_UNTIL", timestamp;
    set-color-command = "CommandCode.SET_COLOR", rgb-color, duration;
    set-gray-command = "CommandCode.SET_GRAY", gray-value, duration;
    set-black-command = "CommandCode.SET_BLACK", duration;
    set-white-command = "CommandCode.SET_WHITE", duration;
    fade-to-color-command = "CommandCode.FADE_TO_COLOR", rgb-color, duration;
    fade-to-gray-command = "CommandCode.FADE_TO_GRAY", gray-value, duration;
    fade-to-black-command = "CommandCode.FADE_TO_BLACK", duration;
    fade-to-white-command = "CommandCode.FADE_TO_WHITE", duration;
    reset-timer-command = "CommandCode.RESET_TIMER";
    set-color-from-channels-command = "CommandCode.SET_COLOR_FROM_CHANNELS",
                                      channel-index * 3, duration;
    fade-to-color-from-channels-command = "CommandCode.SET_COLOR_FROM_CHANNELS",
                                          channel-index * 3, duration;
    jump-command = "CommandCode.JUMP", address;
    set-pyro-command = "CommandCode.SET_PYRO", channel-mask;
    set-pyro-all-command = "CommandCode.SET_PYRO_ALL", channel-values;

    (* Loop blocks *)
    loop-block = iterations, statement-sequence;

    (* Not-so-basic types *)
    address = varuint;
    channel-index = unsigned-byte;
    channel-mask = unsigned-byte;
    channel-values = unsigned-byte;
    duration = varuint;
    gray-value = unsigned-byte;
    iterations = unsigned-byte;
    rgb-color = unsigned-byte, unsigned-byte, unsigned-byte;

    (* Basic types *)
    unsigned-byte = ? numeric value between 0 and 255 (inclusive) ?
    varint = ? varint-encoded representation of a signed integer ?
    varuint = ? varint-encoded representation of an unsigned integer ?
"""

from decimal import Decimal, Inexact, getcontext
from io import BufferedReader
from struct import Struct
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    IO,
    Iterable,
    Generator,
    Generic,
    Optional,
    List,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from warnings import warn

from pyledctrl.utils import first, to_varuint

from .colors import Color
from .errors import BytecodeParserError, BytecodeParserEOFError


class CommandCode:
    """Constants corresponding to the various raw bytecode commands in
    ``ledctrl``'s bytecode.
    """

    END = b"\x00"
    """End of bytecode."""

    NOP = b"\x01"
    """Empty operation, do nothing."""

    SLEEP = b"\x02"
    """Sleep for a given number of frames."""

    WAIT_UNTIL = b"\x03"
    """Wait until the internal clock reaches the given number of frames."""

    SET_COLOR = b"\x04"
    """Set the output RGB color to a given color, then wait for a given number
    of frames.
    """

    SET_GRAY = b"\x05"
    """Set the output RGB color to a given shade of gray, then wait for a given
    number of frames.
    """

    SET_BLACK = b"\x06"
    """Set the output RGB color to black, then wait for a given number of frames.
    """

    SET_WHITE = b"\x07"
    """Set the output RGB color to white, then wait for a given number of frames.
    """

    FADE_TO_COLOR = b"\x08"
    """Fade the current color to the given RGB color over a specified time
    interval.
    """

    FADE_TO_GRAY = b"\x09"
    """Fade the current color to the given shade of gray over a specified time
    interval.
    """

    FADE_TO_BLACK = b"\x0A"
    """Fade the current color to black over a specified time interval."""

    FADE_TO_WHITE = b"\x0B"
    """Fade the current color to white over a specified time interval."""

    LOOP_BEGIN = b"\x0C"
    """Marks the beginning of a loop, followed by an iteration count."""

    LOOP_END = b"\x0D"
    """Marks the end of a loop."""

    RESET_TIMER = b"\x0E"
    """Resets the internal timer to zero."""

    SET_COLOR_FROM_CHANNELS = b"\x10"
    """Sets the current color from some input RC channels."""

    FADE_TO_COLOR_FROM_CHANNELS = b"\x11"
    """Fades the current color to the current values of some input RC channels."""

    JUMP = b"\x12"
    """Jump to a given address in the bytecode."""

    TRIGGERED_JUMP = b"\x13"
    """Jump to a given address in the bytecode when a specified condition happens."""

    SET_PYRO = b"\x14"
    """Sets the output value of a pyro/relay channel to a given value (same value
    for all channels).
    """

    SET_PYRO_ALL = b"\x15"
    """Sets the output value of all pyro/relay channels explicitly to a given
    value.
    """


T = TypeVar("T")


class _NodeMeta(type):
    """Metaclass for AST nodes.

    This metaclass adds the following functionality to node classes
    automatically if the class has a ``_fields`` property that describes the
    fields of the node and optionally a ``_defaults`` property that contains
    the default value for some or all of the fields, and an ``_immutable``
    property that contains the names of the fields that are immutable.

        - Creates an ``__init__`` method that accepts the fields as positional
          or keyword arguments and throws an exception if fields without
          default values are not initialized.

    The ``_defaults`` property must be a dictionary mapping field names to
    either immutable objects or factory functions that create default values.
    When the factory function is a subclass of ``Literal``, the metaclass
    also provides a convenient setter for the corresponding field that wraps
    the incoming value in the appropriate literal type.
    """

    def __new__(cls, name: str, parents, dct):
        fields = dct.get("_fields")
        defaults = dct.get("_defaults")
        immutables = dct.get("_immutable")
        if "__init__" not in dct:
            dct["__init__"] = cls._create_init_method(parents, fields, defaults)
        cls._add_setters_for_literals(defaults, dct, immutables, name)
        return super().__new__(cls, name, parents, dct)

    @classmethod
    def _add_setters_for_literals(cls, defaults, dct, immutables, name: str):
        if not defaults:
            return
        immutables = frozenset(immutables or [])
        for field, default in defaults.items():
            if field in dct:
                continue

            if field in immutables:
                dct[field] = cls._add_getter_for_immutable_field(field)
            elif issubclass(default, Literal):
                dct[field] = cls._add_setter_for_literal(field, default)

    @classmethod
    def _add_getter_for_immutable_field(cls, field: str) -> property:
        field_var = "_" + field

        def getter(self):
            return getattr(self, field_var)

        return property(getter)

    @classmethod
    def _add_setter_for_literal(cls, field: str, literal_type: type) -> property:
        field_var = "_" + field

        def getter(self):
            return getattr(self, field_var)

        def setter(self, value):
            if not isinstance(value, literal_type):
                value = literal_type(value)
            setattr(self, field_var, value)

        return property(getter, setter)

    @classmethod
    def _create_init_method(
        cls,
        parents,
        fields: Optional[Sequence[str]],
        defaults: Optional[Dict[str, Any]],
    ) -> Callable[..., None]:
        if fields is None:
            # Class should be abstract
            def __init__(self, *args, **kwds):  # type: ignore
                raise NotImplementedError("this node type is abstract")

            return __init__

        # Class is not abstract, so we need a real constructor
        node_superclass = first(
            parent for parent in parents if issubclass(parent, Node)
        )
        node_superclass_is_abstract = not hasattr(node_superclass, "_fields")
        num_fields = len(fields)

        def __init__(self, *args, **kwds):
            if not node_superclass_is_abstract:
                node_superclass.__init__(self)
            if args:
                if num_fields < len(args):
                    raise TypeError(
                        "__init__() takes at most {0} "
                        "arguments ({1} given)".format(num_fields, len(args))
                    )
                for arg_name, arg in zip(fields, args):
                    setattr(self, arg_name, arg)
            if kwds:
                for arg_name, arg in kwds.items():
                    if arg_name not in fields:
                        raise TypeError(
                            "__init__() got an unexpected keyword "
                            "argument: {0!r}".format(arg_name)
                        )
                    setattr(self, arg_name, arg)
            if defaults:
                for arg_name, arg in defaults.items():
                    if not hasattr(self, arg_name):
                        if callable(arg):
                            arg = arg()
                        setattr(self, arg_name, arg)
            for arg_name in fields:
                if not hasattr(self, arg_name):
                    raise TypeError(
                        "__init__() did not receive an initial "
                        "value for field {0!r}".format(arg_name)
                    )

        return __init__


class Node(metaclass=_NodeMeta):
    """Base class for nodes in the abstract syntax tree."""

    _fields: ClassVar[Sequence[str]]

    def iter_child_nodes(self) -> Iterable["Node"]:
        """Returns an iterator that yields all field values that are subclasses
        of nodes. When a field maps to a list of nodes, yields all the nodes
        in the list.
        """
        for name in self._fields:
            value = getattr(self, name)
            if isinstance(value, Node):
                yield value
            elif isinstance(value, NodeList):
                for node in value:
                    yield node

    def iter_fields(self) -> Iterable[Tuple[str, Any]]:
        """Returns an iterator that yields ``(field_name, field_value)`` pairs
        for each field of the node.
        """
        for name in self._fields:
            yield name, getattr(self, name)

    def iter_field_values(self) -> Iterable[Any]:
        """Returns an iterator that yields the values of each field of the node,
        in the order defined in the ``_fields`` property.
        """
        for name in self._fields:
            yield getattr(self, name)

    @property
    def length_in_bytes(self) -> int:
        """Returns the length of the node when it is converted into bytecode.
        The default implementation calls ``to_bytecode`` and returns the length
        of the generated bytecode, but you should override it in subclasses
        where possible to make the method more efficient.
        """
        return len(self.to_bytecode())

    def to_bytecode(self) -> bytes:
        """Converts the node into bytecode.

        Returns:
            the bytecode representation of the node
        """
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Converts the node into a dictionary representation that maps the
        names of the children of the node into the corresponding values.
        Works only for concrete nodes where the ``_fields`` class variable
        is defined.
        """
        return dict(self.iter_fields())

    def to_led_source(self) -> str:
        """Converts the node back into the ``.led`` source format.

        Returns:
            the ``.led`` source format representation of the node
        """
        raise NotImplementedError

    def to_pickle(self) -> bytes:
        """Converts the node into a Python pickle.

        Returns:
            a Python pickle representing the node
        """
        from pickle import dumps

        return dumps(self)

    def transform_child_nodes(self) -> Generator["Node", Optional["Node"], None]:
        """Returns a generator that yields all field values that are subclasses
        of nodes and allows the user to replace the nodes with transformed ones
        by sending the new node back into the generator. Sending ``None`` back
        would remove the node.

        When a field maps to a list of nodes, yields all the nodes in the list.
        """
        for name in self._fields:
            value = getattr(self, name)
            if isinstance(value, Node):
                new_value = yield value
                if new_value is not value:
                    setattr(self, name, new_value)
            elif isinstance(value, NodeList):
                index, length = 0, len(value)
                while index < length:
                    old_node = value[index]
                    if isinstance(old_node, Node):
                        new_node = yield old_node
                    else:
                        new_node = old_node
                    if new_node is None:
                        del value[index]
                        length -= 1
                    elif new_node is old_node:
                        index += 1
                    else:
                        value[index] = new_node
                        index += 1

    def __getstate__(self):
        return tuple(getattr(self, arg_name) for arg_name in self._fields)

    def __setstate__(self, state):
        for arg_name, value in zip(self._fields, state):
            try:
                setattr(self, arg_name, value)
            except AttributeError:
                # maybe immutable?
                setattr(self, "_" + arg_name, value)

    def __repr__(self) -> str:
        kvpairs = [
            "{0}={1!r}".format(arg_name, getattr(self, arg_name))
            for arg_name in self._fields
        ]
        return "{0.__class__.__name__}({1})".format(self, ", ".join(kvpairs))


class NodeList(List[Node]):
    """Subclass of list that adds no extra functionality but allows us to
    detect objects that are meant to hold lists of AST nodes.
    """

    pass


class Literal(Node):
    """Base class for literal nodes."""

    pass


class Byte(Literal):
    """Node that represents a signed or unsigned single-byte literal value."""

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return 1


class UnsignedByte(Byte):
    """Node that represents an unsigned single-byte literal value (such as a
    component of an RGB color that is stored on a single byte).
    """

    _fields = ("value",)
    _defaults = {"value": 0}

    _value: int

    @classmethod
    def from_bytecode(cls, data: IO[bytes]):
        """Reads an UnsignedByte from a binary file-like object.

        Parameters:
            data: the stream to read from

        Returns:
            UnsignedByte: the constructed object
        """
        value = data.read(1)
        if not value:
            raise BytecodeParserEOFError(cls)
        return cls(value=ord(value))

    def __init__(self, value: int = 0):
        """Constructor.

        Parameters:
            value: the value of the literal
        """
        self._set_value(value)

    def equals(self, other: "UnsignedByte"):
        """Compares this byte with another byte to decide whether they
        are the same.
        """
        return self._value == other._value

    def to_bytecode(self):
        return bytes([self.value])

    def to_led_source(self):
        return str(self.value)

    @property
    def value(self):
        return self._value

    def _set_value(self, value: Union[int, "UnsignedByte"]) -> None:
        if isinstance(value, UnsignedByte):
            value = value.value
            assert isinstance(value, int)
        if value < 0 or value > 255:
            raise ValueError("value must be between 0 and 255 (inclusive)")
        self._value = value


class Varuint(Literal):
    """Node that represents an unsigned varint-encoded literal value."""

    _fields = ("value",)
    _defaults = {"value": 0}
    _immutable = _fields

    _value: int
    _bytecode: bytes

    @classmethod
    def from_bytecode(cls, data: IO[bytes]):
        """Reads a Varuint from a binary file-like object.

        Parameters:
            data: the stream to read from

        Returns:
            the constructed object
        """
        value = 0
        shift = 0
        while True:
            x = data.read(1)
            if not x:
                raise BytecodeParserEOFError(cls)

            x = ord(x)
            value |= (x & 0x7F) << shift
            shift += 7

            if x < 128:
                break

        return cls(value)

    def __init__(self, value=0):
        self._set_value(int(value))
        self._bytecode = to_varuint(value)

    def equals(self, other: "Varuint"):
        """Compares this varuint with another varuint to decide whether they
        are the same.
        """
        return self._value == other._value

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return len(self._bytecode)

    def to_bytecode(self):
        return self._bytecode

    def to_led_source(self):
        return str(self.value)

    @property
    def value(self):
        return self._value

    def _set_value(self, value: int) -> None:
        if value < 0:
            raise ValueError("value must be non-negative")
        elif value >= 2**28:
            raise ValueError(
                "varuints greater than 2**28 are not supported by the bytecode"
            )
        self._value = value


class ChannelMask(Byte):
    """Literal that represents the channel mask of a SET_PYRO command."""

    _fields = ("enable", "channels")
    _defaults = {"enable": False, "channels": ()}
    _immutable = _fields

    enable: bool
    """Whether to enable or disable the channels in the mask."""

    channels: FrozenSet[int]
    """Indices of the channels to enable or disable."""

    @classmethod
    def from_bytecode(cls, data: IO[bytes]):
        """Parses a ChannelMask object from its bytecode representation.

        Parameters:
            data: the stream to read from

        Returns:
            the constructed object
        """
        value = data.read(1)
        if not value:
            raise BytecodeParserEOFError(cls)

        channels = []
        value = ord(value)
        for index in range(7):
            if value & (1 << index):
                channels.append(index)

        return cls(enable=bool(value & 0x80), channels=tuple(channels))

    def __init__(self, enable: bool = False, channels: Iterable[int] = ()):
        """Constructor.

        Parameters:
            enable: whether to enable or disable the channels in the mask
            channels: collection of channel indices that are present in the mask
        """
        self._enable = bool(enable)
        self._set_channels(channels)

    def equals(self, other: "ChannelMask") -> bool:
        """Compares this byte with another byte to decide whether they
        are the same.
        """
        return self._enable == other._enable and self._channels == other._channels

    def _to_byte(self) -> int:
        result = 0
        for bit in self._channels:
            result |= 1 << bit
        return (result & 127) + (128 if self._enable else 0)

    def to_bytecode(self):
        return bytes([self._to_byte()])

    def to_led_source(self):
        if len(self._channels) == 1:
            return str(tuple(self._channels)[0])
        else:
            return str(tuple(sorted(self._channels)))[1:-1]

    def _set_channels(self, value: Iterable[int]) -> None:
        if any(ch < 0 or ch > 6 for ch in value):
            raise ValueError("channel indices must be between 0 and 6 (inclusive)")
        self._channels = frozenset(value)


class ChannelValues(Byte):
    """Literal that represents the channel value byte of a SET_PYRO_ALL
    command.
    """

    _fields = ("channels",)
    _defaults = {"channels": ()}

    @classmethod
    def from_bytecode(cls, data: IO[bytes]):
        """Parses a ChannelValues object from its bytecode representation.

        Parameters:
            data: the stream to read from

        Returns:
            the constructed object
        """
        value = data.read(1)
        if not value:
            raise BytecodeParserEOFError(cls)

        channels = []
        value = ord(value)
        for index in range(7):
            if value & (1 << index):
                channels.append(index)

        return cls(tuple(channels))

    def __init__(self, channels: Iterable[int] = ()):
        """Constructor.

        Parameters:
            channels (Iterable[int]): collection of channel indices that are
                set to 1 after the execution of the SET_PYRO_ALL command; the
                rest are set to zero.
        """
        self._set_channels(channels)

    def equals(self, other: "ChannelValues") -> bool:
        """Compares this byte with another byte to decide whether they
        are the same.
        """
        return self._channels == other._channels

    def _to_byte(self) -> int:
        result = 0
        for bit in self._channels:
            result |= 1 << bit
        return result & 127

    def to_bytecode(self):
        return bytes([self._to_byte()])

    def to_led_source(self):
        if len(self._channels) != 1:
            return str(tuple(sorted(self._channels)))[1:-1]
        else:
            return str(list(self._channels)[0])

    @property
    def channels(self):
        return self._channels

    def _set_channels(self, value: Iterable[int]) -> None:
        if any(ch < 0 or ch > 6 for ch in value):
            raise ValueError("channel indices must be between 0 and 6 (inclusive)")
        self._channels = frozenset(value)


class RGBColor(Node):
    """Node that represents an RGB color."""

    _fields = ("red", "green", "blue")
    _defaults = {"red": UnsignedByte, "green": UnsignedByte, "blue": UnsignedByte}
    _immutable = _fields

    _instance_cache: ClassVar[Dict[Color, "RGBColor"]] = {}
    _struct: ClassVar[Struct] = Struct("BBB")

    red: UnsignedByte
    green: UnsignedByte
    blue: UnsignedByte

    def __init__(self, red: int, green: int, blue: int):
        self._red = UnsignedByte(red)
        self._green = UnsignedByte(green)
        self._blue = UnsignedByte(blue)

    @classmethod
    def cached(cls, red: int, green: int, blue: int):
        key = red, green, blue
        result = cls._instance_cache.get(key)
        if result is None:
            cls._instance_cache[key] = result = cls(red, green, blue)
        return result

    def equals(self, other: "RGBColor"):
        """Compares this color with another RGBColor to decide whether they
        are the same.
        """
        return (
            self._red.value == other._red.value
            and self._green.value == other._green.value
            and self._blue.value == other._blue.value
        )

    @property
    def is_black(self):
        """Returns ``True`` if the color is black."""
        return self._red.value == 0 and self._green.value == 0 and self._blue.value == 0

    @property
    def is_gray(self):
        """Returns ``True`` if the color is a shade of gray."""
        return (
            self._red.value == self._green.value
            and self._green.value == self._blue.value
        )

    @property
    def is_white(self):
        """Returns ``True`` if the color is white."""
        return (
            self._red.value == 255
            and self._green.value == 255
            and self._blue.value == 255
        )

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return 3

    def to_bytecode(self):
        return self._struct.pack(self.red.value, self.green.value, self.blue.value)

    def to_led_source(self):
        return "{0}, {1}, {2}".format(
            self.red.to_led_source(),
            self.green.to_led_source(),
            self.blue.to_led_source(),
        )


class Duration(Varuint):
    """Node that represents a duration (or a timestamp)."""

    _fields = Varuint._fields
    _instance_cache: ClassVar[Dict[int, "Duration"]] = {}

    FPS: ClassVar[Decimal] = Decimal(50)

    def __init__(self, value: int = 0):
        # Don't remove this constructor -- it prevents NodeMeta from generating
        # one for Duration
        super().__init__(value)

    @classmethod
    def from_frames(cls, frames: int):
        result = cls._instance_cache.get(frames)
        if result is None:
            result = cls(value=frames)
            cls._instance_cache[frames] = result
        return result

    @classmethod
    def from_seconds(cls, seconds: float):
        # Okay, this is tricky. First of all, multiplication between a
        # Decimal and a float is not supported, so we need to convert
        # float seconds into Decimal as well. However, check this:
        #
        # >>> Decimal(0.2) * Decimal(50)
        # Decimal('10.00000000000000055511151231')
        #
        # This is not what we want, but this is what we get because 0.2
        # cannot be represented exactly as a float, so _internally_ it
        # is stored as 0.200000000000000011102230246251565404236316680908203125.
        # But we can cast the float value into a string, which rounds it off
        # nicely, and then we can pass it to the Decimal() constructor.

        if seconds is None:
            seconds = 0

        seconds_as_str = Decimal(str(seconds))
        frame_count = seconds_as_str * cls.FPS
        getcontext().clear_flags()
        frame_count_as_int = int(frame_count.to_integral_exact())
        if getcontext().flags[Inexact]:
            warn(
                "Cannot convert {0} seconds into an integer number of frames "
                "at {1} FPS; this could be a problem in the ledctrl output".format(
                    seconds, cls.FPS
                ),
                stacklevel=1,
            )

        return cls.from_frames(frame_count_as_int)

    @property
    def value_in_frames(self):
        return self.value

    @property
    def value_in_seconds(self):
        return self.value / self.FPS

    def to_bytecode(self):
        return to_varuint(int(self.value))

    def to_led_source(self):
        return str(self.value_in_seconds)


class StatementSequence(Node):
    """Node that represents a sequence of statements."""

    _fields = ["statements"]
    _defaults = {"statements": NodeList}

    statements: NodeList

    @classmethod
    def from_bytecode(cls, data: BufferedReader):
        """Parses a StatementSequence object from its bytecode representation.

        Parameters:
            data: the stream to read from

        Returns:
            the constructed object
        """
        result = cls()

        while True:
            node = _parse_statement_from_bytecode(data)
            if node is None:
                break

            result.append(node)

        return result

    def append(self, node: Node) -> None:
        """Appends a node to the sequence."""
        self.statements.append(node)

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return sum(node.length_in_bytes for node in self.statements)

    def to_bytecode(self):
        return b"".join(node.to_bytecode() for node in self.statements)

    def to_led_source(self):
        return "\n".join(statement.to_led_source() for statement in self.statements)


class Statement(Node):
    """Node that represents a single statement (e.g., a bytecode command or
    a loop block)."""

    def is_equivalent_to(self, other: Node) -> bool:
        """Returns whether this statement is semantically equivalent to
        some other statement.
        """
        return self is other or (
            self.__class__ is other.__class__ and self._is_equivalent_to_inner(other)
        )

    def _is_equivalent_to_inner(self, other: Node):
        """Compares two statements of *exactly* the same class to decide
        whether they are semantically equivalent.

        This class is meant to be overridden in subclasses. The default
        implementation compares the bytecode of the statements.
        """
        return self.to_bytecode() == other.to_bytecode()


class Comment(Statement):
    """Node that represents a comment (i.e. a string that appears in the
    Python representation of the AST but is replaced by an empty byte
    sequence in the bytecode)."""

    _fields = ("value",)

    value: str

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return 0

    def to_bytecode(self):
        return b""

    def to_led_source(self):
        return "\n{0}\ncomment({1!r})\n{0}\n".format("#" * 76, self.value)


class Command(Statement):
    """Node that represents a single bytecode command."""

    code: ClassVar[bytes]
    """The code of this command; must be declared in subclasses."""

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return sum((field.length_in_bytes for field in self.iter_field_values()), 1)

    def to_bytecode(self):
        parts = [self.code]
        parts.extend(field.to_bytecode() for field in self.iter_field_values())
        return b"".join(parts)


class EndCommand(Command):
    """Node that represents the ``END`` command in the bytecode."""

    code = CommandCode.END
    _fields = ()

    def to_led_source(self):
        return "end()"


class NopCommand(Command):
    """Node that represents a ``NOP`` command in the bytecode."""

    code = CommandCode.NOP
    _fields = ()

    def to_led_source(self):
        return "nop()"


class SleepCommand(Command):
    """Node that represents a ``SLEEP`` command in the bytecode."""

    code = CommandCode.SLEEP
    _fields = ("duration",)
    _defaults = {"duration": Duration}

    duration: Duration

    def to_led_source(self):
        return "sleep(duration={0})".format(self.duration.to_led_source())


class WaitUntilCommand(Command):
    """Node that represents a ``WAIT_UNTIL`` command in the bytecode."""

    code = CommandCode.WAIT_UNTIL
    _fields = ("timestamp",)
    _defaults = {"timestamp": Duration}

    timestamp: Duration

    def to_led_source(self):
        return "wait_until(timestamp={0})".format(self.timestamp.to_led_source())


class SetColorCommand(Command):
    """Node that represents a ``SET_COLOR`` command in the bytecode."""

    code = CommandCode.SET_COLOR
    _fields = ("color", "duration")
    _defaults = {"color": RGBColor, "duration": Duration}
    _immutable = _fields

    color: RGBColor
    duration: Duration

    def __init__(self, color: RGBColor, duration: Union[int, Duration]):
        assert isinstance(color, RGBColor)
        assert isinstance(duration, Duration)
        self._color = color
        self._duration = duration

    def _is_equivalent_to_inner(self, other: "SetColorCommand"):
        return self._color.equals(other._color) and self._duration.equals(
            other._duration
        )

    def to_led_source(self):
        return "set_color({0}, duration={1})".format(
            self.color.to_led_source(), self.duration.to_led_source()
        )


class SetGrayCommand(Command):
    """Node that represents a ``SET_GRAY`` command in the bytecode."""

    code = CommandCode.SET_GRAY
    _fields = ("value", "duration")
    _defaults = {"value": UnsignedByte, "duration": Duration}

    value: UnsignedByte
    duration: Duration

    def _is_equivalent_to_inner(self, other: "SetGrayCommand"):
        return self.value.equals(other.value) and self.duration.equals(other.duration)

    def to_led_source(self):
        return "set_gray({0}, duration={1})".format(
            self.value.to_led_source(), self.duration.to_led_source()
        )


class SetBlackCommand(Command):
    """Node that represents a ``SET_BLACK`` command in the bytecode."""

    code = CommandCode.SET_BLACK
    _fields = ("duration",)
    _defaults = {"duration": Duration}

    duration: Duration

    def _is_equivalent_to_inner(self, other: "SetBlackCommand"):
        return self.duration.equals(other.duration)

    def to_led_source(self):
        return "set_black(duration={0})".format(self.duration.to_led_source())


class SetWhiteCommand(Command):
    """Node that represents a ``SET_WHITE`` command in the bytecode."""

    code = CommandCode.SET_WHITE
    _fields = ("duration",)
    _defaults = {"duration": Duration}

    duration: Duration

    def _is_equivalent_to_inner(self, other: "SetWhiteCommand"):
        return self.duration.equals(other.duration)

    def to_led_source(self):
        return "set_white(duration={0})".format(self.duration.to_led_source())


class FadeToColorCommand(Command):
    """Node that represents a ``FADE_TO_COLOR`` command in the bytecode."""

    code = CommandCode.FADE_TO_COLOR
    _fields = ("color", "duration")
    _defaults = {"color": RGBColor, "duration": Duration}
    _immutable = _fields

    color: RGBColor
    duration: Duration

    def __init__(self, color, duration):
        assert isinstance(color, RGBColor)
        assert isinstance(duration, Duration)
        self._color = color
        self._duration = duration

    def _is_equivalent_to_inner(self, other: "FadeToColorCommand"):
        return self._color.equals(other._color) and self._duration.equals(
            other._duration
        )

    def to_led_source(self):
        return "fade_to_color({0}, duration={1})".format(
            self.color.to_led_source(), self.duration.to_led_source()
        )


class FadeToGrayCommand(Command):
    """Node that represents a ``FADE_TO_GRAY`` command in the bytecode."""

    code = CommandCode.FADE_TO_GRAY
    _fields = ("value", "duration")
    _defaults = {"value": UnsignedByte, "duration": Duration}

    value: UnsignedByte
    duration: Duration

    def _is_equivalent_to_inner(self, other: "FadeToGrayCommand"):
        return self.value.equals(other.value) and self.duration.equals(other.duration)

    def to_led_source(self):
        return "fade_to_gray({0}, duration={1})".format(
            self.value.to_led_source(), self.duration.to_led_source()
        )


class FadeToBlackCommand(Command):
    """Node that represents a ``FADE_TO_BLACK`` command in the bytecode."""

    code = CommandCode.FADE_TO_BLACK
    _fields = ("duration",)
    _defaults = {"duration": Duration}

    duration: Duration

    def _is_equivalent_to_inner(self, other: "FadeToBlackCommand"):
        return self.duration.equals(other.duration)

    def to_led_source(self):
        return "fade_to_black(duration={0})".format(self.duration.to_led_source())


class FadeToWhiteCommand(Command):
    """Node that represents a ``FADE_TO_WHITE`` command in the bytecode."""

    code = CommandCode.FADE_TO_WHITE
    _fields = ("duration",)
    _defaults = {"duration": Duration}

    duration: Duration

    def _is_equivalent_to_inner(self, other: "FadeToWhiteCommand"):
        return self.duration.equals(other.duration)

    def to_led_source(self):
        return "fade_to_white(duration={0})".format(self.duration.to_led_source())


class ResetTimerCommand(Command):
    """Node that represents the ``RESET_TIMER`` command in the bytecode."""

    code = CommandCode.RESET_TIMER
    _fields = ()


class SetColorFromChannelsCommand(Command):
    """Node that represents a ``SET_COLOR_FROM_CHANNELS`` command in the
    bytecode."""

    code = CommandCode.SET_COLOR_FROM_CHANNELS
    _fields = ("red_channel", "green_channel", "blue_channel", "duration")
    _defaults = {
        "red_channel": UnsignedByte,
        "green_channel": UnsignedByte,
        "blue_channel": UnsignedByte,
        "duration": Duration,
    }

    red_channel: UnsignedByte
    green_channel: UnsignedByte
    blue_channel: UnsignedByte
    duration: Duration


class FadeToColorFromChannelsCommand(Command):
    """Node that represents a ``FADE_TO_COLOR_FROM_CHANNELS`` command in the
    bytecode."""

    code = CommandCode.FADE_TO_COLOR_FROM_CHANNELS
    _fields = ("red_channel", "green_channel", "blue_channel", "duration")
    _defaults = {
        "red_channel": UnsignedByte,
        "green_channel": UnsignedByte,
        "blue_channel": UnsignedByte,
        "duration": Duration,
    }

    red_channel: UnsignedByte
    green_channel: UnsignedByte
    blue_channel: UnsignedByte
    duration: Duration


class JumpCommand(Command):
    """Node that represents a ``JUMP`` command in the bytecode."""

    code = CommandCode.JUMP
    _fields = ("address",)
    _defaults = {"address": Varuint}

    address: Varuint


class SetPyroCommand(Command):
    """Node that represents a ``SET_PYRO`` command in the bytecode."""

    code = CommandCode.SET_PYRO
    _fields = ("mask",)
    _defaults = {"mask": ChannelMask}
    _immutable = _fields

    mask: ChannelMask

    def __init__(self, mask: ChannelMask):
        assert isinstance(mask, ChannelMask)
        self._mask = mask

    def _is_equivalent_to_inner(self, other: "SetPyroCommand"):
        return self._mask.equals(other._mask)

    def to_led_source(self):
        bits = self.mask.to_led_source()
        if self.mask.enable:
            return "pyro_enable({0})".format(bits)
        else:
            return "pyro_disable({0})".format(bits)


class SetPyroAllCommand(Command):
    """Node that represents a ``SET_PYRO_ALL`` command in the bytecode."""

    code = CommandCode.SET_PYRO_ALL
    _fields = ("values",)
    _defaults = {"values": ChannelValues}
    _immutable = _fields

    values: ChannelValues

    def __init__(self, values: ChannelValues):
        assert isinstance(values, ChannelValues)
        self._values = values

    def _is_equivalent_to_inner(self, other: "SetPyroAllCommand"):
        return self._values.equals(other._values)

    def to_led_source(self):
        value = self._values.to_led_source()
        if value:
            return "pyro_set_all({0})".format(value)
        else:
            return "pyro_clear()"


class LoopBlock(Statement):
    """Node that represents a loop in the bytecode."""

    _fields = ("iterations", "body")
    _defaults = {"iterations": UnsignedByte, "body": StatementSequence}

    iterations: UnsignedByte
    body: StatementSequence

    @classmethod
    def from_bytecode(cls, data: BufferedReader):
        """Reads a LoopBlock from a binary file-like object.

        Parameters:
            data: the stream to read from

        Returns:
            LoopBlock: the constructed object
        """
        code = data.read(1)
        if not code:
            raise BytecodeParserEOFError(cls)

        if code != CommandCode.LOOP_BEGIN:
            raise ValueError("LoopBlock must start with CommandCode.LOOP_BEGIN")

        iterations = UnsignedByte.from_bytecode(data)
        body = StatementSequence.from_bytecode(data)

        code = data.read(1)
        if not code:
            raise BytecodeParserEOFError(cls)

        if code != CommandCode.LOOP_END:
            raise ValueError("LoopBlock must end with CommandCode.LOOP_END")

        return cls(iterations=iterations, body=body)

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        if not self.body.statements or self.iterations.value <= 0:
            return 0
        body_length = sum(node.length_in_bytes for node in self.body.statements)
        if self.iterations.value == 1:
            return body_length
        else:
            return body_length + 2 + self.iterations.length_in_bytes

    def to_bytecode(self):
        if not self.body.statements or self.iterations.value < 0:
            return b""

        body = b"".join(node.to_bytecode() for node in self.body.statements)
        if self.iterations.value == 1:
            return body
        else:
            return (
                CommandCode.LOOP_BEGIN
                + self.iterations.to_bytecode()
                + body
                + CommandCode.LOOP_END
            )

    def to_led_source(self):
        if not self.body.statements or self.iterations.value < 0:
            return ""

        body = self.body.to_led_source()
        if self.iterations.value == 1:
            return body
        else:
            body = body.replace("\n", "\n    ")
        return "with loop(iterations={0}):\n    {1}".format(self.iterations, body)


class NodeVisitor(Generic[T]):
    """Base class for node visitors that walk the abstract syntax tree in a
    top-down manner and call a visitor function for every node found.

    This class is meant to be subclassed; subclasses should add or override
    visitor methods.
    """

    _dispatch_table: Dict[Type[Node], Callable[[Node], T]]

    def __init__(self):
        self._dispatch_table = {}

    def generic_visit(self, node: Node) -> None:
        """This visitor method is called for nodes for which no specific
        visitor method of the form ``self.visit_{classname}`` exists in this
        class. The default implementation of this method simply calls
        ``visit()`` on all children of the node.

        Note that if you specify your custom visitor for a node, the
        generic visitor will *not* be called by default and the children
        of the node will *not* be visited. You must call ``generic_visit()``
        explicitly if you want to visit the children."""
        if isinstance(node, Node):
            for child_node in node.iter_child_nodes():
                self._visit(child_node)

    def visit(self, node: Node) -> T:
        """Visits the given node in the abstract syntax tree. The default
        implementation calls ``self.visit_{classname}`` where ``{classname}``
        is the name of the node class, or ``self.generic_visit()`` if a
        node-specific visitor method does not exist.

        Returns:
            whatever the visitor method returns.
        """
        return self._visit(node)

    def _find_visitor_method(self, node: Node) -> Callable[[Node], T]:
        """Finds an appropriate visitor method within this instance for the
        given node. By default, this function will look for a method named
        ``visit_{classname}`` in ``self`` and fall back to ``generic_visit``
        if such a method does not exist.

        Parameters:
            node: the node to visit

        Returns:
            callable: an appropriate visitor method for the node
        """
        method_name = "visit_{0}".format(node.__class__.__name__)
        return getattr(self, method_name, None) or self.generic_visit

    def _get_visitor_method(self, node: Node) -> Callable[[Node], T]:
        """Returns the visitor method corresponding to the given node."""
        cls = node.__class__
        func = self._dispatch_table.get(cls)
        if func is None:
            func = self._dispatch_table[cls] = self._find_visitor_method(node)
        return func

    def _visit(self, node: Node) -> T:
        return self._get_visitor_method(node)(node)


class NodeTransformer(NodeVisitor[Optional[Node]]):
    """A ``NodeVisitor`` subclass that assumes that the visitor methods return
    an AST node or ``None``. When ``None`` is returned, the visited node is
    removed from the tree. When an AST node is returned, the visited node is
    replaced by the returned AST node (which may of course be the same as the
    original visited node).
    """

    changed: bool

    def __init__(self):
        super().__init__()
        self.changed = False

    def generic_visit(self, node: Node) -> Optional[Node]:
        """This visitor method is called for nodes for which no specific
        visitor method of the form ``self.visit_{classname}`` exists in this
        class. The default implementation of this method simply calls
        ``visit()`` on all children of the node.

        Note that if you specify your custom visitor for a node, the
        generic visitor will *not* be called by default and the children
        of the node will *not* be visited. You must call ``generic_visit()``
        explicitly if you want to visit the children."""
        generator = node.transform_child_nodes()
        new_node = None  # for priming the generator
        while True:
            try:
                child_node = generator.send(new_node)
                new_node = self._visit(child_node)
                if new_node is not child_node:
                    self.changed = True
            except StopIteration:
                return node

    def visit(self, node: Node) -> Optional[Node]:
        self.changed = False
        return super().visit(node)


iter_fields = Node.iter_fields
iter_field_values = Node.iter_field_values
iter_child_nodes = Node.iter_child_nodes


#############################################################################
# Helper functions for parsing


def _parse_statement_from_bytecode(data: BufferedReader) -> Optional[Statement]:
    """Parses a Statement object from its bytecode representation.

    Parameters:
        data: the stream to read the statement from

    Returns:
        Optional[Statement]: the statement that was constructed, or `None` if
            the next statement is the end of a loop block or if there are no
            more statements to parse
    """
    # Peek the next character from the stream
    code = data.peek(1)[:1]
    if not code:
        return None

    # Try to identify the command that the code represents
    for subcls in Command.__subclasses__():
        if getattr(subcls, "code", None) == code:
            break
    else:
        # No such command; maybe it's the start or end of a loop block?
        if code == CommandCode.LOOP_BEGIN:
            subcls = LoopBlock
        elif code == CommandCode.LOOP_END:
            # CommandCode.LOOP_END
            return None
        else:
            subcls = None

    if subcls is None:
        raise BytecodeParserError("unknown command code: {0!r}".format(ord(code)))

    return _parse_node_from_bytecode_by_class(subcls, data)


def _parse_node_from_bytecode_by_class(cls: Type[Node], data: IO[bytes]):
    """Parses a Node subclass from its bytecode representation, assuming that
    we know what node class we expect to see next.

    Parameters:
        cls (class): the Node subclass to construct
        data (IOBase): the stream to read the bytecode representation of the
            node from

    Returns:
        Node: the node that was constructed
    """
    if hasattr(cls, "from_bytecode"):
        # Node provides its own from_bytecode method so let it do the parsing
        return cls.from_bytecode(data)  # type: ignore

    # Default implementation: we assume that we have a command code and a list
    # of fields; the fields are defined in the `_fields` property of the node
    # class and their types can be inferred from the `_defaults` property

    # Consume the code marker, if any
    if hasattr(cls, "code"):
        code = data.read(1)
        cls_code: bytes = cls.code  # type: ignore
        if not code:
            raise BytecodeParserEOFError(cls)
        if code != cls_code:
            raise BytecodeParserError(
                "{0} nodes must start with {1}".format(cls.__name__, ord(cls_code))
            )

    # Consume all the fields of the node
    field_values = {}
    for field in cls._fields:
        defaults: Dict[str, Any] = cls._defaults  # type: ignore
        if field not in defaults:
            raise BytecodeParserError(
                "cannot parse {0}, default value for {1!r} "
                "is not specified".format(cls.__name__, field)
            )

        default_value = defaults[field]
        if callable(default_value) and issubclass(default_value, Node):
            field_value = _parse_node_from_bytecode_by_class(default_value, data)
        else:
            raise BytecodeParserError(
                "cannot parse {0}.{1} of type {2!r}".format(
                    cls.__name__, field, default_value
                )
            )

        field_values[field] = field_value

    # Construct the node
    return cls(**field_values)


#############################################################################

if __name__ == "__main__":
    node = StatementSequence(
        [
            LoopBlock(
                iterations=5,
                body=[
                    SetColorCommand(color=RGBColor(255, 127, 0), duration=50),
                    FadeToWhiteCommand(duration=50),
                ],
            ),
            SleepCommand(4200),
            NopCommand(),
            EndCommand(),
        ]
    )
    print(repr(node))
    print(repr(node.to_bytecode()))
    print(node.length_in_bytes)
