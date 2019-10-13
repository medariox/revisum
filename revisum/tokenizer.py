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
            Token.Comment.Single,
        ]
        self.char_exclusions = [
            '.', '=', '"', "'",
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
                if token[1] in self.char_exclusions:
                    continue

                tokens_list.append(token[1])

            if tokens_list:
                lexed_lines.append(tokens_list)

        return lexed_lines

    @property
    def elements(self):
        lexed_elements = []

        for line in self._lines:
            tokens = lex(line, PythonLexer())
            tokens_list = []

            for token in tokens:
                if token[0] in self.exclusions:
                    continue
                if token[1] in self.char_exclusions:
                    continue

                tokens_list.append(token[0])

            if tokens_list:
                lexed_elements.append(tokens_list)

        return lexed_elements
