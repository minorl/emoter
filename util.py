import asyncio
from asyncio.futures import CancelledError
from functools import partial
from itertools import chain, zip_longest
import requests
import tempfile
import shutil
import traceback


async def get_image(url):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            out_name = next(tempfile._get_candidate_names()) + '.png'
            with open(out_name, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
            return out_name
        raise ValueError


def grouper(it, n, fill=None):
    """Break an iterator into chunks of length n
    Positional arguments:
        it -- iterable to be chunked
        n -- integer length of chunks
    Keyword arguments:
    fill -- Value to fill the last iterator if when
    the length of the input is not divisible by n
    """
    args = [iter(it)] * n
    return zip_longest(*args, fillvalue=fill)


def dict_merge(it):
    """Merge an iterable of dictionaries into one dictionary
    Behavior for duplicate keys is undefined
    Example: dict_merage([{1:2}, {3:4}]) --> {1:2,3:4}
    Positional arguments:
        it -- iterable of dictionaries
    """
    # This is readable
    return dict(chain(*map(dict.items, it)))


def kill_all_tasks():
    for task in asyncio.Task.all_tasks():
        task.cancel()
        print('Cancelled task')


async def handle_async_exception(coro, *args, **kwargs):
    try:
        return await coro(*args, **kwargs)
    except Exception as e:
        if not isinstance(e, CancelledError):
            print('Exception in {}'.format(coro))
            print(traceback.format_exc())
            kill_all_tasks()


_request_funcs = {'GET': requests.get, 'POST': requests.post}


async def make_request(url, params, request_type='GET'):
    loop = asyncio.get_event_loop()
    get = partial(requests.get, params=params)
    res = (await loop.run_in_executor(None, get, url)).json()
    if res['ok'] is not True:
        print('Bad return:', res)
