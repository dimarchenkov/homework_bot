class HomeworkStatusError(KeyError):
    """Homework status error."""

    pass


class HomeworkExistingKey(Exception):
    """Value do not contains key."""

    pass


class HTTPStatusErrorNOT_FOUND(Exception):
    """Bad HTTP response status."""

    pass


class HTTPStatusErrorBAD_REQUEST(Exception):
    """Bad HTTP response status."""

    pass


class HTTPStatusErrorUNAUTHORIZED(Exception):
    """Bad HTTP response status."""

    pass
