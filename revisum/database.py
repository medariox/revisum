import os.path

from peewee import SqliteDatabase, Model, CharField, IntegerField


db = SqliteDatabase(None)


def maybe_init(name):
    if db.is_closed():
        name = str(name)
        path = os.path.dirname(os.path.abspath(__file__))
        db_dir = os.path.join(path, 'data', name)
        db_name = name + '.db'
        db_path = os.path.join(db_dir, db_name)
        db.init(db_path, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 64000,  # 64MB
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 0})

        if not os.path.isfile(db_path):
            print('Database created')
            create()


def create():
    db.create_tables([Review])


class Review(Model):

    review_id = IntegerField()
    pr_number = IntegerField()
    repo_id = IntegerField()
    state = CharField()
    body = CharField()

    class Meta:
        database = db