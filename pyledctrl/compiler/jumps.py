"""Functions and classes related to jumps and labels in the bytecode."""

from collections import defaultdict

from .ast import NodeVisitor

__all__ = ("JumpMarkerCollector", "JumpMarkerResolver")


class JumpMarkerCollector(NodeVisitor):
    """Visitor class that traverses an abstract syntax tree and collects the
    label markers and the corresponding jump markers in the syntax tree.
    """

    def __init__(self):
        """Constructor."""
        super().__init__()
        self._label_markers_by_names = {}
        self._names_to_jump_markers = defaultdict(list)

    def visit_LabelMarker(self, marker):
        if marker.name in self._label_markers_by_names:
            raise RuntimeError(f"Duplicate label name in AST: {marker.name!r}")
        else:
            self._label_markers_by_names[marker.name] = marker

    def visit_UnconditionalJumpMarker(self, marker):
        self._names_to_jump_markers[marker.destination].append(marker)

    @property
    def has_labels(self):
        """Returns whether at least one label marker has been found in the
        abstract syntax tree.
        """
        return bool(self._label_markers_by_names)

    @property
    def result(self):
        """Returns a dictionary mapping label marker nodes to the jump markers
        that _target_ the label marker.
        """
        result = {
            label_marker: self._names_to_jump_markers[name]
            for name, label_marker in self._label_markers_by_names.items()
        }
        for key in self._names_to_jump_markers.keys():
            if key not in self._label_markers_by_names:
                raise RuntimeError(
                    f"Jump to non-existent label {key!r} detected in AST"
                )

        return result


class JumpMarkerResolver(NodeVisitor):
    """Visitor class that traverses an abstract syntax tree, finds all jump
    markers and resolves their destinations (by name) to the corresponding
    label nodes.
    """

    def __init__(self, label_marker_to_jump_markers_map):
        """Constructor."""
        super().__init__()
        self._jump_markers_to_label_markers = {}
        for label_marker, jump_markers in label_marker_to_jump_markers_map.items():
            for jump_marker in jump_markers:
                self._jump_markers_to_label_markers[jump_marker] = label_marker

    def visit_UnconditionalJumpMarker(self, marker):
        marker.resolve_to(self._jump_markers_to_label_markers[marker])
