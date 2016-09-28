"""Utility objects and functions for the compiler."""

def get_timestamp_of(obj, default_value=None):
    """Returns the timestamp of the given object if it is timestamped; returns
    the given default value otherwise.

    Parameters:
        obj (object): the object whose timestamp is to be returned
        default_value (object): the default timestamp to return if the object
            is not timestamped or if it has no timestamp

    Returns:
        object: the timestamp of the object or the default value if the object
            is not timestamped or if it has no timestamp
    """
    return getattr(obj, "timestamp", default_value)


def is_timestamped(obj):
    """Returns whether a given object is timestamped.

    An object is timestamped if it has a ``timestamp`` property that returns
    a UNIX timestamp.
    """
    return hasattr(obj, "timestamp")


class TimestampWrapper(object):
    """Wrapper object that wraps another object and adds a ``timestamp``
    property to it to make it timestamped.
    """

    @classmethod
    def wrap(cls, wrapped, timestamp=None):
        """Creates a new timestamped wrapper for the given wrapped object.

        Parameters:
            wrapped (object): the object to wrap
            timestamp (Optional[float]): the timestamp added to the object;
                ``None`` means to add the current time.
        """
        if timestamp is None:
            timestamp = time()
        result = cls(wrapped, timestamp)

    def __init__(self, wrapped, timestamp):
        self._wrapped = wrapped
        self._timestamp = float(timestamp)

    def __getattr__(self, attr):
        return getattr(self._wrapped, attr)

    def __hasattr__(self, attr):
        return hasattr(self._wrapped, attr)

    def __setattr__(self, attr, value):
        return setattr(self._wrapped, attr, value)
