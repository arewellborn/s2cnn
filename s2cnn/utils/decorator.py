# pylint: disable=R,C,E1101
import threading
import time
from functools import wraps
from functools import lru_cache
import pickle
import gzip
import os
import sys


class WaitPrint(threading.Thread):
    def __init__(self, t, message):
        super().__init__()
        self.t = t
        self.message = message
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        for _ in range(int(self.t // 0.1)):
            time.sleep(0.1)
            if not self.running:
                return
        print(self.message, end="")


def show_running(func):
    @wraps(func)
    def g(*args, **kargs):
        x = WaitPrint(
            2,
            "{}({})... ".format(
                func.__name__,
                ", ".join(
                    [repr(x) for x in args] +
                    ["{}={}".format(key, repr(value)) for key, value in kargs.items()]
                )
            )
        )
        x.start()
        t = time.perf_counter()
        r = func(*args, **kargs)
        if x.is_alive():
            x.stop()
        else:
            print("done in {:.0f} seconds".format(time.perf_counter() - t))
        return r
    return g


def cached_dirpklgz(dirname):
    '''
    Cache a function with a directory
    '''
    def decorator(func):
        '''
        The actual decorator
        '''
        @lru_cache(maxsize=None)
        @wraps(func)
        def wrapper(*args):
            '''
            The wrapper of the function
            '''
            try:
                os.makedirs(dirname)
            except FileExistsError:
                pass

            indexfile = os.path.join(dirname, "index.pkl")

            try:
                with open(indexfile, "rb") as file:
                    index = pickle_loads(file, indexfile)
            except FileNotFoundError:
                index = {}

            try:
                filename = index[args]
            except KeyError:
                index[args] = filename = "{}.pkl.gz".format(len(index))
                with open(indexfile, "wb") as file:
                    pickle_dumps(index, file)

            filepath = os.path.join(dirname, filename)

            try:
                with gzip.open(filepath, "rb") as file:
                    print("load {}... ".format(filename), end="")
                    result = pickle_loads(file, filepath)
            except FileNotFoundError:
                print("compute {}... ".format(filename), end="")
                sys.stdout.flush()
                result = func(*args)
                print("save {}... ".format(filename), end="")
                with gzip.open(filepath, "wb") as file:
                    pickle_dumps(result, file)
            print("done")
            return result
        return wrapper
    return decorator


def pickle_loads(file, file_path):
    max_bytes = 2**31 - 1
    bytes_in = bytearray(0)
    input_size = os.path.getsize(file_path)
    for _ in range(0, input_size, max_bytes):
        bytes_in += file.read(max_bytes)
    result = pickle.loads(bytes_in)
    return result

def pickle_dumps(dump, file):
    max_bytes = 2**31 - 1
    bytes_out = pickle.dumps(dump)
    for idx in range(0, len(dump), max_bytes):
        file.write(bytes_out[idx:idx + max_bytes])