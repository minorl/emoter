import db
from economy.econ_db import AccountDoc

if __name__ == '__main__':
    for obj in AccountDoc.objects:
        for field in ('secondary_currency', 'level'):
            if getattr(obj, field) is None:
                print('Adding field: {} to {}'.format(field, obj.user))
                obj.update(**{field: 0})
