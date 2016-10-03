"""Simple and incomplete parser for Sunlite Suite scene files."""

from __future__ import division

from bisect import bisect
from itertools import izip_longest


class SceneFile(object):
    """Represents a parsed Sunlite Suite scene file (with extension
    ``.sce``)."""

    def __init__(self):
        self.tag = None
        self.timeline = None
        self.fxs = []

    @classmethod
    def from_xml(cls, tag):
        result = cls()
        result.tag = tag

        # Parse the global timeline
        timeline_tag = tag.find("./EasyStep")
        if timeline_tag is not None:
            result.timeline = EasyStepTimeline.from_xml(timeline_tag)

        # Parse the FX objects
        result.fxs = [FX.from_xml(fx_tag)
                      for fx_tag in tag.findall("./Fxs/Fx")]

        # Attach the global timeline to the channels that have no timeline
        # on their own
        for fx in result.fxs:
            for channel in fx.channels:
                if channel.timeline is None:
                    channel.timeline = result.timeline
                elif not channel.timeline.has_instants:
                    channel.timeline.copy_instants_from(result.timeline)

        return result

    def shift(self, by):
        """Shifts all the time steps in the timeline of the file by the given
        amount."""
        timelines_to_shift = set()
        timelines_to_shift.add(self.timeline)
        for fx in self.fxs:
            for channel in fx.channels:
                timelines_to_shift.add(channel.timeline)
        for timeline in timelines_to_shift:
            if timeline is not None:
                timeline.shift(by=by)


class FX(object):
    """Represents an FX object (``<Fx>`` tag) from a Sunlite Suite scene
    file."""

    def __init__(self):
        self.tag = None
        self.channels = []
        self.id = None

    @classmethod
    def from_xml(cls, tag):
        """Creates an FX object from its XML representation."""
        result = cls()
        result.tag = tag
        result.id = tag.get("ID")
        for index, channel_tag in enumerate(tag.findall("./Ch")):
            channel = FXChannel.from_xml(channel_tag)
            assert channel.index == index
            result.channels.append(channel)
        return result

    def add_channel(self, timeline=None):
        """Adds a new channel with the given timeline to the FX object.

        Parameters:
            timeline (Optional[EasyStepTimeline]): the timeline of the new
                channel that will be created

        Returns:
            FXChannel: the newly created channel object
        """
        new_channel = FXChannel(index=len(self.channels))
        new_channel.timeline = timeline
        self.channels.append(new_channel)
        return new_channel


class FXChannel(object):
    """Represents an FX channel (``<Ch>`` tag) from a Sunlite Suite scene
    file."""

    def __init__(self, index=None, timeline=None):
        self.tag = None
        self.index = index
        self.timeline = timeline

    @classmethod
    def from_xml(cls, tag):
        """Creates an FX channel object from its XML representation."""
        result = cls()
        result.tag = tag
        result.index = int(tag.get("Index"))
        timeline_tag = tag.find("EasyStep")
        if timeline_tag is not None:
            result.timeline = EasyStepTimeline.from_xml(timeline_tag)
        return result


