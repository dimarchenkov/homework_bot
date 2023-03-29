from dotenv import load_dotenv
import os

import logging
from logging.handlers import RotatingFileHandler

from http import HTTPStatus
import requests
import telegram
import time
import sys

from exeptions import (
    HomeworkStatusError,
    HomeworkExistingKey,
    HTTPStatusErrorNOT_FOUND,
    HTTPStatusErrorBAD_REQUEST,
    HTTPStatusErrorUNAUTHORIZED
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(name)s,  %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('bot.log', maxBytes=50000000, backupCount=5)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens() -> bool:
    """Check tokens exists."""
    check_status: bool = True

    if not PRACTICUM_TOKEN:
        logger.critical(
            'Отсутствует обязательная переменная '
            'окружения: PRACTICUM_TOKEN = None.'
        )
        check_status = False
    else:
        logger.debug(f'Check tokens - PRACTICUM_TOKEN: {check_status}')

    if not TELEGRAM_TOKEN:
        logger.critical(
            'Отсутствует обязательная переменная '
            'окружения: TELEGRAM_TOKEN = None.'
        )
        check_status = False
    else:
        logger.debug(f'Check tokens - TELEGRAM_TOKEN: {check_status}')

    if not TELEGRAM_CHAT_ID:
        logger.critical(
            'Отсутствует обязательная переменная '
            'окружения: TELEGRAM_CHAT_ID = None.'
        )
        check_status = False
    else:
        logger.debug(f'Check tokens - TELEGRAM_CHAT_ID: {check_status}')

    logger.info(f'Check tokens: {check_status}')
    return check_status


def send_message(bot: telegram.Bot, message: str) -> None:
    """Send message to chat."""
    try:
        logger.debug('Начата отправка сообщения в Telegramm.')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено в Telegramm.')
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {telegram_error}'
        )


def get_api_answer(timestamp: int) -> dict:
    """Get API answer from service."""
    request_params: dict = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    response = {}

    try:
        logger.info(f'Отправляем запрос к API {ENDPOINT}')
        response: dict = requests.get(**request_params)
        response.raise_for_status()
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise HTTPStatusErrorNOT_FOUND()
        if response.status_code == HTTPStatus.BAD_REQUEST:
            raise HTTPStatusErrorBAD_REQUEST()
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise HTTPStatusErrorUNAUTHORIZED()

    except HTTPStatusErrorNOT_FOUND:
        logger.error(
            'Сбой в работе программы: '
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
        response = {}
        return response
    except HTTPStatusErrorBAD_REQUEST:
        logger.error(
            'Сбой в работе программы: '
            f'Wrong from_date format. '
            f'Код ответа API: {response.status_code}'
        )
        response = {}
        return response
    except HTTPStatusErrorUNAUTHORIZED:
        logger.error(
            'Сбой в работе программы: '
            f'Учетные данные не были предоставлены. '
            f'Код ответа API: {response.status_code}'
        )
        response = {}
        return response
    except requests.exceptions.RequestException as error:
        logger.error(error)
    else:
        logger.info('Получен ответ от API')
        return response.json()


def check_response(response) -> bool:
    """Check correct data in response."""
    logger.debug('Проверка ответа от сервера')
    check_response = False
    try:
        if not isinstance(response, dict):
            raise TypeError(
                'Тип ответа API не соответствует ожидаемому dict.'
                f' Полученный ответ: {response}.'
            )

        if not response:
            raise ValueError(
                'Словарь полученный от API пуст.'
                f' Полученный ответ: {response}.'
            )

        if 'homeworks' not in response:
            raise HomeworkExistingKey(
                'Ответ API не содержит ключа "homeworks".'
                f' Полученный ответ: {response}.'
            )

        if 'current_date' not in response:
            raise HomeworkExistingKey(
                'Ответ API не содержит ключа "current_date".'
                f' Полученный ответ: {response}.'
            )
    except TypeError as error:
        logger.error(error)
        return check_response
    except ValueError as error:
        logger.error(error)
        return check_response
    except HomeworkExistingKey as error:
        logger.error(error)
        return check_response
    else:
        logger.debug('Результат проверки: all good')
        return True


def parse_status(homework: dict) -> str:
    """Parse homework status. Return str to send."""
    logger.debug('Старт проверки статуса')

    homework_name: str = homework.get('homework_name')
    homework_status: str = homework.get('status')

    logger.debug(
        f'Parsing status, homework_name: {homework_name}, '
        f'homework_status: {homework_status}'
    )

    if homework_status not in HOMEWORK_VERDICTS:
        raise HomeworkStatusError(
            f'Неизвестный статус домашней рабоыт {homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]

    logger.debug(f'Проверка статуса завершена, вердикт - {verdict}')

    return f'Изменился статус проверки работы {homework_name}: {verdict}'


def main() -> None:
    """Main function."""
    if not check_tokens():
        sys.exit('Критическая ошибка. Отсутствуют переменные окружения.')

    bot: telegram.bot = telegram.Bot(token=TELEGRAM_TOKEN)
    prev_report: dict = {'name': '', 'output': ''}
    current_report: dict = {'name': '', 'output': ''}
    timestamp = int(time.time())

    while True:
        try:
            response: list = get_api_answer(timestamp)
            if check_response(response):
                homework = response.get('homeworks')[0]
                current_report = {
                    'name': homework.get('homework_name'),
                    'output': parse_status(homework)
                }

        except telegram.error.TelegramError as error:
            logging.error(error)

        except Exception as error:
            logging.error(error)
            error_message = f"Сбой в работе программы: {error}"
            logging.exception(error_message)
            send_message(bot, error_message)
        else:
            if prev_report != current_report:
                logging.info(
                    'Подготовлено сообщение для отаравки:'
                    f' {current_report["output"]}'
                )
                send_message(bot, current_report['output'])
            prev_report = current_report.copy()

            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    main()
