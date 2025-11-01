import logging
import time

format = '%(asctime)s [%(levelname)-10s] '
format += '[%(filename)-20s] [%(funcName)-25s] %(message)s'
formatter = logging.Formatter(format)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
timeit_logger = logging.getLogger('utilities.profiling.timeit')
timeit_logger.setLevel(logging.DEBUG)
timeit_logger.addHandler(ch)


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            timeit_logger.debug('{!r}  {:2.2f} ms'.format(
                method.__name__, (te - ts) * 1000))
        return result
    return timed


class Timer():
    def __init__(self):
        self.stopped = True
        self.reset()

    def reset(self):
        if self.stopped:
            self.lap_ts = 0
            self.lap_te = 0
            self.lap_count = 0
            self.total_ts = 0
            self.total_te = 0
            self.stopped = True
            self.is_reset = True

    def start(self):
        if self.is_reset:
            self.total_ts = time.time()
            self.lap_te = self.total_ts
            self.is_reset = False
        self.stopped = False
        return self.lap_time()

    def stop(self):
        total_time, lap_time, self.lap_count = self.lap_time()
        self.stopped = True
        return total_time, lap_time, self.lap_count

    def lap_time(self):
        if not self.stopped:
            self.lap_ts = self.lap_te
            self.lap_te = time.time()
            self.lap_count += 1
        lap_time = self.lap_te - self.lap_ts
        total_time = self.lap_te - self.total_ts
        return total_time, lap_time, self.lap_count
