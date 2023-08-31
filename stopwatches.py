import time

__times = {}


def start(key):
    __times[key] = time.time()


def seconds(key):
    if key in __times:
        return round(time.time() - __times[key], 2)
    else:
        return -1
