"""Implementation of the abstract syntax tree into which the ``.led`` source
files are parsed before they are turned into bytecode.

The API of this module is inspired by (but is not an exact replica of) the
``ast`` module in Python.

The grammar modelled by this syntax tree can roughly be described in EBNF syntax
as follows (where the ``CommandCode.`` constants are considered terminals and
therefore are enclosed in quotes)::

    program = statement-sequence;
    statement-sequence = { statement | statement-sequence };
    statement = command
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
            | jump-command;

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

    (* Loop blocks *)
    loop-block = iterations, statement-sequence;

    (* Not-so-basic types *)
    address = varuint;
    channel-index = unsigned-byte;
    duration = varuint;
    gray-value = unsigned-byte;
    iterations = unsigned-byte;
    rgb-color = unsigned-byte, unsigned-byte, unsigned-byte;

    (* Basic types *)
    unsigned-byte = ? numeric value between 0 and 255 (inclusive) ?
    varint = ? varint-encoded representation of a signed integer ?
    varuint = ? varint-encoded representation of an unsigned integer ?
"""

from __future__ import division

from future_builtins import zip
from pyledctrl.utils import first
from struct import Struct


class CommandCode(object):
    """Constants corresponding to the various raw bytecode commands in
    ``ledctrl``\ 's bytecode."""

    END = b'\x00'
    NOP = b'\x01'
    SLEEP = b'\x02'
    WAIT_UNTIL = b'\x03'
    SET_COLOR = b'\x04'
    SET_GRAY = b'\x05'
    SET_BLACK = b'\x06'
    SET_WHITE = b'\x07'
    FADE_TO_COLOR = b'\x08'
    FADE_TO_GRAY = b'\x09'
    FADE_TO_BLACK = b'\x0A'
    FADE_TO_WHITE = b'\x0B'
    LOOP_BEGIN = b'\x0C'
    LOOP_END = b'\x0D'
    RESET_TIMER = b'\x0E'
    SET_COLOR_FROM_CHANNELS = b'\x10'
    FADE_TO_COLOR_FROM_CHANNELS = b'\x11'
    JUMP = b'\x12'
    TRIGGERED_JUMP = b'\x13'


class EasingMode(object):
    """Constants corresponding to the various easing modes in ``ledctrl``."""

    LINEAR = b'\x00'
    IN_SINE = b'\x01'
    OUT_SINE = b'\x02'
    IN_OUT_SINE = b'\x03'
    IN_QUAD = b'\x04'
    OUT_QUAD = b'\x05'
    IN_OUT_QUAD = b'\x06'
    IN_CUBIC = b'\x07'
    OUT_CUBIC = b'\x08'
    IN_OUT_CUBIC = b'\x09'
    IN_QUART = b'\x0A'
    OUT_QUART = b'\x0B'
    IN_OUT_QUART = b'\x0C'
    IN_QUINT = b'\x0D'
    OUT_QUINT = b'\x0E'
    IN_OUT_QUINT = b'\x0F'
    IN_EXPO = b'\x10'
    OUT_EXPO = b'\x11'
    IN_OUT_EXPO = b'\x12'
    IN_CIRC = b'\x13'
    OUT_CIRC = b'\x14'
    IN_OUT_CIRC = b'\x15'
    IN_BACK = b'\x16'
    OUT_BACK = b'\x17'
    IN_OUT_BACK = b'\x18'
    IN_ELASTIC = b'\x19'
    OUT_ELASTIC = b'\x1A'
    IN_OUT_ELASTIC = b'\x1B'
    IN_BOUNCE = b'\x1C'
    OUT_BOUNCE = b'\x1D'
    IN_OUT_BOUNCE = b'\x1E'

    @classmethod
    def get(cls, spec):
        """Returns an easing mode constant from a string specification.

        Args:
            spec (None or string): a string constant corresponding to the name
                of an easing mode, or ``None`` to denote linear easing. When
                it is a string, it will be turned to uppercase and all the
                dashes will be replaced with underscores before the string
                is looked up in the ``EasingMode`` class.
        """
        if spec is None:
            return cls.LINEAR
        if isinstance(spec, int):
            return spec
        spec = spec.upper().replace("-", "_")
        return getattr(cls, spec)


