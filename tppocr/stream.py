import abc
import json
import logging
import os
import queue
import subprocess
import threading
import time
from typing import Tuple

from tppocr.math import Size2DTuple

_logger = logging.getLogger()


class BaseStream(metaclass=abc.ABCMeta):
    def __init__(self, output_fps: int=4, native_frame_rate: bool=False,
                 frame_queue: queue.Queue=None):
        super().__init__()
        self._output_fps = output_fps
        self._native_frame_rate = native_frame_rate
        self._frame_size = Size2DTuple(0, 0)
        self._frame_queue = frame_queue or queue.Queue(5)
        self._running = False
        self._current_proc = None

    @property
    def frame_size(self) -> Size2DTuple:
        return self._frame_size

    @property
    def frame_queue(self) -> queue.Queue:
        return self._frame_queue

    @abc.abstractmethod
    def _get_ffmpeg_url(self) -> str:
        pass

    def run(self):
        _logger.info('Stream starting...')
        self._running = True

        self._get_video_size()

        while self._running:
            ffmpeg_thread = threading.Thread(target=self._run_ffmpeg, daemon=True)
            ffmpeg_thread.start()
            ffmpeg_thread.join()

            if self._running:
                _logger.info('Sleeping...')
                time.sleep(30)

    def stop(self):
        self._running = False
        self._terminate_ffmpeg()
        self._frame_queue.put(None)

    def _get_video_size(self):
        _logger.info('Getting video size...')
        self._frame_size = get_video_size(self._get_ffmpeg_url())

    def _run_ffmpeg(self):
        _logger.info('Running ffmpeg...')

        args = [
            'ffmpeg',
            '-i', self._get_ffmpeg_url(),
            '-f', 'image2pipe', '-pix_fmt', 'gray', '-vcodec', 'rawvideo',
            '-r', str(self._output_fps),
            '-nostats', '-v', 'error', '-'
        ]

        if self._native_frame_rate:
            args.insert(1, '-re')

        env = os.environ.copy()
        env['AV_LOG_FORCE_NOCOLOR'] = '1'
        self._current_proc = proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            env=env
        )
        frame_width, frame_height = self._frame_size
        frame_data_size = frame_width * frame_height

        frame_data = b''

        _logger.info('Reading frames...')

        while proc.returncode is None:
            frame_data += proc.stdout.read(frame_data_size - len(frame_data))

            if not frame_data:
                _logger.info('No data from ffmpeg')
                break

            if len(frame_data) == frame_data_size:
                _logger.debug('Read 1 frame')
                try:
                    self._frame_queue.put(frame_data, timeout=1)
                except queue.Full:
                    _logger.warning('Queue full')

                frame_data = b''

        self._terminate_ffmpeg()

        _logger.info('FFmpeg exited with %s', proc.returncode)

    def _terminate_ffmpeg(self):
        proc = self._current_proc

        if not proc:
            return

        _logger.info('Terminating ffmpeg...')
        try:
            proc.terminate()
            proc.wait(5)
        except OSError:
            _logger.exception('Terminate ffmpeg')

        try:
            proc.kill()
        except OSError:
            pass

        self._current_proc = None


class LiveStream(BaseStream):
    def __init__(self, url: str, quality: str='medium', **kwargs):
        super().__init__(**kwargs)
        self._url = url
        self._quality = quality
        self._video_url = None
        self._video_url_timestamp = 0

    def _refresh_video_url(self):
        self._video_url = get_video_url(self._url, self._quality)
        self._video_url_timestamp = time.monotonic()

    def _get_ffmpeg_url(self) -> str:
        timestamp_now = time.monotonic()

        if timestamp_now - self._video_url_timestamp > 60:
            _logger.info('Getting fresh stream URL')
            self._refresh_video_url()

        return self._video_url


class URLStream(BaseStream):
    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self._url = url

    def _get_ffmpeg_url(self):
        return self._url

    def _run_ffmpeg(self):
        super()._run_ffmpeg()

        if os.path.exists(self._url):
            _logger.info('Stopping due to local file')
            self.stop()


def get_video_url(channel_url='twitch.tv/twitchplayspokemon', quality='medium') \
        -> str:
    url = subprocess.check_output([
        'livestreamer', channel_url,
        quality,
        '--stream-url',
    ]).decode('utf-8').strip()

    return url


def get_video_size(input_url: str) -> Size2DTuple:
    output = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'stream=width,height',
        '-of', 'json', input_url
    ]).decode('utf-8')

    info = json.loads(output)

    for stream in info['streams']:
        if 'width' in stream:
            return Size2DTuple(stream['width'], stream['height'])
