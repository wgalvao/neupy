""" Code from `tqdm` library: https://github.com/noamraph/tqdm
"""
import sys
import time
import threading


__all__ = ('progressbar',)


def format_interval(t):
    mins, seconds = divmod(int(t), 60)
    hours, minutes = divmod(mins, 60)

    if hours > 0:
        return '{:0>2d}:{:0>2d}:{:0>2d}'.format(hours, minutes, seconds)

    return '{:0>2d}:{:0>2d}'.format(minutes, seconds)


def format_meter(n_finished, n_total, elapsed):
    """ Format meter.
    Parameters
    ----------
    n_finished : int
        Number of finished iterations.
    n_total : int or None
        Total number of iterations.
    elapsed : int
        Number of seconds passed since start
    """
    if n_finished > n_total:
        n_total = None

    elapsed_str = format_interval(elapsed)
    rate = '%5.2f' % (n_finished / elapsed) if elapsed else '?'

    if n_total is not None:
        frac = float(n_finished) / n_total

        n_bars = 10
        bar_length = int(frac * n_bars)
        bar = '#' * bar_length + '-' * (n_bars - bar_length)

        percentage = '%3d%%' % (frac * 100)

        left_str = format_interval(
            elapsed / n_finished * (n_total - n_finished)
        ) if n_finished else '?'

        return '|{}| {}/{} {} [elapsed: {} left: {}, {} iters/sec]'.format(
            bar, n_finished, n_total, percentage,
            elapsed_str, left_str, rate
        )

    return '{} [elapsed: {}, {} iters/sec]'.format(n_finished,
                                                   elapsed_str, rate)


class StatusPrinter(object):
    def __init__(self, file):
        self.file = file
        self.last_printed_len = 0

    def write(self, text):
        n_spaces = max(self.last_printed_len - len(text), 0)
        self.file.write('\r' + text + ' ' * n_spaces)
        self.file.flush()
        self.last_printed_len = len(text)


def progressbar(iterable, desc='', total=None, leave=False, file=sys.stderr,
                mininterval=0.5, miniters=1, init_interval=0):
    """ Get an iterable object, and return an iterator which acts
    exactly like the iterable, but prints a progress meter and updates
    it every time a value is requested.

    Parameters
    ----------
    desc : str
        Can contain a short string, describing the progress,
        that is added in the beginning of the line.
    total : int
        Can give the number of expected iterations. If not given,
        len(iterable) is used if it is defined.
    file : object
        Can be a file-like object to output the progress message to.
    leave : bool
        If leave is False, ``progressbar`` deletes its traces
        from screen after it has finished iterating over all elements.
    mininterval : float
    miniters : int
        If less than mininterval seconds or miniters
        iterations have passed since the last progress meter
        update, it is not updated again.
    """
    if total is None:
        try:
            total = len(iterable)
        except TypeError:
            total = None

    prefix = desc + ': ' if desc else ''

    printer = StatusPrinter(file)
    status = prefix + format_meter(0, total, 0)

    timer = threading.Timer(init_interval, printer.write, args=[status])
    timer.start()

    start_time = last_print_time = time.time()
    last_print_n = 0
    n = 0
    for obj in iterable:
        yield obj
        timer.cancel()

        # Now the object was created and processed, so we
        # can print the meter.
        n += 1
        if n - last_print_n >= miniters:
            # We check the counter first, to reduce the
            # overhead of time.time()
            current_time = time.time()
            if current_time - last_print_time >= mininterval:
                printer.write(
                    prefix + format_meter(n, total, current_time - start_time)
                )
                last_print_n = n
                last_print_time = current_time

    if not leave:
        printer.write('')
        sys.stdout.write('\r')
    else:
        if last_print_n < n:
            current_time = time.time()
            printer.write(
                prefix + format_meter(n, total, current_time - start_time)
            )
        file.write('\n')
