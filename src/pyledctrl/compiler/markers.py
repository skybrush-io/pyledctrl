from typing import Optional, Union

from pyledctrl.compiler.errors import MarkerNotResolvableError

from .ast import JumpCommand, Node


__all__ = ("Marker", "LabelMarker", "JumpMarker", "UnconditionalJumpMarker")


class Marker:
    """Superclass for marker objects placed in the bytecode stream that are
    resolved to actual bytecode in a later compilation stage."""

    def to_ast_node(self) -> Optional[Node]:
        """Returns the abstract syntax tree node that should replace the marker
        in the abstract syntax tree.

        Returns:
            the abstract syntax tree node that should replace the marker or
            ``None`` if the marker should be removed from the abstract syntax tree

        Raises:
            MarkerNotResolvableError: if the marker does not "know" all the
                information that is needed to produce a corresponding abstract
                syntax tree node.
        """
        return None


class LabelMarker(Marker):
    """Marker object for a label that jump instructions can refer to."""

    name: str
    """The name of the marker"""

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return "{0.__class__.__name__}(name={0.name!r})".format(self)


class JumpMarker(Marker):
    """Marker object for a jump instruction."""

    destination: str
    """The destination of the jump instruction."""

    destination_marker: Optional[Marker]
    """The marker corresponding to the jump instruction, if known."""

    address: Optional[int]
    """The integer bytecode address corresponding to the jump instruction,
    if known.
    """

    def __init__(self, destination: str):
        self.destination = destination
        self.destination_marker = None
        self.address = None

    def _resolve_to_address(self, address: int) -> None:
        assert self.address is None
        self.address = address

    def _resolve_to_marker(self, marker: Marker) -> None:
        assert self.destination_marker is None
        self.destination_marker = marker

    def resolve_to(self, address_or_marker: Union[int, Marker]) -> None:
        if isinstance(address_or_marker, int):
            self._resolve_to_address(address_or_marker)
        else:
            self._resolve_to_marker(address_or_marker)

    def to_ast_node(self):
        if self.address is None:
            raise MarkerNotResolvableError(self)
        else:
            return JumpCommand(address=self.address)

    def __repr__(self):
        return "{0.__class__.__name__}(destination={0.destination!r})".format(self)


class UnconditionalJumpMarker(JumpMarker):
    """Marker object for an unconditional jump instruction."""

    pass
