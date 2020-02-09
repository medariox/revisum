import pickle
from collections import OrderedDict
from datetime import datetime

from .chunk import Chunk
from .review import Review
from .tokenizer import LineTokenizer
from .database.snippet import maybe_init, Snippet as DataSnippet


class Snippet(object):

    def __init__(self, snippet_id, merged, chunks, source, target):
        self.snippet_id = snippet_id
        self.merged = merged
        self._chunks = chunks
        self._chunk_ids = []
        self.start = chunks[0].start
        self.length = self.total_len(chunks[0].start, chunks[-1].end)
        self.source_file = str(source)
        self.target_file = str(target)

        self._target_lines = []
        self._source_lines = []
        self._target_tokens = []
        self._source_tokens = []

    def __str__(self):
        return '\n-------------------------\n'.join(self.to_text())

    def to_json(self):
        snippet = OrderedDict()
        snippet['snippet_id'] = self.snippet_id

        reviews = Review.load(self.pr_number(self.snippet_id),
                              self.repo_id(self.snippet_id))
        snippet['reviews'] = [review.to_json() for review in reviews]

        snippet['chunk_ids'] = self.chunk_ids

        return snippet

    @property
    def chunks(self):
        return self._chunks

    @property
    def chunk_ids(self):
        if not self._chunk_ids:
            self._chunk_ids = [c.chunk_id for c in self._chunks]

        return self._chunk_ids

    @staticmethod
    def repo_id(snippet_id):
        return snippet_id.split('-')[3]

    @staticmethod
    def pr_number(snippet_id):
        return snippet_id.split('-')[2]

    @classmethod
    def make_id(cls, hunk_no, file_no, pr_number, repo_id):
        return '-'.join([str(hunk_no), str(file_no),
                         str(pr_number), str(repo_id)])

    @staticmethod
    def total_len(start, end):
        length = end - start + 1
        return length

    def to_tokens(self):
        chunks = []
        for chunk in self._chunks:
            chunks.append(chunk.as_tokens())

        return chunks

    def to_text(self):
        chunks = []
        for chunk in self._chunks:
            chunks.append(chunk.as_text(pretty=True))

        return chunks

    @classmethod
    def as_tokens(cls, code):
        if not isinstance(code, list):
            code = [code]

        tokens = LineTokenizer(code).tokens
        lines = []
        for line in tokens:
            lines += line

        return lines

    @classmethod
    def as_elements(cls, code):
        if not isinstance(code, list):
            code = [code]

        tokens = LineTokenizer(code).elements
        lines = []
        for line in tokens:
            lines += line

        return lines

    @classmethod
    def load(cls, snippet_id, path=None):
        repo_id = cls.repo_id(snippet_id)
        maybe_init(repo_id, path=path)

        db_snippet = DataSnippet.get_or_none(snippet_id=snippet_id)
        if db_snippet:

            chunks = []
            chunk_ids = pickle.loads(db_snippet.chunk_ids)
            for chunk_id in chunk_ids:
                chunks.append(Chunk.load(chunk_id))

            merged = db_snippet.merged
            source = db_snippet.source
            target = db_snippet.target

            snippet = cls(snippet_id, merged, chunks, source, target)
            return snippet

    @classmethod
    def load_all(cls, repo_id, merged_only=False, path=None):
        maybe_init(repo_id, path=path)

        query = DataSnippet.select(
            DataSnippet.snippet_id,
            DataSnippet.chunk_ids,
            DataSnippet.source,
            DataSnippet.target)

        if merged_only:
            query = query.where(DataSnippet.merged == 1)

        query = query.order_by(DataSnippet.last_mod.desc())

        snippets = []
        for db_snippet in query:
            snippet_id = db_snippet.snippet_id

            chunks = []
            chunk_ids = pickle.loads(db_snippet.chunk_ids)
            for chunk_id in chunk_ids:
                chunks.append(Chunk.load(chunk_id))

            merged = db_snippet.merged
            source = db_snippet.source
            target = db_snippet.target

            snippet = cls(snippet_id, merged, chunks, source, target)
            print('Finished loading snippet with ID: {0}'.format(snippet_id))
            snippets.append(snippet)

        return snippets

    def _serialize_ids(self):
        return pickle.dumps(self.chunk_ids, pickle.HIGHEST_PROTOCOL)

    def exists(self):
        repo_id = self.repo_id(self.snippet_id)
        maybe_init(repo_id)

        snippet = DataSnippet.get_or_none(snippet_id=self.snippet_id)
        return bool(snippet)

    def save(self):
        repo_id = self.repo_id(self.snippet_id)
        maybe_init(repo_id)

        snippet = DataSnippet.get_or_none(snippet_id=self.snippet_id)
        if snippet:
            (DataSnippet
             .update(snippet_id=self.snippet_id,
                     merged=self.merged,
                     last_mod=datetime.now(),
                     start=self.start,
                     length=self.length,
                     source=self.source_file,
                     target=self.target_file,
                     chunk_ids=self._serialize_ids())
             .where(DataSnippet.snippet_id == self.snippet_id)
             .execute())
        else:
            (DataSnippet
             .create(snippet_id=self.snippet_id,
                     merged=self.merged,
                     last_mod=datetime.now(),
                     start=self.start,
                     length=self.length,
                     source=self.source_file,
                     target=self.target_file,
                     chunk_ids=self._serialize_ids()))
