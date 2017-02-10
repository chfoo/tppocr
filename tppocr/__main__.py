import argparse
import configparser
import logging
import os
import queue
import signal
import threading
from typing import Iterable

import redis

from tppocr.math import RectangleTuple
from tppocr.ocr import OCR, OCRConfig
from tppocr.queue import ConsumerBroadcastQueue
from tppocr.stream import LiveStream, URLStream, BaseStream
from tppocr.text import TextFilter

_logger = logging.getLogger(__name__)

OCR_SECTION_PREFIX = 'ocr'


def new_stream(config: configparser.ConfigParser, config_filename: str) -> BaseStream:
    source_input = os.path.normpath(os.path.join(
        os.path.dirname(config_filename),
        config['source']['input']
    ))
    output_fps = config['source'].getfloat('process_output_fps')
    native_frame_rate = config['source'].get('process_native_frame_rate')

    if config['source'].getboolean('livestreamer'):
        stream = LiveStream(source_input, output_fps=output_fps,
                            native_frame_rate=native_frame_rate,
                            quality=config['source']['livestreamer_quality'])
    else:
        stream = URLStream(source_input, output_fps=output_fps,
                           native_frame_rate=native_frame_rate)

    return stream


def new_redis_conn(config: configparser.ConfigParser) -> redis.StrictRedis:
    return redis.StrictRedis(
        config['redis']['host'], config['redis'].getint('port'),
        config['redis'].getint('db')
    )


def get_ocr_section_keys(config: configparser.ConfigParser) -> Iterable[str]:
    for key in config.keys():
        if key.startswith(OCR_SECTION_PREFIX):
            yield key


def new_ocr(config: configparser.ConfigParser, ocr_section_key: str,
            stream: BaseStream, text_filter: TextFilter,
            frame_queue: queue.Queue) -> OCR:
    config_section = config[ocr_section_key]

    region = RectangleTuple(
        config_section.getfloat('region-x1'),
        config_section.getfloat('region-y1'),
        config_section.getfloat('region-x2'),
        config_section.getfloat('region-y2'),
    )

    if 'white-region-x1' in config_section:
        white_region = RectangleTuple(
            config_section.getfloat('white-region-x1'),
            config_section.getfloat('white-region-y1'),
            config_section.getfloat('white-region-x2'),
            config_section.getfloat('white-region-y2'),
        )
    else:
        white_region = None

    tesseract_variables = {}
    for key in config_section.keys():
        if key.startswith('tesseract-'):
            tesseract_variables[key[10:]] = config_section[key]

    ocr_config = OCRConfig(
        region,
        language=config_section['language'],
        white_region=white_region,
        text_drop_shadow_filter=config_section.getboolean('text-drop-shadow-filter')
    )
    ocr_config.tesseract_variables.update(tesseract_variables)
    ocr_config.section_name = ocr_section_key[len(OCR_SECTION_PREFIX):]
    ocr_config.fps = config['source'].getfloat('process_output_fps')
    ocr_config.clear_adaptive_classifier = config[ocr_section_key].getboolean('clear-adaptive-classifier')

    return OCR(stream, ocr_config, text_filter, frame_queue)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('config_file')
    arg_parser.add_argument('--debug', action='store_true')

    args = arg_parser.parse_args()

    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    _logger.info('Loading config')

    with open(args.config_file) as file:
        config = configparser.ConfigParser()
        config.read_file(file)

    threads = []

    stream = new_stream(config, args.config_file)
    redis_conn = new_redis_conn(config)
    ocr_section_keys = tuple(get_ocr_section_keys(config))
    consumer_broadcast_queue = ConsumerBroadcastQueue(
        stream.frame_queue, len(ocr_section_keys)
    )

    threads.append(consumer_broadcast_queue)
    threads.append(threading.Thread(target=stream.run, daemon=True))

    for index, ocr_section_key in enumerate(ocr_section_keys):
        text_filter = TextFilter(redis_conn)
        frame_queue = consumer_broadcast_queue.consumer_queues[index]
        ocr = new_ocr(config, ocr_section_key, stream, text_filter, frame_queue)
        threads.append(threading.Thread(target=ocr.run, daemon=True))

    def stop_handler(dummy1, dummy2):
        stream.stop()

    signal.signal(signal.SIGINT, stop_handler)

    for thread in threads:
        thread.start()

    while True:
        for thread in threads:
            thread.join(timeout=1)

        if any(not thread.is_alive() for thread in threads):
            break

    stream.stop()

    _logger.info('Exiting')


if __name__ == '__main__':
    main()
    # cProfile.run('main()')
