import functools
import pickle
from collections import OrderedDict
from datetime import datetime
from itertools import chain
from textwrap import dedent
from zlib import compress, decompress

from pygments import lex
from pygments.lexers import PythonLexer

from .metrics import Metrics, MetricsException
from .tokenizer import LineTokenizer
from .utils import b64_decode, b64_encode
from .database.chunk import maybe_init, Chunk as DataChunk


class ChunkException(Exception):
    pass


class Chunk(object):

    def __init__(self, chunk_id, name, no, file_path, body, start, end):
        self.chunk_id = chunk_id
        self._repo_id = chunk_id.split('-', 4)[4]
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

        # Compute metrics
        self.metrics

    def __str__(self):
        return dedent('\n'.join(self.lines))

    @classmethod
    def make_id(cls, no, snippet_id):
        return '{0}-{1}'.format(no, snippet_id)

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
    def b64_hash(self):
        if not self._encoded_b64_hash:
            self._encoded_b64_hash = b64_encode(
                '+'.join([self._repo_id, self.file_path, str(self.start)])
            )

        return self._encoded_b64_hash

    @property
    def metrics(self):
        if not self._metrics:
            try:
                self._metrics = Metrics(self._repo_id, code=str(self))
            except MetricsException as e:
                raise ChunkException(e)

        return self._metrics

    @metrics.setter
    def metrics(self, metrics_obj):
        self._metrics = metrics_obj

    @property
    def merged_tokens(self):
        merged = list(chain.from_iterable(self.tokens))
        return merged

    def to_json(self):
        chunk = OrderedDict()
        chunk['chunk_id'] = self.chunk_id
        chunk.update(self.metrics.to_json())
        chunk['tokens'] = self.tokens

        return chunk

    def _to_text(self):
        for line_tokens in self._body:
            line = ''.join(line[1] for line in line_tokens)
            self._lines.append(line.rstrip())

        return self._lines

    def _to_tokens(self):
        self._tokens = LineTokenizer(self.lines).tokens
        return self._tokens

    @classmethod
    def compare(cls, chunk_id, other_chunk_id):
        chunk = cls.load(chunk_id)
        other_chunk = cls.load(other_chunk_id)

        result = {}
        rating = round(other_chunk.metrics.rating - chunk.metrics.rating, 2)
        result['rating'] = rating

        metrics = {}
        metrics['sloc'] = round(other_chunk.metrics.sloc - chunk.metrics.sloc, 2)
        metrics['complexity'] = round(other_chunk.metrics.complexity - chunk.metrics.complexity, 2)
        metrics['cognitive'] = round(other_chunk.metrics.cognitive - chunk.metrics.cognitive, 2)
        result['metrics'] = metrics

        return result

    @classmethod
    def load(cls, chunk_id):
        repo_id = cls.repo_id(chunk_id)
        maybe_init(repo_id)

        chunk_data = DataChunk.get_or_none(chunk_id=chunk_id)
        if chunk_data:

            chunk_lines = pickle.loads(decompress(chunk_data.body))
            chunk_body = []
            for line in chunk_lines:
                chunk_body.append(list(lex(line, PythonLexer())))

            chunk = Chunk(
                chunk_id, chunk_data.name, chunk_data.no, chunk_data.file_path,
                chunk_body, chunk_data.start, chunk_data.end
            )

            metrics = Metrics(repo_id, code=str(chunk))
            metrics.sloc = chunk_data.sloc
            metrics.complexity = chunk_data.complexity
            metrics.cognitive = chunk_data.cognitive
            chunk.metrics = metrics

            return chunk

    @classmethod
    def load_snippet_id(cls, chunk_id, path=None):
        repo_id = cls.repo_id(chunk_id)
        maybe_init(repo_id, path=path)

        chunk = DataChunk.get_or_none(chunk_id=chunk_id)
        if chunk:
            return chunk.chunk_id.split('-', 1)[1]

    def as_text(self, pretty=False):
        return '\n'.join(self.lines) if pretty else self.lines

    def as_tokens(self, pretty=False):
        return self.merged_tokens if pretty else LineTokenizer(self.lines).tokens

    @classmethod
    def repo_id(cls, chunk_id):
        return chunk_id.split('-', 4)[4]

    @classmethod
    def pr_number(cls, chunk_id):
        return chunk_id.split('-', 4)[3]

    @classmethod
    @functools.lru_cache(maxsize=1024)
    def info_from_hash(cls, b64_hash):
        decoded_hash = b64_decode(b64_hash)
        return decoded_hash.split('+')

    def _serialize(self):
        return compress(pickle.dumps(self.lines, pickle.HIGHEST_PROTOCOL))

    def save(self, repo_id):
        maybe_init(repo_id)

        chunk = DataChunk.get_or_none(chunk_id=self.chunk_id)
        if chunk:
            (DataChunk
             .update(chunk_id=self.chunk_id,
                     b64_hash=self.b64_hash,
                     name=self.name,
                     no=self.no,
                     file_path=self.file_path,
                     start=self.start,
                     end=self.end,
                     body=self._serialize(),
                     last_mod=datetime.now(),
                     sloc=self.metrics.sloc,
                     complexity=self.metrics.complexity,
                     cognitive=self.metrics.cognitive)
             .where(DataChunk.chunk_id == chunk.chunk_id)
             .execute())
        else:
            (DataChunk
             .create(chunk_id=self.chunk_id,
                     b64_hash=self.b64_hash,
                     name=self.name,
                     no=self.no,
                     file_path=self.file_path,
                     start=self.start,
                     end=self.end,
                     body=self._serialize(),
                     last_mod=datetime.now(),
                     sloc=self.metrics.sloc,
                     complexity=self.metrics.complexity,
                     cognitive=self.metrics.cognitive))