class _NodeMeta(type):
    """Metaclass for AST nodes.

    This metaclass adds the following functionality to node classes
    automatically if the class has a ``_fields`` property that describes the
    fields of the node and optionally a ``_defaults`` property that contains
    the default value for some or all of the fields:

        - Creates an ``__init__`` method that accepts the fields as positional
          or keyword arguments and throws an exception if fields without
          default values are not initialized.

    The ``_defaults`` property must be a dictionary mapping field names to
    either immutable objects or factory functions that create default values.
    When the factory function is a subclass of ``Literal``, the metaclass
    also provides a convenient setter for the corresponding field that wraps
    the incoming value in the appropriate literal type.
    """

    def __new__(cls, name, parents, dct):
        fields = dct.get("_fields")
        defaults = dct.get("_defaults")
        if "__init__" not in dct:
            dct["__init__"] = cls._create_init_method(parents, fields, defaults)
        cls._add_setters_for_literals(defaults, dct)
        return super(_NodeMeta, cls).__new__(cls, name, parents, dct)

    @classmethod
    def _add_setters_for_literals(cls, defaults, dct):
        if not defaults:
            return
        for field, default in defaults.items():
            if field in dct:
                continue
            if issubclass(default, Literal):
                dct[field] = cls._add_setter_for_literal(field, default)

    @classmethod
    def _add_setter_for_literal(cls, field, literal_type):
        field_var = "_" + field

        def getter(self):
            return getattr(self, field_var)

        def setter(self, value):
            if not isinstance(value, literal_type):
                value = literal_type(value)
            setattr(self, field_var, value)
        return property(getter, setter)

    @classmethod
    def _create_init_method(cls, parents, fields, defaults):
        if fields is None:
            # Class should be abstract
            def __init__(self, *args, **kwds):
                raise NotImplementedError("this node type is abstract")
            return __init__

        # Class is not abstract, so we need a real constructor
        node_superclass = first(parent for parent in parents
                                if issubclass(parent, Node))
        node_superclass_is_abstract = not hasattr(node_superclass, "_fields")
        num_fields = len(fields)

        def __init__(self, *args, **kwds):
            if not node_superclass_is_abstract:
                node_superclass.__init__(self)
            if args:
                if num_fields < len(args):
                    raise TypeError("__init__() takes at most {0} "
                                    "arguments ({1} given)".format(
                                        num_fields, len(args)))
                for arg_name, arg in zip(fields, args):
                    setattr(self, arg_name, arg)
            if kwds:
                for arg_name, arg in kwds.items():
                    if arg_name not in fields:
                        raise TypeError("__init__() got an unexpected keyword "
                                        "argument: {0!r}".format(arg_name))
                    setattr(self, arg_name, arg)
            if defaults:
                for arg_name, arg in defaults.items():
                    if not hasattr(self, arg_name):
                        if callable(arg):
                            arg = arg()
                        setattr(self, arg_name, arg)
            for arg_name in fields:
                if not hasattr(self, arg_name):
                    raise TypeError("__init__() did not receive an initial "
                                    "value for field {0!r}".format(arg_name))

        return __init__


class Node(object):
    """Base class for nodes in the abstract syntax tree."""

    __metaclass__ = _NodeMeta

    def iter_child_nodes(self):
        """Returns an iterator that yields all field values that are subclasses
        of nodes. When a field maps to a list of nodes, yields all the nodes
        in the list."""
        for name in self._fields:
            value = getattr(self, name)
            if isinstance(value, Node):
                yield value
            elif isinstance(value, NodeList):
                for node in value:
                    yield node

    def iter_fields(self):
        """Returns an iterator that yields ``(field_name, field_value)`` pairs
        for each child of the node."""
        for name in self._fields:
            yield name, getattr(self, name)

    @property
    def length_in_bytes(self):
        """Returns the length of the node when it is converted into bytecode.
        The default implementation calls ``to_bytecode`` and returns the length
        of the generated bytecode, but you should override it in subclasses
        where possible to make the method more efficient."""
        return len(self.to_bytecode())

    def to_bytecode(self):
        """Converts the node into bytecode.

        Returns:
            bytes: the bytecode representation of the node
        """
        raise NotImplementedError

    def to_dict(self):
        """Converts the node into a dictionary representation that maps the
        names of the children of the node into the corresponding values.
        Works only for concrete nodes where the ``_fields`` class variable
        is defined."""
        return dict(self.iter_fields())

    def to_led_source(self):
        """Converts the node back into the ``.led`` source format.

        Returns:
            str: the ``.led`` source format representation of the node
        """
        raise NotImplementedError

    def transform_child_nodes(self):
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
                    new_node = yield old_node
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
            setattr(self, arg_name, value)

    def __repr__(self):
        kvpairs = ["{0}={1!r}".format(arg_name, getattr(self, arg_name))
                   for arg_name in self._fields]
        return "{0.__class__.__name__}({1})".format(self, ", ".join(kvpairs))


