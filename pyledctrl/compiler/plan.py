"""Compilation plan being used in the bytecode compiler."""

from tqdm import tqdm

__all__ = ("Plan", )


class Plan(object):
    """Represents a compilation plan that consists of a list of steps (stages)
    to execute. Each step must be an instance of CompilationStage_.
    """

    def __init__(self):
        """Constructor."""
        self._steps = []
        self._output_steps = set()

    def add_step(self, step, output=False):
        """Adds the given step to the plan after any other step that has been
        added previously.

        Parameters:
            step (CompilationStage): the step to add
            output (bool): whether to mark the step as an output step. The
                results of steps marked as an output step will be returned
                by the ``execute()`` method.
        """
        self._steps.append(step)
        if output:
            self._mark_as_output(step)

    def execute(self, environment, force=False, verbose=False):
        """Executes the steps of the plan.

        Parameters:
            environment (CompilationStageExecutionEnvironment): the exection
                environment of each compilation stage, provided by the
                compiler that calls this function
            force (bool): force the execution of all steps even if the steps
                indicate that they not need to be run
            verbose (bool): whether to print verbose messages about the
                progress of the plan execution

        Raises:
            CompilerError: in case of a compilation error
        """
        last_step = self._steps[-1] if self._steps else None
        result = []
        bar_format = "{desc}{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}"
        progress_bar = tqdm(self._steps, bar_format=bar_format)
        for step in progress_bar:
            if force or step == last_step or step.should_run():
                if verbose:
                    message = self._get_message_for_step(step)
                    progress_bar.write(message)
                step.run(environment=environment)
                if step in self._output_steps:
                    result.append(step.output)

    def insert_step(self, step, before=None, after=None, output=False):
        """Inserts the given step before or after some other step that is
        already part of the compilation plan.

        Exactly one of ``before`` and ``after`` must be ``None``; the other
        must be a step that is already part of the plan.

        Parameters:
            step (CompilationStage): the step to insert
            before (Optional[CompilationStage]): the step before which the
                new step is to be inserted
            after (Optional[CompilationStage]): the step after which the
                new step is to be inserted
            output (bool): whether to mark the step as an output step
        """
        if (before is None) == (after is None):
            raise ValueError("exactly one of before=... and after=... "
                             "must be None")
        index = self._steps.index(before or after)
        if before is None:
            index += 1
        self._steps.insert(index, step)
        if output:
            self._mark_as_output(step)

    def iter_steps(self, cls=None):
        """Iterates over the steps of this compilation plan.

        Parameters:
            cls (Optional[type]): when it is not ``None``, only the steps
                that are instances of the given class are returned

        Yields:
            CompilationStage: each compilation stage in this plan
        """
        if cls is None:
            return iter(self._steps)
        else:
            return (step for step in self._steps if isinstance(step, cls))

    def _get_message_for_step(self, step):
        """Returns the message to be shown on the console when the given step
        is being executed.
        """
        class_name = step.__class__.__name__
        step_id = getattr(step, "id", None)
        if step_id is not None:
            return "Executing {0} (id={1})...".format(class_name, step_id)
        else:
            return "Executing {0}...".format(class_name, step_id)

    def _mark_as_output(self, step):
        """Marks the given compilation step as an output step. The results of
        the output steps will be returned by the ``execute()`` method of the
        plan.
        """
        self._output_steps.add(step)