class EasyStepTimeline(object):
    """Represents an ``<EasyStep>`` timeline object from a Sunlite Suite
    scene file.

    The sub-tags of this tag are ``<Time>`` tags with a ``Fade`` and a
    ``Wait`` attribute. Each such tag represents a point on the timeline
    when "something" happens with one of the lights in the file.
    """

    def __init__(self):
        self.tag = None
        self.clear()

    def clear(self):
        """Clears the timeline, i.e. removes all instants and steps."""
        self.instants = []
        self.steps = []

    def copy(self):
        """Creates a deep copy of this timeline into another."""
        result = self.__class__()
        result.instants = [instant.copy() for instant in self.instants]
        result.steps = list(self.steps)
        return result

    def copy_instants_from(self, timeline):
        """Copies the time instants from another timeline, replacing any time
        instants in this object."""
        self.instants = list(timeline.instants)

    @classmethod
    def from_xml(cls, tag):
        result = cls()
        result.tag = tag

        time = 0
        for time_tag in tag.findall("./Time"):
            time_obj = Time.from_xml(time_tag, time=time)
            result.instants.append(time_obj)
            time += time_obj.total_duration
        if time > 0:
            result.instants.append(Time(time=time))

        for step_tag in tag.findall("./Step"):
            result.steps.append(Step.from_xml(step_tag))

        return result

    def get_step_for_time(self, time):
        for index, time_obj in enumerate(self.instants):
            if time_obj.time == time:
                return self.steps[index]
        return None

    @property
    def has_instants(self):
        return len(self.instants) > 0

    def has_same_instants(self, other):
        """Checks whether this timeline has exactly the same time instants as
        some other timeline."""
        return self.instants == other.instants

    def iteritems(self):
        return izip_longest(self.instants, self.steps)

    def loop_until(self, end):
        """Loops the sequence in the timeline until the given frame count is
        reached.

        Parameters:
            end (Optional[int]): the desired new frame count of the timeline.
                ``None`` means not to loop at all.
        """
        if end is None:
            # There is nothing to repeat so we can return here
            return

        if not self.has_instants:
            # There are no instants so we can return here
            return

        if len(self.instants) == 1:
            # There is only a single instant. Increase its wait time, set the
            # fade time to zero and add an extra step with the same value
            instant = self.instants[0]
            instant.wait = end - instant.time
            instant.fade = 0

            self.instants.append(Time(time=end))
            self.steps.append(self.steps[0].copy())
            return

        # We have at least two instants so we can loop sensibly.
        # Get the current range first.
        start, current_end = self.range

        # Get the part to be repeated -- this is essentially all the steps
        # but the last one
        to_repeat = list(zip(self.instants, self.steps))
        to_repeat.pop()
        total_length = current_end - start

        # Repeat the current timeline until we are longer than the desired
        # endpoint
        shift = total_length
        to_insert = []
        while start + shift < end:
            to_insert.extend(
                (instant.shifted(by=shift), value)
                for instant, value in to_repeat
            )
            shift += total_length

        # Insert the repeated part into the timeline
        if to_insert:
            self.instants[-1:-1], self.steps[-1:-1] = zip(*to_insert)

        # Update the last time step to end at start + shift
        self.instants[-1].time = start + shift

        # Now trim the timeline to ensure that the timeline ends exactly at
        # the desired position
        self.trim(at=end)

    def looped(self, until):
        """Copies this timeline and loops the copy until the given frame count
        is reached.
        """
        result = self.copy()
        result.loop_until(end=until)
        return result

    def merge_from(self, other):
        """Merges the contents of another timeline into this timeline.

        Currently no overlaps are allowed between the two timelines, i.e.
        the interval spanned by the time instants of this timeline must
        come fully before or after the interval of the other timeline. This
        may be changed later. The first or last time instant of this timeline
        may overlay with the first or last time instant of the other timeline;
        in this case, the steps from the second timeline will take precedence
        over the steps of the first timeline.
        """
        self_range = self.range
        other_range = other.range
        if self.has_instants and other.has_instants and \
                (self_range[1] > other_range[0] or other_range[1] < self_range[0]):
            raise NotImplementedError("not implemented for overlapping ranges "
                                      "yet ( {0} and {1} )"
                                      .format(self_range, other_range))

        self_comes_first = self.range[1] <= other_range[0]
        if self_comes_first:
            if self.has_instants and self_range[1] == other_range[0]:
                self.instants.pop()
                self.steps.pop()
            self.instants.extend(instant.copy() for instant in other.instants)
            self.steps.extend(other.steps)
        else:
            other_end = len(other.instants)
            if other.has_instants and self_range[0] == other_range[1]:
                other_end -= 1
            self.instants[0:0] = [instant.copy() for instant in other.instants[:other_end]]
            self.steps[0:0] = other.steps

    @property
    def range(self):
        """The range spanned by this timeline. It is assumed to be closed from
        the left and open from the right.
        """
        if not self.has_instants:
            return (0, 0)
        else:
            return (self.instants[0].time, self.instants[-1].time)

    def shift(self, by):
        """Shifts all the time steps in the timeline by the given amount."""
        for instant in self.instants:
            instant.shift(by=by)

    def shifted(self, by):
        """Copies this timeline and shifts all the time steps in the copy by
        the given amount."""
        copy = self.copy()
        copy.shift(by=by)
        return copy

    def trim(self, at):
        """Trims the timeline at the given frame. When the given frame has no
        corresponding value, the new value will be interpolated from the
        surrounding ones.
        """
        keys = [instant.time for instant in self.instants]
        pos = bisect(keys, at)

        # bisect() returns an insertion point _after_ the time instant if the
        # time instant is on the timeline. However, we don't really care --
        # the interpolation would work either way.

        if pos == 0:
            # Entire timeline has to be thrown away; nothing remains
            self.clear()
        elif pos == len(keys):
            # Entire timeline has to be kept; there is no need to interpolate
            pass
        else:
            # Interpolate between instants[pos-1] and instants[pos].
            # instants[pos-1] has a "wait time" and a "fade time". The value
            # is constant during the wait time and then it is faded during the
            # fade time, so when interpolating, we need to take the wait time
            # into account, and also update the "wait time" and "fade time"
            # of instants[pos-1].
            instant_before = self.instants[pos-1]
            end_of_wait = instant_before.end_of_wait
            instant_before.fade = max(at - end_of_wait, 0)
            if instant_before.fade == 0:
                value = self.steps[pos-1].value
                instant_before.end_of_wait = at
            else:
                dt = self.instants[pos].time - end_of_wait
                ratio = (at - end_of_wait) / dt
                value = (1-ratio) * self.steps[pos-1].value + \
                    ratio * self.steps[pos].value

            # Discard the part of the list after pos
            del self.instants[pos:]
            del self.steps[pos:]

            # Insert the new value
            self.instants.insert(pos, Time(time=at))
            self.steps.insert(pos, Step(value=value))

    def trimmed(self, at):
        """Copies this timeline and trims the copy at the given frame."""
        copy = self.copy()
        copy.trim(at)
        return copy


