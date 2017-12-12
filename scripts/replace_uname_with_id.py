import config
import db
import requests
from slack.history import HistoryDoc


def main():
    users = requests.get('https://slack.com/api/users.list', params={'token': config.TOKEN}).json()['members']
    uname_to_id = {u['name']: u['id'] for u in users}
    docs = HistoryDoc.objects()
    for d in docs:
        user = d.user
        if user:
            d.update(user=None, uid=uname_to_id[user])
    HistoryDoc.objects.update(unset__user=1)
    print(len(docs))

if __name__ == '__main__':
    main()
