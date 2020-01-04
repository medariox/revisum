from itertools import chain

from .metrics import Metrics
from .tokenizer import LinesTokenizer


class Chunk(object):

    def __init__(self, name, no, body, start, end):
        self.name = name
        self.no = no
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