class Time(object):
    """Represents a ``<Time>`` tag from an ``<EasyStep>`` timeline object.

    A ``<Time>`` tags represents a time instant when "something" happens in
    the file. It has two durations: a wait time and a fade time. The total
    duration of the time step is the sum of the fade time and the wait time.
    The *absolute* position of the time instant on the timeline depends on the
    other ``<Time>`` tags and their ordering in the surrounding ``<EasyStep>``
    timeline object. Nevertheless, the absolute position is also stored there
    in the ``time`` property.
    """

    __slots__ = ("time", "fade", "wait", "tag")

    def __init__(self, time=0, fade=0, wait=0):
        self.tag = None
        self.time = time
        self.fade = fade
        self.wait = wait

    @classmethod
    def from_xml(cls, tag, time=0):
        result = cls(
            time=time,
            fade=int(tag.get("Fade")),
            wait=int(tag.get("Wait"))
        )
        result.tag = tag
        return result

    def copy(self, shift_by=0):
        """Returns a deep copy of the time step, optionally shifted by a given
        number of frames"""
        return self.__class__(time=self.time + shift_by,
                              fade=self.fade, wait=self.wait)

    @property
    def end_of_wait(self):
        """The index of the frame when the *waiting* part of this step ends
        (and the *fading* part starts). We assume that the waiting comes first.
        """
        return self.time + self.wait

    @end_of_wait.setter
    def end_of_wait(self, value):
        if value < self.time:
            raise ValueError("cannot set negative wait time")
        self.wait = value - self.time

    def shift(self, by):
        """Shifts the time step on the time axis by the given amount."""
        self.time += by

    def shifted(self, by):
        """Returns a copy of the time step after shifting it on the time axis by
        the given amount."""
        return self.copy(shift_by=by)

    @property
    def total_duration(self):
        """The total duration of the time step on the timeline. The total
        duration is the sum of the wait time and the fade time."""
        return self.wait + self.fade

    def __eq__(self, other):
        return self.time == other.time and self.fade == other.fade and \
            self.wait == other.wait

    __hash__ = None

    def __repr__(self):
        return "{0.__class__.__name__}(time={0.time!r}, fade={0.fade!r}, wait={0.wait!r})".format(self)


class Step(object):
    """Represents a ``<Step>`` tag from an ``<EasyStep>`` timeline object.

    This type is immutable.
    """

    __slots__ = ("_value", )

    def __init__(self, value=0):
        self._value = value

    @classmethod
    def from_xml(cls, tag):
        result = cls(value=int(tag.get("L")))
        return result

    def updated(self, value):
        return self.__class__(value=value)

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return "{0.__class__.__name__}(value={0.value!r})".format(self)


class Button(object):
    """Represents a ``<Button>`` tag from an ``<EasyShow>`` ``.ses`` file."""

    def __init__(self, position=0, size=0, name=None):
        self.position = position
        self.size = size
        self.name = name
        self.tag = None

    @property
    def left(self):
        """Read-only alias for the ``position`` property."""
        return self.position

    @property
    def right(self):
        """Read-only alias for ``position+size``."""
        return self.position + self.size

    @classmethod
    def from_xml(cls, tag):
        result = cls(position=int(tag.get("position", 0)),
                     size=int(tag.get("size", 0)),
                     name=tag.get("name"))
        result.tag = tag
        return result

    def __repr__(self):
        return "{0.__class__.__name__}(position={0.position!r}, "\
            "size={0.size!r}, name={0.name!r})".format(self)


class SwitchFile(object):
    """Represents a parsed Sunlite Suite switch file (with extension
    ``.ses``).
    """

    def __init__(self):
        self.tag = None
        self.files = {}
        self.buttons = []

    @classmethod
    def from_xml(cls, tag):
        result = cls()
        result.tag = tag

        # Parse the file entries
        file_tags = tag.findall("./bin/light_data/file")
        filenames = [file_tag.get("name") for file_tag in file_tags]
        result.files = dict((filename, filename) for filename in filenames)

        # Parse the button entries
        button_tags = tag.findall("./time_line/tl_light_data/switch/button")
        result.buttons = [
            Button.from_xml(button_tag) for button_tag in button_tags
        ]

        return result


class SunliteSuiteSceneFileParser(object):
    """Simple and incomplete parser for Sunline Suite scene files."""

    def parse(self, fp):
        """Parses the given input and returns a data structure that represents
        the parsed information.

        :param fp: the input of the parser
        :type fp: file-like
        """
        from lxml import etree
        tree = etree.parse(fp)
        return SceneFile.from_xml(tree)


class SunliteSuiteSwitchFileParser(object):
    """Simple and incomplete parser for Sunline Suite files."""

    def parse(self, fp):
        """Parses the given input and returns a data structure that represents
        the parsed information.

        :param fp: the input of the parser
        :type fp: file-like
        """
        from lxml import etree
        tree = etree.parse(fp)
        return SwitchFile.from_xml(tree)
