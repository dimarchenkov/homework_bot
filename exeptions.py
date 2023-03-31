class HomeworkStatusError(KeyError):
    """Homework status error."""

    pass


class HomeworkExistingKey(Exception):
    """Value do not contains key."""

    pass


class HTTPStatusError(Exception):
    """Bad HTTP response status."""

    pass


class RequestError(Exception):
    """Bad HTTP response status."""

    pass


class ConnectionError(Exception):
    """Bad HTTP response status."""

    pass
