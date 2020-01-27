import os.path

from ..utils import get_project_root

from peewee import (
    SqliteDatabase,
    BlobField,
    Model,
    CharField,
    IntegerField
)


db = SqliteDatabase(None)


def init(db_path):
    db.init(str(db_path), pragmas={
        'journal_mode': 'wal',
        'cache_size': -1 * 64000,  # 64MB
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0})


def maybe_init(pr_number, repo_id, path=None):
    if path is not None:
        db_dir = os.path.join(path, 'chunks')
    else:
        db_dir = os.path.join(get_project_root(), 'data', str(repo_id), 'chunks')
    if not os.path.isdir(db_dir):
        os.makedirs(db_dir)

    name = '{0}-{1}'.format(pr_number, repo_id)
    db_name = name + '.db'
    db_path = os.path.join(db_dir, db_name)
    db.init(db_path, pragmas={
        'journal_mode': 'wal',
        'cache_size': -1 * 64000,  # 64MB
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0})

    if not os.path.isfile(db_path):
        create()
        print('Chunks database created for: {0}'.format(name))


def create():
    db.create_tables([Chunk])


class Chunk(Model):

    snippet_id = CharField()
    b64_hash = CharField()
    name = CharField()
    no = IntegerField()
    file_path = CharField()
    start = IntegerField()
    end = IntegerField()
    body = BlobField()
    sloc = IntegerField()
    complexity = IntegerField()

    class Meta:
        database = db
