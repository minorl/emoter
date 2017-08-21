import asyncio
from collections import ChainMap
from functools import partial
import logging

import requests

HEADERS = {'User-Agent': 'Reddit Scraper for Slack'}

logger = logging.getLogger(__name__)

def process_comment(data):
    return {'text': data['body'], 'comment_id': data['id'], 'link_id': data['link_id'], 'created': data['created']} if 'body' in data else None

def process_post(data):
    return {'title': data['title'], 'post_id': data['id'], 'text': data['selftext'], 'created': data['created']}

async def get_posts(user, comments=False, most_recent=float('-inf')):
    loop = asyncio.get_event_loop()

    results = []
    after = None
    while True:
        request_callable = partial(
            requests.get,
            'https://www.reddit.com/user/{}/{}/.json'.format(
                user,
                'comments' if comments else 'submitted'),
            params=ChainMap({'raw_json': 1}, {} if after is None else {'after': after}),
            headers=HEADERS)

        result = await loop.run_in_executor(None, request_callable)
        if result.status_code != 200:
            logger.warning('Request for reddit user %s returned status %d', user, result.status_code)
            return None, most_recent
        children = result.json()['data']['children']

        new_posts = [child['data'] for child in children if child['data']['created'] > most_recent]
        if not new_posts:
            break

        results.extend(val for val in ((process_comment if comments else process_post)(child) for child in new_posts)
            if val is not None)
        logger.info('%d new posts for reddit user %s', len(results), user)
        after = result.json()['data']['after']

        if after is None:
            break

    if results:
        most_recent = results[0]['created']

    return results, most_recent

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    print(loop.run_until_complete(get_posts('davisyoshidasdfadsfasef')))
