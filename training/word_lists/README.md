Word List for Pokemon OCR
=========================

The word list specialized for the Pokemon domain can be obtained through the game such as the Pokedex. A database can be obtained from https://github.com/veekun/pokedex. 

To build the word list on a Linux (Ubuntu) system:

        pip3 install git+https://github.com/veekun/pokedex --user
        python3 -m pokedex setup
        python3 gen_pokedex_word_list.py path/to/veekun/pokedex/data/pokedex.sqlite > word_list.txt

