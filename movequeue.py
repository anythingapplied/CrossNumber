class MoveQueue:
    def __init__(self):
        self._queue = []

    def add(self, x, y, toggle):
        self._queue.append((x, y, tuple(toggle)))

    def undo(self):
        if self._queue:
            return self._queue.pop()
        else:
            pass #TODO

    def save(self):
        pass
        return dic

    def load(self):
        pass
        return self

    def fail(self):
        pass

    def revert(self):
        pass

    def next(self):
        pass
