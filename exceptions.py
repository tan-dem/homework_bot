from telegram.error import TelegramError


class CheckTokensError(Exception):
    """Если отсутствуют обязательные переменные окружения."""

    pass


class APIResponseError(Exception):
    """Если API не возвращает ожидаемый ответ."""

    pass


class APIHTTPStatusError(Exception):
    """Если API недоступен."""

    pass


class TelegramFailureError(TelegramError):
    """Если telegram недоступен."""

    pass
