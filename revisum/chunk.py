import pickle

from itertools import chain

from .metrics import Metrics
from .snippet import Snippet
from .tokenizer import LinesTokenizer
from .database.chunk import maybe_init, Chunk as DataChunk


class Chunk(object):

    def __init__(self, name, no, file_no, body, start, end):
        self.name = name
        self.no = no
        self.file_no = file_no
        self._body = body
        self.start = start
        self.end = end

        self._lines = []
        self._tokens = []
        self._metrics = None

        self.metrics

    def __str__(self):
        return '\n'.join(self.lines)

    @property
    def lines(self):
        if not self._lines:
            self._to_text()
        return self._lines

    @property
    def tokens(self):
        if not self._tokens:
            self._to_tokens()
        return self._tokens

    @property
    def merged_tokens(self):
        merged = list(chain.from_iterable(self.tokens))
        return merged

    def _to_text(self):
        for line_tokens in self._body:
            line = ''.join(line[1] for line in line_tokens)
            self._lines.append(line.rstrip())

        return self._lines

    def _to_tokens(self):
        self._tokens = LinesTokenizer(self.lines).tokens
        return self._tokens

    @property
    def metrics(self):
        if not self._metrics:
            self._metrics = Metrics(str(self))
        return self._metrics

    def _serialize(self):
        return pickle.dumps(self._body, pickle.HIGHEST_PROTOCOL)

    def save(self, snippet_id):
        repo_id = Snippet.repo_id(snippet_id)
        maybe_init(repo_id, snippet_id)

        chunk_id = '{0}-{1}'.format(self.no, snippet_id)
        chunk = DataChunk.get_or_none(
            (DataChunk.start == self.start) &
            (DataChunk.end == self.end) &
            (DataChunk.file_no == self.file_no))

        if chunk:
            (DataChunk
             .update(chunk_id=chunk_id,
                     name=self.name,
                     no=self.no,
                     file_no=self.file_no,
                     start=self.start,
                     end=self.end,
                     body=self._serialize())
             .where(DataChunk.chunk_id == chunk.chunk_id)
             .execute())
        else:
            (DataChunk
             .create(chunk_id=chunk_id,
                     name=self.name,
                     no=self.no,
                     file_no=self.file_no,
                     start=self.start,
                     end=self.end,
                     body=self._serialize()))
