"""AST optimization routines for the ledctrl compiler."""

from itertools import islice
from operator import attrgetter
from pyledctrl.compiler.ast import Node, NodeTransformer, \
    SetBlackCommand, SetGrayCommand, SetWhiteCommand, \
    FadeToBlackCommand, FadeToGrayCommand, FadeToWhiteCommand, \
    LoopBlock, StatementSequence
from pyledctrl.compiler.utils import TimestampWrapper


class ASTOptimiser(object):
    """Base class for optimiser objects that take an AST and mutate it in
    order to reduce the size of the final bytecode.
    """

    def optimise_ast(self, ast):
        """Attempts to optimise the given AST in-place.

        Returns:
            bool: whether the AST was modified by the optimiser.
        """
        raise NotImplementedError

    def optimise(self, obj):
        """Attempts to optimise the given object.

        When the object is an abstract syntax tree, the call will be forwarded
        to ``optimise_ast()``. When the object is a TimestampWrapper_, the
        wrapped object will be extracted and the method will be called again.
        """
        if isinstance(obj, Node):
            return self.optimise_ast(obj)
        elif isinstance(obj, TimestampWrapper):
            return self.optimise(obj.wrapped)
        else:
            raise TypeError("optimisation not supported for {0!r}".format(obj))


class NullASTOptimiser(ASTOptimiser):
    """Null optimiser that does not transform the AST at all."""

    def optimise_ast(self, obj):
        return False


class CompositeASTOptimiser(ASTOptimiser):
    """Composite AST optimiser that uses multiple "child optimisers" and
    returns if none of the child optimisers can modify the AST any more.
    """

    def __init__(self):
        self._optimisers = []

    def add_optimiser(self, optimiser):
        """Adds the given AST optimiser to the list of optimisers that the
        composite optimiser will act on.
        """
        self._optimisers.append(optimiser)

    def optimise_ast(self, ast):
        modified_at_least_once = False
        any_modified = True
        while any_modified:
            any_modified = False
            for optimiser in self._optimisers:
                any_modified = optimiser.optimise(ast) or any_modified
            modified_at_least_once = modified_at_least_once or any_modified
        return modified_at_least_once


class ColorCommandShortener(ASTOptimiser):
    """AST optimiser that replaces some color-related commands with variants
    that take a smaller number of bytes.

    Replacements performed by this optimiser are:

        - ``set_color(0, 0, 0, duration)`` is replaced by ``set_black(duration)``

        - ``set_color(255, 255, 255, duration)`` is replaced by
          ``set_white(duration)``

        - ``set_color(x, x, x, duration)`` is replaced by
          ``set_gray(x, duration)``

        - ``fade_to_color(0, 0, 0, duration)`` is replaced by
          ``fade_to_black(duration)``

        - ``fade_to_color(255, 255, 255, duration)`` is replaced by
          ``fade_to_white(duration)``

        - ``fade_to_color(x, x, x, duration)`` is replaced by
          ``fade_to_gray(x, duration)``
    """

    class Transformer(NodeTransformer):
        """Transformer class that describes the node replacements that this
        optimiser will perform.
        """

        def visit_SetColorCommand(self, node):
            if node.color.is_white:
                return SetWhiteCommand(duration=node.duration)
            elif node.color.is_black:
                return SetBlackCommand(duration=node.duration)
            elif node.color.is_gray:
                return SetGrayCommand(value=node.red, duration=node.duration)
            else:
                return node

        def visit_SetGrayCommand(self, node):
            if node.value == 255:
                return SetWhiteCommand(duration=node.duration)
            elif node.value == 0:
                return SetBlackCommand(duration=node.duration)
            else:
                return node

        def visit_FadeToColorCommand(self, node):
            if node.color.is_white:
                return FadeToWhiteCommand(duration=node.duration)
            elif node.color.is_black:
                return FadeToBlackCommand(duration=node.duration)
            elif node.color.is_gray:
                return FadeToGrayCommand(value=node.red, duration=node.duration)
            else:
                return node

        def visit_FadeToGrayCommand(self, node):
            if node.value == 255:
                return FadeToWhiteCommand(duration=node.duration)
            elif node.value == 0:
                return FadeToBlackCommand(duration=node.duration)
            else:
                return node

    def optimise_ast(self, ast):
        transformer = self.Transformer()
        transformer.visit(ast)
        return transformer.changed


