import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from exceptions import (
    APIHTTPStatusError,
    APIResponseError,
    TelegramFailureError,
)
from settings import (
    ENDPOINT,
    HEADERS,
    PRACTICUM_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_TOKEN,
)

logger = logging.getLogger('__main__')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


RETRY_TIME = 120


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение отправлено: "{message}"')
    except TelegramFailureError as error:
        logger.error(f'Сбой при отправке сообщения: {error}')
        raise TelegramFailureError(f'Сбой при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпойнту API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logger.info('Успешный запрос к API')
    except APIResponseError as error:
        logger.error(f'Ошибка при запросе к API: {error}')
        raise APIResponseError(f'Ошибка при запросе к API: {error}')

    if response.status_code != HTTPStatus.OK:
        logger.error(f'API недоступен, код {response.status_code}')
        raise APIHTTPStatusError(f'API недоступен, код {response.status_code}')

    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info(f'Проверка ответа API: {response}')

    if not isinstance(response, dict):
        logger.error('Ответ API отличен от словаря')
        raise TypeError('Ответ API отличен от словаря')

    if response == {}:
        logger.error('Ответ API содержит пустой словарь')
        raise KeyError('Ответ API содержит пустой словарь')

    if 'homeworks' not in response:
        logger.error('В ответе API нет ключа homeworks')
        raise KeyError('В ответе API нет ключа homeworks')

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        logger.error('По ключу homeworks возвращается не список')
        raise TypeError('По ключу homeworks возвращается не список')

    return homeworks


def parse_status(homework):
    """Извлекает статус из информации о конкретной домашней работе."""
    logger.info('Извлечение статуса домашней работы')

    if not ('homework_name' or 'status') in homework:
        logger.error('Нет ключа homework_name или status')
        raise KeyError('Нет ключа homework_name или status')

    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[f'{homework_status}']

    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Неизвестный статус: {homework_status}')
        raise KeyError(f'Неизвестный статус: {homework_status}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    logger.info('Проверка переменных окружения')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    latest_homework_status = {}
    latest_error_message = (
        'Сбой в работе программы: Нет домашних работ за выбранный период'
    )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        sys.exit(1)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if not homeworks:
                logger.error('Нет домашних работ за выбранный период')
                raise IndexError('Нет домашних работ за выбранный период')

            homework = homeworks[0]
            homework_name = homework['homework_name']
            homework_status = homework['status']

            if homework_name in latest_homework_status and (
                homework_status == latest_homework_status[homework_name]
            ):
                logger.debug('Нет обновлений статуса')
            else:
                status_message = parse_status(homework)
                send_message(bot, status_message)
                latest_homework_status[homework_name] = homework_status

            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != latest_error_message:
                send_message(bot, message)
                latest_error_message = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Принудительное завершение программы')
