from config import DB_NAME
import mongoengine
from slack.history import HistoryDoc

def main():
    mongoengine.connect(DB_NAME)
    seen_timestamps = set()
    docs = HistoryDoc.objects()

    to_delete = []
    for d in docs:
        if d.time in seen_timestamps:
            to_delete.append(d)
        seen_timestamps.add(d.time)
    print('Found {} duplicate timestamps'.format(len(to_delete)))
    if not to_delete or input('Delete duplicates? (y/n): ').lower() != 'y':
        exit()

    for d in to_delete:
        d.delete()

if __name__ == '__main__':
    main()
