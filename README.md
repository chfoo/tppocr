TPPOCR
======

Tesseract OCR of Pokemon dialog text on streaming video.

This project contains scripts and training data needed for running OCR on live streams such as TwitchPlaysPokemon.

It has two language data files:

* `pkmngb_en`: English training data for Gameboy Pokemon games such as Red, Blue, Gold, Silver, Crystal.
* `pkmngba_en`: English training data for Gameboy Advanced / DS Pokemon games such as Ruby, Saphire, Emerald, FireRed, Diamond, Pearl, Platinum.

You may be interested in [PokeTEXT](https://github.com/rctgamer3/poketext) too.

If you just want to use the training data, please skip to the bottom of this document.


Install
=======

Requirements:

* [Python](https://www.python.org/downloads/) 3.4+
* [pip](https://pip.pypa.io/en/stable/installing/) (for installing Python modules)
* [Pillow](https://pillow.readthedocs.io/en/4.0.x/installation.html) (PIL fork)
* [redis-py](https://github.com/andymccurdy/redis-py)
* [Tesseract](https://github.com/tesseract-ocr/tesseract/wiki/Downloads)
* [tesserocr](https://github.com/sirfz/tesserocr) 3.04 (Python bindings to Teseract)
* [Redis](https://redis.io/download)
* [FFmpeg](https://ffmpeg.org/download.html) 2.8+
* [Livestreamer](http://docs.livestreamer.io/install.html)

To run TPPOCR, it's recommended to use a Linux OS.

On Debian/Ubuntu, run the following to install stable versions provided by Debian/Ubuntu:

        apt-get install build-essential tesseract-ocr libtesseract-dev libleptonica-dev cython3 python3 redis-server python3-pip python3-pil

On Debian/Ubuntu, run the following to install the latest Python library versions on your home directory:

        pip3 install tesserocr redis livestreamer --user

Download a recent [static build](https://www.johnvansickle.com/ffmpeg/) of FFmpeg:

        wget http://example.com/PUT_URL_HERE_TO/ffmpeg-release-64bit-static.tar.xz
        tar -xJv ffmpeg-release-64bit-static.tar.xz

TPPOCR will require running Livestreamer and FFmpeg separately. Ensure these files are in `PATH` environment variable:

* `~/.local/bin/livestreamer`
* `ffprobe`
* `ffmpeg`

You can do this by editing your shell profile or by prefixing `PATH=$PATH:~/.local/bin:~/bin/` to commands.

For Twitch streams, Livestreamer will require an Client-ID or OAUTH token. OAUTH token can be [specified in the config file](http://docs.livestreamer.io/twitch_oauth.html). You can generate one using `livestreamer --twitch-oauth-authenticate`. (Keep your token secret!)

Ensure Redis is not exposed to the internet by checking `/etc/redis/6379.conf`. By default on Debian/Ubuntu, it uses `bind 127.0.0.1`. 

Finally, grab TPPOCR from git:

        git clone https://URL_TO_GITHUB_HERE/USERNAME/tppocr

Since TPPOCR is meant to run as a bunch of scripts, it does not currently have an install file.


Usage
=====

The basic structure of the command to start the OCR process is:

        python3 -m tppocr config.ini

In addition, the command may need extra environment variables. For example, if tppocr is the current directory:

        PYTHONPATH=./ TESSDATA_PREFIX=./ python3 -m tppocr config.ini

* `PYTHONPATH` is the directory of the tppocr project directory. It should contain the tppocr package directory.
* `TESSDATA_PREFIX` is directory containing the `tessdata` directory. `tessdata` contains the TPPOCR training data files.

See the example configuration files for details on setting them.

To run the web interface, install [Tornado](http://www.tornadoweb.org/en/stable/) and run:

        pip3 install tornado --user
        python3 -m tppocr.web

Add `--help` to see available settings. If you want to expose this to the Internet, run it behind a web server with websocket support. Tornado has suggestions [here](http://www.tornadoweb.org/en/stable/guide/running.html). Nginx config to enable websocket is described [here](https://www.nginx.com/blog/websocket-nginx/).

To save the data, you can use the following:

        python3 -m tppocr.pub.textfile log_dir/


Standalone
----------

If you simply want to use the training data with Tesseract, copy the traineddata file into the Tesseract data directory.

Or you can run it by specifying the project directory. For example, to read a cropped image of a timestamp:

        tesseract --tessdata-dir ~/Documents/tppocr/tessdata/ -l pkmngba_en out3_1.jpg stdout /usr/share/tesseract-ocr/tessdata/configs/digits


