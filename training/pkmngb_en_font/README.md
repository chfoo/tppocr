Pokemon Crystal English Font
============================

The tile sheet was from https://github.com/rctgamer3/poketext which is forked from https://github.com/rmmh/pokr.

The supplementary tile sheet for the "c" letter is from https://github.com/pret/pokered.

Note, for special symbols, such as the apostrophized letters and Pk ligatures, they are mapped to (incorrect) Unicode code points. Check the source code or inspect the font file for details.

A free font editor is FontForge.

Building
========

To build this font from the tile sheet, you will need

* Linux or Linux environment
* FontForge with Python scripting support
* Python

On Ubuntu:

        apt-get install fontforge python-fontforge python2.7
        python2.7 make_font.py

