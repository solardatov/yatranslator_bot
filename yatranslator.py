# simple

import os
import time
import logging
import requests
from alphabet_detector import AlphabetDetector

TRANSLATOR_BOT_LOG_FILE = 'translator_bot.log'


class TranslatorCore:
    def __init__(self, alphabet_detector, tele_token, ya_token):

        self.alphabet_detector = alphabet_detector

        self.tele_token = tele_token
        self.tele_url_prefix_template = 'https://api.telegram.org/bot{}/'
        self.tele_url_prefix = self.tele_url_prefix_template.format(self.tele_token)
        self.tele_last_update_id = 0

        self.ya_api_key = ya_token
        self.ya_api_url = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key={}&text={}&lang={}'

    def get_updates(self, offset=None):
        url = '{}{}?offset={}'.format(self.tele_url_prefix, 'getUpdates', offset)
        return requests.get(url).json()

    def send_message(self, chat_id, message):
        url = '{}{}?chat_id={}&text={}'.format(self.tele_url_prefix, 'sendMessage', chat_id, message)
        return requests.get(url).json()

    def do_response_for(self, update):
        self.send_message(update['message']['chat']['id'], self.do_translate(update['message']['text']))

    def do_translate(self, message):
        url = self.ya_api_url.format(self.ya_api_key, message, 'ru-en' if self.alphabet_detector.is_cyrillic(message) else 'en-ru')
        response = requests.get(url).json()
        print(response)
        return response['text'][0] if response['code'] == 200 else 'Не удалось перевести :('


    def run(self):
        updates = self.get_updates(self.tele_last_update_id + 1)

        if len(updates):
            if updates['ok']:
                updates_list = updates['result']
                for update in updates_list:
                    print(update)
                    self.tele_last_update_id = update['update_id']
                    self.do_response_for(update)


def main():
    logging.basicConfig(filename=TRANSLATOR_BOT_LOG_FILE, level=logging.INFO)
    logging.info('Translator bot started!')

    bot = TranslatorCore(AlphabetDetector(), os.environ['TELE_TOKEN'], os.environ['YA_API_KEY'])
    while True:
        bot.run()
        time.sleep(0.1)


if __name__ == '__main__':
    main()