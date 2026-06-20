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

from .ast import (
    Assignment,
    ArrayAccess,
    ArrayAssignment,
    ArrayLiteral,
    BinaryExpression,
    BooleanLiteral,
    BreakStatement,
    BuiltinCallExpression,
    BuiltinCallStatement,
    ConstructorCall,
    ContinueStatement,
    EnumDeclaration,
    FieldAssignment,
    FieldAccess,
    ForEachStatement,
    ForStatement,
    FunctionCallExpression,
    FunctionCallStatement,
    FunctionDeclaration,
    FunctionParameter,
    Identifier,
    IfStatement,
    IntegerLiteral,
    LambdaExpression,
    MultiLambdaExpression,
    MapLiteral,
    NumberLiteral,
    Program,
    RecordDeclaration,
    RecordField,
    ReturnStatement,
    SetLiteral,
    StringLiteral,
    SwitchCase,
    SwitchStatement,
    ThrowStatement,
    TernaryExpression,
    TryCatchStatement,
    UnaryExpression,
    VariableDeclaration,
    WhileStatement,
)
from .errors import ParserError
from .lexer import Token
from .stdlib import is_builtin_function


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse_program(self) -> Program:
        statements = []
        self._skip_newlines()
        while self._current().type != "EOF":
            statements.append(self._parse_statement())
            self._skip_newlines()
        self._expect("EOF", "Expected end of file")
        return Program(statements)

    def _parse_statement(self) -> BuiltinCallStatement | FunctionCallStatement | VariableDeclaration | Assignment | ArrayAssignment | FieldAssignment | ForStatement | ForEachStatement | WhileStatement | IfStatement | SwitchStatement | RecordDeclaration | EnumDeclaration | FunctionDeclaration | ReturnStatement | ThrowStatement | ContinueStatement | BreakStatement | TryCatchStatement:
        if self._looks_like_typed_function_declaration():
            return self._parse_function_declaration()
        if self._looks_like_variable_declaration():
            return self._parse_variable_declaration()
        if self._current().type == "RECORD":
            return self._parse_record_declaration()
        if self._current().type == "ENUM":
            return self._parse_enum_declaration()
        if self._current().type == "RETURN":
            return self._parse_return_statement()
        if self._current().type == "THROW":
            return self._parse_throw_statement()
        if self._current().type == "CONTINUE":
            return self._parse_continue_statement()
        if self._current().type == "BREAK":
            return self._parse_break_statement()
        if self._current().type == "FOR":
            return self._parse_for_statement()
        if self._current().type == "WHILE":
            return self._parse_while_statement()
        if self._current().type == "IF":
            return self._parse_if_statement()
        if self._current().type == "SWITCH":
            return self._parse_switch_statement()
        if self._current().type == "TRY":
            return self._parse_try_catch_statement()
        if self._current().type == "IDENTIFIER":
            if self._looks_like_ufcs_call_statement():
                return self._parse_ufcs_call_statement()
            if self._peek().type == "LPAREN" and is_builtin_function(self._current().value or ""):
                return self._parse_builtin_call_statement()
            if self._peek().type == "LPAREN":
                return self._parse_function_call_statement()
            if self._peek().type == "IDENTIFIER":
                return self._parse_variable_declaration()
            return self._parse_assignment_statement()
        current = self._current()
        raise ParserError("Expected statement", current.line, current.column)

    def _parse_variable_declaration(self) -> VariableDeclaration:
        is_const = False
        if self._current().type == "CONST":
            self._advance()
            is_const = True
        type_name = self._parse_type_name()
        name_token = self._expect("IDENTIFIER", "Expected identifier")
        if self._current().type == "LBRACKET":
            self._advance()
            self._expect("RBRACKET", "Expected ']'")
            type_name = f"{type_name}[]"
        self._expect("ASSIGN", "Expected '='")
        value = self._parse_expression()
        self._expect_statement_terminator()
        return VariableDeclaration(type_name, name_token.value or "", value, is_const)

    def _parse_record_declaration(self) -> RecordDeclaration:
        self._expect("RECORD", "Expected 'record'")
        name_token = self._expect("IDENTIFIER", "Expected record name")
        self._expect("LPAREN", "Expected '('")
        fields: list[RecordField] = []
        if self._current().type != "RPAREN":
            while True:
                field_type = self._parse_type_name()
                field_name = self._expect("IDENTIFIER", "Expected field name")
                fields.append(RecordField(field_type, field_name.value or ""))
                if self._current().type != "COMMA":
                    break
                self._advance()
        self._expect("RPAREN", "Expected ')'")
        self._expect("SEMICOLON", "Expected ';'")
        return RecordDeclaration(name_token.value or "", fields)

    def _parse_enum_declaration(self) -> EnumDeclaration:
        self._expect("ENUM", "Expected 'enum'")
        name_token = self._expect("IDENTIFIER", "Expected enum name")
        self._expect("LBRACE", "Expected '{'")
        members: list[str] = []
        while self._current().type != "RBRACE":
            member_name = self._expect("IDENTIFIER", "Expected enum member")
            members.append(member_name.value or "")
            if self._current().type == "COMMA":
                self._advance()
            elif self._current().type != "RBRACE":
                token = self._current()
                raise ParserError("Expected ',' or '}'", token.line, token.column)
        self._expect("RBRACE", "Expected '}'")
        return EnumDeclaration(name_token.value or "", members)

    def _parse_function_declaration(self) -> FunctionDeclaration:
        is_cached = False
        if self._current().type == "CACHED":
            self._advance()
            is_cached = True
        declared_return_type = self._parse_type_name()
        name_token = self._expect("IDENTIFIER", "Expected function name")
        self._expect("LPAREN", "Expected '('")
        parameters: list[FunctionParameter] = []
        if self._current().type != "RPAREN":
            while True:
                parameter_type = self._current()
                if parameter_type.type not in {"INT", "STRING_TYPE", "NUMBER_TYPE", "IDENTIFIER"}:
                    raise ParserError("Expected parameter type", parameter_type.line, parameter_type.column)
                type_name = self._parse_type_name()
                parameter_name = self._expect("IDENTIFIER", "Expected parameter name")
                parameters.append(FunctionParameter(type_name, parameter_name.value or ""))
                if self._current().type != "COMMA":
                    break
                self._advance()
        self._expect("RPAREN", "Expected ')'")
        body = self._parse_block_suite()
        return FunctionDeclaration(name_token.value or "", parameters, body, declared_return_type, is_cached)

    def _parse_builtin_call_statement(self) -> BuiltinCallStatement:
        name_token = self._expect("IDENTIFIER", "Expected builtin function name")
        arguments = self._parse_call_arguments()
        self._expect_statement_terminator()
        return BuiltinCallStatement(name_token.value or "", arguments)

    def _parse_function_call_statement(self) -> FunctionCallStatement:
        name_token = self._expect("IDENTIFIER", "Expected function name")
        arguments = self._parse_call_arguments()
        self._expect_statement_terminator()
        return FunctionCallStatement(name_token.value or "", arguments)

    def _parse_ufcs_call_statement(self) -> BuiltinCallStatement | FunctionCallStatement:
        receiver_name = self._expect("IDENTIFIER", "Expected receiver variable")
        self._expect("DOT", "Expected '.'")
        function_name = self._expect("IDENTIFIER", "Expected function name")
        arguments = [Identifier(receiver_name.value or ""), *self._parse_call_arguments()]
        self._expect_statement_terminator()
        if is_builtin_function(function_name.value or ""):
            return BuiltinCallStatement(function_name.value or "", arguments)
        return FunctionCallStatement(function_name.value or "", arguments)

    def _parse_return_statement(self) -> ReturnStatement:
        self._expect("RETURN", "Expected 'return'")
        value = None
        if self._current().type not in {"SEMICOLON", "NEWLINE", "DEDENT", "EOF"}:
            value = self._parse_expression()
        self._expect_statement_terminator()
        return ReturnStatement(value)

    def _parse_throw_statement(self) -> ThrowStatement:
        self._expect("THROW", "Expected 'throw'")
        value = self._parse_expression()
        self._expect_statement_terminator()
        return ThrowStatement(value)

    def _parse_continue_statement(self) -> ContinueStatement:
        self._expect("CONTINUE", "Expected 'continue'")
        self._expect_statement_terminator()
        return ContinueStatement()

    def _parse_break_statement(self) -> BreakStatement:
        self._expect("BREAK", "Expected 'break'")
        self._expect_statement_terminator()
        return BreakStatement()

    def _parse_expression(self):
        if self._looks_like_multi_lambda_expression():
            parameters = self._parse_lambda_parameters()
            self._expect("ARROW", "Expected '->'")
            if self._current().type == "LBRACE":
                self._advance()
                body = []
                while self._current().type != "RBRACE":
                    body.append(self._parse_statement())
                self._expect("RBRACE", "Expected '}'")
                return MultiLambdaExpression(parameters, body)
            return MultiLambdaExpression(parameters, self._parse_expression())
        if self._looks_like_lambda_expression():
            parameter_type = self._parse_type_name()
            parameter_name = self._expect("IDENTIFIER", "Expected lambda parameter name")
            self._expect("ARROW", "Expected '->'")
            if self._current().type == "LBRACE":
                self._advance()
                body = []
                while self._current().type != "RBRACE":
                    body.append(self._parse_statement())
                self._expect("RBRACE", "Expected '}'")
                return LambdaExpression(parameter_type, parameter_name.value or "", body)
            return LambdaExpression(parameter_type, parameter_name.value or "", self._parse_expression())
        expression = self._parse_or_expression()
        if self._current().type == "QUESTION":
            self._advance()
            when_true = self._parse_expression()
            self._expect("COLON", "Expected ':'")
            when_false = self._parse_expression()
            return TernaryExpression(expression, when_true, when_false)
        return expression

    def _parse_or_expression(self):
        expression = self._parse_and_expression()
        while self._current().type == "OR":
            self._advance()
            right = self._parse_and_expression()
            expression = BinaryExpression(expression, "||", right)
        return expression

    def _parse_and_expression(self):
        expression = self._parse_bitwise_or_expression()
        while self._current().type == "AND":
            self._advance()
            right = self._parse_bitwise_or_expression()
            expression = BinaryExpression(expression, "&&", right)
        return expression

    def _parse_bitwise_or_expression(self):
        expression = self._parse_bitwise_xor_expression()
        while self._current().type == "BIT_OR":
            self._advance()
            right = self._parse_bitwise_xor_expression()
            expression = BinaryExpression(expression, "|", right)
        return expression

    def _parse_bitwise_xor_expression(self):
        expression = self._parse_bitwise_and_expression()
        while self._current().type == "BIT_XOR":
            self._advance()
            right = self._parse_bitwise_and_expression()
            expression = BinaryExpression(expression, "^", right)
        return expression

    def _parse_bitwise_and_expression(self):
        expression = self._parse_comparison_expression()
        while self._current().type == "BIT_AND":
            self._advance()
            right = self._parse_comparison_expression()
            expression = BinaryExpression(expression, "&", right)
        return expression

    def _parse_comparison_expression(self):
        expression = self._parse_shift_expression()
        while self._current().type in {"EQ", "NEQ", "LT", "LTE", "GT", "GTE", "IN"} or (
            self._current().type == "NOT" and self._peek().type == "IN"
        ):
            if self._current().type == "NOT":
                self._advance()
                self._expect("IN", "Expected 'in' after 'not'")
                operator = "not in"
            else:
                operator = self._advance().value or ""
            right = self._parse_shift_expression()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_shift_expression(self):
        expression = self._parse_additive_expression()
        while self._current().type in {"SHIFT_LEFT", "SHIFT_RIGHT"}:
            operator = self._advance().value or ""
            right = self._parse_additive_expression()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_additive_expression(self):
        expression = self._parse_term()
        while self._current().type in {"PLUS", "MINUS"}:
            operator = self._advance().value or ""
            right = self._parse_term()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_term(self):
        expression = self._parse_factor()
        while self._current().type in {"STAR", "SLASH", "PERCENT"}:
            operator = self._advance().value or ""
            right = self._parse_factor()
            expression = BinaryExpression(expression, operator, right)
        return expression

    def _parse_factor(self):
        current = self._current()
        if current.type == "NOT":
            self._advance()
            return UnaryExpression("!", self._parse_factor())
        if current.type == "MINUS":
            self._advance()
            operand = self._parse_factor()
            if isinstance(operand, IntegerLiteral):
                return IntegerLiteral(-operand.value)
            if isinstance(operand, NumberLiteral):
                return NumberLiteral(-operand.value, operand.scale)
            return BinaryExpression(IntegerLiteral(0), "-", operand)
        if current.type == "INTEGER":
            token = self._advance()
            expression = IntegerLiteral(int(token.value or "0"))
            return self._parse_postfix_expression(expression)
        if current.type == "NUMBER":
            token = self._advance()
            raw_value = token.value or "0"
            whole_part, fractional_part = raw_value.split(".", maxsplit=1)
            expression = NumberLiteral(int(whole_part + fractional_part), len(fractional_part))
            return self._parse_postfix_expression(expression)
        if current.type == "STRING":
            token = self._advance()
            expression = StringLiteral(token.value or "")
            return self._parse_postfix_expression(expression)
        if current.type == "LBRACKET":
            self._advance()
            items = []
            if self._current().type != "RBRACKET":
                while True:
                    items.append(self._parse_expression())
                    if self._current().type != "COMMA":
                        break
                    self._advance()
            self._expect("RBRACKET", "Expected ']'")
            expression = ArrayLiteral(items)
            return self._parse_postfix_expression(expression)
        if current.type == "LBRACE":
            self._advance()
            if self._current().type == "RBRACE":
                expression = MapLiteral([])
                self._expect("RBRACE", "Expected '}'")
                return self._parse_postfix_expression(expression)
            first = self._parse_expression()
            if self._current().type == "COLON":
                self._advance()
                value = self._parse_expression()
                items = [(first, value)]
                while self._current().type == "COMMA":
                    self._advance()
                    key = self._parse_expression()
                    self._expect("COLON", "Expected ':'")
                    value = self._parse_expression()
                    items.append((key, value))
                expression = MapLiteral(items)
            else:
                items = [first]
                while self._current().type == "COMMA":
                    self._advance()
                    items.append(self._parse_expression())
                expression = SetLiteral(items)
            self._expect("RBRACE", "Expected '}'")
            return self._parse_postfix_expression(expression)
        if current.type == "IDENTIFIER":
            token = self._advance()
            if token.value in {"true", "false"} and self._current().type != "LPAREN":
                return BooleanLiteral(token.value == "true")
            if self._current().type == "LPAREN":
                arguments = self._parse_call_arguments()
                if is_builtin_function(token.value or ""):
                    expression = BuiltinCallExpression(token.value or "", arguments)
                    return self._parse_postfix_expression(expression)
                if (token.value or "")[:1].isupper():
                    expression = ConstructorCall(token.value or "", arguments)
                    return self._parse_postfix_expression(expression)
                expression = FunctionCallExpression(token.value or "", arguments)
                return self._parse_postfix_expression(expression)
            expression = Identifier(token.value or "")
            return self._parse_postfix_expression(expression)
        if current.type == "LPAREN":
            self._advance()
            expression = self._parse_expression()
            self._expect("RPAREN", "Expected ')'")
            return self._parse_postfix_expression(expression)
        raise ParserError("Expected expression", current.line, current.column)

    def _parse_postfix_expression(self, expression):
        while self._current().type in {"DOT", "LBRACKET"}:
            if self._current().type == "DOT":
                self._advance()
                member_name = self._expect("IDENTIFIER", "Expected field name")
                if self._current().type == "LPAREN":
                    arguments = [expression, *self._parse_call_arguments()]
                    if is_builtin_function(member_name.value or ""):
                        expression = BuiltinCallExpression(member_name.value or "", arguments)
                    else:
                        expression = FunctionCallExpression(member_name.value or "", arguments)
                    continue
                expression = FieldAccess(expression, member_name.value or "")
                continue
            self._advance()
            index = IntegerLiteral(0) if self._current().type == "COLON" else self._parse_expression()
            if self._current().type == "COLON":
                self._advance()
                if self._current().type == "RBRACKET":
                    end = BuiltinCallExpression("length", [expression])
                else:
                    end = self._parse_expression()
                self._expect("RBRACKET", "Expected ']'")
                expression = BuiltinCallExpression("slice", [expression, index, end])
                continue
            self._expect("RBRACKET", "Expected ']'")
            expression = ArrayAccess(expression, index)
        return expression

    def _parse_assignment_statement(self) -> Assignment | ArrayAssignment | FieldAssignment:
        assignment = self._parse_assignment()
        self._expect_statement_terminator()
        return assignment

    def _parse_assignment(self) -> Assignment | ArrayAssignment | FieldAssignment:
        name_token = self._expect("IDENTIFIER", "Expected identifier")
        target = self._parse_postfix_expression(Identifier(name_token.value or ""))
        current = self._current()
        if current.type == "ASSIGN":
            self._advance()
            value = self._parse_expression()
            if isinstance(target, Identifier):
                return Assignment(target.name, value)
            if isinstance(target, ArrayAccess):
                return ArrayAssignment(target, value)
            if isinstance(target, FieldAccess):
                return FieldAssignment(target, value)
            raise ParserError("Invalid assignment target", current.line, current.column)
        if current.type == "PLUS_ASSIGN":
            self._advance()
            increment = self._parse_expression()
            return self._build_compound_assignment(target, "+", increment, current.line, current.column)
        if current.type == "MINUS_ASSIGN":
            self._advance()
            decrement = self._parse_expression()
            return self._build_compound_assignment(target, "-", decrement, current.line, current.column)
        if current.type == "STAR_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "*", value, current.line, current.column)
        if current.type == "SLASH_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "/", value, current.line, current.column)
        if current.type == "PERCENT_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "%", value, current.line, current.column)
        if current.type == "BIT_AND_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "&", value, current.line, current.column)
        if current.type == "BIT_OR_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "|", value, current.line, current.column)
        if current.type == "BIT_XOR_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "^", value, current.line, current.column)
        if current.type == "SHIFT_LEFT_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, "<<", value, current.line, current.column)
        if current.type == "SHIFT_RIGHT_ASSIGN":
            self._advance()
            value = self._parse_expression()
            return self._build_compound_assignment(target, ">>", value, current.line, current.column)
        if current.type == "PLUS_PLUS":
            if not isinstance(target, Identifier):
                raise ParserError("'++' requires an identifier target", current.line, current.column)
            self._advance()
            return Assignment(
                target.name,
                BinaryExpression(Identifier(target.name), "+", IntegerLiteral(1)),
            )
        if current.type == "MINUS_MINUS":
            if not isinstance(target, Identifier):
                raise ParserError("'--' requires an identifier target", current.line, current.column)
            self._advance()
            return Assignment(
                target.name,
                BinaryExpression(Identifier(target.name), "-", IntegerLiteral(1)),
            )
        raise ParserError("Expected assignment operator", current.line, current.column)

    def _build_compound_assignment(self, target, operator: str, value, line: int, column: int):
        if isinstance(target, Identifier):
            return Assignment(target.name, BinaryExpression(Identifier(target.name), operator, value))
        if isinstance(target, ArrayAccess):
            current_value = ArrayAccess(target.target, target.index)
            return ArrayAssignment(target, BinaryExpression(current_value, operator, value))
        if isinstance(target, FieldAccess):
            current_value = FieldAccess(target.target, target.field_name)
            return FieldAssignment(target, BinaryExpression(current_value, operator, value))
        symbol = {
            "+": "+=",
            "-": "-=",
            "*": "*=",
            "/": "/=",
            "%": "%=",
            "&": "&=",
            "|": "|=",
            "^": "^=",
            "<<": "<<=",
            ">>": ">>=",
        }[operator]
        raise ParserError(f"'{symbol}' requires an identifier, array access, or field access target", line, column)

    def _parse_for_statement(self) -> ForStatement | ForEachStatement:
        self._expect("FOR", "Expected 'for'")
        self._expect("LPAREN", "Expected '('")
        if self._looks_like_for_each_loop():
            item_type = self._parse_type_name()
            item_name = self._expect("IDENTIFIER", "Expected iterator name")
            if self._current().type not in {"COLON", "IN"}:
                raise ParserError("Expected ':' or 'in'", self._current().line, self._current().column)
            self._advance()
            iterable = self._parse_expression()
            self._expect("RPAREN", "Expected ')'")
            body = self._parse_block_suite()
            return ForEachStatement(item_type, item_name.value or "", iterable, body)
        if self._looks_like_variable_declaration():
            initializer = self._parse_variable_declaration()
        else:
            initializer = self._parse_assignment_statement()
        condition = self._parse_expression()
        self._expect("SEMICOLON", "Expected ';'")
        update = self._parse_assignment()
        self._expect("RPAREN", "Expected ')'")
        body = self._parse_block_suite()
        return ForStatement(initializer, condition, update, body)

    def _parse_if_statement(self) -> IfStatement:
        self._expect("IF", "Expected 'if'")
        self._expect("LPAREN", "Expected '('")
        condition = self._parse_expression()
        self._expect("RPAREN", "Expected ')'")
        then_body = self._parse_block_suite()

        else_body = []
        if self._current().type == "ELSE":
            self._advance()
            if self._current().type == "IF":
                else_body.append(self._parse_if_statement())
            else:
                else_body = self._parse_block_suite()

        return IfStatement(condition, then_body, else_body)

    def _parse_while_statement(self) -> WhileStatement:
        self._expect("WHILE", "Expected 'while'")
        self._expect("LPAREN", "Expected '('")
        condition = self._parse_expression()
        self._expect("RPAREN", "Expected ')'")
        body = self._parse_block_suite()
        return WhileStatement(condition, body)

    def _parse_switch_statement(self) -> SwitchStatement:
        self._expect("SWITCH", "Expected 'switch'")
        self._expect("LPAREN", "Expected '('")
        expression = self._parse_expression()
        self._expect("RPAREN", "Expected ')'")
        switch_uses_braces = self._current().type == "LBRACE"
        if switch_uses_braces:
            self._advance()
        else:
            self._expect("COLON", "Expected ':' or '{'")
            self._expect("NEWLINE", "Expected newline after ':'")
            self._expect("INDENT", "Expected indented switch body")
        cases: list[SwitchCase] = []
        default_body: list = []
        saw_default = False
        self._skip_newlines()
        switch_end = "RBRACE" if switch_uses_braces else "DEDENT"
        while self._current().type != switch_end:
            if self._current().type == "CASE":
                self._advance()
                value = self._parse_expression()
                body = self._parse_block_suite()
                cases.append(SwitchCase(value, body))
                self._skip_newlines()
                continue
            if self._current().type == "DEFAULT":
                if saw_default:
                    token = self._current()
                    raise ParserError("Switch can only have one default case", token.line, token.column)
                saw_default = True
                self._advance()
                default_body = self._parse_block_suite()
                self._skip_newlines()
                continue
            token = self._current()
            end_label = "}" if switch_uses_braces else "end of indented switch"
            raise ParserError(f"Expected 'case', 'default', or {end_label!r}", token.line, token.column)
        if switch_uses_braces:
            self._expect("RBRACE", "Expected '}'")
        else:
            self._expect("DEDENT", "Expected end of indented switch")
        return SwitchStatement(expression, cases, default_body)

    def _parse_try_catch_statement(self) -> TryCatchStatement:
        self._expect("TRY", "Expected 'try'")
        try_body = self._parse_block_suite()
        self._skip_newlines()
        self._expect("CATCH", "Expected 'catch'")
        self._expect("LPAREN", "Expected '('")
        catch_type = self._parse_type_name()
        if catch_type != "string":
            token = self._current()
            raise ParserError("Catch parameter type must be exception", token.line, token.column)
        catch_name = self._expect("IDENTIFIER", "Expected catch variable name")
        self._expect("RPAREN", "Expected ')'")
        catch_body = self._parse_block_suite()
        return TryCatchStatement(try_body, catch_name.value or "", catch_body)

    def _expect(self, token_type: str, message: str) -> Token:
        token = self._current()
        if token.type != token_type:
            raise ParserError(message, token.line, token.column)
        self.index += 1
        return token

    def _expect_statement_terminator(self) -> None:
        token = self._current()
        if token.type == "SEMICOLON":
            self._advance()
            self._skip_newlines()
            return
        if token.type in {"NEWLINE", "DEDENT", "EOF"}:
            self._skip_newlines()
            return
        raise ParserError("Expected statement terminator", token.line, token.column)

    def _parse_block_suite(self) -> list:
        if self._current().type == "LBRACE":
            self._advance()
            body = []
            self._skip_newlines()
            while self._current().type != "RBRACE":
                body.append(self._parse_statement())
                self._skip_newlines()
            self._expect("RBRACE", "Expected '}'")
            return body
        self._expect("COLON", "Expected ':' or '{'")
        if self._current().type == "LBRACE":
            self._advance()
            body = []
            self._skip_newlines()
            while self._current().type != "RBRACE":
                body.append(self._parse_statement())
                self._skip_newlines()
            self._expect("RBRACE", "Expected '}'")
            return body
        self._expect("NEWLINE", "Expected newline after ':'")
        self._expect("INDENT", "Expected indented block")
        body = []
        self._skip_newlines()
        while self._current().type != "DEDENT":
            body.append(self._parse_statement())
            self._skip_newlines()
        self._expect("DEDENT", "Expected end of indented block")
        return body

    def _skip_newlines(self) -> None:
        while self._current().type == "NEWLINE":
            self._advance()

    def _advance(self) -> Token:
        token = self._current()
        self.index += 1
        return token

    def _current(self) -> Token:
        return self.tokens[self.index]

    def _peek(self) -> Token:
        next_index = self.index + 1
        if next_index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[next_index]

    def _parse_constructor_call(self, type_name: str) -> ConstructorCall:
        arguments = self._parse_call_arguments()
        return ConstructorCall(type_name, arguments)

    def _parse_type_name(self) -> str:
        type_token = self._current()
        if type_token.type not in {"INT", "STRING_TYPE", "NUMBER_TYPE", "VOID", "IDENTIFIER"}:
            raise ParserError("Expected type declaration", type_token.line, type_token.column)
        self._advance()
        type_name = type_token.value or ""
        if type_name == "exception":
            type_name = "string"
        if type_name == "map":
            self._expect("LT", "Expected '<'")
            key_type = self._parse_type_name()
            self._expect("COMMA", "Expected ','")
            value_type = self._parse_type_name()
            self._expect_generic_close()
            type_name = f"map<{key_type},{value_type}>"
        elif type_name == "set":
            self._expect("LT", "Expected '<'")
            item_type = self._parse_type_name()
            self._expect_generic_close()
            type_name = f"set<{item_type}>"
        elif type_name == "prio_q":
            self._expect("LT", "Expected '<'")
            item_type = self._parse_type_name()
            self._expect_generic_close()
            type_name = f"prio_q<{item_type}>"
        while self._current().type == "LBRACKET":
            self._advance()
            self._expect("RBRACKET", "Expected ']'")
            type_name = f"{type_name}[]"
        return type_name

    def _looks_like_for_each_loop(self) -> bool:
        index = self._scan_type_end(self.index)
        if index is None:
            return False
        return self._token_at(index).type == "IDENTIFIER" and self._token_at(index + 1).type in {"COLON", "IN"}

    def _looks_like_typed_function_declaration(self) -> bool:
        index = self.index
        token = self._token_at(index)
        if token.type == "CACHED":
            index += 1
            token = self._token_at(index)
        if token.type not in {"INT", "STRING_TYPE", "NUMBER_TYPE", "VOID", "IDENTIFIER"}:
            return False
        if token.type == "IDENTIFIER" and token.value == "function":
            return False
        index = self._scan_type_end(index)
        if index is None:
            return False
        return self._token_at(index).type == "IDENTIFIER" and self._token_at(index + 1).type == "LPAREN"

    def _looks_like_variable_declaration(self) -> bool:
        index = self.index
        token = self._token_at(index)
        if token.type == "CONST":
            index += 1
            token = self._token_at(index)
        if token.type not in {"INT", "STRING_TYPE", "NUMBER_TYPE", "IDENTIFIER"}:
            return False
        index = self._scan_type_end(index)
        if index is None:
            return False
        return self._token_at(index).type == "IDENTIFIER"

    def _looks_like_lambda_expression(self) -> bool:
        index = self._scan_type_end(self.index)
        if index is None:
            return False
        return self._token_at(index).type == "IDENTIFIER" and self._token_at(index + 1).type == "ARROW"

    def _looks_like_multi_lambda_expression(self) -> bool:
        if self._current().type != "LPAREN":
            return False
        index = self.index + 1
        saw_parameter = False
        while True:
            type_end = self._scan_type_end(index)
            if type_end is None or self._token_at(type_end).type != "IDENTIFIER":
                return False
            saw_parameter = True
            index = type_end + 1
            if self._token_at(index).type == "COMMA":
                index += 1
                continue
            if self._token_at(index).type != "RPAREN":
                return False
            return saw_parameter and self._token_at(index + 1).type == "ARROW"

    def _parse_lambda_parameters(self) -> list[FunctionParameter]:
        self._expect("LPAREN", "Expected '('")
        parameters: list[FunctionParameter] = []
        while True:
            type_name = self._parse_type_name()
            parameter_name = self._expect("IDENTIFIER", "Expected lambda parameter name")
            parameters.append(FunctionParameter(type_name, parameter_name.value or ""))
            if self._current().type != "COMMA":
                break
            self._advance()
        self._expect("RPAREN", "Expected ')'")
        return parameters

    def _token_at(self, index: int) -> Token:
        if index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[index]

    def _split_shift_right_token(self, index: int) -> None:
        token = self._token_at(index)
        if token.type != "SHIFT_RIGHT":
            return
        self.tokens[index:index + 1] = [
            Token("GT", ">", token.line, token.column),
            Token("GT", ">", token.line, token.column + 1),
        ]

    def _expect_generic_close(self) -> Token:
        if self._current().type == "SHIFT_RIGHT":
            self._split_shift_right_token(self.index)
        return self._expect("GT", "Expected '>'")

    def _scan_type_end(self, index: int) -> int | None:
        token = self._token_at(index)
        if token.type not in {"INT", "STRING_TYPE", "NUMBER_TYPE", "VOID", "IDENTIFIER"}:
            return None
        if token.type == "IDENTIFIER" and token.value == "map":
            index += 1
            if self._token_at(index).type != "LT":
                return None
            index += 1
            index = self._scan_type_end(index)
            if index is None or self._token_at(index).type != "COMMA":
                return None
            index += 1
            index = self._scan_type_end(index)
            if index is not None and self._token_at(index).type == "SHIFT_RIGHT":
                self._split_shift_right_token(index)
            if index is None or self._token_at(index).type != "GT":
                return None
            index += 1
        elif token.type == "IDENTIFIER" and token.value == "set":
            index += 1
            if self._token_at(index).type != "LT":
                return None
            index += 1
            index = self._scan_type_end(index)
            if index is not None and self._token_at(index).type == "SHIFT_RIGHT":
                self._split_shift_right_token(index)
            if index is None or self._token_at(index).type != "GT":
                return None
            index += 1
        elif token.type == "IDENTIFIER" and token.value == "prio_q":
            index += 1
            if self._token_at(index).type != "LT":
                return None
            index += 1
            index = self._scan_type_end(index)
            if index is not None and self._token_at(index).type == "SHIFT_RIGHT":
                self._split_shift_right_token(index)
            if index is None or self._token_at(index).type != "GT":
                return None
            index += 1
        else:
            index += 1
        while self._token_at(index).type == "LBRACKET":
            if self._token_at(index + 1).type != "RBRACKET":
                return None
            index += 2
        return index

    def _looks_like_ufcs_call_statement(self) -> bool:
        return (
            self._current().type == "IDENTIFIER"
            and self._peek().type == "DOT"
            and self._token_at(self.index + 2).type == "IDENTIFIER"
            and self._token_at(self.index + 3).type == "LPAREN"
        )

    def _parse_call_arguments(self) -> list:
        self._expect("LPAREN", "Expected '('")
        arguments: list = []
        if self._current().type != "RPAREN":
            while True:
                arguments.append(self._parse_expression())
                if self._current().type != "COMMA":
                    break
                self._advance()
        self._expect("RPAREN", "Expected ')'")
        return arguments


def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse_program()
