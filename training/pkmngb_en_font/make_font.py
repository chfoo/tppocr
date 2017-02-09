# encoding=utf8

import PIL.Image
import itertools
import fontforge

CHARS = (
    u'ABCDEFGHIJKLMNOP',
    u'QRSTUVWXYZ():;[]',
    u'abcdefghijklmnop',
    u'qrstuvwxyz',
    u'ÄÖÜäöü',
    u'ḍḷṃṛṣṭṿ',
    u"'ⓅⓂ-  ?! &é    ♂",
    u'$×./,♀0123456789',
    u'',
    u'⒫⒦“” …'
)
SQUARE_SIZE = 100
VERSION = '1.0'
COPYRIGHT = 'Original by Nintendo / Game Freak / Pokemon Co. ' \
            'Converted by TPPOCR project.'


def get_pixel_data():
    image = PIL.Image.open('crystal_tiles.png')
    image = image.convert('1')

    data = []

    for tile_row in range(10):
        row_data = []

        for tile_col in range(16):
            tile_pixel_data = []
            for tile_y, tile_x in itertools.product(range(8), range(8)):
                x = tile_col * 8 + tile_x
                y = tile_row * 8 + tile_y

                tile_pixel_data.append(image.getpixel((x, y)))

            row_data.append(tile_pixel_data)

        data.append(row_data)

    return data


def main():
    font = fontforge.font()
    font.descent = 1 * SQUARE_SIZE
    font.ascent = 8 * SQUARE_SIZE
    font.upos = -1 * SQUARE_SIZE
    font.uwidth = SQUARE_SIZE
    font.fontname = 'pkmn_gb_en_tppocr-regular'
    font.familyname = 'pkmn_gb_en_tppocr'
    font.fullname = 'PkMn GB English TPPOCR Regular'
    font.encoding = 'unicode'

    char_pixel_data = get_pixel_data()

    for char_row, row in enumerate(CHARS):
        for char_col, char in enumerate(row):
            if char == ' ':
                continue

            glyph = font.createChar(ord(char))
            glyph.clear()
            pixel_data = char_pixel_data[char_row][char_col]
            pen = glyph.glyphPen()

            for tile_y, tile_x in itertools.product(range(8), range(8)):
                if pixel_data[tile_y * 8 + tile_x] != 0:
                    continue

                x = tile_x * SQUARE_SIZE
                y = 7 * SQUARE_SIZE - tile_y * SQUARE_SIZE

                # Add +/-1 to slightly increase the block size so each block
                # will slightly overlap and ensure no points overlap.
                pen.moveTo((x - 1, y - 1))
                pen.lineTo((x + SQUARE_SIZE + 1, y - 1))
                pen.lineTo((x + SQUARE_SIZE + 1, y + SQUARE_SIZE + 1))
                pen.lineTo((x - 1, y + SQUARE_SIZE + 1))
                pen.closePath()

            glyph.width = SQUARE_SIZE * 8

    glyph = font.createChar(ord(' '))
    glyph.width = SQUARE_SIZE * 8

    font.selection.all()
    font.removeOverlap()
    font.simplify()
    font.correctDirection()

    font.version = VERSION
    font.copyright = COPYRIGHT

    font.generate(font.fontname + '.ttf', flags=('no-hints',))


if __name__ == '__main__':
    main()
