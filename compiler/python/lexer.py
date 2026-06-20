# Copyright 2026 Torbjörn Nilsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass

from .errors import LexerError


@dataclass(slots=True)
class Token:
    type: str
    value: str | None
    line: int
    column: int


class Lexer:
    def __init__(self, source: str, *, emit_layout_tokens: bool = False) -> None:
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1
        self.emit_layout_tokens = emit_layout_tokens
        self.indent_stack: list[int] = [0]
        self.paren_depth = 0
        self.bracket_depth = 0
        self.brace_depth = 0
        self.at_line_start = True
        self.saw_line_break = False
        self.emitted_token = False

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        while not self._is_at_end():
            if self.emit_layout_tokens and self.at_line_start and self._layout_is_active():
                self._consume_layout(tokens)
                if self._is_at_end():
                    break

            current = self._peek()

            if current in " \t\r":
                self._advance()
                continue

            if current == "\n":
                self._advance()
                if self.emit_layout_tokens and self._layout_is_active():
                    self.at_line_start = True
                    self.saw_line_break = True
                continue

            if current == "#":
                self._skip_comment()
                continue

            if current == "/" and self._peek_next() == "*":
                self._skip_block_comment()
                continue

            if current.isalpha() or current == "_":
                tokens.append(self._read_identifier())
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "(":
                tokens.append(self._simple_token("LPAREN", "("))
                self.paren_depth += 1
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == ")":
                tokens.append(self._simple_token("RPAREN", ")"))
                self.paren_depth -= 1
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "{":
                tokens.append(self._simple_token("LBRACE", "{"))
                self.brace_depth += 1
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "}":
                tokens.append(self._simple_token("RBRACE", "}"))
                self.brace_depth -= 1
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "[":
                tokens.append(self._simple_token("LBRACKET", "["))
                self.bracket_depth += 1
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "]":
                tokens.append(self._simple_token("RBRACKET", "]"))
                self.bracket_depth -= 1
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == ",":
                tokens.append(self._simple_token("COMMA", ","))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == ".":
                tokens.append(self._simple_token("DOT", "."))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == ":":
                tokens.append(self._simple_token("COLON", ":"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "?":
                tokens.append(self._simple_token("QUESTION", "?"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "+":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("PLUS_ASSIGN", "+="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "+":
                    tokens.append(self._compound_token("PLUS_PLUS", "++"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("PLUS", "+"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "-":
                if self._peek_next() == ">":
                    tokens.append(self._compound_token("ARROW", "->"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("MINUS_ASSIGN", "-="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "-":
                    tokens.append(self._compound_token("MINUS_MINUS", "--"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("MINUS", "-"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "*":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("STAR_ASSIGN", "*="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("STAR", "*"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "/":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("SLASH_ASSIGN", "/="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("SLASH", "/"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "%":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("PERCENT_ASSIGN", "%="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("PERCENT", "%"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "&":
                if self._peek_next() == "&":
                    tokens.append(self._compound_token("AND", "&&"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("BIT_AND_ASSIGN", "&="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("BIT_AND", "&"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "|":
                if self._peek_next() == "|":
                    tokens.append(self._compound_token("OR", "||"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("BIT_OR_ASSIGN", "|="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("BIT_OR", "|"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "^":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("BIT_XOR_ASSIGN", "^="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("BIT_XOR", "^"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "=":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("EQ", "=="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("ASSIGN", "="))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "!":
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("NEQ", "!="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("NOT", "!"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "<":
                if self._peek_next() == "<" and self._peek_after_next() == "=":
                    tokens.append(self._triple_token("SHIFT_LEFT_ASSIGN", "<<="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "<":
                    tokens.append(self._compound_token("SHIFT_LEFT", "<<"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("LTE", "<="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("LT", "<"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == ">":
                if self._peek_next() == ">" and self._peek_after_next() == "=":
                    tokens.append(self._triple_token("SHIFT_RIGHT_ASSIGN", ">>="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == ">":
                    tokens.append(self._compound_token("SHIFT_RIGHT", ">>"))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                if self._peek_next() == "=":
                    tokens.append(self._compound_token("GTE", ">="))
                    self.at_line_start = False
                    self.emitted_token = True
                    continue
                tokens.append(self._simple_token("GT", ">"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == ";":
                tokens.append(self._simple_token("SEMICOLON", ";"))
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current.isdigit():
                tokens.append(self._read_integer())
                self.at_line_start = False
                self.emitted_token = True
                continue

            if current == "'":
                tokens.append(self._read_string())
                self.at_line_start = False
                self.emitted_token = True
                continue

            raise LexerError(f"Unexpected character {current!r}", self.line, self.column)

        if self.emit_layout_tokens:
            while len(self.indent_stack) > 1:
                tokens.append(Token("DEDENT", None, self.line, self.column))
                self.indent_stack.pop()

        tokens.append(Token("EOF", None, self.line, self.column))
        return tokens

    def _read_identifier(self) -> Token:
        line = self.line
        column = self.column
        start = self.index

        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()

        value = self.source[start:self.index]
        if value == "int":
            return Token("INT", value, line, column)
        if value == "for":
            return Token("FOR", value, line, column)
        if value == "if":
            return Token("IF", value, line, column)
        if value == "switch":
            return Token("SWITCH", value, line, column)
        if value == "case":
            return Token("CASE", value, line, column)
        if value == "default":
            return Token("DEFAULT", value, line, column)
        if value == "while":
            return Token("WHILE", value, line, column)
        if value == "else":
            return Token("ELSE", value, line, column)
        if value == "in":
            return Token("IN", value, line, column)
        if value == "continue":
            return Token("CONTINUE", value, line, column)
        if value == "break":
            return Token("BREAK", value, line, column)
        if value == "and":
            return Token("AND", value, line, column)
        if value == "or":
            return Token("OR", value, line, column)
        if value == "not":
            return Token("NOT", value, line, column)
        if value == "record":
            return Token("RECORD", value, line, column)
        if value == "enum":
            return Token("ENUM", value, line, column)
        if value == "return":
            return Token("RETURN", value, line, column)
        if value == "throw":
            return Token("THROW", value, line, column)
        if value == "try":
            return Token("TRY", value, line, column)
        if value == "catch":
            return Token("CATCH", value, line, column)
        if value == "cached":
            return Token("CACHED", value, line, column)
        if value == "const":
            return Token("CONST", value, line, column)
        if value == "num":
            return Token("NUMBER_TYPE", "num", line, column)
        if value == "string":
            return Token("STRING_TYPE", value, line, column)
        if value == "void":
            return Token("VOID", value, line, column)
        return Token("IDENTIFIER", value, line, column)

    def _read_integer(self) -> Token:
        line = self.line
        column = self.column
        start = self.index

        while not self._is_at_end() and self._peek().isdigit():
            self._advance()

        if not self._is_at_end() and self._peek() == "." and (self._peek_next() or "").isdigit():
            self._advance()
            while not self._is_at_end() and self._peek().isdigit():
                self._advance()
            return Token("NUMBER", self.source[start:self.index], line, column)

        return Token("INTEGER", self.source[start:self.index], line, column)

    def _read_string(self) -> Token:
        line = self.line
        column = self.column
        self._advance()
        characters: list[str] = []

        while not self._is_at_end():
            current = self._peek()
            if current == "'":
                self._advance()
                return Token("STRING", "".join(characters), line, column)
            if current == "\\":
                escape_line = self.line
                escape_column = self.column
                self._advance()
                if self._is_at_end():
                    raise LexerError("Unterminated string escape", escape_line, escape_column)
                escaped = self._advance()
                if escaped == "\\":
                    characters.append("\\")
                    continue
                if escaped == "'":
                    characters.append("'")
                    continue
                if escaped == "n":
                    characters.append("\n")
                    continue
                if escaped == "r":
                    characters.append("\r")
                    continue
                if escaped == "t":
                    characters.append("\t")
                    continue
                raise LexerError(f"Unsupported string escape \\{escaped}", escape_line, escape_column)
            characters.append(self._advance())

        raise LexerError("Unterminated string literal", line, column)

    def _simple_token(self, token_type: str, value: str) -> Token:
        line = self.line
        column = self.column
        self._advance()
        return Token(token_type, value, line, column)

    def _compound_token(self, token_type: str, value: str) -> Token:
        line = self.line
        column = self.column
        self._advance()
        self._advance()
        return Token(token_type, value, line, column)

    def _triple_token(self, token_type: str, value: str) -> Token:
        line = self.line
        column = self.column
        self._advance()
        self._advance()
        self._advance()
        return Token(token_type, value, line, column)

    def _peek(self) -> str:
        return self.source[self.index]

    def _peek_next(self) -> str | None:
        next_index = self.index + 1
        if next_index >= len(self.source):
            return None
        return self.source[next_index]

    def _peek_after_next(self) -> str | None:
        next_index = self.index + 2
        if next_index >= len(self.source):
            return None
        return self.source[next_index]

    def _advance(self) -> str:
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _skip_comment(self) -> None:
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self) -> None:
        line = self.line
        column = self.column
        self._advance()
        self._advance()
        while not self._is_at_end():
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        raise LexerError("Unterminated block comment", line, column)

    def _is_at_end(self) -> bool:
        return self.index >= len(self.source)

    def _layout_is_active(self) -> bool:
        return self.paren_depth == 0 and self.bracket_depth == 0 and self.brace_depth == 0

    def _consume_layout(self, tokens: list[Token]) -> None:
        while not self._is_at_end():
            indent = 0
            line = self.line
            column = self.column

            while not self._is_at_end():
                current = self._peek()
                if current == " ":
                    indent += 1
                    self._advance()
                    continue
                if current == "\t":
                    raise LexerError("Tabs are not allowed in indentation", self.line, self.column)
                if current == "\r":
                    self._advance()
                    continue
                break

            if self._is_at_end():
                return

            current = self._peek()
            if current == "\n":
                self._advance()
                self.saw_line_break = self.saw_line_break or self.emitted_token
                continue

            if current == "#":
                self._skip_comment()
                continue

            if current == "/" and self._peek_next() == "*":
                self._skip_block_comment()
                continue

            if self.saw_line_break and self.emitted_token:
                tokens.append(Token("NEWLINE", None, line, column))
            self.saw_line_break = False

            current_indent = self.indent_stack[-1]
            if indent > current_indent:
                self.indent_stack.append(indent)
                tokens.append(Token("INDENT", None, line, column))
            else:
                while indent < self.indent_stack[-1]:
                    self.indent_stack.pop()
                    tokens.append(Token("DEDENT", None, line, column))
                if indent != self.indent_stack[-1]:
                    raise LexerError("Indentation does not match any outer block", line, column)

            self.at_line_start = False
            return


def tokenize(source: str, *, emit_layout_tokens: bool = False) -> list[Token]:
    return Lexer(source, emit_layout_tokens=emit_layout_tokens).tokenize()
