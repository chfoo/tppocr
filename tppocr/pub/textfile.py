import argparse
import datetime
import json
import os

import redis
import time

from tppocr.text import PUBLISH_CHANNEL


class TextLogger:
    def __init__(self, log_directory: str):
        self._log_directory = log_directory
        self._log_path = None
        self._log_file = None

    def _open_log(self):
        datetime_now = datetime.datetime.now(datetime.timezone.utc)
        date_now = datetime_now.date()

        path = os.path.join(self._log_directory,
                            'tppocr.{}.log'.format(date_now.isoformat())
                            )

        if path != self._log_path:
            if self._log_file:
                self._log_file.close()

            self._log_path = path
            self._log_file = open(path, 'w')

    def log_text(self, text: str):
        self._open_log()
        self._log_file.write(text)
        self._log_file.write('\n')
        self._log_file.flush()


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('output_directory')

    arg_parser.add_argument('--redis-host', default='localhost')
    arg_parser.add_argument('--redis-port', default=6379, type=int)
    arg_parser.add_argument('--redis-db', default=0, type=int)

    args = arg_parser.parse_args()

    redis_conn = redis.StrictRedis(
        args.redis_host, args.redis_port, args.redis_db,
        decode_responses=True, errors='replace'
    )

    text_logger = TextLogger(args.output_directory)
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(PUBLISH_CHANNEL)

    while True:
        message = pubsub.get_message()
        if message:
            if message.get('channel') == PUBLISH_CHANNEL and \
                    message.get('type') == 'message':
                text = message['data']
                doc = json.loads(text)
                if doc['type'] == 'output_text':
                    text_logger.log_text(text)
        else:
            time.sleep(0.1)


if __name__ == '__main__':
    main()
