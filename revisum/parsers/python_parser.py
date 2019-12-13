import io

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token

from ..utils import reverse_enum


class PythonFileParser(object):

    def __init__(self, raw_file):
        self._raw_file = raw_file
        self.snippets = []
        self._reset()

    @property
    def title(self):
        second_token = self._snippet_body[0][0][1]
        if second_token.strip() == '':
            title = self._snippet_body[0][3][1]
        else:
            title = self._snippet_body[0][2][1]

        return title

    @property
    def f(self):
        # f = open(self.file_path, encoding='utf-8')
        f = self._raw_file.iter_lines(decode_unicode=True)
        return f

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

    def _reset(self):
        self._snippet_body = []
        self._snippet_start = None
        self._snippet_end = None

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

    def parse(self, start=None, stop=None):
        for i, line in self._read(start=start):
            line_tokens = list(lex(line, PythonLexer()))

            if self.is_func_or_class(line_tokens):
                if self._is_complete():
                    self._make_snippet()
                if stop is not None and i > stop:
                    break

                self._snippet_body.append(line_tokens)
                self._snippet_start = i
            elif self._snippet_body:
                self._snippet_body.append(line_tokens)
                self._snippet_end = i

        if self._snippet_body:
            self._make_snippet()

    def parse_single(self, start, stop):
        self._snippet_start = start
        self._snippet_end = stop

        for i, line in self._read_reverse(start=start):
            line_tokens = list(lex(line, PythonLexer()))

            if self.is_func_or_class(line_tokens):
                self._snippet_body.append(line_tokens)
                self._snippet_start = i

                if self._is_complete():
                    self._reset()
                    return self.parse(start=i, stop=stop)
            else:
                self._snippet_body.append(line_tokens)
                self._snippet_end = i

    def _make_snippet(self):

        self._rm_last_line()

        print('----------------')
        print(self.title)
        print(self._snippet_start)
        print(self._snippet_end)
        print('----------------')

        snippet = []
        for line_tokens in self._snippet_body:
            line = ''.join(line[1] for line in line_tokens)
            snippet.append(line)

        self.snippets.append(snippet)
        self._reset()

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
