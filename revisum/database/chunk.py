import os.path

from ..utils import get_project_root

from peewee import (
    SqliteDatabase,
    DateTimeField,
    BlobField,
    Model,
    CharField,
    IntegerField
)


db = SqliteDatabase(None)


def maybe_init(repo_id, path=None):
    if path is not None:
        db_dir = path
    else:
        db_dir = os.path.join(get_project_root(), 'data', str(repo_id))
    if not os.path.isdir(db_dir):
        os.makedirs(db_dir)

    db_name = 'chunks.db'
    db_path = os.path.join(db_dir, db_name)
    db.init(db_path, pragmas={
        'journal_mode': 'wal',
        'cache_size': -1 * 64000,  # 64MB
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0})

    if not os.path.isfile(db_path):
        create()
        print('Chunks database created for: {0}'.format(repo_id))


def create():
    db.create_tables([Chunk])


class Chunk(Model):

    chunk_id = CharField()
    sha1_hash = CharField()
    name = CharField()
    no = IntegerField()
    file_path = CharField()
    start = IntegerField()
    end = IntegerField()
    body = BlobField()
    last_mod = DateTimeField()
    sloc = IntegerField()
    complexity = IntegerField()
    cognitive = IntegerField()

    class Meta:
        database = db
