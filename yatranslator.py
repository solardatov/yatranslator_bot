# Simple telegram bot using Yandex translate API
# solardatov@gmail.com

import os
import sys
import signal
import time
import logging
import json
import requests
from alphabet_detector import AlphabetDetector

LANG_MAP = {'english': 'en',
            'spanish': 'es',
            'german': 'de',
            'french': 'fr',
            'italian': 'it',
            'finnish': 'fi',
            'chinese': 'zh',
            'korean': 'ko',
            'hebrew': 'he',
            'thai': 'th',
            'turkish': 'tr',
            'swedish': 'sv',
            'czech': 'cs',
            'estonian': 'es',
            'latvian': 'lv',
            'dutch': 'nl',
            'arabic': 'ar',
            'japanese': 'ja'
            }
LANG_DEFAULT = list(LANG_MAP.keys())[0]
LOG = logging.getLogger('yatranslator')
LOG_FILE = 'yatranslator.log'


def sigint_handler(signal, frame):
    LOG.info('Hey, you pressed CTRL-C, starting releasing LOG handlers...')

    for handler in LOG.handlers:
        handler.close()
        LOG.removeFilter(handler)

    LOG.info('Almost done, good luck dude!')

    sys.exit(0)


class TranslatorCore:
    def __init__(self, alphabet_detector, tele_token, ya_token, admin_username):

        self.alphabet_detector = alphabet_detector

        self.tele_token = tele_token
        self.tele_url_prefix_template = 'https://api.telegram.org/bot{}/'
        self.tele_url_prefix = self.tele_url_prefix_template.format(self.tele_token)
        self.tele_last_update_id = 0

        self.ya_api_key = ya_token
        self.ya_api_url = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key={}&text={}&lang={}'
        self.admin_username = admin_username

        self.language = 'english' # english by default

        # in-memory stats
        self.total_request_count = 0
        self.users = set()

        self.start_time = time.time()

    def help_str(self):
        help_message = self.make_bold('Доступные команды:\n')
        for command in LANG_MAP:
            help_message += '/' + command + '\n'
        return help_message

    def make_bold(self, text):
        return '*' + text + '*'

    def make_italic(self, text):
        return '_' + text + '_'

    def is_admin(self, update):
        return update['message']['from']['username'] == self.admin_username

    def set_language(self, language):
        if language in LANG_MAP:
            self.language = language
            return True
        else:
            self.language = LANG_DEFAULT
            return False

    def get_language(self):
        try:
            return LANG_MAP[self.language]
        except KeyError:
            return LANG_MAP[LANG_DEFAULT]

    def get_lang_direction(self, message):
        return 'ru-'+self.get_language() if self.alphabet_detector.is_cyrillic(message) else self.get_language()+'-ru'

    def get_updates(self, offset=None):
        url = '{}{}?offset={}'.format(self.tele_url_prefix, 'getUpdates', offset)
        return requests.get(url).json()

    # reply markup TBD
    def send_message(self, chat_id, reply_to_message_id, message, reply_markup=None):
        url = '{}{}?chat_id={}&reply_to_message_id={}&text={}&parse_mode=Markdown'.format(self.tele_url_prefix, 'sendMessage', chat_id, reply_to_message_id, message)
        if reply_markup:
            url += "&reply_markup={}".format(json.dumps(reply_markup))

        return requests.get(url).json()

    def do_response_for(self, update):
        message = update['message']['text']

        if message[0] == '/':
            command = message[1:]
            if command == 'start':
                self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                                  self.help_str())
            elif command == 'stats':
                if self.is_admin(update):
                    self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                                      'total=' + str(self.total_request_count) + ' users='+str(self.users))
            elif command == 'uptime':
                if self.is_admin(update):
                    self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                                      'uptime=' + str((time.time() - self.start_time)/(60*60)) + ' hours')
            else:
                self.update_stats(update)
                self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                                  ('Язык изменен: ' if self.set_language(
                                      command) else 'Данный язык не поддерживается, установлен: ') + self.make_italic(
                                      self.language))
        else:
            self.send_message(update['message']['chat']['id'], update['message']['message_id'],
                self.make_bold(self.do_translate(message)) + self.make_italic(' (' + self.language + ')'))

    def do_translate(self, message):
        url = self.ya_api_url.format(self.ya_api_key, message, self.get_lang_direction(message))
        response = requests.get(url).json()
        LOG.info(response)
        return response['text'][0] if response['code'] == 200 else 'Не удалось перевести :( Код ошибки ' + response['code']

    def update_stats(self, update):
        self.total_request_count += 1
        self.users.add(update['message']['from']['username'])

    def run(self):
        updates = self.get_updates(self.tele_last_update_id + 1)

        if len(updates):
            if updates['ok']:
                updates_list = updates['result']
                for update in updates_list:
                    LOG.info(update)
                    self.tele_last_update_id = update['update_id']
                    self.do_response_for(update)


def main():
    # catch CTRL-C
    signal.signal(signal.SIGINT, sigint_handler)

    #setup logging
    LOG.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log_file = logging.FileHandler(LOG_FILE)
    log_file.setLevel(logging.INFO)
    log_file.setFormatter(formatter)
    LOG.addHandler(log_file)

    log_stdout = logging.StreamHandler()
    log_stdout.setLevel(logging.INFO)
    log_stdout.setFormatter(formatter)
    LOG.addHandler(log_stdout)

    LOG.info('Yatranslator is starting!')

    bot = TranslatorCore(AlphabetDetector(), os.environ['TELE_TOKEN'], os.environ['YA_API_KEY'], os.environ['ADMIN_USERNAME'])
    while True:
        bot.run()
        time.sleep(0.1)


if __name__ == '__main__':
    main()