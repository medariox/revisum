from pygments.token import Token

from .parser import FileParser


class PythonFileParser(FileParser):

    def is_func_or_class(self, line_tokens):
        if len(line_tokens) > 2 and line_tokens[0][0] == Token.Keyword:
            name_token = line_tokens[2]
        elif len(line_tokens) > 3 and line_tokens[1][0] == Token.Keyword:
            name_token = line_tokens[3]
        else:
            return False

        if name_token[1] == '__init__' or name_token[0] == Token.Name.Function.Magic:
            return False

        if name_token[0] not in (Token.Name.Class, Token.Name.Function):
            return False

        return True

    def _is_next_chunk(self, first_line_tokens):
        if not self._snippet_body:
            return True

        if first_line_tokens[0][1] == '\n':
            return False

        first_body_type = self._snippet_body[0][2]
        if first_body_type[0] == Token.Name.Class:
            func_in_class = (x[0] for b in self._snippet_body for x in b)
            count = 0
            for func in func_in_class:
                if func == Token.Name.Function:
                    count += 1
            if count < 1:
                return False

        first_token_type = [token[0] for token in first_line_tokens[0:4]]
        if Token.Name.Decorator in first_token_type:
            return True

        if Token.Name.Function in first_token_type or Token.Name.Class in first_token_type:

            first_token = self._snippet_body[0][0]
            # Detect indentation level of current chunk
            if first_token[0] == Token.Text and first_token[1].strip() == '':
                first_token_len = len(first_token[1])
            else:
                first_token_len = 0

            if first_line_tokens[0][0] == Token.Keyword:
                return True
            elif first_line_tokens[1][0] == Token.Keyword:
                if first_body_type[0] == Token.Name.Class:
                    # First inner function
                    if first_token_len + 4 == len(first_line_tokens[0][1]):
                        return True
                if len(first_line_tokens[0][1]) <= first_token_len:
                    return True

        if first_line_tokens[0][0] == Token.Comment.Single:
            return True

        if first_line_tokens[0][0] == Token.Name:
            return True

        return False

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
