import pickle

from .tokenizer import LinesTokenizer
from .database.snippet import maybe_init, Snippet as DataSnippet


class Snippet(object):

    def __init__(self, snippet_id, hunks, source, target):
        self.snippet_id = snippet_id
        self._hunk = hunks
        self.start = hunks[0].start
        self.length = self.total_len(hunks[0].start, hunks[-1].end)
        self.source_file = source
        self.target_file = target

        self._target_lines = []
        self._source_lines = []
        self._target_tokens = []
        self._source_tokens = []

    def __str__(self):
        return '\n'.join(line for line in self.target_lines())

    @staticmethod
    def repo_id(snippet_id):
        return snippet_id.split('-')[3]

    @staticmethod
    def pr_number(snippet_id):
        return snippet_id.split('-')[2]

    @staticmethod
    def total_len(start, end):
        length = end - start + 1
        return length

    def target_lines(self):
        if not self._target_lines:
            # self._normalize_lines('target')
            for hunk in self._hunk:
                for line in hunk.lines:
                    self._target_lines.append(line)

        return self._target_lines

    def source_lines(self):
        if not self._source_lines:
            self._normalize_lines('source')
        return self._source_lines

    @staticmethod
    def _verify_arg(arg):
        if arg not in ('target', 'source'):
            raise ValueError('{arg} value has to be either `target` or'
                             ' `source`.'.format(arg=arg))

    def _normalize_lines(self, origin):
        self._verify_arg(origin)
        if origin == 'target':
            lines = self._hunk.target_lines()
            pre_char = '+'
            destination = self._target_lines
        elif origin == 'source':
            lines = self._hunk.source_lines()
            pre_char = '-'
            destination = self._source_lines

        for line in lines:
            single_line = str(line).rstrip()
            if single_line.startswith(pre_char):
                single_line = single_line.replace(pre_char, ' ', 1)
            destination.append(single_line)

    def as_tokens(self, origin):
        self._verify_arg(origin)
        if origin == 'target':
            lines = self.target_lines()
        elif origin == 'source':
            lines = self.source_lines()

        return LinesTokenizer(lines).tokens

    @classmethod
    def tokenize(cls, code):
        if not isinstance(code, list):
            code = [code]

        tokens = LinesTokenizer(code).tokens
        lines = []
        for line in tokens:
            lines += line

        return lines

    @classmethod
    def tokenize_el(cls, code):
        if not isinstance(code, list):
            code = [code]

        tokens = LinesTokenizer(code).elements
        lines = []
        for line in tokens:
            lines += line

        return lines

    @classmethod
    def load(cls, snippet_id, path=None):
        repo_id = cls.repo_id(snippet_id)
        pr_number = cls.pr_number(snippet_id)
        maybe_init(repo_id, pr_number=pr_number, path=path)

        snippet = DataSnippet.get_or_none(snippet_id=snippet_id)
        if snippet:
            return pickle.loads(snippet.hunk)

    def _serialize(self):
        return pickle.dumps(self, pickle.HIGHEST_PROTOCOL)

    def save(self):
        repo_id = self.repo_id(self.snippet_id)
        pr_number = self.pr_number(self.snippet_id)
        maybe_init(repo_id, pr_number=pr_number)

        snippet = DataSnippet.get_or_none(snippet_id=self.snippet_id)
        if snippet:
            (DataSnippet
             .update(snippet_id=self.snippet_id,
                     start=self.start,
                     length=self.length,
                     source=self.source_file,
                     target=self.target_file,
                     hunk=self._serialize())
             .where(DataSnippet.snippet_id == self.snippet_id)
             .execute())
        else:
            (DataSnippet
             .create(snippet_id=self.snippet_id,
                     start=self.start,
                     length=self.length,
                     source=self.source_file,
                     target=self.target_file,
                     hunk=self._serialize()))
