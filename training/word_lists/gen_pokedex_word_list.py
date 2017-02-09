import argparse
import re
import sqlite3
import itertools
import collections


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('pokedex_db_path')
    arg_parser.add_argument('--frequency', type=int, default=None)

    args = arg_parser.parse_args()

    conn = sqlite3.connect(args.pokedex_db_path)

    all_words = collections.Counter()

    rows = itertools.chain(
        conn.execute('select name from pokemon_species_names where local_language_id = 9'),
        conn.execute('select name from move_names where local_language_id = 9')
    )

    for row in rows:
        all_words[row[0]] += 1

    text_rows = itertools.chain(
        conn.execute('select flavor_text  from pokemon_species_flavor_text where language_id = 9'),
        conn.execute('select flavor_text  from move_flavor_text where language_id = 9;')
    )

    for row in text_rows:
        text = row[0]
        text = text.replace('\xad\n', '').replace('\xad', '')
        text = text.replace('’', "'")  # normalize and include both later
        text = re.sub(r'[–—]|--', ' ', text) # rejoin words split on lines
        text = re.sub(r'(\w)\.(\w)', '\1. \2', text)  # missing space after period

        words = text.split()
        cleaned_words = []

        for word in words:
            if re.search(r'\d', word):
                # Ignore words that may just be numbers or unit
                continue

            word = re.sub(r'\'s$', '', word)  # remove "'s"
            word = re.sub(r'(^\W)|(\W$)', '', word)  # strip leading/trailing punctuation

            if word:
                cleaned_words.append(word)
                if "'" in word:
                    cleaned_words.append(word.replace("'", '’'))

            if word == 'cir':
                assert False, row

        for word in cleaned_words:
            all_words[word] += 1

    if args.frequency:
        for word, frequency in sorted(all_words.most_common(args.frequency)):
            print(word)
    else:
        for word in sorted(all_words.keys()):
            print(word)


if __name__ == '__main__':
    main()
