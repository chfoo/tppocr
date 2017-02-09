import argparse

import redis
import tornado.ioloop

from tppocr.web.app import App


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--port', type=int, default=8095)
    arg_parser.add_argument('--xheaders', action='store_true',
                            help='Whether to use X-Real-IP')
    arg_parser.add_argument('--redis-host', default='localhost')
    arg_parser.add_argument('--redis-port', default=6379, type=int)
    arg_parser.add_argument('--redis-db', default=0, type=int)
    arg_parser.add_argument('--debug', action='store_true')
    arg_parser.add_argument(
        '--path-prefix', default='',
        help='Prefix to the URL path to run app on something other than /'
    )

    args = arg_parser.parse_args()

    redis_conn = redis.StrictRedis(args.redis_host, args.redis_port,
                                   args.redis_db, decode_responses=True,
                                   errors='replace')

    app = App(redis_conn, debug=args.debug, path_prefix=args.path_prefix)
    app.listen(args.port, xheaders=args.xheaders)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
