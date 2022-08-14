from telegram.error import TelegramError

class APIResponseError(Exception):
    """Если API не возвращает ожидаемый ответ."""

    pass


class APIHTTPStatusError(Exception):
    """Если API недоступен."""

    pass


class TelegramFailureError(TelegramError):
    """Если telegram недоступен."""

    pass
