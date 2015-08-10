"""Compilation plan being used in the bytecode compiler."""

__all__ = ["Plan"]


class Plan(object):
    """Represents a compilation plan that consists of a list of steps (stages)
    to execute. Each step must be an instance of CompilationStage_.
    """

    def __init__(self):
        self._steps = []

    def add_step(self, step):
        """Adds the given step to the plan after any other step that has been
        added previously."""
        self._steps.append(step)

    def execute(self, force=False):
        """Executes the steps of the plan.

        :param force: force the execution of all steps even if the steps
            indicate that they not need to be run
        :type force: bool

        :raises CompilerError: in case of a compilation error
        """
        last_step = self._steps[-1] if self._steps else None
        for step in self.iter_steps():
            if force or step == last_step or step.should_run():
                step.run()

    def insert_step(self, step, before=None, after=None):
        """Inserts the given step before or after some other step that is
        already part of the compilation plan.

        Exactly one of ``before`` and ``after`` must be ``None``; the other
        must be a step that is already part of the plan.

        :param step: the step to insert
        :type step: CompilationStage
        :param before: the step before which the new step is to be inserted
        :type before: CompilationStage or None
        :param after: the step after which the new step is to be inserted
        :type after: CompilationStage or None
        """
        if (before is None) == (after is None):
            raise ValueError("exactly one of before=... and after=... must be None")
        index = self._steps.index(before or after)
        if before is None:
            index += 1
        self._steps.insert(index, step)

    def iter_steps(self, cls=None):
        """Iterates over the steps of this compilation plan.

        :param cls: optional class filter; when it is not ``None``, only the
            steps that are instances of the given class are returned
        :type cls: type or None
        """
        if cls is None:
            return iter(self._steps)
        else:
            return (step for step in self._steps if isinstance(step, cls))
