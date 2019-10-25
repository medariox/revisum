import os.path

from ..utils import get_project_root
from peewee import SqliteDatabase, Model, BlobField, CharField, IntegerField


db = SqliteDatabase(None)


def maybe_init(repo_id, pr_number=None, path=None):
    if path is not None:
        db_dir = path
    else:
        db_dir = os.path.join(get_project_root(), 'data', str(repo_id))
    if not os.path.isdir(db_dir):
        os.makedirs(db_dir)

    db_name = 'snippets.db'
    db_path = os.path.join(db_dir, db_name)
    db.init(db_path, pragmas={
        'journal_mode': 'wal',
        'cache_size': -1 * 64000,  # 64MB
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0})

    if not os.path.isfile(db_path):
        if pr_number is None:
            print('PR number required to init a snippet for: {0}'.format(repo_id))
            return

        create()
        print('Snippet database created for: {0}-{1}'.format(pr_number, repo_id))


def create():
    db.create_tables([Snippet])


class Snippet(Model):

    snippet_id = CharField()
    start = IntegerField()
    length = IntegerField()
    source = CharField()
    target = CharField()
    hunk = BlobField()

    class Meta:
        database = db
