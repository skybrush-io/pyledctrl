"""Compilation plan being used in the bytecode compiler."""

from __future__ import division

from collections import defaultdict
from functools import partial

__all__ = ("Plan",)


class _FakeProgressBar(object):
    """Fake progress bar class that provides the same interface as `tqdm.tqdm()`
    to be used in places where `tdqm` does not have to be present (e.g.,
    Blender).
    """

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwds):
        pass

    def set_postfix_str(self, *args, **kwds):
        pass

    def update(self, *args, **kwds):
        pass

    def write(self, *args, **kwds):
        pass


class Plan(object):
    """Represents a compilation plan that consists of a list of steps (stages)
    to execute. Each step must be an instance of CompilationStage_.
    """

    def __init__(self):
        """Constructor."""
        self._steps = []
        self._output_steps = set()
        self._callbacks = defaultdict(list)

    def add_step(self, step, output=False):
        """Adds the given step to the plan after any other step that has been
        added previously.

        Parameters:
            step (CompilationStage): the step to add
            output (bool): whether to mark the step as an output step. The
                results of steps marked as an output step will be returned
                by the ``execute()`` method.

        Returns:
            Continuation: a helper object that can be used to attach hook
                functions to the execution of the step
        """
        self._steps.append(step)
        if output:
            self._mark_as_output(step)
        return Continuation(self, step)

    def execute(
        self,
        environment,
        *,
        description: str = None,
        force: bool = False,
        progress: bool = False,
        verbose: bool = False,
    ):
        """Executes the steps of the plan.

        Parameters:
            environment (CompilationStageExecutionEnvironment): the execution
                environment of each compilation stage, provided by the
                compiler that calls this function
            force: force the execution of all steps even if the steps indicate
                that they not need to be run
            progress: whether to show a progress bar to indicate the progress of
                the plan execution
            description: a short string to display next to the progress bar that
                tells the user what we are compiling now
            verbose: whether to print verbose messages about the progress of the
                plan execution

        Raises:
            CompilerError: in case of a compilation error
        """
        result = []
        bar_format = "{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}{postfix}"

        step_index, num_steps = 0, len(self._steps)

        tqdm_kwds = {
            "desc": description,
            "disable": not progress,
            "bar_format": bar_format,
            "total": num_steps,
        }
        try:
            from tqdm import tqdm

            progress = partial(tqdm, **tqdm_kwds)
        except ImportError:
            progress = _FakeProgressBar

        with progress() as progress_bar:
            while step_index < num_steps:
                step = self._steps[step_index]
                is_last = step_index == num_steps - 1

                progress_bar.set_postfix_str(getattr(step, "label", "working..."))

                if force or is_last or step.should_run():
                    # Print information about the step being executed if
                    # needed
                    if verbose:
                        message = self._get_message_for_step(step)
                        progress_bar.write(message)

                    # Run the step
                    step.run(environment=environment)

                    # Call any 'done' callbacks for the step
                    callbacks = self._callbacks.get((step, "done"))
                    if callbacks:
                        for callback in callbacks:
                            if hasattr(step, "output"):
                                callback(step.output)
                            else:
                                callback()

                    # If this was an output step, collect the result
                    if step in self._output_steps:
                        result.append(step.output)

                    # Re-evaluate num_steps because the last step may have
                    # appended more steps to the plan on-the-fly
                    num_steps = len(self._steps)
                    new_step_index = self._steps.index(step) + 1
                    delta_step_index = new_step_index - step_index
                    step_index = new_step_index

                    # Update the progress bar
                    progress_bar.total = num_steps
                    progress_bar.update(delta_step_index)

            progress_bar.set_postfix_str("done.")

        # Unwrap timestamped objects from the result before returning them
        result = [getattr(item, "wrapped", item) for item in result]
        return result

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
            raise ValueError("exactly one of before=... and after=... must be None")
        index = self._steps.index(before or after)
        if before is None:
            index += 1
        self._steps.insert(index, step)
        if output:
            self._mark_as_output(step)
        return Continuation(self, step)

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

    def when_step_is_done(self, step, func=None):
        """Registers a function to be called when the given compilation
        step is done.

        Parameters:
            step (CompilationStage): the compilation stage
            func (Optional[callable]): the function to be called. It will be
                called with the output of the stage if it has an ``output``
                attribute, or with no arguments otherwise. When omitted, the
                function acts as a decorator, i.e. it will return another
                function that registers the decorated function as a callback.
        """
        if func is not None:
            return self._register_callback(step, "done", func)
        else:

            def decorator(decorated):
                self.when_step_is_done(step, decorated)
                return decorated

            return decorator

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

    def _register_callback(self, step, callback_type, func):
        self._callbacks[step, callback_type].append(func)


class Continuation(object):
    """Helper object that is returned from the ``add_step()`` and
    ``insert_step()`` methods of Plan_ in order to help specifying hook
    functions for the execution of a compilation step.
    """

    def __init__(self, plan, step):
        """Constructor.

        Parameters:
            plan (Plan): the compilation plan
            step (CompilationStage): the compilation step
        """
        self.plan = plan
        self.step = step

    def and_when_done(self, func):
        """Specifies the given function to be called when the plan finishes
        the execution of the step. The function will be invoked with the
        value of the ``output`` property of the step if it has such a
        property, otherwise it will be invoked with no arguments.

        Parameters:
            func (callable): the callable to call when the step finishes
        """
        self.plan.when_step_is_done(self.step, func)
