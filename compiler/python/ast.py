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


class ASTNode:
    pass


class Expression(ASTNode):
    pass


@dataclass(slots=True)
class Program(ASTNode):
    statements: list[ASTNode]


@dataclass(slots=True)
class StringLiteral(Expression):
    value: str


@dataclass(slots=True)
class IntegerLiteral(Expression):
    value: int


@dataclass(slots=True)
class BooleanLiteral(Expression):
    value: bool


@dataclass(slots=True)
class NumberLiteral(Expression):
    value: int
    scale: int


@dataclass(slots=True)
class BuiltinCallExpression(Expression):
    name: str
    arguments: list[Expression]


@dataclass(slots=True)
class LambdaExpression(Expression):
    parameter_type: str
    parameter_name: str
    body: Expression | list[ASTNode]


@dataclass(slots=True)
class MultiLambdaExpression(Expression):
    parameters: list["FunctionParameter"]
    body: Expression | list[ASTNode]


@dataclass(slots=True)
class FunctionCallExpression(Expression):
    name: str
    arguments: list[Expression]


@dataclass(slots=True)
class Identifier(Expression):
    name: str


@dataclass(slots=True)
class BinaryExpression(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass(slots=True)
class TernaryExpression(Expression):
    condition: Expression
    when_true: Expression
    when_false: Expression


@dataclass(slots=True)
class UnaryExpression(Expression):
    operator: str
    operand: Expression


@dataclass(slots=True)
class ConstructorCall(Expression):
    type_name: str
    arguments: list[Expression]


@dataclass(slots=True)
class FieldAccess(Expression):
    target: Expression
    field_name: str


@dataclass(slots=True)
class ArrayAccess(Expression):
    target: Expression
    index: Expression


@dataclass(slots=True)
class ArrayLiteral(Expression):
    items: list[Expression]


@dataclass(slots=True)
class MapLiteral(Expression):
    items: list[tuple[Expression, Expression]]


@dataclass(slots=True)
class SetLiteral(Expression):
    items: list[Expression]


@dataclass(slots=True)
class RecordField(ASTNode):
    type_name: str
    name: str


@dataclass(slots=True)
class RecordDeclaration(ASTNode):
    name: str
    fields: list[RecordField]


@dataclass(slots=True)
class EnumDeclaration(ASTNode):
    name: str
    members: list[str]


@dataclass(slots=True)
class FunctionParameter(ASTNode):
    type_name: str
    name: str


@dataclass(slots=True)
class FunctionDeclaration(ASTNode):
    name: str
    parameters: list[FunctionParameter]
    body: list[ASTNode]
    return_type: str | None = None
    cached: bool = False


@dataclass(slots=True)
class ReturnStatement(ASTNode):
    value: Expression | None


@dataclass(slots=True)
class ThrowStatement(ASTNode):
    value: Expression


@dataclass(slots=True)
class ContinueStatement(ASTNode):
    pass


@dataclass(slots=True)
class BreakStatement(ASTNode):
    pass


@dataclass(slots=True)
class VariableDeclaration(ASTNode):
    type_name: str
    name: str
    value: Expression
    is_const: bool = False


@dataclass(slots=True)
class Assignment(ASTNode):
    name: str
    value: Expression


@dataclass(slots=True)
class ArrayAssignment(ASTNode):
    target: ArrayAccess
    value: Expression


@dataclass(slots=True)
class FieldAssignment(ASTNode):
    target: FieldAccess
    value: Expression


@dataclass(slots=True)
class ForStatement(ASTNode):
    initializer: VariableDeclaration | Assignment
    condition: Expression
    update: Assignment
    body: list[ASTNode]


@dataclass(slots=True)
class ForEachStatement(ASTNode):
    item_type: str
    item_name: str
    iterable: Expression
    body: list[ASTNode]


@dataclass(slots=True)
class WhileStatement(ASTNode):
    condition: Expression
    body: list[ASTNode]


@dataclass(slots=True)
class IfStatement(ASTNode):
    condition: Expression
    then_body: list[ASTNode]
    else_body: list[ASTNode]


@dataclass(slots=True)
class SwitchCase(ASTNode):
    value: Expression
    body: list[ASTNode]


@dataclass(slots=True)
class SwitchStatement(ASTNode):
    expression: Expression
    cases: list[SwitchCase]
    default_body: list[ASTNode]


@dataclass(slots=True)
class TryCatchStatement(ASTNode):
    try_body: list[ASTNode]
    catch_name: str
    catch_body: list[ASTNode]


@dataclass(slots=True)
class FunctionCallStatement(ASTNode):
    name: str
    arguments: list[Expression]


@dataclass(slots=True)
class BuiltinCallStatement(ASTNode):
    name: str
    arguments: list[Expression]
