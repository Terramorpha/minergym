import queue
from typing import Generic, TypeVar

T = TypeVar("T")


class Channel(Generic[T]):
    """Since we are running the Energyplus simulation in a different thread, we
    need a mechanism for the user thread (the one in which the user might
    presumably run their policy and the .step function) to exchange actuator
    values sensor values. Moreover, this communication mechanism must act as a
    rendezvous point: a chan.put() must return only if a chan.get() has been
    executed on the other thread.

    """

    _q: queue.Queue[queue.Queue[T]]
    _closed: bool

    def __init__(self):
        self.q = queue.Queue()
        self.closed = False

    def put(self, v: T) -> None:
        assert not self.closed

        wait_q = self.q.get()
        wait_q.put(v)

    def get(self) -> T:
        assert not self.closed
        wait_q: queue.Queue[T] = queue.Queue()
        self.q.put(wait_q)

        return wait_q.get()

    def close(self) -> None:
        """Close the channel. In python 3.13, we will be able to call
        .shutdown() on a queue, which will remove the possible race condition
        that happens when .close() is run at the same time as .put() or .get().
        """

        assert not self.closed
        self.closed = True
