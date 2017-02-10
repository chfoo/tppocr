import base64
import difflib
import json
import io
import collections
import logging
import time

import redis
import PIL.Image
from typing import List, Optional

PUBLISH_CHANNEL = 'tppocr'
TEXT_LIST_KEY = 'tppocr.recent_text'
TEXT_LIST_LIMIT = 1000
DEFAULT_TEXT_BUFFER_TIME = 20

_logger = logging.getLogger(__name__)


class TextBlock:
    matcher = difflib.SequenceMatcher(isjunk=lambda x: x in ' \n')

    def __init__(self, text: str):
        self.text = text
        self.timestamp = time.time()
        self.touch_timestamp = self.timestamp

        self.matcher.set_seq2(text)

    def append_text(self, new_text: str) -> bool:
        self.matcher.set_seq1(new_text[:len(self.text)])
        threshold = 0.6 if len(new_text) < 10 else 0.7
        ratio = self.matcher.ratio()

        _logger.debug('Append ratio %s (%s)', ratio, threshold)

        if ratio > threshold:
            self.text = new_text
            self.matcher.set_seq2(self.text)
            self.touch_timestamp = time.time()
            return True
        else:
            return False

    def splitlines(self) -> List[str]:
        return list(
            line for line in (line.strip() for line in self.text.splitlines())
            if line
        )


class TextLine:
    def __init__(self, text: str, timestamp: float, touch_timestamp: float):
        self.text = text
        self.timestamp = timestamp
        self.touch_timestamp = touch_timestamp


class TextFilter:
    line_matcher = difflib.SequenceMatcher()

    def __init__(self, redis_conn: redis.StrictRedis):
        self._redis_conn = redis_conn
        self._text_blocks = collections.defaultdict(collections.deque)
        self._text_lines = collections.defaultdict(collections.deque)

    def feed_text(self, text: str, confidence: int=100,
                  section: Optional[str]=None):
        self._publish_raw_text(text, confidence, section)
        _logger.debug('Raw text %s %s', ascii(text), confidence)

        if confidence > 50:
            self._add_new_text(text, section)

        self._publish_text_lines()

    def flush_text(self, buffer_time: float=DEFAULT_TEXT_BUFFER_TIME):
        self._publish_text_lines(buffer_time)

    def feed_image(self, image: PIL.Image.Image, section: str=None):
        self._publish_image(image, section=section)

    def _publish_raw_text(self, text: str, confidence: Optional[float]=None,
                          section: str=None):
        doc = {
            'type': 'raw_text',
            'text': text,
            'timestamp': time.time(),
            'confidence': confidence,
            'section': section
        }
        json_str = json.dumps(doc)

        self._redis_conn.publish(PUBLISH_CHANNEL, json_str)

    def _publish_text(self, text: str, timestamp: float=None,
                      section: str=None):
        doc = {
            'type': 'output_text',
            'text': text,
            'timestamp': timestamp or time.time(),
            'section': section
        }
        json_str = json.dumps(doc)

        self._redis_conn.rpush(TEXT_LIST_KEY, json_str)
        self._redis_conn.ltrim(TEXT_LIST_KEY, -TEXT_LIST_LIMIT, -1)
        self._redis_conn.publish(PUBLISH_CHANNEL, json_str)

    def _publish_image(self, image: PIL.Image.Image, section: str=None):
        buffer = io.BytesIO()
        image.save(buffer, format='png')
        doc = {
            'type': 'debug_image',
            'image': base64.b64encode(buffer.getvalue()).decode('ascii'),
            'format': 'image/png;base64',
            'timestamp': time.time(),
            'section': section
        }
        json_str = json.dumps(doc)

        self._redis_conn.publish(PUBLISH_CHANNEL, json_str)

    def _add_new_text(self, text: str, section: Optional[str]=None):
        if not self._text_blocks[section]:
            self._text_blocks[section].append(TextBlock(text))
            _logger.debug('Created new text block %s', ascii(text))
        else:
            text_block = self._text_blocks[section][-1]

            if not text_block.append_text(text):
                self._text_blocks[section].append(TextBlock(text))
                _logger.debug('Created new text block %s', ascii(text))
            else:
                _logger.debug('Append to text block %s', ascii(text_block.text))

    def _split_text_blocks(self, buffer_time: float=DEFAULT_TEXT_BUFFER_TIME):
        current_timestamp = time.time()

        for section, text_blocks in self._text_blocks.items():
            while text_blocks:
                time_diff = current_timestamp - text_blocks[0].touch_timestamp
                if len(text_blocks) == 1 and time_diff < buffer_time:
                    break

                text_block = text_blocks.popleft()

                lines = text_block.splitlines()

                for line in lines:
                    self._text_lines[section].append(
                        TextLine(line, text_block.timestamp,
                                 text_block.touch_timestamp)
                    )

    def _publish_text_lines(self, buffer_time: float=DEFAULT_TEXT_BUFFER_TIME):
        self._split_text_blocks(buffer_time)
        current_timestamp = time.time()

        for section, text_lines in self._text_lines.items():
            if not text_lines:
                return

            start_time_diff = current_timestamp - text_lines[0].touch_timestamp
            if start_time_diff < buffer_time:
                return

            end_time_diff = current_timestamp - text_lines[-1].touch_timestamp
            if start_time_diff < buffer_time and end_time_diff < buffer_time:
                return

            lines = []
            timestamp = None

            while text_lines:
                text_line = text_lines.popleft()

                if lines:
                    self.line_matcher.set_seqs(text_line.text, lines[-1])
                    if self.line_matcher.ratio() > 0.9:
                        _logger.debug('Skipped text line %s %s',
                                      ascii(text_line.text), ascii(lines[-1]))
                        continue

                lines.append(text_line.text)
                _logger.debug('Appended text line %s', ascii(text_line.text))

                if not timestamp:
                    timestamp = text_line.timestamp

            self._publish_text('\n'.join(lines), timestamp, section)
