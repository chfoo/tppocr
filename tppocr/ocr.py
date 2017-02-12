import cProfile
import logging
import os
import queue
from typing import Tuple
import io

import tesserocr
import PIL.Image
import PIL.ImageFilter
import PIL.ImageStat
import PIL.ImageDraw
import PIL.ImageOps
import PIL.ImageMath
import PIL.ImageEnhance
import itertools

from tppocr.math import RectangleTuple
from tppocr.stream import BaseStream
from tppocr.text import TextFilter

_logger = logging.getLogger(__name__)


class RegionInfo:
    def __init__(self):
        self.computed_ocr_region = None
        self.scale_factor = None
        self.computed_ocr_image_white_region = None


class OCRConfig:
    def __init__(self, region: RectangleTuple,
                 white_region: RectangleTuple=None,
                 language: str='eng',
                 text_drop_shadow_filter: bool=False
                 ):
        self.region = region
        self.white_region = white_region
        self.language = language
        self.text_drop_shadow_filter = text_drop_shadow_filter
        self.tesseract_variables = {}
        self.section_name = '[default]'
        self.fps = None
        self.clear_adaptive_classifier = False


class OCR:
    MIN_OCR_IMAGE_HEIGHT = 200

    def __init__(self, stream: BaseStream, config: OCRConfig,
                 text_filter: TextFilter, frame_queue: queue.Queue):
        self._stream = stream
        self._config = config
        self._text_filter = text_filter
        self._frame_queue = frame_queue

    def run(self):
        # profiler = cProfile.Profile()
        # profiler.enable()
        self._run()
        # profiler.disable()
        # profiler.dump_stats('stat.dat')

    def _prime_frame_queue(self):
        self._frame_queue.get()
        _logger.debug('Video size %s', self._stream.frame_size)

    def _get_computed_rectangle(self, rect: RectangleTuple) -> RectangleTuple:
        x1 = int(self._stream.frame_size[0] * rect.x1)
        y1 = int(self._stream.frame_size[1] * rect.y1)
        x2 = int(self._stream.frame_size[0] * rect.x2)
        y2 = int(self._stream.frame_size[1] * rect.y2)

        assert x1 < x2
        assert y1 < y2

        return RectangleTuple(x1, y1, x2, y2)

    def _get_computed_cropping_params(self, rect: RectangleTuple) -> \
            Tuple[RectangleTuple, float]:
        rect = self._get_computed_rectangle(rect)
        height = rect.y2 - rect.y1
        scale_factor = max(1, self.MIN_OCR_IMAGE_HEIGHT / height)

        return rect, scale_factor

    def _compute_regions(self) -> RegionInfo:
        info = RegionInfo()
        computed_ocr_region, scale_factor = self._get_computed_cropping_params(
            self._config.region
        )
        info.computed_ocr_region = computed_ocr_region
        info.scale_factor = scale_factor

        if self._config.white_region:
            computed_white_region = self._get_computed_rectangle(
                self._config.white_region
            )

            assert self._config.region.x1 <= self._config.white_region.x1 < self._config.white_region.x2 <= self._config.region.x2
            assert self._config.region.y1 <= self._config.white_region.y1 < self._config.white_region.y2 <= self._config.region.y2

            x1 = (computed_white_region.x1 - computed_ocr_region.x1) \
                * scale_factor
            y1 = (computed_white_region.y1 - computed_ocr_region.y1) \
                * scale_factor
            x2 = (computed_white_region.x2 - computed_ocr_region.x1) \
                * scale_factor
            y2 = (computed_white_region.y2 - computed_ocr_region.y1) \
                * scale_factor

            info.computed_ocr_image_white_region = RectangleTuple(
                int(x1), int(y1), int(x2), int(y2),
            )
        else:
            info.computed_ocr_image_white_region = None

        return info

    def _preprocess_image(self, frame_data: bytes, region_info: RegionInfo) -> \
            PIL.Image.Image:
        region = region_info.computed_ocr_region
        scale_factor = region_info.scale_factor
        x1, y1, x2, y2 = region
        width = x2 - x1
        height = y2 - y1

        assert width > 0
        assert height > 0

        _logger.debug('ORC cropping to %s,%s %sx%s (scale %s)', x1, y1, width,
                      height, scale_factor)

        image = PIL.Image.frombytes('L', self._stream.frame_size, frame_data)

        image = image.crop((x1, y1, x2, y2))
        image = PIL.ImageOps.autocontrast(image)

        image = image.resize(
            (int(width * scale_factor), int(height * scale_factor)),
            resample=PIL.Image.BILINEAR
        )

        if self._config.text_drop_shadow_filter:
            image = image.point(lambda i: 255 if i > 100 else i)

        return image

    def _compute_white_region_confidence(
            self, ocr_image: PIL.Image.Image, region_info: RegionInfo,
            nonwhite_pixel_count_threshold: int=5) -> int:
        if not region_info.computed_ocr_image_white_region:
            return 100

        image = ocr_image.crop(region_info.computed_ocr_image_white_region)

        stat = PIL.ImageStat.Stat(image)

        assert 0 <= stat.extrema[0][0] <= stat.extrema[0][1] <= 255
        assert nonwhite_pixel_count_threshold >= 0

        pixel_sum = stat.sum[0]
        pixel_count = stat.count[0]
        expected_pixel_sum = 255 * pixel_count
        nonwhite_pixel_count = expected_pixel_sum - pixel_sum

        assert nonwhite_pixel_count >= 0, nonwhite_pixel_count

        if nonwhite_pixel_count_threshold:
            nonwhite_ratio = nonwhite_pixel_count / nonwhite_pixel_count_threshold
            return 100 - min(100, int(nonwhite_ratio * 100))
        else:
            return 100 if nonwhite_pixel_count == 0 else 0

    def _render_debug_image(self, source_image: PIL.Image.Image,
                            ocr_image: PIL.Image.Image,
                            api: tesserocr.PyTessBaseAPI,
                            region_info: RegionInfo) -> PIL.Image.Image:
        debug_image_width = max(source_image.width, ocr_image.width)
        debug_image_height = source_image.height + ocr_image.height
        debug_image = PIL.Image.new(
            'L', (debug_image_width, debug_image_height)
        )

        debug_image.paste(source_image, (0, 0))
        debug_image.paste(ocr_image, (0, source_image.height))

        draw_context = PIL.ImageDraw.Draw(debug_image)

        for box_image, box, block_id, para_id in api.GetTextlines():
            x = box['x']
            y = box['y'] + source_image.height
            w = box['w']
            h = box['h']
            draw_context.rectangle((x, y, x + w, y + h), outline=127)

        if region_info.computed_ocr_image_white_region:
            draw_context.rectangle((
                region_info.computed_ocr_image_white_region.x1,
                region_info.computed_ocr_image_white_region.y1 + source_image.height,
                region_info.computed_ocr_image_white_region.x2,
                region_info.computed_ocr_image_white_region.y2 + source_image.height
            ), outline=220)

        return debug_image

    def _run(self):
        self._check_tessdir()
        self._prime_frame_queue()

        with tesserocr.PyTessBaseAPI(lang=self._config.language) as api:
            api.SetVariable("tessedit_write_images", "T")

            for key, value in self._config.tesseract_variables.items():
                _logger.info('Setting tesseract variable %s=%s', key, value)
                api.SetVariable(key, value)

            if self._config.clear_adaptive_classifier:
                _logger.info('Clearing adaptive classifier after each run')

            for counter in itertools.count():
                frame_data = self._frame_queue.get()

                if not frame_data:
                    break

                region_info = self._compute_regions()
                image = self._preprocess_image(frame_data, region_info)

                assert image.mode == 'L'
                api.SetImageBytes(bytes(image.getdata(0)),
                                  image.width, image.height, 1, image.width)

                text = api.GetUTF8Text().strip()
                ocr_image = api.GetThresholdedImage()

                if text:
                    confidence = api.MeanTextConf()
                    white_confidence = self._compute_white_region_confidence(
                        ocr_image, region_info)
                    confidence -= 100 - white_confidence
                    confidence = max(0, confidence)
                    self._text_filter.feed_text(
                        text, confidence=confidence,
                        section=self._config.section_name)
                else:
                    self._text_filter.flush_text()

                if counter % self._config.fps == 0:
                    debug_image = self._render_debug_image(
                        image, ocr_image, api, region_info
                    )
                    self._text_filter.feed_image(
                        debug_image, section=self._config.section_name
                    )

                if self._config.clear_adaptive_classifier:
                    api.ClearAdaptiveClassifier()

        _logger.info('Tesseract quit')

    def _check_tessdir(self):
        tess_dir = os.environ.get('TESSDATA_PREFIX', '/usr/share/tesseract-ocr/')
        tessdata_dir = os.path.join(tess_dir, 'tessdata')

        if not os.path.isdir(tessdata_dir):
            _logger.error('Please set the directory containing the training '
                          'data using the TESSDATA_PREFIX environment '
                          'variable.')
            raise OSError('The directory {} does not contain'
                          ' tessdata directory'.format(tess_dir))

        _logger.info('Starting tesseract API...')
        _logger.info('If Segmentation Fault occurs, please check '
                     '".traineddata" file exists. TESSDATA_PREFIX=%s', tess_dir)
