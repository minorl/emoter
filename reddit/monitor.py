import asyncio
import logging

from mongoengine.errors import DoesNotExist
from reddit.schema import RedditUser, RedditPost, RedditComment
from reddit.scraper import get_posts


logger = logging.getLogger(__name__)

SCRAPE_DELAY = 600


async def get_or_make_user(username):
    try:
        obj = RedditUser.objects.get(uname=username)
    except DoesNotExist:
        obj = RedditUser(uname=username, latest_comment=float('-inf'), latest_post=float('-inf'))
        obj.save()
        await get_posts_for_user(obj)
        obj = RedditUser.objects.get(uname=username)
        if len(obj.posts) == 0 and len(obj.comments) == 0:
            obj.delete()
            logger.info('User %s has no posts or comments', username)
            return None
    return obj

async def get_user_posts(username):
    user_obj = await get_or_make_user(username)
    if user_obj is None:
        return []
    return [(p.title, p.text) for p in user_obj.posts]


async def get_user_comments(username):
    user_obj = await get_or_make_user(username)
    if user_obj is None:
        return []
    return [c.text for c in user_obj.comments]


async def get_posts_for_user(user):
    logger.info('Getting reddit posts for user %s', user.uname)
    comments, latest_comment = await get_posts(user.uname, comments=True, most_recent=user.latest_comment)
    if comments:
        user.update(latest_comment=latest_comment)

        for comment in comments:
            comment_obj = RedditComment(**comment)
            comment_obj.save()
            user.update(push__comments=comment_obj)

    posts, latest_post = await get_posts(user.uname, comments=False, most_recent=user.latest_post)
    if posts:
        user.update(latest_post=latest_post)
        for post in posts:
            post_obj = RedditPost(**post)
            post_obj.save()
            user.update(push__posts=post_obj)


async def run():
    while True:
        for user in RedditUser.objects():
            await get_posts_for_user(user)
        await asyncio.sleep(SCRAPE_DELAY)
