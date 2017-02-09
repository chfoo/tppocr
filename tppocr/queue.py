import queue
import threading

from typing import Tuple


class ConsumerBroadcastQueue(threading.Thread):
    def __init__(self, producer_queue: queue.Queue, num_consumer_queues: int=0, consumer_queue_maxsize: int=5):
        threading.Thread.__init__(self, daemon=True)
        self._producer_queue = producer_queue
        self._consumer_queues = tuple(
            queue.Queue(consumer_queue_maxsize)
            for dummy in range(num_consumer_queues)
        )

    @property
    def producer_queue(self) -> queue.Queue:
        return self._producer_queue

    @property
    def consumer_queues(self) -> Tuple[queue.Queue]:
        return self._consumer_queues

    def run(self):
        while True:
            item = self._producer_queue.get()

            if item is None:
                break

            for consumer_queue in self._consumer_queues:
                try:
                    consumer_queue.put(item, timeout=1)
                except queue.Full:
                    pass
