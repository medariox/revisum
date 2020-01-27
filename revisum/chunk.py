import functools
import pickle
from itertools import chain
from textwrap import dedent

from .metrics import Metrics, MetricsException
from .tokenizer import LinesTokenizer
from .utils import b64_decode, b64_encode
from .database.chunk import maybe_init, Chunk as DataChunk


class ChunkException(Exception):
    pass


class Chunk(object):

    def __init__(self, snippet_id, name, no, file_path, body, start, end):
        self.snippet_id = snippet_id
        self.name = name
        self.no = no
        self.file_path = file_path
        self._body = body
        self.start = start
        self.end = end

        self._lines = []
        self._tokens = []
        self._metrics = None
        self._encoded_b64_hash = None

        self.metrics

    def __str__(self):
        return dedent('\n'.join(self.lines))

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
    def repo_id(self):
        return self.snippet_id.split('-', 2)[1]

    @property
    def pr_id(self):
        return self.snippet_id.split('-', 2)[2]

    @property
    def b64_hash(self):
        if not self._encoded_b64_hash:
            self._encoded_b64_hash = b64_encode(
                '+'.join([self.pr_id, self.file_path,
                          str(self.start), str(self.end)])
            )

        return self._encoded_b64_hash

    @property
    def metrics(self):
        if not self._metrics:
            try:
                self._metrics = Metrics(self.repo_id, code=str(self))
            except MetricsException as e:
                raise ChunkException(e)
        return self._metrics

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

    @classmethod
    def load(cls, b64_hash):
        pr_number, repo_id = cls.pr_id_from_hash(b64_hash)
        maybe_init(pr_number, repo_id)

        chunk = DataChunk.get_or_none(b64_hash=b64_hash)
        if chunk:
            return pickle.loads(chunk.body)

    @classmethod
    def load_snippet_id(cls, b64_hash, path=None):
        pr_number, repo_id = cls.pr_id_from_hash(b64_hash)
        maybe_init(pr_number, repo_id, path)

        chunk = DataChunk.get_or_none(b64_hash=b64_hash)
        if chunk:
            return chunk.snippet_id

    @classmethod
    def as_text(cls, body, pretty=False):
        lines = []
        for line_tokens in body:
            line = ''.join(line[1] for line in line_tokens)
            lines.append(line.rstrip())

        return '\n'.join(lines) if pretty else lines

    @classmethod
    def as_tokens(cls, body):
        return LinesTokenizer(cls.as_text(body)).tokens

    @classmethod
    def pr_number_from_hash(cls, b64_hash):
        return cls.pr_id_from_hash(b64_hash)[0]

    @classmethod
    def repo_id_from_hash(cls, b64_hash):
        return cls.pr_id_from_hash(b64_hash)[1]

    @classmethod
    @functools.lru_cache(maxsize=1024)
    def pr_id_from_hash(cls, b64_hash):
        decoded_hash = b64_decode(b64_hash)
        pr_number, repo_id = decoded_hash.split('+', 1)[0].split('-', 1)
        return pr_number, repo_id

    def _serialize(self):
        return pickle.dumps(self._body, pickle.HIGHEST_PROTOCOL)

    def save(self, pr_number, repo_id):
        maybe_init(pr_number, repo_id)

        chunk = DataChunk.get_or_none(b64_hash=self.b64_hash)
        if chunk:
            (DataChunk
             .update(snippet_id=self.snippet_id,
                     b64_hash=self.b64_hash,
                     name=self.name,
                     no=self.no,
                     file_path=self.file_path,
                     start=self.start,
                     end=self.end,
                     body=self._serialize(),
                     sloc=self.metrics.sloc,
                     complexity=self.metrics.complexity)
             .where(DataChunk.b64_hash == chunk.b64_hash)
             .execute())
        else:
            (DataChunk
             .create(snippet_id=self.snippet_id,
                     b64_hash=self.b64_hash,
                     name=self.name,
                     no=self.no,
                     file_path=self.file_path,
                     start=self.start,
                     end=self.end,
                     body=self._serialize(),
                     sloc=self.metrics.sloc,
                     complexity=self.metrics.complexity))
