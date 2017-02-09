from __future__ import print_function, division

import argparse
import os
import tempfile
import shutil

import fontforge
import PIL.Image
import math
import PIL.ImageFont
import PIL.ImageDraw


import io


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('font_file')
    arg_parser.add_argument('chart_png_filename')
    arg_parser.add_argument('--font-size', type=int, default=16)
    arg_parser.add_argument('--bit-depth', choices=[1, 8], default=8, type=int)
    args = arg_parser.parse_args()
    font = fontforge.open(args.font_file)

    print("# fontname =", font.fontname)
    print("# familyname =", font.familyname)
    print("# fullname = ", font.fullname)

    font_images = {}

    temp_dir = tempfile.mkdtemp()
    try:
        for glyph in font.glyphs():
            print(glyph.unicode,
                  'U+{:04x}'.format(glyph.unicode) if glyph.unicode > 0 else '',
                  glyph.glyphname,
                  sep='\t'
                  )

            if glyph.unicode > 0:
                path = os.path.join(temp_dir, '{:04x}.png'.format(glyph.unicode))
                glyph.export(path, args.font_size, args.bit_depth)

                with open(path, 'rb') as file:
                    font_images[glyph.unicode] = file.read()
    finally:
        shutil.rmtree(temp_dir)

    cols = 32
    rows = int(math.ceil(len(font_images) / cols))
    col_width = 32
    row_height = 32

    draw_font = PIL.ImageFont.load_default()
    image = PIL.Image.new('L', (cols * col_width, rows * row_height), color=255)
    draw_context = PIL.ImageDraw.Draw(image)

    for index, char_code in enumerate(sorted(font_images.keys())):
        image_data = font_images[char_code]
        char_image = PIL.Image.open(io.BytesIO(image_data))

        col = index % cols
        row = index // cols

        image.paste(char_image, (col * col_width, row * row_height + 12))
        draw_context.text((col * col_width, row * row_height),
                          '{:02x}'.format(char_code), font=draw_font)

    image.save(args.chart_png_filename)


if __name__ == '__main__':
    main()
