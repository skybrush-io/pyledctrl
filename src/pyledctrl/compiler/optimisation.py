"""AST optimization routines for the ledctrl compiler."""

from itertools import islice
from operator import attrgetter
from pyledctrl.compiler.ast import (
    Duration,
    Node,
    NodeTransformer,
    SetBlackCommand,
    SetGrayCommand,
    SetWhiteCommand,
    SetColorCommand,
    FadeToBlackCommand,
    FadeToGrayCommand,
    FadeToWhiteCommand,
    FadeToColorCommand,
    SleepCommand,
    LoopBlock,
    StatementSequence,
)
from pyledctrl.compiler.utils import TimestampWrapper


def are_statements_equivalent(first, second):
    """Returns whether two statements in the syntax tree are equivalent for
    the purposes of loop identification and optimization.
    """
    return hasattr(first, "is_equivalent_to") and first.is_equivalent_to(second)


class ASTOptimiser:
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
        """Dummy implementation that does nothing."""
        return False


class CompositeASTOptimiser(ASTOptimiser):
    """Composite AST optimiser that uses multiple "child optimisers" and
    returns if none of the child optimisers can modify the AST any more.
    """

    def __init__(self):
        """Constructor."""
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

        - ``set_color(0, 0, 0, duration)`` is replaced by
          ``set_black(duration)``

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
                return SetGrayCommand(value=node.color.red, duration=node.duration)
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
                return FadeToGrayCommand(value=node.color.red, duration=node.duration)
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


class CommandMerger(ASTOptimiser):
    """AST optimiser that merges consecutive commands into one if they
    meet certain conditions.

    This optimiser uses the following rules:

        - A ``set_color()`` command with a given color is merged with any
          ``set_color()``, ``fade_to_color()`` or ``sleep()`` commands that
          follow it if they refer to *exactly* the same color (the color
          restriction is not applicable for ``sleep()`` of course). The final
          command will have a duration corresponding to the total duration of
          the commands that were merged.

        - A ``fade_to_color()`` command followed by a sequence of additional
          ``fade_to_color()``, ``set_color()`` or ``sleep()`` commands of
          exactly the same color are replaced by the first command and
          a ``sleep()`` command with its duration equal to the total duration
          of the *remaining* commands that were merged.

        - A sequence of ``sleep()`` commands are replaced by a single
          ``sleep()`` command whose duration equals the total duration of the
          commands that were merged.
    """

    class Transformer(NodeTransformer):
        """AST transformer that analyses ``StatementSequence`` nodes and
        replaces command sequences described in the desription of
        CommandMerger_ appropriately.
        """

        def _handle_set_color_command(self, body, index):
            original_command = body[index]
            assert isinstance(original_command, SetColorCommand)
            color = original_command.color
            duration, length = 0, 0
            for statement in islice(body, index, None):
                if isinstance(statement, SetColorCommand) and statement.color.equals(
                    color
                ):
                    duration += statement.duration.value
                elif isinstance(
                    statement, FadeToColorCommand
                ) and statement.color.equals(color):
                    duration += statement.duration.value
                elif isinstance(statement, SleepCommand):
                    duration += statement.duration.value
                else:
                    break
                length += 1

            if length > 1:
                duration = Duration(value=duration)
                replacement = [SetColorCommand(color=color, duration=duration)]
                return length, replacement
            else:
                return None, None

        def _handle_fade_to_color_command(self, body, index):
            original_command = body[index]
            assert isinstance(original_command, FadeToColorCommand)
            color = original_command.color
            duration, length = 0, 1
            for statement in islice(body, index + 1, None):
                if isinstance(statement, SetColorCommand) and statement.color.equals(
                    color
                ):
                    duration += statement.duration.value
                elif isinstance(
                    statement, FadeToColorCommand
                ) and statement.color.equals(color):
                    duration += statement.duration.value
                elif isinstance(statement, SleepCommand):
                    duration += statement.duration.value
                else:
                    break
                length += 1

            if length > 1:
                duration = Duration(value=duration)
                replacement = [original_command, SleepCommand(duration=duration)]
                return length, replacement
            else:
                return None, None

        def _handle_sleep_command(self, body, index):
            original_command = body[index]
            assert isinstance(original_command, SleepCommand)
            duration, length = 0, 0
            for statement in islice(body, index, None):
                if isinstance(statement, SleepCommand):
                    duration += statement.duration.value
                else:
                    break
                length += 1

            if length > 1:
                duration = Duration(value=duration)
                replacement = [SleepCommand(duration=duration)]
                return length, replacement
            else:
                return None, None

        def visit_StatementSequence(self, node):
            body = node.statements
            index = 0
            num_statements = len(body)
            while index < num_statements:
                statement = body[index]
                if isinstance(statement, SetColorCommand):
                    length_to_replace, replacement = self._handle_set_color_command(
                        body, index
                    )
                elif isinstance(statement, FadeToColorCommand):
                    length_to_replace, replacement = self._handle_fade_to_color_command(
                        body, index
                    )
                elif isinstance(statement, SleepCommand):
                    length_to_replace, replacement = self._handle_sleep_command(
                        body, index
                    )
                else:
                    replacement = None
                if replacement is not None:
                    body[index : (index + length_to_replace)] = replacement
                    index += len(replacement)
                    num_statements = len(body)
                else:
                    index += 1

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

        def _identify_loop_iteration_count(
            self, statements, start_index, loop_body_length
        ):
            """Identifies the maximum iteration count of a potential loop
            that starts at the given index and has the given assumed body
            length.
            """
            num_statements = len(statements)
            first, second = start_index, start_index + loop_body_length
            while second < num_statements and statements[first].is_equivalent_to(
                statements[second]
            ):
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
                end = index + 1
                max_end = min(num_statements, index + self.max_loop_len)
                for end in range(index + 1, max_end):
                    end_statement = body[end]
                    if are_statements_equivalent(statement, end_statement):
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
                    blocks = [
                        LoopBlock(
                            iterations=iterations_,
                            body=StatementSequence(body[index:end]),
                        )
                        for end, iterations_ in potential_loops
                    ]
                    best_block = min(blocks, key=attrgetter("length_in_bytes"))
                    end = index + best_block.iterations.value * len(
                        best_block.body.statements
                    )
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
        result.add_optimiser(CommandMerger())
        result.add_optimiser(ColorCommandShortener())
    if level >= 2:
        result.add_optimiser(LoopDetector())
    return result
