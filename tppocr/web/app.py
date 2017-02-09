import json
import os

import redis
import tornado.web
import tornado.websocket
import tornado.ioloop

from tppocr.text import TEXT_LIST_KEY, PUBLISH_CHANNEL


class App(tornado.web.Application):
    def __init__(self, redis_conn: redis.StrictRedis, debug=False,
                 path_prefix: str=''):
        self.redis_conn = redis_conn
        handlers = [
            (path_prefix + r'/', IndexHandler),
            (path_prefix + r'/api/events', EventsHandler),
            (path_prefix + r'/api/recent', RecentHandler)
        ]

        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        super().__init__(
            handlers,
            template_path=template_path,
            static_path=static_path,
            static_url_prefix=path_prefix + '/static',
            debug=debug
        )

        self.pubsub = self.redis_conn.pubsub()
        self.pubsub.subscribe(PUBLISH_CHANNEL)

        self.pubsub_timer = tornado.ioloop.PeriodicCallback(self._poll_pubsub, 100)
        self.pubsub_timer.start()

    def _poll_pubsub(self):
        for dummy in range(10):
            message = self.pubsub.get_message()
            if message:
                if message.get('channel') == PUBLISH_CHANNEL and \
                        message.get('type') == 'message':
                    EventsHandler.pubsub_handler(message)
            else:
                break


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        news_html = ''

        news_path = os.path.join(os.path.dirname(__file__), 'static', 'news.html')
        if os.path.exists(news_path):
            with open(news_path) as file:
                news_html = file.read()

        self.render('index.html', news_html=news_html)


class EventsHandler(tornado.websocket.WebSocketHandler):
    handlers = set()

    @classmethod
    def pubsub_handler(cls, message):
        for handler in cls.handlers:
            handler.write_message(message['data'])

    def open(self):
        self.handlers.add(self)

    def on_close(self):
        self.handlers.remove(self)


class RecentHandler(tornado.web.RequestHandler):
    def get(self):
        values = list(
            json.loads(item)
            for item in self.application.redis_conn.lrange(TEXT_LIST_KEY, 0, -1)
        )
        self.write({
            'recent_texts': values
        })
