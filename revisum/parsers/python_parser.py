from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token

from ..chunk import Chunk, ChunkException
from ..snippet import Snippet
from ..utils import reverse_enum, norm_path


class PythonFileParser(object):

    def __init__(self, pr_number, repo_id, file_path, raw_file=None):
        self.pr_number = pr_number
        self.repo_id = repo_id
        self._raw_file = raw_file
        self._file_path = str(file_path)
        self._file_len = None
        self._chunks = []
        self._chunks_count = 1

        self._reset()

    @property
    def f(self):
        if self._raw_file:
            f = self._raw_file.iter_lines(decode_unicode=True)
        else:
            f = open(self._file_path, encoding='utf-8')

        return f

    @property
    def file_len(self):
        if self._file_len is None:
            self._file_len = len(list(self.f))

        return self._file_len

    @property
    def file_path(self):
        return norm_path(self._file_path)

    @property
    def chunk_name(self):
        if not self._chunk_name:
            second_token = self._snippet_body[0][0][1]
            if second_token.strip() == '':
                self._chunk_name = self._snippet_body[0][3][1]
            else:
                self._chunk_name = self._snippet_body[0][2][1]

        return self._chunk_name

    @property
    def snippet_id(self):
        return Snippet.make_id(self._hunk_no, self._file_no,
                               self.pr_number, self.repo_id)

    def chunk_start(self, start):
        if start > 1:
            return start + 3

        return start

    def chunk_end(self, end):
        if end < self.file_len:
            return end - 3

        return end

    def _reset(self, soft=False):
        self._chunk_name = ''
        self._snippet_body = []
        self._snippet_start = None
        self._snippet_end = None
        if not soft:
            self._hunk_no = 0
            self._file_no = 0

    def _read(self, start=None):
        for i, line in enumerate(self.f, 1):
            if start is not None and i < start:
                continue
            yield i, line.rstrip('\n')

    def _read_reverse(self, start=None):
        for i, line in reverse_enum(self.f, 1):
            if start is not None and i > start:
                continue
            yield i, line.rstrip('\n')

    def _is_complete(self):
        if all([self._snippet_body, self._snippet_start, self._snippet_end]):
            return True
        return False

    def is_func_or_class(self, line_tokens):
        for i, token in enumerate(line_tokens):
            # Remember the first token
            if i == 0:
                first_token = token

            if token[1] == '__init__':
                continue

            if token[0] in (Token.Name.Class, Token.Name.Function, Token.Name.Function.Magic):
                if self._snippet_body:
                    # Detect inner functions based on indentations
                    if first_token[0] == Token.Text and first_token[1].strip() == '':
                        first_body_token = self._snippet_body[0][0]

                        # Current snippet also starts with an indent
                        if first_body_token[0] == Token.Text:
                            if len(first_body_token[1]) < len(first_token[1]):
                                return False

                        # Current snippet starts with a keyword
                        elif first_body_token[0] == Token.Keyword:
                            body_token_type = self._snippet_body[0][2][0]
                            if body_token_type != Token.Name.Class:
                                return False

                return True

    def parse(self, file_no=None, start=None, stop=None):
        if file_no:
            self._file_no = file_no

        for i, line in self._read(start=start):
            line_tokens = list(lex(line, PythonLexer()))

            if self.is_func_or_class(line_tokens):
                if self._is_complete():
                    self._make_chunk()
                if stop is not None and i > stop:
                    break

                self._snippet_body.append(line_tokens)
                self._snippet_start = i
            elif self._snippet_body:
                self._snippet_body.append(line_tokens)
                self._snippet_end = i

        if self._snippet_body:
            self._make_chunk()

        chunks = self._chunks
        self._chunks = []

        return chunks

    def parse_single(self, hunk_no, file_no, start, stop):
        start = self.chunk_start(start)
        stop = self.chunk_end(stop)

        self._hunk_no = hunk_no
        self._file_no = file_no
        self._snippet_start = start
        self._snippet_end = stop

        for i, line in self._read_reverse(start=start):
            line_tokens = list(lex(line, PythonLexer()))

            if self.is_func_or_class(line_tokens):
                self._snippet_body.append(line_tokens)
                self._snippet_start = i

                if self._is_complete():
                    self._reset(soft=True)
                    return self.parse(start=i, stop=stop)
            else:
                self._snippet_body.append(line_tokens)
                self._snippet_end = i

    def _rm_last_line(self):
        should_rm = False

        tokens_text = [token[1] for token in self._snippet_body[-1][0:2]]
        # Remove empty lines
        if tokens_text[0] == '\n':
            should_rm = True

        # Remove comments
        if any(token.startswith('#') for token in tokens_text):
            should_rm = True

        tokens_type = [token[0] for token in self._snippet_body[-1][0:2]]
        # Remove decorators
        if Token.Name.Decorator in tokens_type:
            should_rm = True

        if should_rm:
            del self._snippet_body[-1]
            self._snippet_end -= 1
            return self._rm_last_line()

    def _make_chunk(self):
        self._rm_last_line()

        print('----------------')
        print(self.chunk_name)
        print(self._snippet_start)
        print(self._snippet_end)
        print('----------------')

        try:
            chunk = Chunk(
                self.snippet_id, self.chunk_name, self._chunks_count, self.file_path,
                self._snippet_body, self._snippet_start, self._snippet_end
            )

            self._chunks.append(chunk)
            self._chunks_count += 1
        except ChunkException as e:
            print('Skipping invalid chunk: {0}, {1}\n{2}'.format(self.snippet_id, self.chunk_name, e))

        self._reset(soft=True)
