"""Context objects for the bytecode compiler.

Context objects provide a dictionary mapping identifiers to functions that
are injected into the namespace in which the source code of a LED control
file is evaluated. This allows us to implement custom "commands" that the
user can use in a LED control file.
"""

from __future__ import absolute_import

from contextlib import contextmanager
from functools import wraps

from pyledctrl.utils import ensure_tuple

from . import bytecode
from .ast import EndCommand, LoopBlock, Node, StatementSequence
from .bytecode import LabelMarker, Marker
from .errors import DuplicateLabelError, MarkerNotResolvableError
from .jumps import JumpMarkerCollector, JumpMarkerResolver


def _flatten_bytes(iterable):
    """Given an iterable containing bytes objects, Markers and other iterables
    containing bytes object, returns a list that contains the same bytes and
    markers in the same order but "flattened" so there are no nestings
    wihtin the list.
    """
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
        """Constuctor."""
        self.reset()

    @property
    def ast(self):
        """Returns the abstract syntax tree that was parsed after evaluating
        the source code.
        """
        return self._ast

    @property
    def bytecode(self):
        """Returns the compiled bytecode."""
        return self._ast.to_bytecode()

    def evaluate(self, code, add_end_command=False):
        """Evaluates the given Python code object in this execution context.

        :param code: the code to evaluate
        :param add_end_command: whether to add a terminating ``END`` command
            automatically to the end of the bytecode
        """
        global_vars = self.get_globals()
        exec(code, global_vars, {})
        if add_end_command:
            last_command = self._ast
            while isinstance(last_command, StatementSequence):
                statements = last_command.statements
                if statements:
                    last_command = statements[-1]
                else:
                    last_command = None
            if not isinstance(last_command, EndCommand):
                global_vars["end"]()
        self._postprocess_syntax_tree()

    def get_globals(self):
        """Returns a dictionary containing the global variables to be made
        available in the executed file.
        """
        if self._globals is None:
            self._globals = self._construct_globals()
        return self._globals

    def reset(self):
        """Resets the execution context to a pristine state."""
        self._ast = StatementSequence()
        self._ast_stack = [self._ast]
        self._labels = {}
        self._globals = None

    def _construct_globals(self):
        wrapper_for = self._create_bytecode_func_wrapper
        result = {
            "comment": wrapper_for(bytecode.comment),
            "end": wrapper_for(bytecode.end),
            "fade_to_black": wrapper_for(bytecode.fade_to_black),
            "fade_to_color": wrapper_for(bytecode.fade_to_color),
            "fade_to_gray": wrapper_for(bytecode.fade_to_gray),
            "fade_to_white": wrapper_for(bytecode.fade_to_white),
            "jump": wrapper_for(bytecode.jump),
            "label": wrapper_for(bytecode.label),
            "nop": wrapper_for(bytecode.nop),
            "pyro_clear": wrapper_for(bytecode.pyro_clear),
            "pyro_disable": wrapper_for(bytecode.pyro_disable),
            "pyro_enable": wrapper_for(bytecode.pyro_enable),
            "pyro_set_all": wrapper_for(bytecode.pyro_set_all),
            "set_black": wrapper_for(bytecode.set_black),
            "set_color": wrapper_for(bytecode.set_color),
            "set_gray": wrapper_for(bytecode.set_gray),
            "set_white": wrapper_for(bytecode.set_white),
            "sleep": wrapper_for(bytecode.sleep),
        }
        aliases = dict(off="set_black", on="set_white", goto="jump")
        for alias, func in aliases.items():
            result[alias] = result[func]

        @contextmanager
        def _loop_context(iterations=None):
            loop_block = LoopBlock()
            self._ast_stack.append(loop_block.body)
            yield
            self._ast_stack.pop()
            self._ast_stack[-1].append(loop_block)

        result["loop"] = _loop_context
        return {k: v for k, v in result.items() if not k.startswith("_")}

    def _create_bytecode_func_wrapper(self, func):
        @wraps(func)
        def wrapped(*args, **kwds):
            node = func(*args, **kwds)
            if isinstance(node, (Node, Marker)):
                self._ast_stack[-1].append(node)
            else:
                raise ValueError(
                    "unknown value returned from bytecode "
                    "function: {0!r}".format(node)
                )
            if isinstance(node, LabelMarker):
                if node.name in self._labels:
                    raise DuplicateLabelError(node.name)
                else:
                    self._labels[node.name] = node

        return wrapped

    def _postprocess_syntax_tree(self):
        """Post-processes the abstract syntax tree and the additional markers
        collected in ``self._ast`` at the end of an execution, finalizes
        jump addresses etc.
        """
        collector = JumpMarkerCollector()
        collector.visit(self._ast)

        if collector.has_labels:
            raise NotImplementedError("Jumps and labels are not supported yet")

        resolver = JumpMarkerResolver(collector.result)
        resolver.visit(self._ast)

        # At this point all the jump markers know the _identity_ of the label
        # they should jump to, but not their _address_ in the compiled bytecode.
        # This comes later.

        """
        if jumps_by_destination:
            # Process the bytecode from the front. If we encounter a label,
            # resolve the corresponding jumps to the address (that we know
            # exactly by now).
            address_offset = 0
            for address, item in enumerate(self._bytecode):
                if isinstance(item, bytecode.LabelMarker):
                    for jump in jumps_by_destination.get(item.name, []):
                        jump.resolve_to(address - address_offset)
                    address_offset += 1

            # We can now eliminate all label markers.
            self._resolve_markers(bytecode.LabelMarker)

            # And then all other markers (including jump markers) as well
            self._resolve_markers()
        """

    def _resolve_markers(self, cls=Marker, graceful=False):
        """Tries to resolve all markers of the given class within the abstract
        syntax tree by replacing them with the result of calling their
        ``to_ast_node()`` method.

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
                        replacement = marker.to_ast_node()
                    except MarkerNotResolvableError:
                        replacement = None
                else:
                    replacement = marker.to_ast_node()
                if replacement is not None:
                    replacement = _flatten_bytes(ensure_tuple(replacement))
                    self._bytecode[index : (index + 1)] = replacement
                    length += len(replacement) - 1
            index += 1
