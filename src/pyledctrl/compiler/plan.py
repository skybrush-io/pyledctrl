"""Compilation plan being used in the bytecode compiler."""

from collections import defaultdict
from contextlib import AbstractContextManager
from functools import partial
from typing import (
    Any,
    Callable,
    DefaultDict,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
    overload,
)

from .stages import CompilationStage, CompilationStageExecutionEnvironment

__all__ = ("Plan",)


class _FakeProgressBar(AbstractContextManager):  # pragma: no cover
    """Fake progress bar class that provides the same interface as `tqdm.tqdm()`
    to be used in places where `tdqm` does not have to be present.
    """

    def __exit__(self, *args, **kwds):
        pass

    def set_postfix_str(self, *args, **kwds):
        pass

    def update(self, *args, **kwds):
        pass

    def write(self, *args, **kwds):
        pass


class Plan:
    """Represents a compilation plan that consists of a list of steps (stages)
    to execute. Each step must be an instance of CompilationStage_.
    """

    _steps: List[CompilationStage]
    """The list of compilation steps to execute."""

    _output_steps: List[CompilationStage]
    """A sub-list of the compilation steps that are marked as ones that produce
    outputs.
    """

    _callbacks: DefaultDict[Tuple[CompilationStage, str], List[Callable[..., None]]]

    def __init__(self):
        """Constructor."""
        self._steps = []
        self._output_steps = []
        self._callbacks = defaultdict(list)

    def add_step(self, step: CompilationStage) -> "Continuation":
        """Adds the given step to the plan after any other step that has been
        added previously.

        Parameters:
            step: the step to add

        Returns:
            a helper object that can be used to attach hook functions to the
            execution of the step
        """
        self._steps.append(step)
        return Continuation(self, step)

    def execute(
        self,
        environment: Optional[CompilationStageExecutionEnvironment] = None,
        *,
        description: Optional[str] = None,
        force: bool = False,
        progress: bool = False,
        verbose: bool = False,
    ) -> tuple:
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

        Returns:
            a tuple containing one object for each step in the execution plan
            that was marked as an output step, in exactly the same order as
            the output steps were marked as such

        Raises:
            CompilerError: in case of a compilation error
        """
        environment = environment or CompilationStageExecutionEnvironment()

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

            progress_bar_factory = partial(tqdm, **tqdm_kwds)
        except ImportError:  # pragma: no cover
            progress_bar_factory = _FakeProgressBar

        with progress_bar_factory() as progress_bar:
            while step_index < num_steps:
                step = self._steps[step_index]
                is_output_step = step in self._output_steps

                progress_bar.set_postfix_str(getattr(step, "label", "working..."))

                if force or is_output_step or step.should_run():
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
                            if hasattr(step, "output_object"):
                                callback(step.output_object)  # type: ignore
                            elif hasattr(step, "output"):
                                callback(step.output)  # type: ignore
                            else:
                                callback()

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

        # Collect the results of the output steps into a result list
        result = [step.output_object for step in self._output_steps]  # type: ignore

        # Unwrap timestamped objects from the result before returning them
        result = [getattr(item, "wrapped", item) for item in result]

        # Return a tuple to prevent mutation
        return tuple(result)

    def insert_step(
        self,
        step: CompilationStage,
        *,
        before: Optional[CompilationStage] = None,
        after: Optional[CompilationStage] = None,
    ) -> "Continuation":
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
        """
        if (before is None) == (after is None):
            raise ValueError("exactly one of before=... and after=... must be None")
        index = self._steps.index(before or after)  # type: ignore
        if before is None:
            index += 1
        self._steps.insert(index, step)
        return Continuation(self, step)

    def iter_steps(self, cls: Optional[type] = None) -> Iterable[CompilationStage]:
        """Iterates over the steps of this compilation plan.

        Parameters:
            cls: when it is not ``None``, only the steps that are instances of
                the given class are returned

        Yields:
            CompilationStage: each compilation stage in this plan
        """
        if cls is None:
            return iter(self._steps)
        else:
            return (step for step in self._steps if isinstance(step, cls))

    @overload
    def when_step_is_done(
        self, step: CompilationStage, *args: Any
    ) -> Callable[[Callable[..., None]], Callable[..., None]]: ...

    @overload
    def when_step_is_done(
        self, step: CompilationStage, func: Callable[..., None], *args: Any
    ) -> None: ...

    def when_step_is_done(self, step: CompilationStage, func=None, *args: Any) -> Any:
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
            return self._register_callback(
                step, "done", partial(func, *args) if args else func
            )
        else:

            def decorator(
                decorated: Callable[..., None], *args: Any
            ) -> Callable[..., None]:
                self.when_step_is_done(step, decorated, *args)
                return decorated

            return decorator

    def _get_message_for_step(self, step: CompilationStage) -> str:
        """Returns the message to be shown on the console when the given step
        is being executed.
        """
        class_name = step.__class__.__name__
        step_id = getattr(step, "id", None)
        if step_id is not None:
            return "Executing {0} (id={1})...".format(class_name, step_id)
        else:
            return "Executing {0}...".format(class_name)

    def mark_as_output(self, step: CompilationStage) -> None:
        """Marks the given compilation step as an output step. The results of
        the output steps will be returned by the ``execute()`` method of the
        plan.
        """
        if step not in self._steps:
            raise RuntimeError("step is not part of the plan")

        self._output_steps.append(step)

    def _register_callback(
        self, step: CompilationStage, callback_type: str, func: Callable[..., None]
    ) -> None:
        self._callbacks[step, callback_type].append(func)


C = TypeVar("C", bound="Continuation")


class Continuation:
    """Helper object that is returned from the ``add_step()`` and
    ``insert_step()`` methods of Plan_ in order to help specifying hook
    functions for the execution of a compilation step.
    """

    def __init__(self, plan: Plan, step: CompilationStage):
        """Constructor.

        Parameters:
            plan: the compilation plan
            step: the compilation step
        """
        self.plan = plan
        self.step = step

    def and_when_done(self: C, func: Callable[..., None], *args: Any) -> C:
        """Specifies the given function to be called when the plan finishes
        the execution of the step. The function will be invoked with the
        value of the ``output`` property of the step if it has such a
        property, otherwise it will be invoked with no arguments.

        Parameters:
            func (callable): the callable to call when the step finishes

        Returns:
            the continuation object itself for easy chaining
        """
        self.plan.when_step_is_done(self.step, func, *args)
        return self

    def mark_as_output(self: C) -> C:
        """Marks the compilation step as an output step so the plan knows that
        the output of the compilation step has to be exposed explicitly in the
        result object.
        """
        self.plan.mark_as_output(self.step)
        return self
