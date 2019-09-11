from multiprocessing.dummy import Pool
from functools import partial


def run(func, iterable, thread_pool_size, **kwargs):
    """run executes a function for each item in the input iterable.
    execution will be multithreaded according to the input thread_pool_size.
    kwargs are passed to the input function (optional)."""

    pool = Pool(thread_pool_size)
    func_partial = partial(func, **kwargs)
    return pool.map(func_partial, iterable, chunksize=1)
