import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class CheckTokensError(Exception):
    """Если отсутствуют обязательные переменные окружения."""

    pass


class APIResponseError(Exception):
    """Если API не возвращает ожидаемый ответ."""

    pass


class APIHTTPStatusError(Exception):
    """Если API недоступен."""

    pass


class SendMessageError(Exception):
    """Если сообщение в telegram не отправилось."""

    pass


def send_message(bot, message):
    """Отправляет сообщение в telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение отправлено: "{message}"')
    except SendMessageError:
        logger.error('Сбой при отправке сообщения')


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
    homeworks = response['homeworks']
    logger.info(f'Проверка ответа API: {response}')
    if not isinstance(response, dict):
        logger.error('Ответ API отличен от словаря')
        raise TypeError('Ответ API отличен от словаря')
    if not isinstance(homeworks, list):
        logger.error('По ключу homeworks возвращается не список')
        raise TypeError('По ключу homeworks возвращается не список')
    if response == {}:
        logger.error('Ответ API содержит пустой словарь')
        raise KeyError('Ответ API содержит пустой словарь')
    for key in ['homeworks', 'current_date']:
        if key not in response:
            logger.error(f'В ответе API нет ключа {key}')
            raise KeyError(f'В ответе API нет ключа {key}')
    return homeworks


def parse_status(homework):
    """Извлекает статус из информации о конкретной домашней работе."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    logger.info('Извлечение статуса домашней работы')
    for key in ['homework_name', 'status']:
        if key not in homework:
            logger.error(f'Нет ключа {key}')
            raise KeyError(f'Нет ключа {key}')
    verdict = HOMEWORK_STATUSES[f'{homework_status}']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Неизвестный статус: {homework_status}')
        raise KeyError(f'Неизвестный статус: {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    logger.info('Проверка переменных окружения')
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    latest_homework_status = {}
    latest_error_message = ''

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    try:
        check_tokens()
    except CheckTokensError:
        logger.critical('Отсутствуют обязательные переменные окружения')

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
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != latest_error_message:
                send_message(bot, message)
                latest_error_message = message
            time.sleep(RETRY_TIME)
        else:
            logging.info('Успешное завершение программы')


if __name__ == '__main__':
    main()
