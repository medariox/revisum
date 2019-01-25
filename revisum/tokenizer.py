from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


class LinesTokenizer(object):

    def __init__(self, lines):
        self._lines = lines
        self.exclusions = [
            Token.Text,
            Token.Punctuation,
            Token.Comment,
        ]

    @property
    def tokens(self):
        lexed_lines = []

        for line in self._lines:
            tokens = lex(line, PythonLexer())
            tokens_list = []

            for token in tokens:
                if token[0] in self.exclusions:
                    continue
                tokens_list.append(token[1])

            if tokens_list:
                lexed_lines.append(tokens_list)

        return lexed_lines
