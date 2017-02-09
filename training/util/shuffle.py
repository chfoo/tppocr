import random

import io

if __name__ == '__main__':
    text = io.StringIO()

    while True:
        try:
            text.write(input().replace(' ', ''))
        except EOFError:
            break

    l = list(text.getvalue())
    random.shuffle(l)

    print(''.join(l))
