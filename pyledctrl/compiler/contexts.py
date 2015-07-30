"""Context objects for the bytecode compiler.

Context objects provide a dictionary mapping identifiers to functions that
are injected into the namespace in which the source code of a LED control
file is evaluated. This allows us to implement custom "commands" that the
user can use in a LED control file.
"""

from __future__ import absolute_import

from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from pyledctrl.compiler import bytecode
from pyledctrl.compiler.bytecode import Marker
from pyledctrl.compiler.errors import DuplicateLabelError
from pyledctrl.utils import ensure_tuple


def _flatten_bytes(iterable):
    """Given an iterable containing bytes objects, Markers and other iterables
    containing bytes object, returns a list that contains the same bytes and
    markers in the same order but "flattened" so there are no nestings
    wihtin the list."""
    return list(_flatten_bytes_helper(iterable))

def _flatten_bytes_helper(iterable):
    for item in iterable:
        if isinstance(item, bytes):
            for char in item:
                yield char
        elif isinstance(item, Marker):
            yield item
        else:
            for sub_item in _flatten_bytes_helper(item):
                yield sub_item

class ExecutionContext(object):
    """Base class for execution contexts.

    Execution contexts provide a dictionary mapping identifiers to functions
    that are injected into the namespace in which the source code of a LED
    control file is evaluated. This allows us to implement custom "commands"
    that the user can use in a LED control file.
    """

    def __init__(self):
        self.reset()

    @property
    def bytecode(self):
        """Returns the compiled bytecode."""
        return list(self._bytecode)

    def evaluate(self, code, add_end_command=False):
        """Evaluates the given Python code object in this execution context.

        :param code: the code to evaluate
        :param add_end_command: whether to add a terminating ``END`` command
            automatically to the end of the bytecode
        """
        global_vars = self.get_globals()
        exec(code, global_vars, {})
        if add_end_command:
            global_vars["end"]()
        self._postprocess_bytecode()

    def get_globals(self):
        """Returns a dictionary containing the global variables to be made
        available in the executed file."""
        if self._globals is None:
            self._globals = self._construct_globals()
        return self._globals

    def reset(self):
        """Resets the execution context to a pristine state."""
        self._bytecode = []
        self._labels = {}
        self._globals = None

    def _construct_globals(self):
        wrapper_for = self._create_bytecode_func_wrapper
        result = {
            "_loop_begin": wrapper_for(bytecode.loop_begin),
            "_loop_end": wrapper_for(bytecode.loop_end),
            "end": wrapper_for(bytecode.end),
            "fade_to_black": wrapper_for(bytecode.fade_to_black),
            "fade_to_color": wrapper_for(bytecode.fade_to_color),
            "fade_to_gray": wrapper_for(bytecode.fade_to_gray),
            "fade_to_white": wrapper_for(bytecode.fade_to_white),
            "jump": wrapper_for(bytecode.jump),
            "label": wrapper_for(bytecode.label),
            "nop": wrapper_for(bytecode.nop),
            "set_black": wrapper_for(bytecode.set_black),
            "set_color": wrapper_for(bytecode.set_color),
            "set_gray": wrapper_for(bytecode.set_gray),
            "set_white": wrapper_for(bytecode.set_white)
        }
        aliases = dict(off="set_black", on="set_white", goto="jump")
        for alias, func in aliases.items():
            result[alias] = result[func]

        @contextmanager
        def _loop_context(iterations=None):
            result["_loop_begin"](iterations)
            yield
            result["_loop_end"]()

        result["loop"] = _loop_context
        return {k: v for k, v in result.items() if not k.startswith("_")}

    def _create_bytecode_func_wrapper(self, func):
        @wraps(func)
        def wrapped(*args, **kwds):
            result = _flatten_bytes(ensure_tuple(func(*args, **kwds)))
            for token in result:
                if isinstance(token, bytes):
                    self._bytecode.extend(token)
                elif isinstance(token, Marker):
                    self._bytecode.append(token)
                else:
                    raise ValueError("unknown value returned from bytecode "
                                     "function: {0!r}".format(token))
                if isinstance(token, bytecode.LabelMarker):
                    if token.name in self._labels:
                        raise DuplicateLabelError(token.name)
                    else:
                        self._labels = len(self._bytecode)-1
        return wrapped

    def _postprocess_bytecode(self):
        """Post-processes the bytecode and the additional instructions
        collected in ``self._bytecode`` at the end of an execution, finalizes
        jump addresses etc."""

        # Find all the jump instructions in the bytecode
        jumps_by_destination = defaultdict(list)
        for item in self._bytecode:
            if isinstance(item, bytecode.JumpMarker):
                jumps_by_destination[item.destination].append(item)

        if jumps_by_destination:
            # Process the bytecode from the front. If we encounter a label,
            # resolve the corresponding jumps to the address (that we know
            # exactly by now).
            address_offset = 0
            for address, item in enumerate(self._bytecode):
                if isinstance(item, bytecode.LabelMarker):
                    for jump in jumps_by_destination.get(item.name, []):
                        jump.resolve_to_address(address-address_offset)
                    address_offset += 1

            # We can now eliminate all label markers.
            self._resolve_markers(bytecode.LabelMarker)

            # And then all other markers (including jump markers) as well
            self._resolve_markers()

    def _resolve_markers(self, cls=Marker, graceful=False):
        """Tries to resolve all markers of the given class within the bytecode
        by replacing them with the result of calling their ``as_bytecode()``
        method.

        Args:
            cls (type): the marker class to replace
            graceful (bool): whether to ignore MarkerNotResolvableError
                errors raised by the markers
        """
        index, length = 0, len(self._bytecode)
        while index < length:
            marker = self._bytecode[index]
            if isinstance(marker, cls):
                if graceful:
                    try:
                        replacement = marker.as_bytecode()
                    except MarkerNotResolvableError:
                        replacement = None
                else:
                    replacement = marker.as_bytecode()
                if replacement is not None:
                    replacement = _flatten_bytes(ensure_tuple(replacement))
                    self._bytecode[index:(index+1)] = replacement
                    length += len(replacement)-1
            index += 1


class FileWriterExecutionContext(ExecutionContext):
    """Execution context that writes the generated bytecode in response to each
    command to a file-like object."""

    def __init__(self, fp):
        """Constructor.

        :param fp: a file-like object to write the generated bytecode to
        :type fp: file-like
        """
        super(FileWriterExecutionContext, self).__init__()
        self.fp = fp

    def evaluate(self, code, add_end_command=False):
        super(FileWriterExecutionContext, self).evaluate(code, add_end_command)
        self.fp.write("".join(self.bytecode))
