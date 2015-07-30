"""Simple and incomplete parser for Sunlite Suite scene files."""

from itertools import izip_longest


class SceneFile(object):
    """Represents a parsed Sunlite Suite scene file."""

    def __init__(self):
        self.tag = None
        self.timeline = None
        self.fxs = []

    @classmethod
    def from_xml(cls, tag):
        result = cls()

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
        result.channels = [FXChannel.from_xml(channel_tag)
                           for channel_tag in tag.findall("./Ch")]
        return result


class FXChannel(object):
    """Represents an FX channel (``<Ch>`` tag) from a Sunlite Suite scene
    file."""

    def __init__(self):
        self.tag = None
        self.index = None
        self.timeline = None

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
    scene file."""

    def __init__(self):
        self.tag = None
        self.instants = []
        self.steps = []

    def copy_instants_from(self, timeline):
        """Copies the time instants from another timeline, replacing any time
        instants in this object."""
        self.instants = list(timeline.instants)

    @property
    def has_instants(self):
        return len(self.instants) > 0

    def has_same_instants(self, other):
        """Checks whether this timeline has exactly the same time instants as
        some other timeline."""
        return self.instants == other.instants

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

    def iteritems(self):
        return izip_longest(self.instants, self.steps)


class Time(object):
    """Represents a ``<Time>`` tag from an ``<EasyStep>`` timeline object."""

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
    """Represents a ``<Step>`` tag from an ``<EasyStep>`` timeline object."""

    def __init__(self, value=0):
        self.value = value
        self.tag = None

    @classmethod
    def from_xml(cls, tag):
        result = cls(value=int(tag.get("L")))
        result.tag = tag
        return result

    def __repr__(self):
        return "{0.__class__.__name__}(value={0.value!r})".format(self)


class SunliteSuiteParser(object):
    """Simple and incomplete parser for Sunline Suite files."""

    def parse(self, fp):
        """Parses the given input and returns a data structure that represents
        the parsed information.

        :param fp: the input of the parser
        :type fp: file-like
        """
        from lxml import etree
        tree = etree.parse(fp)
        return SceneFile.from_xml(tree)
