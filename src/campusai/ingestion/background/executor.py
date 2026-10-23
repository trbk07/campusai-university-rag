"""Small bounded executor; cancelling queued work actually removes its item."""
from collections import deque
from concurrent.futures import Future
import threading

from .state import JobQueueFull


class BoundedExecutor:
    def __init__(self,max_workers,max_pending):
        self._condition = threading.Condition()
        self._queue = deque()
        self._capacity = max_workers+max_pending
        self._closed = False
        self._threads = [threading.Thread(target=self._worker,daemon=True,
            name=f'campusai-ingest-{number+1}') for number in range(max_workers)]
        for thread in self._threads: thread.start()

    def submit(self,function,*args):
        with self._condition:
            if self._closed: raise RuntimeError('executor is closed')
            if len(self._queue) >= self._capacity: raise JobQueueFull('executor queue full')
            future = Future()
            self._queue.append((future,function,args))
            self._condition.notify()
            return future

    def cancel(self,future):
        with self._condition:
            for item in self._queue:
                if item[0] is future:
                    self._queue.remove(item)
                    return future.cancel()
            return False

    @property
    def pending_count(self):
        with self._condition: return len(self._queue)

    def _worker(self):
        while True:
            with self._condition:
                while not self._queue and not self._closed: self._condition.wait()
                if not self._queue: return
                future,function,args = self._queue.popleft()
                if not future.set_running_or_notify_cancel(): continue
            try:
                result = function(*args)
            except BaseException as error:
                future.set_exception(error)
            else:
                future.set_result(result)

    def shutdown(self,wait=True,*,cancel_futures=False):
        with self._condition:
            self._closed = True
            if cancel_futures:
                while self._queue: self._queue.popleft()[0].cancel()
            self._condition.notify_all()
        if wait:
            for thread in self._threads:
                if thread is not threading.current_thread(): thread.join()