class NodeList(list):
    """Subclass of list that adds no extra functionality but allows us to
    detect objects that are meant to hold lists of AST nodes."""
    pass


class Literal(Node):
    """Base class for literal nodes."""
    pass


class Byte(Literal):
    """Node that represents a single-byte literal value."""
    pass


class UnsignedByte(Byte):
    """Node that represents a single-byte literal value (such as a component
    of an RGB color that is stored on a single byte."""

    _fields = ("value", )
    _defaults = {
        "value": 0
    }
    _struct = Struct("B")

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return self._struct.size

    def to_bytecode(self):
        return self._struct.pack(self.value)

    def to_led_source(self):
        return str(self.value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value < 0 or value > 255:
            raise ValueError("value must be between 0 and 255 (inclusive)")
        self._value = value


class Varuint(Literal):
    """Node that represents an unsigned varint-encoded literal value."""

    _fields = ("value", )
    _defaults = {
        "value": 0
    }

    @staticmethod
    def _to_varuint(value):
        """Converts the given numeric value into its varuint representation."""
        result = []
        if value < 0:
            raise ValueError("negative varuints are not supported")
        elif value == 0:
            result = [0]
        else:
            while value > 0:
                if value < 128:
                    result.append(value)
                else:
                    result.append((value & 0x7F) + 0x80)
                value >>= 7
        return bytes(bytearray(result))

    def to_bytecode(self):
        return self._to_varuint(self.value)

    def to_led_source(self):
        return str(self.value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value < 0:
            raise ValueError("value must be non-negative")
        elif value >= 2**28:
            raise ValueError("varuints greater than 2**28 are not supported "
                             "by the bytecode")
        self._value = value


class RGBColor(Node):
    """Node that represents an RGB color."""

    _fields = ["red", "green", "blue"]
    _defaults = {
        "red": UnsignedByte,
        "green": UnsignedByte,
        "blue": UnsignedByte
    }

    @property
    def is_black(self):
        """Returns ``True`` if the color is black."""
        return self.red.value == 0 and self.green.value == 0 and \
            self.blue.value == 0

    @property
    def is_gray(self):
        """Returns ``True`` if the color is a shade of gray."""
        return self.red.value == self.green.value and \
            self.green.value == self.blue.value

    @property
    def is_white(self):
        """Returns ``True`` if the color is white."""
        return self.red.value == 255 and self.green.value == 255 and \
            self.blue.value == 255

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return 3

    def to_bytecode(self):
        return b"".join(field.to_bytecode() for _, field in self.iter_fields())

    def to_led_source(self):
        return "{0}, {1}, {2}".format(
            self.red.to_led_source(),
            self.green.to_led_source(),
            self.blue.to_led_source()
        )


class Duration(Varuint):
    """Node that represents a duration."""

    _fields = Varuint._fields
    FPS = 50

    @classmethod
    def from_frames(cls, frames):
        result = cls()
        result.value_in_frames = frames
        return result

    @classmethod
    def from_seconds(cls, seconds):
        result = cls()
        result.value_in_seconds = seconds
        return result

    @property
    def value_in_frames(self):
        return self.value * self.FPS

    @value_in_frames.setter
    def value_in_frames(self, value):
        self.value = value / self.FPS

    @property
    def value_in_seconds(self):
        return self.value

    @value_in_seconds.setter
    def value_in_seconds(self, value):
        self.value = value

    def to_bytecode(self):
        return self._to_varuint(int(self.value_in_frames))



class StatementSequence(Node):
    """Node that represents a sequence of statements."""

    _fields = ["statements"]
    _defaults = {
        "statements": NodeList
    }

    def append(self, node):
        """Appends a node to the sequence."""
        self.statements.append(node)

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return sum(node.length_in_bytes for node in self.statements)

    def to_bytecode(self):
        return b"".join(node.to_bytecode() for node in self.statements)

    def to_led_source(self):
        return "\n".join(statement.to_led_source()
                         for statement in self.statements)

class Statement(Node):
    """Node that represents a single statement (e.g., a bytecode command or
    a loop block)."""
    pass


class Command(Statement):
    """Node that represents a single bytecode command."""

    code = None

    @Node.length_in_bytes.getter
    def length_in_bytes(self):
        return sum((field.length_in_bytes for _, field in self.iter_fields()), 1)

    def to_bytecode(self):
        parts = [self.code]
        parts.extend(field.to_bytecode() for _, field in self.iter_fields())
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
    _fields = ("duration", )
    _defaults = {
        "duration": Varuint
    }

    def to_led_source(self):
        return "sleep(duration={0})".format(self.duration.to_led_source())


class WaitUntilCommand(Command):
    """Node that represents a ``WAIT_UNTIL`` command in the bytecode."""

    code = CommandCode.WAIT_UNTIL
    _fields = ("timestamp", )
    _defaults = {
        "timestamp": Varuint
    }


class SetColorCommand(Command):
    """Node that represents a ``SET_COLOR`` command in the bytecode."""

    code = CommandCode.SET_COLOR
    _fields = ("color", "duration")
    _defaults = {
        "color": RGBColor,
        "duration": Varuint
    }

    def to_led_source(self):
        return "set_color({0}, duration={1})".format(
            self.color.to_led_source(), self.duration.to_led_source()
        )


class SetGrayCommand(Command):
    """Node that represents a ``SET_GRAY`` command in the bytecode."""

    code = CommandCode.SET_GRAY
    _fields = ("value", "duration")
    _defaults = {
        "value": UnsignedByte,
        "duration": Varuint
    }

    def to_led_source(self):
        return "set_gray({0}, duration={1})".format(
            self.value.to_led_source(), self.duration.to_led_source()
        )


class SetBlackCommand(Command):
    """Node that represents a ``SET_BLACK`` command in the bytecode."""

    code = CommandCode.SET_BLACK
    _fields = ("duration", )
    _defaults = {
        "duration": Varuint
    }

    def to_led_source(self):
        return "set_black(duration={0})".format(self.duration.to_led_source())


class SetWhiteCommand(Command):
    """Node that represents a ``SET_WHITE`` command in the bytecode."""

    code = CommandCode.SET_WHITE
    _fields = ("duration", )
    _defaults = {
        "duration": Varuint
    }

    def to_led_source(self):
        return "set_white(duration={0})".format(self.duration.to_led_source())


class FadeToColorCommand(Command):
    """Node that represents a ``FADE_TO_COLOR`` command in the bytecode."""

    code = CommandCode.FADE_TO_COLOR
    _fields = ("color", "duration")
    _defaults = {
        "color": RGBColor,
        "duration": Varuint
    }

    def to_led_source(self):
        return "fade_to_color({0}, duration={1})".format(
            self.color.to_led_source(), self.duration.to_led_source()
        )


class FadeToGrayCommand(Command):
    """Node that represents a ``FADE_TO_GRAY`` command in the bytecode."""

    code = CommandCode.FADE_TO_GRAY
    _fields = ("value", "duration")
    _defaults = {
        "value": UnsignedByte,
        "duration": Varuint
    }

    def to_led_source(self):
        return "fade_to_gray({0}, duration={1})".format(
            self.value.to_led_source(), self.duration.to_led_source()
        )


class FadeToBlackCommand(Command):
    """Node that represents a ``FADE_TO_BLACK`` command in the bytecode."""

    code = CommandCode.FADE_TO_BLACK
    _fields = ("duration", )
    _defaults = {
        "duration": Varuint
    }

    def to_led_source(self):
        return "fade_to_black(duration={0})".format(
            self.duration.to_led_source()
        )


class FadeToWhiteCommand(Command):
    """Node that represents a ``FADE_TO_WHITE`` command in the bytecode."""

    code = CommandCode.FADE_TO_WHITE
    _fields = ("duration", )
    _defaults = {
        "duration": Varuint
    }

    def to_led_source(self):
        return "fade_to_white(duration={0})".format(
            self.duration.to_led_source()
        )


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
        "duration": Varuint
    }


class FadeToColorFromChannelsCommand(Command):
    """Node that represents a ``FADE_TO_COLOR_FROM_CHANNELS`` command in the
    bytecode."""

    code = CommandCode.FADE_TO_COLOR_FROM_CHANNELS
    _fields = ("red_channel", "green_channel", "blue_channel", "duration")
    _defaults = {
        "red_channel": UnsignedByte,
        "green_channel": UnsignedByte,
        "blue_channel": UnsignedByte,
        "duration": Varuint
    }


class JumpCommand(Command):
    """Node that represents a ``JUMP`` command in the bytecode."""

    code = CommandCode.JUMP
    _fields = ("address", )
    _defaults = {
        "address": Varuint
    }


class LoopBlock(Statement):
    """Node that represents a loop in the bytecode."""

    _fields = ("iterations", "body")
    _defaults = {
        "iterations": UnsignedByte,
        "body": StatementSequence
    }

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
        if not self.body.statements or self.iterations.value <= 0:
            return b""

        body = b"".join(node.to_bytecode() for node in self.body.statements)
        if self.iterations.value == 1:
            return body
        else:
            return CommandCode.LOOP_BEGIN + self.iterations.to_bytecode() + \
                body + CommandCode.LOOP_END

    def to_led_source(self):
        if not self.body.statements or self.iterations.value <= 0:
            return ""

        body = self.body.to_led_source()
        if self.iterations.value == 1:
            return body
        else:
            body = body.replace("\n", "\n    ")
        return "with loop(iterations={0}):\n    {1}".format(self.iterations, body)


class NodeVisitor(object):
    """Base class for node visitors that walk the abstract syntax tree in a
    top-down manner and call a visitor function for every node found.

    This class is meant to be subclassed; subclasses should add or override
    visitor methods."""

    def __init__(self):
        self._dispatch_table = {}

    def generic_visit(self, node):
        """This visitor method is called for nodes for which no specific
        visitor method of the form ``self.visit_{classname}`` exists in this
        class. The default implementation of this method simply calls
        ``visit()`` on all children of the node.

        Note that if you specify your custom visitor for a node, the
        generic visitor will *not* be called by default and the children
        of the node will *not* be visited. You must call ``generic_visit()``
        explicitly if you want to visit the children."""
        for child_node in node.iter_child_nodes():
            self._visit(child_node)

    def visit(self, node):
        """Visits the given node in the abstract syntax tree. The default
        implementation calls ``self.visit_{classname}`` where ``{classname}``
        is the name of the node class, or ``self.generic_visit()`` if a
        node-specific visitor method does not exist.

        Returns:
            object: whatever the visitor method returns.
        """
        return self._visit(node)

    def _find_visitor_method(self, node):
        """Finds an appropriate visitor method within this instance for the
        given node. By default, this function will look for a method named
        ``visit_{classname}`` in ``self`` and fall back to ``generic_visit``
        if such a method does not exist.

        Args:
            node (Node): the node to visit

        Returns:
            callable: an appropriate visitor method for the node
        """
        method_name = "visit_{0}".format(node.__class__.__name__)
        return getattr(self, method_name, None) or self.generic_visit

    def _get_visitor_method(self, node):
        """Returns the visitor method corresponding to the given node."""
        cls = node.__class__
        func = self._dispatch_table.get(cls)
        if func is None:
            func = self._dispatch_table[cls] = self._find_visitor_method(node)
        return func

    def _visit(self, node):
        return self._get_visitor_method(node)(node)


class NodeTransformer(NodeVisitor):
    """A ``NodeVisitor`` subclass that assumes that the visitor methods return
    an AST node or ``None``. When ``None`` is returned, the visited node is
    removed from the tree. When an AST node is returned, the visited node is
    replaced by the returned AST node (which may of course be the same as the
    original visited node)."""

    def __init__(self):
        super(NodeTransformer, self).__init__()
        self.changed = False

    def generic_visit(self, node):
        """This visitor method is called for nodes for which no specific
        visitor method of the form ``self.visit_{classname}`` exists in this
        class. The default implementation of this method simply calls
        ``visit()`` on all children of the node.

        Note that if you specify your custom visitor for a node, the
        generic visitor will *not* be called by default and the children
        of the node will *not* be visited. You must call ``generic_visit()``
        explicitly if you want to visit the children."""
        generator = node.transform_child_nodes()
        new_node = None            # for priming the generator
        while True:
            try:
                child_node = generator.send(new_node)
                new_node = self._visit(child_node)
                if new_node is not child_node:
                    self.changed = True
            except StopIteration:
                return node

    def visit(self, node):
        self.changed = False
        return super(NodeTransformer, self).visit(node)


iter_fields = Node.iter_fields
iter_child_nodes = Node.iter_child_nodes


if __name__ == "__main__":
    node = StatementSequence([
        LoopBlock(iterations=5, body=[
            SetColorCommand(color=RGBColor(255, 127, 0), duration=50),
            FadeToWhiteCommand(duration=50)
        ]),
        SleepCommand(4200),
        NopCommand(),
        EndCommand(),
    ])
    print(repr(node))
    print(repr(node.to_bytecode()))
    print(node.length_in_bytes)
