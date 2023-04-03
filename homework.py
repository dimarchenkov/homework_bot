import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exeptions import (HomeworkExistingKey, HomeworkStatusError,
                       HTTPStatusError, RequestError, ConnectionError)

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


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens() -> None:
    """Check tokens exists."""
    logger.info('Проверка токенов')
    check_status = True
    check_list = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    for token in check_list:
        if not globals()[token]:
            logger.critical(
                'Отсутствует обязательная переменная '
                f'окружения: {token} = None.'
            )
            check_status = False
    if not check_status:
        logger.info(f'Проверка завершена с ошибкой: Статус: {check_status}')
        sys.exit('Критическая ошибка. Отсутствуют переменные окружения.')
    else:
        logger.info(f'Проверка завершена успешно: Статус: {check_status}')


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
    logger.info(
        'Начата подготовка к запросу API, '
        f'url - {ENDPOINT}, timestamp - {timestamp}'
    )

    try:
        response: dict = requests.get(**request_params)
        if response.status_code != 200:
            raise HTTPStatusError(response.reason)
    except requests.ConnectionError as error:
        raise ConnectionError(f'Ошибка подключения - {error}')
    except requests.RequestException as error:
        raise RequestError(
            'Ошибка в запросе, '
            f'url {ENDPOINT}, '
            f'timestamp {timestamp}, {error}'
        )
    else:
        logger.info('Получен ответ от API')
        return response.json()


def check_response(response) -> None:
    """Check correct data in response."""
    logger.info('Проверка ответа от сервера')

    if not isinstance(response, dict):
        raise TypeError(
            'Тип ответа API не соответствует ожидаемому dict.'
        )
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Тип ответа API не соответствует ожидаемому list.'
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
    logger.info('Результат проверки: all good')


def parse_status(homework: dict) -> str:
    """Parse homework status. Return str to send."""
    logger.info('Старт проверки статуса')

    homework_name: str = homework.get('homework_name')
    homework_status: str = homework.get('status')

    logger.debug(
        f'Parsing status, homework_name: {homework_name}, '
        f'homework_status: {homework_status}'
    )

    if homework_name is None:
        raise HomeworkStatusError(
            f'Пустое имя домашней работы {homework_name}'
        )
    if homework_status is None:
        raise HomeworkStatusError(
            f'Пустое имя домашней работы {homework_name}'
        )
    if homework_status not in HOMEWORK_VERDICTS:
        raise HomeworkStatusError(
            f'Неизвестный статус домашней рабоыт {homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]

    logger.info(f'Проверка статуса завершена, вердикт - {verdict}')

    return f'Изменился статус проверки работы "{homework_name}": {verdict}'


def main() -> None:
    """Main function."""
    check_tokens()

    bot: telegram.bot = telegram.Bot(token=TELEGRAM_TOKEN)
    homework_status: str = ''
    timestamp = int(time.time())

    while True:
        try:
            send_message(bot, 'Работаю, тружусь, все хорошо')
            response: list = get_api_answer(timestamp)
            check_response(response)
            timestamp = response['current_date']
            homework = response.get('homeworks')
            if homework:
                homework = response.get('homeworks')[0]
                if homework_status != parse_status(homework):
                    homework_status = parse_status(homework)
                    logging.info(
                        'Подготовлено сообщение для отаравки:'
                        f' {homework_status}'
                    )
                    send_message(bot, homework_status)
            else:
                logger.debug('Новые статусы отстутствуют')
            error_status: bool = False
        except Exception as error:
            error_message: str = logger.error(
                f'Сбой в работе программы: {error}', exc_info=True
            )
            if not error_status:
                send_message(bot, error_message)
                error_status = True
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    main()
