import os.path

from utils import get_project_root
from peewee import (
    BooleanField,
    SqliteDatabase,
    Model, CharField,
    FloatField,
    IntegerField
)


db = SqliteDatabase(None)


def maybe_init(repo_id):
    path = get_project_root()
    db_dir = os.path.join(path, 'data', str(repo_id))
    if not os.path.isdir(db_dir):
        os.makedirs(db_dir)

    db_name = 'reviews.db'
    db_path = os.path.join(db_dir, db_name)
    db.init(db_path, pragmas={
        'journal_mode': 'wal',
        'cache_size': -1 * 64000,  # 64MB
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0})

    if not os.path.isfile(db_path):
        print('Review database created for: {0}'.format(repo_id))
        create()


def create():
    db.create_tables([Review])


class Review(Model):

    comment_id = IntegerField()
    pr_number = IntegerField()
    pr_merged = BooleanField()
    repo_id = IntegerField()
    state = CharField()
    rating = FloatField()
    user_id = IntegerField()
    user_login = CharField()
    body = CharField()

    class Meta:
        database = db