class LoopDetector(ASTOptimiser):
    """AST optimiser that attempts to detect repetitive invocations of the
    same set of commands, and replaces them with a loop of fixed length.
    """

    class Transformer(NodeTransformer):
        """AST transformer that analyses ``StatementSequence`` nodes and
        replaces repetitive slices of the statement sequence with loop
        blocks.
        """

        def __init__(self):
            super(LoopDetector.Transformer, self).__init__()
            self.max_loop_len = 8

        def _identify_loop_iteration_count(self, statements, start_index,
                                           loop_body_length):
            """Identifies the maximum iteration count of a potential loop
            that starts at the given index and has the given assumed body
            length.
            """
            num_statements = len(statements)
            first, second = start_index, start_index + loop_body_length
            num_matches = 0
            while second < num_statements and \
                    statements[first].is_equivalent_to(statements[second]):
                first += 1
                second += 1

            # Don't detect more than 255 iterations because we cannot represent
            # more than 255 anyway
            return min((second - start_index) // loop_body_length, 255)

        def visit_StatementSequence(self, node):
            body = node.statements
            index = 0
            num_statements = len(body)
            while index < num_statements:
                # For each statement in the body, look ahead to see if we
                # find an identical one. Two statements are identical if
                # they have the same class and resolve to the same bytecode.
                # Once we have found an identical statement N statements
                # later, we have a potential loop of length N (commands).
                # We can then find how many iterations this loop would have
                # and calculate how many bytes we would save with this.
                # We save each such potential loop in a list
                potential_loops = []
                statement = body[index]
                statement_class = statement.__class__
                end = index + 1
                max_end = min(num_statements, index + self.max_loop_len)
                for end in xrange(index+1, max_end):
                    end_statement = body[end]
                    if statement.is_equivalent_to(end_statement):
                        # A potential loop starts at index with a body
                        # length of end-index. Check how long the loop
                        # would be.
                        body_length = end - index
                        iterations = self._identify_loop_iteration_count(
                            body, index, body_length
                        )
                        if iterations > 1:
                            potential_loops.append((end, iterations))

                if potential_loops:
                    # Find the best loop, i.e. the one that takes the smallest
                    # amount of space, and replace the body with the best
                    # loop
                    blocks = [LoopBlock(iterations=iterations,
                                        body=StatementSequence(body[index:end]))
                              for end, iterations in potential_loops]
                    best_block = min(blocks, key=attrgetter("length_in_bytes"))
                    end = index + best_block.iterations.value * \
                        len(best_block.body.statements)
                    body[index:end] = [best_block]
                    num_statements = len(body)
                    index += 1
                else:
                    # Just jump to the next statement
                    index += 1

    def optimise_ast(self, ast):
        transformer = self.Transformer()
        transformer.visit(ast)
        return transformer.changed


def create_optimiser_for_level(level=2):
    """Creates an AST optimiser for the given optimisation level.

    Currently we have the following optimisation levels:

        - 0: don't optimise the AST at all

        - 1: perform only basic optimisations

        - 2: perform more aggressive optimisations to make the generated
          bytecode smaller (default)

    Parameters:
        level (int): the optimisation level

    Returns:
        ASTOptimiser: the AST optimiser to use for the given optimisation level
    """
    if level <= 0:
        return NullASTOptimiser()

    result = CompositeASTOptimiser()
    if level >= 1:
        result.add_optimiser(ColorCommandShortener())
    if level >= 2:
        result.add_optimiser(LoopDetector())
    return result
