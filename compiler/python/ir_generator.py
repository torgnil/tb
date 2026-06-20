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
from decimal import Decimal, InvalidOperation, localcontext

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
    ReturnStatement,
    SetLiteral,
    StringLiteral,
    SwitchStatement,
    ThrowStatement,
    TernaryExpression,
    TryCatchStatement,
    UnaryExpression,
    VariableDeclaration,
    WhileStatement,
)
from .ir import (
    IRArrayIndex,
    IRArrayCollect,
    IRArrayFilter,
    IRArrayLength,
    IRArrayLiteral,
    IRArrayMap,
    IRArrayClear,
    IRArrayInsert,
    IRArrayPop,
    IRArrayPush,
    IRArrayRemove,
    IRArraySort,
    IRArraySet,
    IRMapSet,
    IRAssignInt,
    IRAssignArray,
    IRAssignBool,
    IRAssignRecord,
    IRAssignString,
    IRBinaryOperation,
    IRBoolean,
    IRCallArgument,
    IRCallExpression,
    IRComparison,
    IRCloseFile,
    IRBreak,
    IRContinue,
    IRDeclareArray,
    IRDeclareBool,
    IRDeclareFile,
    IRDeclareInt,
    IRDeclareMap,
    IRDeclarePriorityQueue,
    IRDeclareRecord,
    IRDeclareString,
    IRForLoop,
    IRFunctionCall,
    IRFunctionDefinition,
    IRFunctionParameter,
    IRIf,
    IRInteger,
    IRIntToString,
    IRLogicalCondition,
    IRMapIndex,
    IRMapLiteral,
    IRModule,
    IRPrintInt,
    IRPrintString,
    IRRecordConstruct,
    IRRecordField,
    IRRecordType,
    IRRecordTypeField,
    IRReturn,
    IRSelect,
    IRSetRecordField,
    IRSetLiteral,
    IRString,
    IRStringIndex,
    IRStringConcat,
    IRStringLiteral,
    IRThrow,
    IRTryCatch,
    IRWhileLoop,
    IRWriteLine,
    IRVariable,
    IRAssignMap,
    IRAssignPriorityQueue,
    IRPriorityQueueCreate,
)
from .foreign_modules import foreign_module_functions
from .stdlib import resolve_builtin


@dataclass(slots=True)
class RecordInstance:
    type_name: str
    field_values: dict[str, object]


@dataclass(slots=True)
class NumberValue:
    value: int
    scale: int


@dataclass(slots=True)
class ArrayValue:
    item_type: str
    items: list[object]


class IRGenerator:
    def __init__(self, foreign_modules: list[str] | None = None) -> None:
        self.module = IRModule()
        self.foreign_modules = list(foreign_modules or [])
        self.string_labels: dict[str, str] = {}
        self.int_constants: dict[str, int] = {}
        self.bool_variables: dict[str, bool] = {}
        self.variable_types: dict[str, str] = {}
        self.string_variables: dict[str, str] = {}
        self.number_variables: dict[str, NumberValue] = {}
        self.array_variables: dict[str, ArrayValue] = {}
        self.record_types: dict[str, dict[str, str]] = {}
        self.record_variables: dict[str, RecordInstance] = {}
        self.enum_types: dict[str, list[str]] = {}
        self.enum_variables: dict[str, str] = {}
        self.function_signatures: dict[str, tuple[str, ...]] = {}
        self.function_return_types: dict[str, str] = {}
        self.function_declarations: dict[str, FunctionDeclaration] = {}
        self.current_function_return_type: str | None = None
        self.loop_depth = 0
        self.synthetic_counter = 0
        self.runtime_bound_variables: set[str] = set()
        self.mutable_global_variables: set[str] = set()
        self.const_variables: set[str] = set()

    def generate(self, program: Program) -> IRModule:
        self._register_foreign_functions()
        self._register_named_types(program)
        self._register_global_declarations(program)
        self._register_functions(program)
        for statement in program.statements:
            lowered = self._lower_statement(statement)
            if isinstance(statement, FunctionDeclaration):
                self.module.functions.extend(lowered)
            else:
                self.module.instructions.extend(lowered)
        if self.module.entry_function_name is not None and any(not self._is_global_initializer(instruction) for instruction in self.module.instructions):
            raise TypeError("Top-level executable statements are not allowed when int main(string[] args) is declared")
        return self.module

    def _register_foreign_functions(self) -> None:
        for function in foreign_module_functions(self.foreign_modules):
            self.function_signatures[function.symbol_name] = function.argument_types
            self.function_return_types[function.symbol_name] = function.return_type

    @staticmethod
    def _is_global_initializer(instruction) -> bool:
        return isinstance(
            instruction,
            (IRDeclareInt, IRDeclareBool, IRDeclareString, IRDeclareMap, IRDeclareArray, IRDeclarePriorityQueue, IRDeclareRecord, IRDeclareFile),
        )

    def _register_named_types(self, program: Program) -> None:
        for statement in program.statements:
            if isinstance(statement, RecordDeclaration):
                self.record_types[statement.name] = {field.name: field.type_name for field in statement.fields}
                if not any(record_type.name == statement.name for record_type in self.module.record_types):
                    self.module.record_types.append(
                        IRRecordType(
                            statement.name,
                            [IRRecordTypeField(field.type_name, field.name) for field in statement.fields],
                        )
                    )
                continue
            if isinstance(statement, EnumDeclaration):
                self.enum_types[statement.name] = statement.members.copy()

    def _register_global_declarations(self, program: Program) -> None:
        global_names: set[str] = set()
        for statement in program.statements:
            if isinstance(statement, VariableDeclaration):
                self.variable_types[statement.name] = statement.type_name
                if statement.is_const:
                    self.const_variables.add(statement.name)
                else:
                    self.const_variables.discard(statement.name)
                global_names.add(statement.name)
        self.mutable_global_variables = set()
        for statement in program.statements:
            if isinstance(statement, FunctionDeclaration):
                for body_statement in statement.body:
                    self.mutable_global_variables.update(
                        name for name in self._assigned_binding_names(body_statement) if name in global_names
                    )

    def _lower_statement(self, statement):
        if isinstance(statement, BuiltinCallStatement):
            lowered = self._lower_builtin_call(statement)
            return [] if lowered is None else [lowered]
        if isinstance(statement, FunctionCallStatement):
            lowered = self._lower_function_call(statement)
            return [] if lowered is None else [lowered]
        if isinstance(statement, FunctionDeclaration):
            lowered = self._lower_function_declaration(statement)
            return [] if lowered is None else [lowered]
        if isinstance(statement, RecordDeclaration):
            self.record_types[statement.name] = {field.name: field.type_name for field in statement.fields}
            if not any(record_type.name == statement.name for record_type in self.module.record_types):
                self.module.record_types.append(
                    IRRecordType(
                        statement.name,
                        [IRRecordTypeField(field.type_name, field.name) for field in statement.fields],
                    )
                )
            return []
        if isinstance(statement, EnumDeclaration):
            self.enum_types[statement.name] = statement.members.copy()
            return []
        if isinstance(statement, VariableDeclaration):
            return self._lower_variable_declaration(statement)
        if isinstance(statement, Assignment):
            return self._lower_assignment(statement)
        if isinstance(statement, ArrayAssignment):
            return self._lower_array_assignment(statement)
        if isinstance(statement, FieldAssignment):
            return self._lower_field_assignment(statement)
        if isinstance(statement, ForEachStatement):
            return self._lower_for_each(statement)
        if isinstance(statement, ForStatement):
            return [self._lower_for_loop(statement)]
        if isinstance(statement, WhileStatement):
            return [self._lower_while_statement(statement)]
        if isinstance(statement, IfStatement):
            return [self._lower_if_statement(statement)]
        if isinstance(statement, SwitchStatement):
            return self._lower_switch_statement(statement)
        if isinstance(statement, ReturnStatement):
            lowered = self._lower_return_statement(statement)
            return [] if lowered is None else [lowered]
        if isinstance(statement, ThrowStatement):
            return [self._lower_throw_statement(statement)]
        if isinstance(statement, ContinueStatement):
            return [self._lower_continue_statement(statement)]
        if isinstance(statement, BreakStatement):
            return [self._lower_break_statement(statement)]
        if isinstance(statement, TryCatchStatement):
            return [self._lower_try_catch_statement(statement)]
        raise TypeError(f"Unsupported AST node: {type(statement).__name__}")

    def _lower_builtin_call(self, statement: BuiltinCallStatement):
        if statement.name == "sort":
            if len(statement.arguments) != 2:
                raise TypeError("sort requires an array and a comparator")
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("sort requires an array variable")
            array_name = statement.arguments[0].name
            self._ensure_mutable_binding(array_name, "mutate")
            array_type = self.variable_types.get(array_name)
            if array_type is None or not self._is_array_type(array_type):
                raise TypeError("sort currently requires an array variable")
            self.array_variables.pop(array_name, None)
            item_type = self._array_item_type(array_type)
            return IRArraySort(array_name, item_type, self._lower_sort_comparator(statement.arguments[1], item_type))
        argument_types = tuple(self._expression_type(argument) for argument in statement.arguments)
        if statement.name == "print" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
            return IRPrintString(self._lower_enum_expression(statement.arguments[0], argument_types[0]))
        overload = resolve_builtin(statement.name, argument_types)

        if statement.name == "print" and overload.lowering == "print_string":
            return IRPrintString(self._lower_string_expression(statement.arguments[0]))
        if statement.name == "print" and overload.lowering == "print_number":
            return IRPrintString(self._lower_number_expression(statement.arguments[0]))
        if statement.name == "print" and overload.lowering == "print_int":
            return IRPrintInt(self._lower_integer_expression(statement.arguments[0]))
        if statement.name == "print" and overload.lowering == "print_bool":
            constant_value = self._boolean_constant_value(statement.arguments[0])
            if constant_value is not None:
                return IRPrintString(self._string_literal("true" if constant_value else "false"))
            return IRPrintString(
                IRSelect(
                    self._lower_condition(statement.arguments[0]),
                    self._string_literal("true"),
                    self._string_literal("false"),
                    "string",
                )
            )
        if statement.name == "print" and overload.lowering == "print_int_array":
            constant_value = self._array_constant_value(statement.arguments[0], "int[]")
            if constant_value is not None:
                return IRPrintString(self._string_literal(self._format_int_array_value(constant_value)))
            return IRPrintString(
                IRCallExpression(
                    "array_to_string_int",
                    [IRCallArgument("int[]", self._lower_array_expression(statement.arguments[0], "int[]"))],
                    "string",
                    builtin=True,
                )
            )
        if statement.name == "print" and overload.lowering == "print_string_array":
            constant_value = self._array_constant_value(statement.arguments[0], "string[]")
            if constant_value is not None:
                return IRPrintString(self._string_literal(self._format_string_array_value(constant_value)))
            return IRPrintString(
                IRCallExpression(
                    "array_to_string_string",
                    [IRCallArgument("string[]", self._lower_array_expression(statement.arguments[0], "string[]"))],
                    "string",
                    builtin=True,
                )
            )
        if statement.name == "print" and overload.lowering == "print_bool_array":
            constant_value = self._array_constant_value(statement.arguments[0], "bool[]")
            if constant_value is not None:
                return IRPrintString(self._string_literal(self._format_bool_array_value(constant_value)))
            return IRPrintString(
                IRCallExpression(
                    "array_to_string_bool",
                    [IRCallArgument("bool[]", self._lower_array_expression(statement.arguments[0], "bool[]"))],
                    "string",
                    builtin=True,
                )
            )
        if statement.name == "print" and overload.lowering == "print_int_set":
            return IRPrintString(
                IRCallExpression(
                    "tb_int_set_to_string",
                    [IRCallArgument("set<int>", self._lower_set_expression(statement.arguments[0], "set<int>"))],
                    "string",
                )
            )
        if statement.name == "write_line" and overload.lowering == "write_line":
            if not isinstance(statement.arguments[0], Identifier) or self.variable_types.get(statement.arguments[0].name) != "file":
                raise TypeError("write_line requires a file variable")
            return IRWriteLine(statement.arguments[0].name, self._lower_string_expression(statement.arguments[1]))
        if statement.name == "close" and overload.lowering == "close_file":
            if not isinstance(statement.arguments[0], Identifier) or self.variable_types.get(statement.arguments[0].name) != "file":
                raise TypeError("close requires a file variable")
            return IRCloseFile(statement.arguments[0].name)
        if statement.name == "push" and overload.lowering == "array_push":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("push requires an array variable")
            array_name = statement.arguments[0].name
            self._ensure_mutable_binding(array_name, "mutate")
            array_type = self.variable_types.get(array_name)
            if array_type is None or not self._is_array_type(array_type):
                raise TypeError("push requires an array variable")
            item_type = self._array_item_type(array_type)
            self.array_variables.pop(array_name, None)
            return IRArrayPush(array_name, item_type, self._lower_typed_expression(statement.arguments[1], item_type))
        if statement.name == "push" and overload.lowering == "prio_q_push":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("push requires a priority queue variable")
            queue_name = statement.arguments[0].name
            self._ensure_mutable_binding(queue_name, "mutate")
            queue_type = self.variable_types.get(queue_name)
            if queue_type is None or not self._is_priority_queue_type(queue_type):
                raise TypeError("push requires a priority queue variable")
            item_type = self._priority_queue_item_type(queue_type)
            return IRFunctionCall(
                "tb_pq_push",
                [
                    self._lower_call_argument(statement.arguments[0], queue_type),
                    self._lower_call_argument(statement.arguments[1], item_type),
                ],
                "void",
            )
        if statement.name == "pop" and overload.lowering == "array_pop":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("pop requires an array variable")
            array_name = statement.arguments[0].name
            self._ensure_mutable_binding(array_name, "mutate")
            array_type = self.variable_types.get(array_name)
            if array_type is None or not self._is_array_type(array_type):
                raise TypeError("pop requires an array variable")
            self.array_variables.pop(array_name, None)
            return IRArrayPop(array_name, self._array_item_type(array_type))
        if statement.name == "insert" and overload.lowering == "array_insert":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("insert requires an array variable")
            array_name = statement.arguments[0].name
            self._ensure_mutable_binding(array_name, "mutate")
            array_type = self.variable_types.get(array_name)
            if array_type is None or not self._is_array_type(array_type):
                raise TypeError("insert requires an array variable")
            item_type = self._array_item_type(array_type)
            self.array_variables.pop(array_name, None)
            return IRArrayInsert(
                array_name,
                item_type,
                self._lower_integer_expression(statement.arguments[1]),
                self._lower_typed_expression(statement.arguments[2], item_type),
            )
        if statement.name == "remove_at" and overload.lowering == "array_remove_at":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("remove_at requires an array variable")
            array_name = statement.arguments[0].name
            self._ensure_mutable_binding(array_name, "mutate")
            array_type = self.variable_types.get(array_name)
            if array_type is None or not self._is_array_type(array_type):
                raise TypeError("remove_at requires an array variable")
            self.array_variables.pop(array_name, None)
            return IRArrayRemove(
                array_name,
                self._array_item_type(array_type),
                self._lower_integer_expression(statement.arguments[1]),
            )
        if statement.name == "clear" and overload.lowering == "array_clear":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("clear requires an array variable")
            array_name = statement.arguments[0].name
            self._ensure_mutable_binding(array_name, "mutate")
            array_type = self.variable_types.get(array_name)
            if array_type is None or not self._is_array_type(array_type):
                raise TypeError("clear requires an array variable")
            self.array_variables[array_name] = ArrayValue(self._array_item_type(array_type), [])
            return IRArrayClear(array_name)
        if statement.name == "add" and overload.lowering == "set_add_int":
            if not isinstance(statement.arguments[0], Identifier):
                raise TypeError("add requires a set variable")
            set_name = statement.arguments[0].name
            self._ensure_mutable_binding(set_name, "mutate")
            set_type = self.variable_types.get(set_name)
            if set_type is None or not self._is_set_type(set_type):
                raise TypeError("add requires a set variable")
            item_type = self._set_item_type(set_type)
            return IRFunctionCall(
                "tb_set_add",
                [
                    IRCallArgument(set_type, self._lower_set_expression(statement.arguments[0], set_type)),
                    IRCallArgument(item_type, self._lower_typed_expression(statement.arguments[1], item_type)),
                ],
                "void",
            )
        if statement.name == "dump_runtime_activity" and overload.lowering == "dump_runtime_activity":
            return IRFunctionCall("dump_runtime_activity", [], "void")
        if statement.name == "reset_runtime_activity" and overload.lowering == "reset_runtime_activity":
            return IRFunctionCall("reset_runtime_activity", [], "void")

        raise TypeError(f"Unsupported builtin lowering: {statement.name}/{overload.lowering}")

    def _lower_sort_comparator(self, expression, item_type: str) -> str:
        if isinstance(expression, Identifier):
            if expression.name in self.variable_types:
                raise TypeError("sort comparator identifier must name a function")
            signature = self.function_signatures.get(expression.name)
            return_type = self.function_return_types.get(expression.name)
            if signature != (item_type, item_type) or return_type != "int":
                raise TypeError(
                    f"sort comparator function must have signature int {expression.name}({item_type}, {item_type})"
                )
            return expression.name
        if isinstance(expression, MultiLambdaExpression):
            if len(expression.parameters) != 2:
                raise TypeError("sort comparator lambda must take exactly two parameters")
            if expression.parameters[0].type_name != item_type or expression.parameters[1].type_name != item_type:
                raise TypeError(f"sort comparator lambda must take ({item_type}, {item_type})")
            return_type = self._callable_return_type(expression.parameters, expression.body, {})
            if return_type != "int":
                raise TypeError("sort comparator lambda must return int")
            return self._lower_multi_lambda(expression, "int")
        raise TypeError("sort comparator must be a named function or a two-parameter lambda")

    def _validate_priority_queue_comparator(self, expression, item_type: str) -> None:
        if isinstance(expression, Identifier):
            if expression.name in self.variable_types:
                raise TypeError("priority queue comparator identifier must name a function")
            signature = self.function_signatures.get(expression.name)
            return_type = self.function_return_types.get(expression.name)
            if signature != (item_type, item_type) or return_type != "int":
                raise TypeError(
                    f"priority queue comparator function must have signature int {expression.name}({item_type}, {item_type})"
                )
            return
        if isinstance(expression, MultiLambdaExpression):
            if len(expression.parameters) != 2:
                raise TypeError("priority queue comparator lambda must take exactly two parameters")
            if expression.parameters[0].type_name != item_type or expression.parameters[1].type_name != item_type:
                raise TypeError(f"priority queue comparator lambda must take ({item_type}, {item_type})")
            return_type = self._callable_return_type(expression.parameters, expression.body, {})
            if return_type != "int":
                raise TypeError("priority queue comparator lambda must return int")
            return
        raise TypeError("priority queue comparator must be a named function or a two-parameter lambda")

    def _lower_priority_queue_expression(self, expression, expected_type: str):
        item_type = self._priority_queue_item_type(expected_type)
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected priority queue variable of type {expected_type}: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, BuiltinCallExpression) and expression.name == "create_prio_q":
            if len(expression.arguments) != 2:
                raise TypeError("create_prio_q requires an array and a comparator")
            source_type = self._expression_type(expression.arguments[0])
            if source_type != f"{item_type}[]":
                raise TypeError(f"create_prio_q requires {item_type}[], got {source_type}")
            return IRPriorityQueueCreate(
                self._lower_array_expression(expression.arguments[0], source_type),
                item_type,
                self._lower_sort_comparator(expression.arguments[1], item_type),
            )
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, expected_type)
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected {expected_type}-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                expected_type,
            )
        raise TypeError(f"Unsupported priority queue expression node: {type(expression).__name__}")

    def _lower_function_call(self, statement: FunctionCallStatement) -> IRFunctionCall | None:
        argument_types = tuple(self._expression_type(argument) for argument in statement.arguments)
        if statement.name == "add" and len(argument_types) == 2 and self._is_set_type(argument_types[0]) and self._set_item_type(argument_types[0]) == argument_types[1]:
            if isinstance(statement.arguments[0], Identifier):
                self._ensure_mutable_binding(statement.arguments[0].name, "mutate")
            return IRFunctionCall(
                "tb_set_add",
                [
                    self._lower_call_argument(statement.arguments[0], argument_types[0]),
                    self._lower_call_argument(statement.arguments[1], argument_types[1]),
                ],
                "void",
            )
        signature = self.function_signatures.get(statement.name)
        if signature is None:
            raise TypeError(f"Unknown function: {statement.name}")
        if argument_types != signature:
            raise TypeError(f"Argument mismatch for function {statement.name}: expected {signature}, got {argument_types}")
        arguments = [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(statement.arguments, signature, strict=True)]
        return IRFunctionCall(statement.name, arguments, self.function_return_types.get(statement.name, "void"))

    def _lower_function_declaration(self, statement: FunctionDeclaration) -> IRFunctionDefinition | None:
        saved_variable_types = self.variable_types.copy()
        saved_int_constants = self.int_constants.copy()
        saved_bool_variables = self.bool_variables.copy()
        saved_string_variables = self.string_variables.copy()
        saved_number_variables = self.number_variables.copy()
        saved_array_variables = self.array_variables.copy()
        saved_record_variables = self.record_variables.copy()
        saved_enum_variables = self.enum_variables.copy()
        saved_current_function_return_type = self.current_function_return_type
        saved_runtime_bound_variables = self.runtime_bound_variables.copy()
        saved_const_variables = self.const_variables.copy()

        self.runtime_bound_variables = self.mutable_global_variables.copy()
        for name in self.mutable_global_variables:
            self.int_constants.pop(name, None)
            self.bool_variables.pop(name, None)
            self.string_variables.pop(name, None)
            self.number_variables.pop(name, None)
            self.array_variables.pop(name, None)
            self.record_variables.pop(name, None)
            self.enum_variables.pop(name, None)
        for body_statement in statement.body:
            self.runtime_bound_variables.update(self._assigned_binding_names(body_statement))
        for parameter in statement.parameters:
            self.variable_types[parameter.name] = parameter.type_name
            self.const_variables.discard(parameter.name)

        self.current_function_return_type = self.function_return_types.get(statement.name, "void")
        body_instructions = []
        for body_statement in statement.body:
            body_instructions.extend(self._lower_statement(body_statement))
        if (
            statement.name == "main"
            and self.function_return_types.get(statement.name) == "int"
            and not self._instructions_terminate(body_instructions)
        ):
            body_instructions.append(IRReturn(IRInteger(0), "int"))

        self.variable_types = saved_variable_types
        self.int_constants = saved_int_constants
        self.bool_variables = saved_bool_variables
        self.string_variables = saved_string_variables
        self.number_variables = saved_number_variables
        self.array_variables = saved_array_variables
        self.record_variables = saved_record_variables
        self.enum_variables = saved_enum_variables
        self.current_function_return_type = saved_current_function_return_type
        self.runtime_bound_variables = saved_runtime_bound_variables
        self.const_variables = saved_const_variables

        return IRFunctionDefinition(
            statement.name,
            [IRFunctionParameter(parameter.type_name, parameter.name) for parameter in statement.parameters],
            body_instructions,
            self.function_return_types.get(statement.name, "void"),
            statement.cached,
        )

    def _lower_return_statement(self, statement: ReturnStatement) -> IRReturn:
        if self.current_function_return_type is None:
            raise TypeError("Return statements are only valid inside functions")
        if statement.value is None:
            if self.current_function_return_type != "void":
                raise TypeError(f"Function must return {self.current_function_return_type}, got bare return")
            return IRReturn(None, "void")
        return IRReturn(
            self._lower_typed_expression(statement.value, self.current_function_return_type),
            self.current_function_return_type,
        )

    def _lower_throw_statement(self, statement: ThrowStatement) -> IRThrow:
        return IRThrow(self._lower_string_expression(statement.value))

    def _lower_typed_expression(self, expression, type_name: str):
        if type_name == "int":
            return self._lower_integer_expression(expression)
        if type_name == "bool":
            return self._lower_boolean_expression(expression)
        if type_name == "string":
            return self._lower_string_expression(expression)
        if type_name in self.enum_types:
            return self._lower_enum_expression(expression, type_name)
        if self._is_map_type(type_name):
            return self._lower_map_expression(expression, type_name)
        if self._is_set_type(type_name):
            return self._lower_set_expression(expression, type_name)
        if self._is_priority_queue_type(type_name):
            return self._lower_priority_queue_expression(expression, type_name)
        if self._is_array_type(type_name):
            return self._lower_array_expression(expression, type_name)
        if type_name in self.record_types:
            return self._lower_record_expression(expression, type_name)
        raise TypeError(f"Unsupported runtime type: {type_name}")

    def _lower_last_array_value(self, expression, expected_type: str):
        array_type = self._expression_type(expression.arguments[0])
        return IRArrayIndex(
            self._lower_array_expression(expression.arguments[0], array_type),
            IRBinaryOperation(
                IRArrayLength(
                    self._lower_array_expression(expression.arguments[0], array_type),
                    self._array_item_type(array_type),
                ),
                "-",
                IRInteger(1),
            ),
            expected_type,
        )

    def _is_runtime_value_type(self, type_name: str) -> bool:
        if type_name in {"int", "bool", "string"}:
            return True
        if type_name in self.enum_types:
            return True
        if self._is_array_type(type_name):
            return self._is_runtime_value_type(self._array_item_type(type_name))
        if self._is_set_type(type_name):
            return self._is_cache_stringifiable_type(self._set_item_type(type_name))
        if type_name in self.record_types:
            return all(self._is_runtime_value_type(field_type) for field_type in self.record_types[type_name].values())
        return False

    def _is_cache_stringifiable_type(self, type_name: str) -> bool:
        if type_name in {"int", "bool", "string"}:
            return True
        if type_name in self.enum_types:
            return True
        if self._is_array_type(type_name):
            return self._is_cache_stringifiable_type(self._array_item_type(type_name))
        if type_name in self.record_types:
            return all(self._is_cache_stringifiable_type(field_type) for field_type in self.record_types[type_name].values())
        return False

    @staticmethod
    def _is_array_type(type_name: str) -> bool:
        return type_name.endswith("[]")

    @staticmethod
    def _array_item_type(type_name: str) -> str:
        return type_name.removesuffix("[]")

    @staticmethod
    def _is_set_type(type_name: str) -> bool:
        return type_name.startswith("set<") and type_name.endswith(">")

    @staticmethod
    def _set_item_type(type_name: str) -> str:
        return type_name[4:-1]

    @staticmethod
    def _is_map_type(type_name: str) -> bool:
        return type_name.startswith("map<") and type_name.endswith(">")

    @staticmethod
    def _is_priority_queue_type(type_name: str) -> bool:
        return type_name.startswith("prio_q<") and type_name.endswith(">")

    @staticmethod
    def _priority_queue_item_type(type_name: str) -> str:
        return type_name[7:-1]

    @staticmethod
    def _map_parts(type_name: str) -> tuple[str, str]:
        inner = type_name[4:-1]
        depth = 0
        for index, char in enumerate(inner):
            if char == "<":
                depth += 1
            elif char == ">":
                depth -= 1
            elif char == "," and depth == 0:
                return inner[:index], inner[index + 1 :]
        raise TypeError(f"Invalid map type: {type_name}")

    def _membership_overload(self, item_type: str, container_type: str):
        if self._is_set_type(container_type) or self._is_array_type(container_type) or self._is_map_type(container_type):
            return resolve_builtin("contains", (container_type, item_type))
        raise TypeError(f"Unsupported membership container type: {container_type}")

    def _lower_membership_call(self, item_expression, container_expression):
        item_type = self._expression_type(item_expression)
        container_type = self._expression_type(container_expression)
        overload = self._membership_overload(item_type, container_type)
        return IRCallExpression(
            "contains",
            [
                self._lower_call_argument(container_expression, container_type),
                self._lower_call_argument(item_expression, item_type),
            ],
            overload.return_type,
            builtin=True,
        )

    def _lower_variable_declaration(self, statement: VariableDeclaration):
        if statement.is_const:
            self.const_variables.add(statement.name)
        else:
            self.const_variables.discard(statement.name)
        if statement.type_name == "int":
            self.variable_types[statement.name] = "int"
            constant_value = self._integer_constant_value(statement.value)
            if constant_value is not None:
                self.int_constants[statement.name] = constant_value
            else:
                self.int_constants.pop(statement.name, None)
            return [IRDeclareInt(statement.name, self._lower_integer_expression(statement.value))]

        if statement.type_name == "bool":
            self.variable_types[statement.name] = "bool"
            constant_value = self._boolean_constant_value(statement.value)
            if constant_value is not None:
                self.bool_variables[statement.name] = constant_value
                if statement.name not in self.runtime_bound_variables:
                    return []
            self.bool_variables.pop(statement.name, None)
            return [IRDeclareBool(statement.name, self._lower_boolean_expression(statement.value))]

        if statement.type_name == "string":
            self.variable_types[statement.name] = "string"
            constant_value = self._string_constant_value(statement.value)
            if constant_value is not None:
                self.string_variables[statement.name] = constant_value
            else:
                self.string_variables.pop(statement.name, None)
            return [IRDeclareString(statement.name, self._lower_string_expression(statement.value))]

        if statement.type_name in self.enum_types:
            self.variable_types[statement.name] = statement.type_name
            constant_value = self._enum_constant_value(statement.value, statement.type_name)
            if constant_value is not None:
                self.enum_variables[statement.name] = constant_value
            else:
                self.enum_variables.pop(statement.name, None)
            return [IRDeclareString(statement.name, self._lower_enum_expression(statement.value, statement.type_name))]

        if statement.type_name == "num":
            self.variable_types[statement.name] = "num"
            self.number_variables[statement.name] = self._coerce_number_value(statement.value)
            return []

        if self._is_array_type(statement.type_name):
            self.variable_types[statement.name] = statement.type_name
            constant_value = self._array_constant_value(statement.value, statement.type_name)
            if constant_value is not None:
                self.array_variables[statement.name] = constant_value
            else:
                self.array_variables.pop(statement.name, None)
            return [IRDeclareArray(statement.type_name, statement.name, self._lower_array_expression(statement.value, statement.type_name))]

        if self._is_map_type(statement.type_name):
            self.variable_types[statement.name] = statement.type_name
            return [IRDeclareMap(statement.type_name, statement.name, self._lower_map_expression(statement.value, statement.type_name))]

        if self._is_set_type(statement.type_name):
            self.variable_types[statement.name] = statement.type_name
            self.array_variables.pop(statement.name, None)
            return [IRDeclareArray(statement.type_name, statement.name, self._lower_set_expression(statement.value, statement.type_name))]

        if self._is_priority_queue_type(statement.type_name):
            self.variable_types[statement.name] = statement.type_name
            return [
                IRDeclarePriorityQueue(
                    statement.type_name,
                    statement.name,
                    self._lower_priority_queue_expression(statement.value, statement.type_name),
                )
            ]

        if statement.type_name == "file":
            self.variable_types[statement.name] = "file"
            return [IRDeclareFile(statement.name, self._lower_file_expression(statement.value))]

        if statement.type_name in self.record_types:
            self.variable_types[statement.name] = statement.type_name
            constant_value = self._record_constant_value(statement.type_name, statement.value)
            if constant_value is not None:
                self.record_variables[statement.name] = constant_value
            else:
                self.record_variables.pop(statement.name, None)
            return [IRDeclareRecord(statement.type_name, statement.name, self._lower_record_expression(statement.value, statement.type_name))]

        raise TypeError(f"Unsupported variable type: {statement.type_name}")

    def _lower_assignment(self, statement: Assignment):
        self._ensure_mutable_binding(statement.name, "assign to")
        variable_type = self.variable_types.get(statement.name)
        if variable_type == "int":
            lowered_value = self._lower_integer_expression(statement.value)
            constant_value = self._integer_constant_value(statement.value)
            if constant_value is not None:
                self.int_constants[statement.name] = constant_value
            else:
                self.int_constants.pop(statement.name, None)
            return [IRAssignInt(statement.name, lowered_value)]
        if variable_type == "bool":
            lowered_value = self._lower_boolean_expression(statement.value)
            constant_value = self._boolean_constant_value(statement.value)
            if constant_value is not None:
                self.bool_variables[statement.name] = constant_value
                if statement.name not in self.runtime_bound_variables:
                    return []
            self.bool_variables.pop(statement.name, None)
            return [IRAssignBool(statement.name, lowered_value)]
        if variable_type == "string":
            lowered_value = self._lower_string_expression(statement.value)
            constant_value = self._string_constant_value(statement.value)
            if constant_value is not None:
                self.string_variables[statement.name] = constant_value
            else:
                self.string_variables.pop(statement.name, None)
            return [IRAssignString(statement.name, lowered_value)]
        if variable_type in self.enum_types:
            lowered_value = self._lower_enum_expression(statement.value, variable_type)
            constant_value = self._enum_constant_value(statement.value, variable_type)
            if constant_value is not None:
                self.enum_variables[statement.name] = constant_value
            else:
                self.enum_variables.pop(statement.name, None)
            return [IRAssignString(statement.name, lowered_value)]
        if variable_type == "num":
            self.number_variables[statement.name] = self._coerce_number_value(statement.value)
            return []
        if variable_type is not None and self._is_array_type(variable_type):
            lowered_value = self._lower_array_expression(statement.value, variable_type)
            constant_value = self._array_constant_value(statement.value, variable_type)
            if constant_value is not None:
                self.array_variables[statement.name] = constant_value
            else:
                self.array_variables.pop(statement.name, None)
            return [IRAssignArray(variable_type, statement.name, lowered_value)]
        if variable_type is not None and self._is_map_type(variable_type):
            return [IRAssignMap(variable_type, statement.name, self._lower_map_expression(statement.value, variable_type))]
        if variable_type is not None and self._is_set_type(variable_type):
            self.array_variables.pop(statement.name, None)
            return [IRAssignArray(variable_type, statement.name, self._lower_set_expression(statement.value, variable_type))]
        if variable_type is not None and self._is_priority_queue_type(variable_type):
            return [IRAssignPriorityQueue(variable_type, statement.name, self._lower_priority_queue_expression(statement.value, variable_type))]
        if variable_type == "file":
            return [IRDeclareFile(statement.name, self._lower_file_expression(statement.value))]
        if variable_type in self.record_types:
            lowered_value = self._lower_record_expression(statement.value, variable_type)
            constant_value = self._record_constant_value(variable_type, statement.value)
            if constant_value is not None:
                self.record_variables[statement.name] = constant_value
            else:
                self.record_variables.pop(statement.name, None)
            return [IRAssignRecord(variable_type, statement.name, lowered_value)]
        raise TypeError(f"Unknown variable: {statement.name}")

    def _lower_array_assignment(self, statement: ArrayAssignment):
        if not isinstance(statement.target.target, Identifier):
            raise TypeError("Array assignment currently requires an array variable target")
        variable_name = statement.target.target.name
        self._ensure_mutable_binding(variable_name, "mutate")
        variable_type = self.variable_types.get(variable_name)
        if variable_type is not None and self._is_map_type(variable_type):
            key_type, value_type = self._map_parts(variable_type)
            return [
                IRMapSet(
                    variable_name,
                    key_type,
                    value_type,
                    self._lower_typed_expression(statement.target.index, key_type),
                    self._lower_typed_expression(statement.value, value_type),
                )
            ]
        if variable_type is None or not self._is_array_type(variable_type):
            raise TypeError(f"Expected array variable: {variable_name}")
        self.array_variables.pop(variable_name, None)
        return [
            IRArraySet(
                variable_name,
                self._array_item_type(variable_type),
                self._lower_integer_expression(statement.target.index),
                self._lower_typed_expression(statement.value, self._array_item_type(variable_type)),
            )
        ]

    def _lower_field_assignment(self, statement: FieldAssignment):
        if not isinstance(statement.target.target, Identifier):
            raise TypeError("Field assignment currently requires a record variable target")
        variable_name = statement.target.target.name
        self._ensure_mutable_binding(variable_name, "mutate")
        record_type = self.variable_types.get(variable_name)
        if record_type not in self.record_types:
            raise TypeError(f"Expected record variable: {variable_name}")
        field_type = self.record_types[record_type].get(statement.target.field_name)
        if field_type is None:
            raise TypeError(f"Unknown field {statement.target.field_name!r} on {record_type}")
        self.record_variables.pop(variable_name, None)
        return [
            IRSetRecordField(
                variable_name,
                record_type,
                statement.target.field_name,
                field_type,
                self._lower_typed_expression(statement.value, field_type),
            )
        ]

    def _lower_for_each(self, statement: ForEachStatement):
        iterable_type = self._expression_type(statement.iterable)
        if not self._is_array_type(iterable_type) and not self._is_set_type(iterable_type):
            raise TypeError("foreach requires an array expression")
        iterable_item_type = self._array_item_type(iterable_type) if self._is_array_type(iterable_type) else self._set_item_type(iterable_type)
        if iterable_item_type != statement.item_type:
            raise TypeError(f"Expected foreach item type {statement.item_type}, got {iterable_item_type}")

        iterable = self._array_constant_value(statement.iterable, iterable_type) if self._is_array_type(iterable_type) else None
        if iterable is None or self._contains_loop_control_statement(statement.body):
            return self._lower_runtime_for_each(statement, iterable_type)

        instructions = []
        saved_variable_types = self.variable_types.copy()
        saved_int_constants = self.int_constants.copy()
        saved_bool_variables = self.bool_variables.copy()
        saved_string_variables = self.string_variables.copy()
        saved_number_variables = self.number_variables.copy()
        saved_array_variables = self.array_variables.copy()
        saved_record_variables = self.record_variables.copy()
        saved_enum_variables = self.enum_variables.copy()
        saved_const_variables = self.const_variables.copy()

        for item in iterable.items:
            self.variable_types[statement.item_name] = statement.item_type
            self.const_variables.discard(statement.item_name)
            if statement.item_type == "int":
                constant_value = self._integer_constant_value(item)
                if constant_value is None:
                    raise TypeError("Foreach currently requires compile-time int items")
                self.int_constants[statement.item_name] = constant_value
                instructions.extend(
                    self._lower_statement(
                        VariableDeclaration("int", statement.item_name, IntegerLiteral(constant_value))
                    )
                )
            elif statement.item_type == "string":
                constant_value = self._string_constant_value(item)
                if constant_value is None:
                    raise TypeError("Foreach currently requires compile-time string items")
                self.string_variables[statement.item_name] = constant_value
            elif self._is_array_type(statement.item_type):
                constant_value = self._array_constant_value(item, statement.item_type)
                if constant_value is None:
                    raise TypeError("Foreach currently requires compile-time array items")
                self.array_variables[statement.item_name] = constant_value
            else:
                raise TypeError(f"Unsupported foreach item type: {statement.item_type}")
            for body_statement in statement.body:
                lowered = self._lower_statement(body_statement)
                instructions.extend(lowered)

        self.variable_types = saved_variable_types
        self.int_constants = saved_int_constants
        self.bool_variables = saved_bool_variables
        self.string_variables = saved_string_variables
        self.number_variables = saved_number_variables
        self.array_variables = saved_array_variables
        self.record_variables = saved_record_variables
        self.enum_variables = saved_enum_variables
        self.const_variables = saved_const_variables
        return instructions

    def _lower_runtime_for_each(self, statement: ForEachStatement, iterable_type: str):
        if self._expression_type(statement.iterable) != iterable_type:
            raise TypeError("foreach iterable type changed during lowering")
        base_variable_types = self.variable_types.copy()
        base_int_constants = self.int_constants.copy()
        base_bool_variables = self.bool_variables.copy()
        base_string_variables = self.string_variables.copy()
        base_number_variables = self.number_variables.copy()
        base_array_variables = self.array_variables.copy()
        base_record_variables = self.record_variables.copy()
        base_enum_variables = self.enum_variables.copy()
        base_const_variables = self.const_variables.copy()
        if not isinstance(statement.iterable, Identifier):
            temp_array_name = self._next_synthetic_name("foreach_array")
            iterable_value = (
                self._lower_array_expression(statement.iterable, iterable_type)
                if self._is_array_type(iterable_type)
                else self._lower_set_expression(statement.iterable, iterable_type)
            )
            setup = [IRDeclareArray(iterable_type, temp_array_name, iterable_value)]
            iterable_expression = Identifier(temp_array_name)
            self.variable_types[temp_array_name] = iterable_type
        else:
            setup = []
            iterable_expression = statement.iterable

        index_name = self._next_synthetic_name("foreach_index")
        self.variable_types[index_name] = "int"
        self.variable_types[statement.item_name] = statement.item_type
        self.const_variables.discard(index_name)
        self.const_variables.discard(statement.item_name)
        self.loop_depth += 1
        try:
            if self._is_set_type(iterable_type) and statement.item_type == "int":
                body_instructions = [
                    IRDeclareInt(
                        statement.item_name,
                        IRArrayIndex(
                            self._lower_set_expression(iterable_expression, iterable_type),
                            IRVariable(index_name),
                            "int",
                        ),
                    )
                ]
            else:
                body_instructions = self._lower_statement(
                    VariableDeclaration(
                        statement.item_type,
                        statement.item_name,
                        ArrayAccess(iterable_expression, Identifier(index_name)),
                    )
                )
            for body_statement in statement.body:
                self._invalidate_assigned_bindings(body_statement)
                body_instructions.extend(self._lower_statement(body_statement))
        finally:
            self.loop_depth -= 1
        loop_int_constants = self.int_constants.copy()
        loop_bool_variables = self.bool_variables.copy()
        loop_string_variables = self.string_variables.copy()
        loop_number_variables = self.number_variables.copy()
        loop_array_variables = self.array_variables.copy()
        loop_record_variables = self.record_variables.copy()
        loop_enum_variables = self.enum_variables.copy()
        iterable_ir_expression = (
            self._lower_array_expression(iterable_expression, iterable_type)
            if self._is_array_type(iterable_type)
            else self._lower_set_expression(iterable_expression, iterable_type)
        )
        iterable_item_type = self._array_item_type(iterable_type) if self._is_array_type(iterable_type) else self._set_item_type(iterable_type)

        self.variable_types = base_variable_types
        self.int_constants = self._restore_runtime_bindings(
            base_variable_types, base_int_constants, loop_int_constants, lambda type_name: type_name == "int"
        )
        self.bool_variables = self._restore_runtime_bindings(
            base_variable_types, base_bool_variables, loop_bool_variables, lambda type_name: type_name == "bool"
        )
        self.string_variables = self._restore_runtime_bindings(
            base_variable_types, base_string_variables, loop_string_variables, lambda type_name: type_name == "string"
        )
        self.number_variables = self._restore_runtime_bindings(
            base_variable_types, base_number_variables, loop_number_variables, lambda type_name: type_name == "num"
        )
        self.array_variables = self._restore_runtime_bindings(
            base_variable_types, base_array_variables, loop_array_variables, self._is_array_type
        )
        self.record_variables = self._restore_runtime_bindings(
            base_variable_types, base_record_variables, loop_record_variables, lambda type_name: type_name in self.record_types
        )
        self.enum_variables = self._restore_runtime_bindings(
            base_variable_types, base_enum_variables, loop_enum_variables, lambda type_name: type_name in self.enum_types
        )
        self.const_variables = base_const_variables

        return setup + [
            IRForLoop(
                IRDeclareInt(index_name, IRInteger(0)),
                IRComparison(
                    IRVariable(index_name),
                    "<",
                    IRArrayLength(
                        iterable_ir_expression,
                        iterable_item_type,
                    ),
                ),
                IRAssignInt(index_name, IRBinaryOperation(IRVariable(index_name), "+", IRInteger(1))),
                body_instructions,
            )
        ]

    def _next_synthetic_name(self, prefix: str) -> str:
        name = f"__{prefix}_{self.synthetic_counter}"
        self.synthetic_counter += 1
        return name

    def _lower_lambda(self, expression: LambdaExpression, return_type: str) -> str:
        return self._lower_callable_definition(
            [FunctionParameter(expression.parameter_type, expression.parameter_name)],
            expression.body,
            return_type,
        )

    def _lower_multi_lambda(self, expression: MultiLambdaExpression, return_type: str) -> str:
        return self._lower_callable_definition(expression.parameters, expression.body, return_type)

    def _lower_single_parameter_lambda_body(
        self,
        expression: LambdaExpression,
        parameter_type: str,
        return_type: str,
    ):
        if expression.parameter_type != parameter_type:
            raise TypeError(f"Expected lambda parameter type {parameter_type}, got {expression.parameter_type}")
        saved_variable_types = self.variable_types.copy()
        saved_int_constants = self.int_constants.copy()
        saved_bool_variables = self.bool_variables.copy()
        saved_string_variables = self.string_variables.copy()
        saved_number_variables = self.number_variables.copy()
        saved_array_variables = self.array_variables.copy()
        saved_record_variables = self.record_variables.copy()
        saved_enum_variables = self.enum_variables.copy()
        saved_const_variables = self.const_variables.copy()
        self.variable_types[expression.parameter_name] = parameter_type
        self.const_variables.discard(expression.parameter_name)
        self.int_constants.pop(expression.parameter_name, None)
        self.bool_variables.pop(expression.parameter_name, None)
        self.string_variables.pop(expression.parameter_name, None)
        self.number_variables.pop(expression.parameter_name, None)
        self.array_variables.pop(expression.parameter_name, None)
        self.record_variables.pop(expression.parameter_name, None)
        self.enum_variables.pop(expression.parameter_name, None)
        body = self._extract_lambda_body_expression(expression, return_type)
        self.variable_types = saved_variable_types
        self.int_constants = saved_int_constants
        self.bool_variables = saved_bool_variables
        self.string_variables = saved_string_variables
        self.number_variables = saved_number_variables
        self.array_variables = saved_array_variables
        self.record_variables = saved_record_variables
        self.enum_variables = saved_enum_variables
        self.const_variables = saved_const_variables
        return body

    def _lower_callable_definition(
        self,
        parameters: list[FunctionParameter],
        body_expression,
        return_type: str,
    ) -> str:
        function_name = self._next_synthetic_name("lambda")
        saved_variable_types = self.variable_types.copy()
        saved_int_constants = self.int_constants.copy()
        saved_bool_variables = self.bool_variables.copy()
        saved_string_variables = self.string_variables.copy()
        saved_number_variables = self.number_variables.copy()
        saved_array_variables = self.array_variables.copy()
        saved_record_variables = self.record_variables.copy()
        saved_enum_variables = self.enum_variables.copy()
        saved_current_function_return_type = self.current_function_return_type
        saved_const_variables = self.const_variables.copy()

        for parameter in parameters:
            self.variable_types[parameter.name] = parameter.type_name
            self.const_variables.discard(parameter.name)
            self.int_constants.pop(parameter.name, None)
            self.bool_variables.pop(parameter.name, None)
            self.string_variables.pop(parameter.name, None)
            self.number_variables.pop(parameter.name, None)
            self.array_variables.pop(parameter.name, None)
            self.record_variables.pop(parameter.name, None)
            self.enum_variables.pop(parameter.name, None)
        self.current_function_return_type = return_type
        if isinstance(body_expression, list):
            body = []
            for statement in body_expression:
                body.extend(self._lower_statement(statement))
        else:
            body = [IRReturn(self._lower_typed_expression(body_expression, return_type), return_type)]

        self.variable_types = saved_variable_types
        self.int_constants = saved_int_constants
        self.bool_variables = saved_bool_variables
        self.string_variables = saved_string_variables
        self.number_variables = saved_number_variables
        self.array_variables = saved_array_variables
        self.record_variables = saved_record_variables
        self.enum_variables = saved_enum_variables
        self.current_function_return_type = saved_current_function_return_type
        self.const_variables = saved_const_variables

        self.module.functions.append(
            IRFunctionDefinition(
                function_name,
                [IRFunctionParameter(parameter.type_name, parameter.name) for parameter in parameters],
                body,
                return_type,
            )
        )
        return function_name

    def _lower_for_loop(self, statement: ForStatement) -> IRForLoop:
        initializer_instructions = self._lower_statement(statement.initializer)
        if len(initializer_instructions) != 1 or not isinstance(initializer_instructions[0], (IRDeclareInt, IRAssignInt)):
            raise TypeError("For-loop initializer must lower to a single int instruction")
        loop_variable_name: str | None = None
        if isinstance(statement.initializer, VariableDeclaration):
            loop_variable_name = statement.initializer.name
        elif isinstance(statement.initializer, Assignment):
            loop_variable_name = statement.initializer.name
        if loop_variable_name is not None:
            self.int_constants.pop(loop_variable_name, None)
            self.bool_variables.pop(loop_variable_name, None)
            self.string_variables.pop(loop_variable_name, None)
            self.array_variables.pop(loop_variable_name, None)
            self.record_variables.pop(loop_variable_name, None)
        base_variable_types = self.variable_types.copy()
        base_int_constants = self.int_constants.copy()
        base_bool_variables = self.bool_variables.copy()
        base_string_variables = self.string_variables.copy()
        base_number_variables = self.number_variables.copy()
        base_array_variables = self.array_variables.copy()
        base_record_variables = self.record_variables.copy()
        base_enum_variables = self.enum_variables.copy()
        base_const_variables = self.const_variables.copy()
        body_instructions = []
        self.loop_depth += 1
        try:
            for body_statement in statement.body:
                self._invalidate_assigned_bindings(body_statement)
                body_instructions.extend(self._lower_statement(body_statement))
        finally:
            self.loop_depth -= 1
        self._invalidate_assigned_bindings(statement.update)
        update_instructions = self._lower_assignment(statement.update)
        if len(update_instructions) != 1 or not isinstance(update_instructions[0], IRAssignInt):
            raise TypeError("For-loop update must lower to a single int assignment")
        self.int_constants = self._restore_runtime_bindings(
            base_variable_types, base_int_constants, self.int_constants, lambda type_name: type_name == "int"
        )
        self.bool_variables = self._restore_runtime_bindings(
            base_variable_types, base_bool_variables, self.bool_variables, lambda type_name: type_name == "bool"
        )
        self.string_variables = self._restore_runtime_bindings(
            base_variable_types, base_string_variables, self.string_variables, lambda type_name: type_name == "string"
        )
        self.number_variables = self._restore_runtime_bindings(
            base_variable_types, base_number_variables, self.number_variables, lambda type_name: type_name == "num"
        )
        self.array_variables = self._restore_runtime_bindings(
            base_variable_types, base_array_variables, self.array_variables, self._is_array_type
        )
        self.record_variables = self._restore_runtime_bindings(
            base_variable_types, base_record_variables, self.record_variables, lambda type_name: type_name in self.record_types
        )
        self.enum_variables = self._restore_runtime_bindings(
            base_variable_types, base_enum_variables, self.enum_variables, lambda type_name: type_name in self.enum_types
        )
        self.const_variables = base_const_variables
        return IRForLoop(
            initializer_instructions[0],
            self._lower_condition(statement.condition),
            update_instructions[0],
            body_instructions,
        )

    def _lower_while_statement(self, statement: WhileStatement) -> IRWhileLoop:
        base_variable_types = self.variable_types.copy()
        base_int_constants = self.int_constants.copy()
        base_bool_variables = self.bool_variables.copy()
        base_string_variables = self.string_variables.copy()
        base_number_variables = self.number_variables.copy()
        base_array_variables = self.array_variables.copy()
        base_record_variables = self.record_variables.copy()
        base_enum_variables = self.enum_variables.copy()
        base_const_variables = self.const_variables.copy()
        body_instructions: list = []
        self.loop_depth += 1
        try:
            for body_statement in statement.body:
                self._invalidate_assigned_bindings(body_statement)
                body_instructions.extend(self._lower_statement(body_statement))
        finally:
            self.loop_depth -= 1
        loop_int_constants = self.int_constants.copy()
        loop_bool_variables = self.bool_variables.copy()
        loop_string_variables = self.string_variables.copy()
        loop_number_variables = self.number_variables.copy()
        loop_array_variables = self.array_variables.copy()
        loop_record_variables = self.record_variables.copy()
        loop_enum_variables = self.enum_variables.copy()
        self.variable_types = base_variable_types
        self.int_constants = self._restore_runtime_bindings(
            base_variable_types, base_int_constants, loop_int_constants, lambda type_name: type_name == "int"
        )
        self.bool_variables = self._restore_runtime_bindings(
            base_variable_types, base_bool_variables, loop_bool_variables, lambda type_name: type_name == "bool"
        )
        self.string_variables = self._restore_runtime_bindings(
            base_variable_types, base_string_variables, loop_string_variables, lambda type_name: type_name == "string"
        )
        self.number_variables = self._restore_runtime_bindings(
            base_variable_types, base_number_variables, loop_number_variables, lambda type_name: type_name == "num"
        )
        self.array_variables = self._restore_runtime_bindings(
            base_variable_types, base_array_variables, loop_array_variables, self._is_array_type
        )
        self.record_variables = self._restore_runtime_bindings(
            base_variable_types, base_record_variables, loop_record_variables, lambda type_name: type_name in self.record_types
        )
        self.enum_variables = self._restore_runtime_bindings(
            base_variable_types, base_enum_variables, loop_enum_variables, lambda type_name: type_name in self.enum_types
        )
        self.const_variables = base_const_variables
        return IRWhileLoop(self._lower_condition(statement.condition), body_instructions)

    def _lower_switch_statement(self, statement: SwitchStatement) -> list:
        selector_type = self._expression_type(statement.expression)
        if selector_type not in {"int", "string"} and selector_type not in self.enum_types:
            raise TypeError("switch supports only int, string, and enum expressions")
        for case in statement.cases:
            case_type = self._expression_type(case.value)
            if case_type != selector_type:
                raise TypeError(f"Switch case type mismatch: expected {selector_type}, got {case_type}")
        if not statement.cases:
            lowered: list = []
            for body_statement in statement.default_body:
                lowered.extend(self._lower_statement(body_statement))
            return lowered
        current_else = statement.default_body
        chained_statement: IfStatement | None = None
        for case in reversed(statement.cases):
            chained_statement = IfStatement(
                BinaryExpression(statement.expression, "==", case.value),
                case.body,
                current_else,
            )
            current_else = [chained_statement]
        if chained_statement is None:
            return []
        return [self._lower_if_statement(chained_statement)]

    def _lower_if_statement(self, statement: IfStatement) -> IRIf:
        constant_condition = self._boolean_constant_value(statement.condition)
        if constant_condition is not None and (
            not isinstance(statement.condition, BinaryExpression) or statement.condition.operator in {"&&", "||"}
        ):
            selected_body = statement.then_body if constant_condition else statement.else_body
            selected_instructions: list = []
            for body_statement in selected_body:
                selected_instructions.extend(self._lower_statement(body_statement))
            if constant_condition:
                return IRIf(IRComparison(IRInteger(1), "==", IRInteger(1)), selected_instructions, [])
            return IRIf(IRComparison(IRInteger(0), "==", IRInteger(1)), [], selected_instructions)

        condition = self._lower_condition(statement.condition)
        base_variable_types = self.variable_types.copy()
        base_int_constants = self.int_constants.copy()
        base_bool_variables = self.bool_variables.copy()
        base_string_variables = self.string_variables.copy()
        base_number_variables = self.number_variables.copy()
        base_array_variables = self.array_variables.copy()
        base_record_variables = self.record_variables.copy()
        base_enum_variables = self.enum_variables.copy()
        base_const_variables = self.const_variables.copy()

        then_instructions: list = []
        for body_statement in statement.then_body:
            then_instructions.extend(self._lower_statement(body_statement))
        then_int_constants = self.int_constants.copy()
        then_bool_variables = self.bool_variables.copy()
        then_string_variables = self.string_variables.copy()
        then_number_variables = self.number_variables.copy()
        then_array_variables = self.array_variables.copy()
        then_record_variables = self.record_variables.copy()
        then_enum_variables = self.enum_variables.copy()

        self.variable_types = base_variable_types.copy()
        self.int_constants = base_int_constants.copy()
        self.bool_variables = base_bool_variables.copy()
        self.string_variables = base_string_variables.copy()
        self.number_variables = base_number_variables.copy()
        self.array_variables = base_array_variables.copy()
        self.record_variables = base_record_variables.copy()
        self.enum_variables = base_enum_variables.copy()
        self.const_variables = base_const_variables.copy()

        else_instructions: list = []
        for body_statement in statement.else_body:
            else_instructions.extend(self._lower_statement(body_statement))
        else_int_constants = self.int_constants.copy()
        else_bool_variables = self.bool_variables.copy()
        else_string_variables = self.string_variables.copy()
        else_number_variables = self.number_variables.copy()
        else_array_variables = self.array_variables.copy()
        else_record_variables = self.record_variables.copy()
        else_enum_variables = self.enum_variables.copy()

        self.variable_types = base_variable_types
        self.int_constants = base_int_constants
        self.bool_variables = base_bool_variables
        self.string_variables = base_string_variables
        self.number_variables = base_number_variables
        self.array_variables = base_array_variables
        self.record_variables = base_record_variables
        self.enum_variables = base_enum_variables
        self.const_variables = base_const_variables

        if self._contains_file_instruction(then_instructions) or self._contains_file_instruction(else_instructions):
            raise TypeError("If statements do not yet support file declarations or writes")
        self.int_constants = self._merge_if_int_constants(base_int_constants, then_int_constants, else_int_constants)
        self.bool_variables = self._merge_if_bindings(base_variable_types, "bool", base_bool_variables, then_bool_variables, else_bool_variables)
        self.string_variables = self._merge_if_bindings(base_variable_types, "string", base_string_variables, then_string_variables, else_string_variables)
        self.number_variables = self._merge_if_bindings(base_variable_types, "num", base_number_variables, then_number_variables, else_number_variables)
        self.array_variables = self._merge_if_bindings(base_variable_types, self._is_array_type, base_array_variables, then_array_variables, else_array_variables)
        self.record_variables = self._merge_if_bindings(
            base_variable_types, lambda type_name: type_name in self.record_types, base_record_variables, then_record_variables, else_record_variables
        )
        self.enum_variables = self._merge_if_bindings(
            base_variable_types, lambda type_name: type_name in self.enum_types, base_enum_variables, then_enum_variables, else_enum_variables
        )
        return IRIf(condition, then_instructions, else_instructions)

    def _lower_continue_statement(self, statement: ContinueStatement) -> IRContinue:
        if self.loop_depth <= 0:
            raise TypeError("continue is only allowed inside loops")
        return IRContinue()

    def _lower_break_statement(self, statement: BreakStatement) -> IRBreak:
        if self.loop_depth <= 0:
            raise TypeError("break is only allowed inside loops")
        return IRBreak()

    def _lower_try_catch_statement(self, statement: TryCatchStatement) -> IRTryCatch:
        try_body: list = []
        for body_statement in statement.try_body:
            try_body.extend(self._lower_statement(body_statement))

        saved_variable_types = self.variable_types.copy()
        saved_bool_variables = self.bool_variables.copy()
        saved_string_variables = self.string_variables.copy()
        saved_number_variables = self.number_variables.copy()
        saved_array_variables = self.array_variables.copy()
        saved_record_variables = self.record_variables.copy()
        saved_enum_variables = self.enum_variables.copy()
        saved_runtime_bound_variables = self.runtime_bound_variables.copy()
        saved_const_variables = self.const_variables.copy()

        catch_body: list = []
        self.variable_types[statement.catch_name] = "string"
        for body_statement in statement.catch_body:
            catch_body.extend(self._lower_statement(body_statement))

        self.variable_types = saved_variable_types
        self.bool_variables = saved_bool_variables
        self.string_variables = saved_string_variables
        self.number_variables = saved_number_variables
        self.array_variables = saved_array_variables
        self.record_variables = saved_record_variables
        self.enum_variables = saved_enum_variables
        self.runtime_bound_variables = saved_runtime_bound_variables
        self.const_variables = saved_const_variables
        return IRTryCatch(statement.catch_name, try_body, catch_body)

    def _expression_type(self, expression, expected_type: str | None = None) -> str:
        if isinstance(expression, StringLiteral):
            return "string"
        if isinstance(expression, IntegerLiteral):
            return "int"
        if isinstance(expression, BooleanLiteral):
            return "bool"
        if isinstance(expression, NumberLiteral):
            return "num"
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "create_prio_q":
                if len(expression.arguments) != 2:
                    raise TypeError("create_prio_q requires an array and a comparator")
                source_type = argument_types[0]
                if not self._is_array_type(source_type):
                    raise TypeError(f"create_prio_q requires an array, got {source_type}")
                item_type = self._array_item_type(source_type)
                self._validate_priority_queue_comparator(expression.arguments[1], item_type)
                return f"prio_q<{item_type}>"
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                return "int"
            return resolve_builtin(expression.name, argument_types).return_type
        if isinstance(expression, LambdaExpression):
            local_types = self.variable_types.copy()
            local_types[expression.parameter_name] = expression.parameter_type
            return f"lambda<{expression.parameter_type},{self._lambda_return_type(expression, local_types)}>"
        if isinstance(expression, MultiLambdaExpression):
            local_types = self.variable_types.copy()
            for parameter in expression.parameters:
                local_types[parameter.name] = parameter.type_name
            parameter_types = ", ".join(parameter.type_name for parameter in expression.parameters)
            return f"lambda<{parameter_types},{self._callable_return_type(expression.parameters, expression.body, local_types)}>"
        if isinstance(expression, FunctionCallExpression):
            signature = self.function_signatures.get(expression.name)
            if signature is None:
                raise TypeError(f"Unknown function: {expression.name}")
            if len(expression.arguments) != len(signature):
                raise TypeError(f"Argument mismatch for function {expression.name}: expected {signature}, got {len(expression.arguments)} arguments")
            argument_types = tuple(
                self._expression_type(argument, arg_type)
                for argument, arg_type in zip(expression.arguments, signature, strict=True)
            )
            if expression.name == "union" and argument_types == ("set<int>", "set<int>"):
                return "set<int>"
            if argument_types != signature:
                raise TypeError(f"Argument mismatch for function {expression.name}: expected {signature}, got {argument_types}")
            return self.function_return_types.get(expression.name, "void")
        if isinstance(expression, Identifier):
            variable_type = self.variable_types.get(expression.name)
            if variable_type is None:
                raise TypeError(f"Unknown variable: {expression.name}")
            return variable_type
        if isinstance(expression, TernaryExpression):
            if self._expression_type(expression.condition) != "bool":
                raise TypeError("Ternary condition must be boolean")
            true_type = self._expression_type(expression.when_true, expected_type)
            false_type = self._expression_type(expression.when_false, expected_type)
            if true_type != false_type:
                raise TypeError(f"Ternary branches must have matching types, got {true_type} and {false_type}")
            return true_type
        if isinstance(expression, UnaryExpression):
            operand_type = self._expression_type(expression.operand)
            if expression.operator == "!" and operand_type == "bool":
                return "bool"
            raise TypeError(f"Unsupported unary operator {expression.operator} for {operand_type}")
        if isinstance(expression, ArrayLiteral):
            if not expression.items and expected_type is not None and self._is_array_type(expected_type):
                return expected_type
            array = self._coerce_array_value(expression)
            return f"{array.item_type}[]"
        if isinstance(expression, SetLiteral):
            if not expression.items:
                raise TypeError("Cannot infer type of empty set literal")
            item_type = self._expression_type(expression.items[0])
            for item in expression.items[1:]:
                if self._expression_type(item) != item_type:
                    raise TypeError("Set literal entries must have consistent item types")
            return f"set<{item_type}>"
        if isinstance(expression, MapLiteral):
            if not expression.items and expected_type is not None and self._is_map_type(expected_type):
                return expected_type
            if not expression.items:
                raise TypeError("Cannot infer type of empty map literal")
            key_type = self._expression_type(expression.items[0][0])
            value_type = self._expression_type(expression.items[0][1])
            for key, value in expression.items[1:]:
                if self._expression_type(key) != key_type or self._expression_type(value) != value_type:
                    raise TypeError("Map literal entries must have consistent key and value types")
            return f"map<{key_type},{value_type}>"
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type(expression.target)
            if target_type == "string":
                if self._expression_type(expression.index) != "int":
                    raise TypeError("String index must be an int")
                return "string"
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if self._expression_type(expression.index) != key_type:
                    raise TypeError(f"Map key must be {key_type}")
                return value_type
            if not target_type.endswith("[]"):
                raise TypeError(f"Expected array expression, got {target_type}")
            if self._expression_type(expression.index) != "int":
                raise TypeError("Array index must be an int")
            return target_type.removesuffix("[]")
        if isinstance(expression, ConstructorCall):
            if expression.type_name not in self.record_types:
                raise TypeError(f"Unknown record type: {expression.type_name}")
            return expression.type_name
        if isinstance(expression, FieldAccess):
            if isinstance(expression.target, Identifier) and expression.target.name in self.enum_types:
                if expression.field_name not in self.enum_types[expression.target.name]:
                    raise TypeError(f"Unknown enum member {expression.field_name!r} on {expression.target.name}")
                return expression.target.name
            record_type, field_name = self._resolve_field_metadata(expression)
            field_type = self.record_types[record_type].get(field_name)
            if field_type is None:
                raise TypeError(f"Unknown field {field_name!r} on {record_type}")
            return field_type
        if isinstance(expression, BinaryExpression):
            left_type = self._expression_type(expression.left)
            right_type = self._expression_type(expression.right)
            if expression.operator in {"in", "not in"}:
                self._membership_overload(left_type, right_type)
                return "bool"
            if expression.operator in {"&&", "||"} and left_type == "bool" and right_type == "bool":
                return "bool"
            if left_type == "bool" and right_type == "bool" and expression.operator in {"==", "!="}:
                return "bool"
            if left_type == "int" and right_type == "int" and expression.operator in {"==", "!=", "<", "<=", ">", ">="}:
                return "bool"
            if left_type == "string" and right_type == "string" and expression.operator in {"==", "!="}:
                return "bool"
            if left_type in self.enum_types and right_type == left_type and expression.operator in {"==", "!="}:
                return "bool"
            if expression.operator == "+" and {left_type, right_type}.issubset({"string", "int", "num"}) and "string" in {left_type, right_type}:
                return "string"
            if expression.operator in {"+", "-", "*", "/"} and {left_type, right_type}.issubset({"int", "num"}) and "num" in {left_type, right_type}:
                return "num"
            if left_type == "int" and right_type == "int" and expression.operator in {"+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"}:
                return "int"
            raise TypeError(f"Unsupported operand types for {expression.operator}: {left_type}, {right_type}")
        raise TypeError(f"Unsupported expression node: {type(expression).__name__}")

    def _lower_integer_expression(self, expression):
        if isinstance(expression, IntegerLiteral):
            return IRInteger(expression.value)
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != "int":
                raise TypeError(f"Expected int variable: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is not None:
                return self._lower_integer_expression(expression.when_true if condition else expression.when_false)
            return IRSelect(
                self._lower_condition(expression.condition),
                self._lower_integer_expression(expression.when_true),
                self._lower_integer_expression(expression.when_false),
                "int",
            )
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    "hash",
                    [IRCallArgument("string", self._lower_enum_expression(expression.arguments[0], argument_types[0]))],
                    "int",
                    builtin=True,
                )
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "to_int" and overload.lowering == "to_int":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression("to_int", [self._lower_call_argument(expression.arguments[0], "string")], "int", builtin=True)
            if expression.name == "hash" and overload.lowering in {"hash_int", "hash_num", "hash_string"}:
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    "hash",
                    [self._lower_call_argument(expression.arguments[0], argument_types[0])],
                    "int",
                    builtin=True,
                )
            if expression.name == "index_of" and overload.lowering == "index_of":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    "index_of",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                    ],
                    "int",
                    builtin=True,
                )
            if expression.name == "length" and overload.lowering == "string_length":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression("length", [self._lower_call_argument(expression.arguments[0], "string")], "int", builtin=True)
            if expression.name == "length" and overload.lowering == "array_length":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                array_type = self._expression_type(expression.arguments[0])
                return IRArrayLength(
                    self._lower_array_expression(expression.arguments[0], array_type),
                    self._array_item_type(array_type),
                )
            if expression.name == "length" and overload.lowering == "set_length":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                set_type = self._expression_type(expression.arguments[0])
                return IRArrayLength(
                    self._lower_set_expression(expression.arguments[0], set_type),
                    self._set_item_type(set_type),
                )
            if expression.name == "length" and overload.lowering == "map_length":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                map_type = self._expression_type(expression.arguments[0])
                return IRCallExpression(
                    "length",
                    [self._lower_call_argument(expression.arguments[0], map_type)],
                    "int",
                    builtin=True,
                )
            if expression.name == "last" and overload.lowering == "last_array":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return self._lower_last_array_value(expression, "int")
            if expression.name == "sum" and overload.lowering in {"sum_int_array", "sum_bool_array"}:
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    "sum",
                    [self._lower_call_argument(expression.arguments[0], argument_types[0])],
                    "int",
                    builtin=True,
                )
            if expression.name == "abs" and overload.lowering == "abs_int":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    "abs",
                    [self._lower_call_argument(expression.arguments[0], "int")],
                    "int",
                    builtin=True,
                )
            if expression.name == "popcount" and overload.lowering == "popcount_int":
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    "popcount",
                    [self._lower_call_argument(expression.arguments[0], "int")],
                    "int",
                    builtin=True,
                )
            if expression.name in {"min", "max"} and overload.lowering in {"min_int", "max_int"}:
                constant_value = self._integer_constant_value(expression)
                if constant_value is not None:
                    return IRInteger(constant_value)
                return IRCallExpression(
                    expression.name,
                    [
                        self._lower_call_argument(expression.arguments[0], "int"),
                        self._lower_call_argument(expression.arguments[1], "int"),
                    ],
                    "int",
                    builtin=True,
                )
            if expression.name == "pop" and overload.lowering == "array_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayPop(expression.arguments[0].name, overload.return_type)
            if expression.name == "pop" and overload.lowering == "prio_q_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires a priority queue variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                queue_type = self.variable_types.get(expression.arguments[0].name)
                if queue_type is None or not self._is_priority_queue_type(queue_type):
                    raise TypeError("pop requires a priority queue variable")
                return IRCallExpression(
                    "tb_pq_pop",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    overload.return_type,
                )
            if expression.name == "remove_at" and overload.lowering == "array_remove_at":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("remove_at requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayRemove(
                    expression.arguments[0].name,
                    overload.return_type,
                    self._lower_integer_expression(expression.arguments[1]),
                )
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != "int":
                raise TypeError(f"Expected int-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                "int",
            )
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type(expression.target)
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if value_type != "int":
                    raise TypeError(f"Expected int-valued map expression, got {target_type}")
                return IRMapIndex(
                    self._lower_map_expression(expression.target, target_type),
                    self._lower_typed_expression(expression.index, key_type),
                    key_type,
                    value_type,
                )
            constant_value = self._integer_constant_value(expression)
            if constant_value is not None:
                return IRInteger(constant_value)
            return IRArrayIndex(
                self._lower_array_expression(expression.target, target_type),
                self._lower_integer_expression(expression.index),
                "int",
            )
        if isinstance(expression, FieldAccess):
            constant_value = self._integer_constant_value(expression)
            if constant_value is not None:
                return IRInteger(constant_value)
            return self._lower_record_field_expression(expression, "int")
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "time_ms" and overload.lowering == "time_ms":
                return IRCallExpression("time_ms", [], "int", builtin=True)
        if isinstance(expression, BinaryExpression):
            if self._expression_type(expression) != "int":
                raise TypeError(f"Expected int expression for operator {expression.operator}")
            return IRBinaryOperation(
                self._lower_integer_expression(expression.left),
                expression.operator,
                self._lower_integer_expression(expression.right),
            )
        raise TypeError(f"Unsupported expression node: {type(expression).__name__}")

    def _lower_condition(self, expression) -> IRComparison:
        if self._expression_type(expression) != "bool":
            raise TypeError("Condition must be boolean")
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != "bool":
                raise TypeError(f"Expected bool variable: {expression.name}")
            constant_value = self._boolean_constant_value(expression)
            if constant_value is not None:
                return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
            return IRComparison(IRVariable(expression.name), "==", IRBoolean(True))
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != "bool":
                raise TypeError(f"Expected bool-returning function: {expression.name}")
            return IRComparison(
                IRCallExpression(
                    expression.name,
                    [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                    "bool",
                ),
                "==",
                IRBoolean(True),
            )
        if isinstance(expression, ArrayAccess):
            constant_value = self._boolean_constant_value(expression)
            if constant_value is not None:
                return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
            target_type = self._expression_type(expression.target)
            return IRComparison(
                IRArrayIndex(
                    self._lower_array_expression(expression.target, target_type),
                    self._lower_integer_expression(expression.index),
                    "bool",
                ),
                "==",
                IRBoolean(True),
            )
        if isinstance(expression, FieldAccess):
            constant_value = self._boolean_constant_value(expression)
            if constant_value is not None:
                return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
            return IRComparison(self._lower_record_field_expression(expression, "bool"), "==", IRBoolean(True))
        if isinstance(expression, BinaryExpression):
            if expression.operator == "in":
                return IRComparison(self._lower_membership_call(expression.left, expression.right), "==", IRBoolean(True))
            if expression.operator == "not in":
                return IRComparison(self._lower_membership_call(expression.left, expression.right), "==", IRBoolean(False))
            if expression.operator in {"&&", "||"}:
                return IRLogicalCondition(
                    self._lower_condition(expression.left),
                    expression.operator,
                    self._lower_condition(expression.right),
                )
            left_type = self._expression_type(expression.left)
            right_type = self._expression_type(expression.right)
            if (
                left_type == right_type
                and expression.operator in {"==", "!="}
                and (left_type == "string" or left_type in self.enum_types)
            ):
                constant_value = self._boolean_constant_value(expression)
                if constant_value is not None:
                    return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
                return IRComparison(
                    IRCallExpression(
                        "strcmp",
                        [
                            IRCallArgument(
                                "string",
                                self._lower_string_expression(expression.left)
                                if left_type == "string"
                                else self._lower_enum_expression(expression.left, left_type),
                            ),
                            IRCallArgument(
                                "string",
                                self._lower_string_expression(expression.right)
                                if right_type == "string"
                                else self._lower_enum_expression(expression.right, right_type),
                            ),
                        ],
                        "int",
                        builtin=True,
                    ),
                    expression.operator,
                    IRInteger(0),
                )
            if left_type == "bool" and right_type == "bool" and expression.operator in {"==", "!="}:
                constant_value = self._boolean_constant_value(expression)
                if constant_value is not None:
                    return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
                return IRComparison(
                    IRSelect(self._lower_condition(expression.left), IRBoolean(True), IRBoolean(False), "bool"),
                    expression.operator,
                    IRSelect(self._lower_condition(expression.right), IRBoolean(True), IRBoolean(False), "bool"),
                )
            return IRComparison(
                self._lower_integer_expression(expression.left),
                expression.operator,
                self._lower_integer_expression(expression.right),
            )
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                value = self._enum_constant_value(expression.arguments[0], argument_types[0])
                if value is None:
                    return None
                return self._hash_string_value(value)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "is_empty" and overload.lowering == "is_empty":
                constant_value = self._boolean_constant_value(expression)
                if constant_value is not None:
                    return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
                container_type = argument_types[0]
                if container_type == "string":
                    return IRComparison(
                        IRCallExpression("length", [self._lower_call_argument(expression.arguments[0], "string")], "int", builtin=True),
                        "==",
                        IRInteger(0),
                    )
                if self._is_array_type(container_type):
                    return IRComparison(
                        IRArrayLength(
                            self._lower_array_expression(expression.arguments[0], container_type),
                            self._array_item_type(container_type),
                        ),
                        "==",
                        IRInteger(0),
                    )
                if self._is_set_type(container_type):
                    return IRComparison(
                        IRArrayLength(
                            self._lower_set_expression(expression.arguments[0], container_type),
                            self._set_item_type(container_type),
                        ),
                        "==",
                        IRInteger(0),
                    )
                return IRComparison(
                    IRCallExpression("length", [self._lower_call_argument(expression.arguments[0], container_type)], "int", builtin=True),
                    "==",
                    IRInteger(0),
                )
            if expression.name == "is_empty" and overload.lowering == "prio_q_is_empty":
                queue_type = argument_types[0]
                return IRComparison(
                    IRCallExpression(
                        "tb_pq_is_empty",
                        [self._lower_call_argument(expression.arguments[0], queue_type)],
                        "bool",
                    ),
                    "==",
                    IRBoolean(True),
                )
            if expression.name == "contains" and overload.lowering == "contains":
                constant_value = self._boolean_constant_value(expression)
                if constant_value is not None:
                    return IRComparison(IRInteger(1 if constant_value else 0), "==", IRInteger(1))
                return IRComparison(
                    IRCallExpression(
                        "index_of",
                        [
                            self._lower_call_argument(expression.arguments[0], "string"),
                            self._lower_call_argument(expression.arguments[1], "string"),
                        ],
                        "int",
                        builtin=True,
                    ),
                    "!=",
                    IRInteger(-1),
                )
            if expression.name == "contains" and overload.lowering in {
                "array_contains_int",
                "array_contains_string",
                "array_contains_bool",
                "set_contains",
                "map_contains_key_string_int",
                "map_contains_key",
            }:
                return IRComparison(
                    IRCallExpression(
                        "contains",
                        [
                            self._lower_call_argument(expression.arguments[0], argument_types[0]),
                            self._lower_call_argument(expression.arguments[1], argument_types[1]),
                        ],
                        "bool",
                        builtin=True,
                    ),
                    "==",
                    IRBoolean(True),
                )
            if expression.name in {"starts_with", "ends_with", "starts_with_at", "is_digit", "is_alpha", "is_alnum", "is_whitespace", "is_space", "has_flag"}:
                constant_value = self._boolean_constant_value(expression)
                if constant_value is not None:
                    return IRComparison(IRBoolean(constant_value), "==", IRBoolean(True))
                if expression.name == "starts_with":
                    return IRComparison(
                        IRCallExpression(
                            "starts_with",
                            [
                                self._lower_call_argument(expression.arguments[0], "string"),
                                self._lower_call_argument(expression.arguments[1], "string"),
                            ],
                            "bool",
                            builtin=True,
                        ),
                        "==",
                        IRBoolean(True),
                    )
                if expression.name == "ends_with":
                    return IRComparison(
                        IRCallExpression(
                            "ends_with",
                            [
                                self._lower_call_argument(expression.arguments[0], "string"),
                                self._lower_call_argument(expression.arguments[1], "string"),
                            ],
                            "bool",
                            builtin=True,
                        ),
                        "==",
                        IRBoolean(True),
                    )
                if expression.name == "starts_with_at":
                    return IRComparison(
                        IRCallExpression(
                            "starts_with_at",
                            [
                                self._lower_call_argument(expression.arguments[0], "string"),
                                self._lower_call_argument(expression.arguments[1], "string"),
                                self._lower_call_argument(expression.arguments[2], "int"),
                            ],
                            "bool",
                            builtin=True,
                        ),
                        "==",
                        IRBoolean(True),
                    )
                if expression.name == "has_flag":
                    return IRComparison(
                        IRCallExpression(
                            "has_flag",
                            [
                                self._lower_call_argument(expression.arguments[0], "string[]"),
                                self._lower_call_argument(expression.arguments[1], "string"),
                            ],
                            "bool",
                            builtin=True,
                        ),
                        "==",
                        IRBoolean(True),
                    )
                runtime_name = "is_whitespace" if expression.name == "is_space" else expression.name
                return IRComparison(
                    IRCallExpression(
                        runtime_name,
                        [self._lower_call_argument(expression.arguments[0], "string")],
                        "bool",
                        builtin=True,
                    ),
                    "==",
                    IRBoolean(True),
                )
        if isinstance(expression, UnaryExpression) and expression.operator == "!":
            return self._negate_condition(self._lower_condition(expression.operand))
        value = self._boolean_constant_value(expression)
        if value is None:
            raise TypeError("Condition must be compile-time evaluable")
        return IRComparison(IRInteger(1 if value else 0), "==", IRInteger(1))

    def _lower_boolean_expression(self, expression):
        constant_value = self._boolean_constant_value(expression)
        if constant_value is not None:
            return IRBoolean(constant_value)
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != "bool":
                raise TypeError(f"Expected bool variable: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != "bool":
                raise TypeError(f"Expected bool-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                "bool",
            )
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is not None:
                return self._lower_boolean_expression(expression.when_true if condition else expression.when_false)
            return IRSelect(
                self._lower_condition(expression.condition),
                self._lower_boolean_expression(expression.when_true),
                self._lower_boolean_expression(expression.when_false),
                "bool",
            )
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                value = self._enum_constant_value(expression.arguments[0], argument_types[0])
                if value is None:
                    return None
                return self._hash_string_value(value)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name in {"starts_with", "ends_with"} and overload.lowering in {"starts_with", "ends_with"}:
                return IRCallExpression(
                    expression.name,
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                    ],
                    "bool",
                    builtin=True,
                )
            if expression.name == "contains" and overload.lowering in {
                "array_contains_int",
                "array_contains_string",
                "array_contains_bool",
                "set_contains",
                "map_contains_key_string_int",
                "map_contains_key",
            }:
                return IRCallExpression(
                    "contains",
                    [
                        self._lower_call_argument(expression.arguments[0], argument_types[0]),
                        self._lower_call_argument(expression.arguments[1], argument_types[1]),
                    ],
                    "bool",
                    builtin=True,
                )
            if expression.name == "starts_with_at" and overload.lowering == "starts_with_at":
                return IRCallExpression(
                    "starts_with_at",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                        self._lower_call_argument(expression.arguments[2], "int"),
                    ],
                    "bool",
                    builtin=True,
                )
            if expression.name == "has_flag" and overload.lowering == "has_flag":
                return IRCallExpression(
                    "has_flag",
                    [
                        self._lower_call_argument(expression.arguments[0], "string[]"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                    ],
                    "bool",
                    builtin=True,
                )
            if expression.name == "is_empty" and overload.lowering == "prio_q_is_empty":
                queue_type = argument_types[0]
                return IRCallExpression(
                    "tb_pq_is_empty",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    "bool",
                )
            if expression.name == "is_empty" and overload.lowering == "is_empty":
                return IRComparison(
                    self._lower_integer_expression(BuiltinCallExpression("length", [expression.arguments[0]])),
                    "==",
                    IRInteger(0),
                )
            if expression.name in {"is_digit", "is_alpha", "is_alnum", "is_whitespace", "is_space"} and overload.lowering in {"is_digit", "is_alpha", "is_alnum", "is_whitespace", "is_space"}:
                return IRCallExpression(
                    "is_whitespace" if expression.name == "is_space" else expression.name,
                    [self._lower_call_argument(expression.arguments[0], "string")],
                    "bool",
                    builtin=True,
                )
            if expression.name == "pop" and overload.lowering == "array_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayPop(expression.arguments[0].name, overload.return_type)
            if expression.name == "pop" and overload.lowering == "prio_q_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires a priority queue variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                queue_type = self.variable_types.get(expression.arguments[0].name)
                if queue_type is None or not self._is_priority_queue_type(queue_type):
                    raise TypeError("pop requires a priority queue variable")
                return IRCallExpression(
                    "tb_pq_pop",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    overload.return_type,
                )
            if expression.name == "remove_at" and overload.lowering == "array_remove_at":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("remove_at requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayRemove(
                    expression.arguments[0].name,
                    overload.return_type,
                    self._lower_integer_expression(expression.arguments[1]),
                )
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type(expression.target)
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if value_type != "bool":
                    raise TypeError(f"Expected bool-valued map expression, got {target_type}")
                return IRMapIndex(
                    self._lower_map_expression(expression.target, target_type),
                    self._lower_typed_expression(expression.index, key_type),
                    key_type,
                    value_type,
                )
            return IRArrayIndex(
                self._lower_array_expression(expression.target, target_type),
                self._lower_integer_expression(expression.index),
                "bool",
            )
        if isinstance(expression, FieldAccess):
            return self._lower_record_field_expression(expression, "bool")
        if self._expression_type(expression) == "bool":
            return IRSelect(self._lower_condition(expression), IRBoolean(True), IRBoolean(False), "bool")
        raise TypeError(f"Unsupported bool expression node: {type(expression).__name__}")

    def _lower_string_expression(self, expression):
        constant_value = self._string_constant_value(expression)
        if constant_value is not None:
            return self._string_literal(constant_value)
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != "string":
                raise TypeError(f"Expected string variable: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                value = self._enum_constant_value(expression.arguments[0], argument_types[0])
                if value is None:
                    return None
                return self._hash_string_value(value)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "to_string":
                argument_type = argument_types[0]
                if argument_type == "string":
                    return self._lower_string_expression(expression.arguments[0])
                if argument_type == "int":
                    constant_value = self._string_constant_value(expression)
                    if constant_value is not None:
                        return self._string_literal(constant_value)
                    return IRIntToString(self._lower_integer_expression(expression.arguments[0]))
                if argument_type == "num":
                    return self._lower_number_expression(expression.arguments[0])
                if argument_type == "bool":
                    constant_value = self._boolean_constant_value(expression.arguments[0])
                    if constant_value is not None:
                        return self._string_literal("true" if constant_value else "false")
                    return IRSelect(
                        self._lower_condition(expression.arguments[0]),
                        self._string_literal("true"),
                        self._string_literal("false"),
                        "string",
                    )
                if argument_type == "int[]":
                    constant_value = self._array_constant_value(expression.arguments[0], "int[]")
                    if constant_value is not None:
                        try:
                            return self._string_literal(self._format_int_array_value(constant_value))
                        except TypeError:
                            pass
                    return IRCallExpression(
                        "array_to_string_int",
                        [IRCallArgument("int[]", self._lower_array_expression(expression.arguments[0], "int[]"))],
                        "string",
                        builtin=True,
                    )
                if argument_type == "string[]":
                    constant_value = self._array_constant_value(expression.arguments[0], "string[]")
                    if constant_value is not None:
                        try:
                            return self._string_literal(self._format_string_array_value(constant_value))
                        except TypeError:
                            pass
                    return IRCallExpression(
                        "array_to_string_string",
                        [IRCallArgument("string[]", self._lower_array_expression(expression.arguments[0], "string[]"))],
                        "string",
                        builtin=True,
                    )
                if argument_type == "bool[]":
                    constant_value = self._array_constant_value(expression.arguments[0], "bool[]")
                    if constant_value is not None:
                        try:
                            return self._string_literal(self._format_bool_array_value(constant_value))
                        except TypeError:
                            pass
                    return IRCallExpression(
                        "array_to_string_bool",
                        [IRCallArgument("bool[]", self._lower_array_expression(expression.arguments[0], "bool[]"))],
                        "string",
                        builtin=True,
                    )
                if argument_type == "set<int>":
                    return IRCallExpression(
                        "tb_int_set_to_string",
                        [IRCallArgument("set<int>", self._lower_set_expression(expression.arguments[0], "set<int>"))],
                        "string",
                    )
            if expression.name == "pop" and overload.lowering == "array_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayPop(expression.arguments[0].name, overload.return_type)
            if expression.name == "pop" and overload.lowering == "prio_q_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires a priority queue variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                queue_type = self.variable_types.get(expression.arguments[0].name)
                if queue_type is None or not self._is_priority_queue_type(queue_type):
                    raise TypeError("pop requires a priority queue variable")
                return IRCallExpression(
                    "tb_pq_pop",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    overload.return_type,
                )
            if expression.name == "remove_at" and overload.lowering == "array_remove_at":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("remove_at requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayRemove(
                    expression.arguments[0].name,
                    overload.return_type,
                    self._lower_integer_expression(expression.arguments[1]),
                )
            if expression.name == "read_file" and overload.lowering == "read_file":
                constant_value = self._string_constant_value(expression)
                if constant_value is not None:
                    return self._string_literal(constant_value)
                return IRCallExpression("read_file", [self._lower_call_argument(expression.arguments[0], "string")], "string", builtin=True)
            if expression.name == "time_ms" and overload.lowering == "time_ms":
                return IRCallExpression("time_ms", [], "int", builtin=True)
            if expression.name == "trim" and overload.lowering == "trim_string":
                return IRCallExpression(
                    "trim",
                    [self._lower_call_argument(expression.arguments[0], "string")],
                    "string",
                    builtin=True,
                )
            if expression.name == "trim_left" and overload.lowering == "trim_left_string":
                return IRCallExpression(
                    "trim_left",
                    [self._lower_call_argument(expression.arguments[0], "string")],
                    "string",
                    builtin=True,
                )
            if expression.name == "trim_right" and overload.lowering == "trim_right_string":
                return IRCallExpression(
                    "trim_right",
                    [self._lower_call_argument(expression.arguments[0], "string")],
                    "string",
                    builtin=True,
                )
            if expression.name == "last" and overload.lowering == "last_string":
                return IRCallExpression(
                    "char_at",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_integer_expression(
                            BinaryExpression(BuiltinCallExpression("length", [expression.arguments[0]]), "-", IntegerLiteral(1))
                        ),
                    ],
                    "string",
                    builtin=True,
                )
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, "string")
            if expression.name == "substring" and overload.lowering in {"substring_from", "substring_range"}:
                return IRCallExpression(
                    "substring",
                    [self._lower_call_argument(argument, expected) for argument, expected in zip(expression.arguments, ("string", "int", "int"))][: len(expression.arguments)],
                    "string",
                    builtin=True,
                )
            if expression.name == "slice" and overload.lowering == "slice_string":
                return IRCallExpression(
                    "slice",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "int"),
                        self._lower_call_argument(expression.arguments[2], "int"),
                    ],
                    "string",
                    builtin=True,
                )
            if expression.name == "char_at" and overload.lowering == "char_at":
                return IRCallExpression(
                    "char_at",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "int"),
                    ],
                    "string",
                    builtin=True,
                )
            if expression.name == "replace" and overload.lowering == "replace_string":
                return IRCallExpression(
                    "replace",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                        self._lower_call_argument(expression.arguments[2], "string"),
                    ],
                    "string",
                    builtin=True,
                )
            if expression.name == "join" and overload.lowering == "join_strings":
                constant_value = self._string_constant_value(expression)
                if constant_value is not None:
                    return self._string_literal(constant_value)
                return IRCallExpression(
                    "join",
                    [
                        self._lower_call_argument(expression.arguments[0], "string[]"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                    ],
                    "string",
                    builtin=True,
                )
            if expression.name == "option_value" and overload.lowering == "option_value":
                constant_value = self._string_constant_value(expression)
                if constant_value is not None:
                    return self._string_literal(constant_value)
                return IRCallExpression(
                    "option_value",
                    [
                        self._lower_call_argument(expression.arguments[0], "string[]"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                    ],
                    "string",
                    builtin=True,
                )
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != "string":
                raise TypeError(f"Expected string-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                "string",
            )
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is not None:
                return self._lower_string_expression(expression.when_true if condition else expression.when_false)
            return IRSelect(
                self._lower_condition(expression.condition),
                self._lower_string_expression(expression.when_true),
                self._lower_string_expression(expression.when_false),
                "string",
            )
        if isinstance(expression, ArrayAccess):
            if self._expression_type(expression.target) == "string":
                index = self._integer_constant_value(expression.index)
                target_value = self._string_constant_value(expression.target)
                if target_value is not None and index is not None:
                    return self._lower_string_expression(self._resolve_indexed_value(expression))
                return IRStringIndex(
                    self._lower_string_expression(expression.target),
                    self._lower_integer_expression(expression.index),
                )
            constant_value = self._string_constant_value(expression)
            if constant_value is not None:
                return self._string_literal(constant_value)
            target_type = self._expression_type(expression.target)
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if value_type != "string":
                    raise TypeError(f"Expected string-valued map expression, got {target_type}")
                return IRMapIndex(
                    self._lower_map_expression(expression.target, target_type),
                    self._lower_typed_expression(expression.index, key_type),
                    key_type,
                    value_type,
                )
            return IRArrayIndex(
                self._lower_array_expression(expression.target, target_type),
                self._lower_integer_expression(expression.index),
                "string",
            )
        if isinstance(expression, FieldAccess):
            constant_value = self._string_constant_value(expression)
            if constant_value is not None:
                return self._string_literal(constant_value)
            return self._lower_record_field_expression(expression, "string")
        if isinstance(expression, BinaryExpression):
            if self._expression_type(expression) != "string":
                raise TypeError(f"Expected string expression for operator {expression.operator}")
            return IRStringConcat(self._lower_string_part(expression.left), self._lower_string_part(expression.right))
        raise TypeError(f"Unsupported string expression node: {type(expression).__name__}")

    def _lower_enum_expression(self, expression, expected_type: str):
        if expected_type not in self.enum_types:
            raise TypeError(f"Expected enum type, got {expected_type}")
        if self._expression_type(expression) != expected_type:
            raise TypeError(f"Expected enum expression of type {expected_type}")
        constant_value = self._enum_constant_value(expression, expected_type)
        if constant_value is not None:
            return self._string_literal(constant_value)
        if isinstance(expression, Identifier):
            return IRVariable(expression.name)
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "pop" and overload.lowering == "array_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayPop(expression.arguments[0].name, expected_type)
            if expression.name == "pop" and overload.lowering == "prio_q_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires a priority queue variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                queue_type = self.variable_types.get(expression.arguments[0].name)
                if queue_type is None or not self._is_priority_queue_type(queue_type):
                    raise TypeError("pop requires a priority queue variable")
                return IRCallExpression(
                    "tb_pq_pop",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    expected_type,
                )
            if expression.name == "remove_at" and overload.lowering == "array_remove_at":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("remove_at requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayRemove(
                    expression.arguments[0].name,
                    expected_type,
                    self._lower_integer_expression(expression.arguments[1]),
                )
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, expected_type)
        raise TypeError(f"Unsupported enum expression node: {type(expression).__name__}")

    def _lower_array_expression(self, expression, expected_type: str):
        constant_value = self._array_constant_value(expression, expected_type)
        if isinstance(expression, ArrayLiteral):
            item_type = self._array_item_type(expected_type)
            return IRArrayLiteral(
                item_type,
                [self._lower_typed_expression(item, item_type) for item in expression.items],
            )
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected array variable of type {expected_type}: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                value = self._enum_constant_value(expression.arguments[0], argument_types[0])
                if value is None:
                    return None
                return self._hash_string_value(value)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "pop" and overload.lowering == "array_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayPop(expression.arguments[0].name, expected_type)
            if expression.name == "pop" and overload.lowering == "prio_q_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires a priority queue variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                queue_type = self.variable_types.get(expression.arguments[0].name)
                if queue_type is None or not self._is_priority_queue_type(queue_type):
                    raise TypeError("pop requires a priority queue variable")
                return IRCallExpression(
                    "tb_pq_pop",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    expected_type,
                )
            if expression.name == "remove_at" and overload.lowering == "array_remove_at":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("remove_at requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayRemove(
                    expression.arguments[0].name,
                    expected_type,
                    self._lower_integer_expression(expression.arguments[1]),
                )
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, expected_type)
            if expression.name == "read_lines" and overload.lowering == "read_lines":
                if constant_value is not None:
                    return IRArrayLiteral("string", [self._lower_string_expression(item) for item in constant_value.items])
                return IRCallExpression("read_lines", [self._lower_call_argument(expression.arguments[0], "string")], "string[]", builtin=True)
            if expression.name == "split" and overload.lowering == "split_string":
                if constant_value is not None:
                    return IRArrayLiteral("string", [self._lower_string_expression(item) for item in constant_value.items])
                return IRCallExpression(
                    "split",
                    [
                        self._lower_call_argument(expression.arguments[0], "string"),
                        self._lower_call_argument(expression.arguments[1], "string"),
                    ],
                    "string[]",
                    builtin=True,
                )
            if expression.name == "split_lines" and overload.lowering == "split_lines":
                if constant_value is not None:
                    return IRArrayLiteral("string", [self._lower_string_expression(item) for item in constant_value.items])
                return IRCallExpression(
                    "split_lines",
                    [self._lower_call_argument(expression.arguments[0], "string")],
                    "string[]",
                    builtin=True,
                )
            if expression.name == "slice" and overload.lowering == "slice_array":
                array_type = argument_types[0]
                item_type = self._array_item_type(array_type)
                if constant_value is not None:
                    return IRArrayLiteral(item_type, [self._lower_typed_expression(item, item_type) for item in constant_value.items])
                return IRCallExpression(
                    "slice",
                    [
                        self._lower_call_argument(expression.arguments[0], array_type),
                        self._lower_call_argument(expression.arguments[1], "int"),
                        self._lower_call_argument(expression.arguments[2], "int"),
                    ],
                    array_type,
                    builtin=True,
                )
            if expression.name == "range" and overload.lowering in {"range_int", "range_int_int"}:
                if constant_value is not None:
                    return IRArrayLiteral("int", [self._lower_integer_expression(item) for item in constant_value.items])
                if overload.lowering == "range_int":
                    arguments = [self._lower_call_argument(expression.arguments[0], "int")]
                else:
                    arguments = [
                        self._lower_call_argument(expression.arguments[0], "int"),
                        self._lower_call_argument(expression.arguments[1], "int"),
                    ]
                return IRCallExpression(
                    "range",
                    arguments,
                    "int[]",
                    builtin=True,
                )
            if expression.name == "keys" and overload.lowering == "map_keys_string_int":
                map_type = argument_types[0]
                return IRCallExpression(
                    "keys",
                    [self._lower_call_argument(expression.arguments[0], map_type)],
                    overload.return_type,
                    builtin=True,
                )
            if expression.name == "values" and overload.lowering == "map_values_string_int":
                map_type = argument_types[0]
                return IRCallExpression(
                    "values",
                    [self._lower_call_argument(expression.arguments[0], map_type)],
                    overload.return_type,
                    builtin=True,
                )
            if expression.name == "keys" and overload.lowering == "map_keys":
                map_type = argument_types[0]
                return IRCallExpression(
                    "keys",
                    [self._lower_call_argument(expression.arguments[0], map_type)],
                    overload.return_type,
                    builtin=True,
                )
            if expression.name == "values" and overload.lowering == "map_values":
                map_type = argument_types[0]
                return IRCallExpression(
                    "values",
                    [self._lower_call_argument(expression.arguments[0], map_type)],
                    overload.return_type,
                    builtin=True,
                )
            if expression.name == "length" and overload.lowering == "map_length":
                map_type = argument_types[0]
                return IRCallExpression(
                    "length",
                    [self._lower_call_argument(expression.arguments[0], map_type)],
                    "int",
                    builtin=True,
                )
            if expression.name == "map_to" and overload.lowering == "map_array":
                lambda_expression = expression.arguments[1]
                if not isinstance(lambda_expression, LambdaExpression):
                    raise TypeError("map_to requires a lambda expression")
                source_array_type = argument_types[0]
                source_item_type = self._array_item_type(source_array_type)
                result_item_type = self._array_item_type(overload.return_type)
                body = self._lower_single_parameter_lambda_body(lambda_expression, source_item_type, result_item_type)
                return IRArrayMap(
                    self._lower_array_expression(expression.arguments[0], source_array_type),
                    source_item_type,
                    result_item_type,
                    lambda_expression.parameter_name,
                    body,
                )
            if expression.name == "flat_map" and overload.lowering == "flat_map_array":
                lambda_expression = expression.arguments[1]
                if not isinstance(lambda_expression, LambdaExpression):
                    raise TypeError("flat_map requires a lambda expression")
                source_array_type = argument_types[0]
                source_item_type = self._array_item_type(source_array_type)
                result_item_type = self._array_item_type(overload.return_type)
                body = self._lower_single_parameter_lambda_body(
                    lambda_expression,
                    source_item_type,
                    f"{result_item_type}[]",
                )
                return IRArrayCollect(
                    IRArrayMap(
                        self._lower_array_expression(expression.arguments[0], source_array_type),
                        source_item_type,
                        f"{result_item_type}[]",
                        lambda_expression.parameter_name,
                        body,
                    ),
                    result_item_type,
                )
            if expression.name == "filter" and overload.lowering == "filter_array":
                lambda_expression = expression.arguments[1]
                if not isinstance(lambda_expression, LambdaExpression):
                    raise TypeError("filter requires a lambda expression")
                source_array_type = argument_types[0]
                source_item_type = self._array_item_type(source_array_type)
                predicate = self._lower_single_parameter_lambda_body(lambda_expression, source_item_type, "bool")
                return IRArrayFilter(
                    self._lower_array_expression(expression.arguments[0], source_array_type),
                    source_item_type,
                    lambda_expression.parameter_name,
                    predicate,
                )
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected {expected_type}-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                expected_type,
            )
        if isinstance(expression, ArrayAccess):
            item_type = self._expression_type(expression)
            if item_type != expected_type:
                raise TypeError(f"Expected array item type {expected_type}, got {item_type}")
            target_type = self._expression_type(expression.target)
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                return IRMapIndex(
                    self._lower_map_expression(expression.target, target_type),
                    self._lower_typed_expression(expression.index, key_type),
                    key_type,
                    value_type,
                )
            return IRArrayIndex(
                self._lower_array_expression(expression.target, target_type),
                self._lower_integer_expression(expression.index),
                expected_type,
            )
        if isinstance(expression, FieldAccess):
            return self._lower_record_field_expression(expression, expected_type)
        raise TypeError(f"Unsupported array expression node: {type(expression).__name__}")

    def _lower_map_expression(self, expression, expected_type: str):
        key_type, value_type = self._map_parts(expected_type)
        if not self._is_cache_stringifiable_type(key_type):
            raise TypeError(f"Unsupported map key type: {key_type}")
        if not self._is_runtime_value_type(value_type):
            raise TypeError(f"Unsupported map value type: {value_type}")
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected map variable of type {expected_type}: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, MapLiteral):
            return IRMapLiteral(
                key_type,
                value_type,
                [(self._lower_typed_expression(key, key_type), self._lower_typed_expression(value, value_type)) for key, value in expression.items],
            )
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected {expected_type}-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                expected_type,
            )
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, expected_type)
        raise TypeError(f"Unsupported map expression node: {type(expression).__name__}")

    def _lower_set_expression(self, expression, expected_type: str):
        item_type = self._set_item_type(expected_type)
        if not self._is_cache_stringifiable_type(item_type):
            raise TypeError(f"Unsupported set item type: {item_type}")
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected set variable of type {expected_type}: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, SetLiteral):
            return IRSetLiteral(item_type, [self._lower_typed_expression(item, item_type) for item in expression.items])
        if isinstance(expression, MapLiteral) and not expression.items:
            return IRSetLiteral(item_type, [])
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "to_set" and overload.lowering == "to_set_int_array":
                return IRCallExpression(
                    "to_set",
                    [self._lower_call_argument(expression.arguments[0], "int[]")],
                    "set<int>",
                    builtin=True,
                )
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, expected_type)
        if isinstance(expression, FunctionCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "union" and argument_types == (expected_type, expected_type):
                return IRCallExpression(
                    "tb_set_union",
                    [
                        self._lower_call_argument(expression.arguments[0], expected_type),
                        self._lower_call_argument(expression.arguments[1], expected_type),
                    ],
                    expected_type,
                )
            if self.function_return_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected {expected_type}-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                expected_type,
            )
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type(expression.target)
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if value_type != expected_type:
                    raise TypeError(f"Expected {expected_type}-valued map expression, got {target_type}")
                return IRMapIndex(
                    self._lower_map_expression(expression.target, target_type),
                    self._lower_typed_expression(expression.index, key_type),
                    key_type,
                    value_type,
                )
        raise TypeError(f"Unsupported set expression node: {type(expression).__name__}")

    def _lower_record_expression(self, expression, expected_type: str):
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected record variable of type {expected_type}: {expression.name}")
            return IRVariable(expression.name)
        if isinstance(expression, ConstructorCall):
            if expression.type_name != expected_type:
                raise TypeError(f"Expected constructor {expected_type}, got {expression.type_name}")
            fields = self.record_types[expected_type]
            if len(expression.arguments) != len(fields):
                raise TypeError(f"Expected {len(fields)} constructor arguments for {expected_type}")
            lowered_fields: list[tuple[str, str, object]] = []
            for (field_name, field_type), argument in zip(fields.items(), expression.arguments, strict=True):
                lowered_fields.append((field_name, field_type, self._lower_typed_expression(argument, field_type)))
            return IRRecordConstruct(expected_type, lowered_fields)
        if isinstance(expression, FunctionCallExpression):
            if self.function_return_types.get(expression.name) != expected_type:
                raise TypeError(f"Expected {expected_type}-returning function: {expression.name}")
            return IRCallExpression(
                expression.name,
                [self._lower_call_argument(argument, arg_type) for argument, arg_type in zip(expression.arguments, self.function_signatures[expression.name], strict=True)],
                expected_type,
            )
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type(expression.target)
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if value_type != expected_type:
                    raise TypeError(f"Expected {expected_type}-valued map expression, got {target_type}")
                return IRMapIndex(
                    self._lower_map_expression(expression.target, target_type),
                    self._lower_typed_expression(expression.index, key_type),
                    key_type,
                    value_type,
                )
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "pop" and overload.lowering == "array_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayPop(expression.arguments[0].name, expected_type)
            if expression.name == "pop" and overload.lowering == "prio_q_pop":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("pop requires a priority queue variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                queue_type = self.variable_types.get(expression.arguments[0].name)
                if queue_type is None or not self._is_priority_queue_type(queue_type):
                    raise TypeError("pop requires a priority queue variable")
                return IRCallExpression(
                    "tb_pq_pop",
                    [self._lower_call_argument(expression.arguments[0], queue_type)],
                    expected_type,
                )
            if expression.name == "remove_at" and overload.lowering == "array_remove_at":
                if not isinstance(expression.arguments[0], Identifier):
                    raise TypeError("remove_at requires an array variable")
                self._ensure_mutable_binding(expression.arguments[0].name, "mutate")
                return IRArrayRemove(
                    expression.arguments[0].name,
                    expected_type,
                    self._lower_integer_expression(expression.arguments[1]),
                )
            if expression.name == "last" and overload.lowering == "last_array":
                return self._lower_last_array_value(expression, expected_type)
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type(expression.target)
            return IRArrayIndex(
                self._lower_array_expression(expression.target, target_type),
                self._lower_integer_expression(expression.index),
                expected_type,
            )
        if isinstance(expression, FieldAccess):
            return self._lower_record_field_expression(expression, expected_type)
        raise TypeError(f"Unsupported record expression node: {type(expression).__name__}")

    def _lower_record_field_expression(self, expression: FieldAccess, expected_type: str):
        record_type, field_name = self._resolve_field_metadata(expression)
        field_type = self.record_types[record_type].get(field_name)
        if field_type != expected_type:
            raise TypeError(f"Expected field {field_name} on {record_type} to have type {expected_type}, got {field_type}")
        return IRRecordField(
            self._lower_record_expression(expression.target, record_type),
            record_type,
            field_name,
            expected_type,
        )

    def _lower_number_expression(self, expression):
        number = self._coerce_number_value(expression)
        return self._string_literal(self._format_number_value(number))

    def _lower_call_argument(self, expression, arg_type: str) -> IRCallArgument:
        if arg_type == "int":
            return IRCallArgument("int", self._lower_integer_expression(expression))
        if arg_type == "bool":
            return IRCallArgument("bool", self._lower_boolean_expression(expression))
        if arg_type == "string":
            return IRCallArgument("string", self._lower_string_expression(expression))
        if self._is_map_type(arg_type):
            return IRCallArgument(arg_type, self._lower_map_expression(expression, arg_type))
        if self._is_set_type(arg_type):
            return IRCallArgument(arg_type, self._lower_set_expression(expression, arg_type))
        if self._is_priority_queue_type(arg_type):
            return IRCallArgument(arg_type, self._lower_priority_queue_expression(expression, arg_type))
        if self._is_array_type(arg_type):
            return IRCallArgument(arg_type, self._lower_array_expression(expression, arg_type))
        if arg_type in self.record_types:
            return IRCallArgument(arg_type, self._lower_record_expression(expression, arg_type))
        raise TypeError(f"Unsupported function argument type: {arg_type}")

    def _evaluate_string_expression(self, expression) -> str:
        if isinstance(expression, StringLiteral):
            return expression.value
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is None:
                raise TypeError("Ternary string condition must be compile-time evaluable")
            return self._evaluate_string_expression(expression.when_true if condition else expression.when_false)
        if isinstance(expression, Identifier):
            variable_type = self.variable_types.get(expression.name)
            if variable_type == "string":
                value = self.string_variables.get(expression.name)
                if value is None:
                    raise TypeError(f"Unknown string variable: {expression.name}")
                return value
            if variable_type == "int":
                value = self.int_constants.get(expression.name)
                if value is None:
                    raise TypeError(f"Expected compile-time int variable: {expression.name}")
                return str(value)
            if variable_type == "num":
                number = self.number_variables.get(expression.name)
                if number is None:
                    raise TypeError(f"Unknown num variable: {expression.name}")
                return self._format_number_value(number)
            if variable_type == "bool":
                value = self.bool_variables.get(expression.name)
                if value is None:
                    raise TypeError(f"Unknown bool variable: {expression.name}")
                return "true" if value else "false"
            if variable_type in self.enum_types:
                value = self.enum_variables.get(expression.name)
                if value is None:
                    raise TypeError(f"Unknown enum variable: {expression.name}")
                return value
            raise TypeError(f"Expected string-compatible variable: {expression.name}")
        if isinstance(expression, ArrayAccess):
            return self._evaluate_string_expression(self._resolve_indexed_value(expression))
        if isinstance(expression, FieldAccess):
            field_value = self._resolve_field_value(expression)
            return self._evaluate_string_expression(field_value)
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                value = self._enum_constant_value(expression.arguments[0], argument_types[0])
                if value is None:
                    return None
                return self._hash_string_value(value)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "read_lines" and overload.lowering == "read_lines":
                raise TypeError("read_lines must be used as an array expression")
            if expression.name == "to_int" and overload.lowering == "to_int":
                return str(int(self._evaluate_string_expression(expression.arguments[0])))
            if expression.name == "to_num" and overload.lowering == "to_num":
                return self._format_number_value(self._coerce_number_value(expression))
            if expression.name == "to_string":
                argument_type = argument_types[0]
                if argument_type == "string":
                    return self._evaluate_string_expression(expression.arguments[0])
                if argument_type == "int":
                    value = self._integer_constant_value(expression.arguments[0])
                    if value is None:
                        raise TypeError("Expected compile-time int expression")
                    return str(value)
                if argument_type == "num":
                    return self._format_number_value(self._coerce_number_value(expression.arguments[0]))
                if argument_type == "bool":
                    return "true" if self._coerce_bool_value(expression.arguments[0]) else "false"
                if argument_type == "int[]":
                    return self._format_int_array_value(self._coerce_array_value(expression.arguments[0], "int[]"))
                if argument_type == "string[]":
                    return self._format_string_array_value(self._coerce_array_value(expression.arguments[0], "string[]"))
                if argument_type == "bool[]":
                    return self._format_bool_array_value(self._coerce_array_value(expression.arguments[0], "bool[]"))
            if expression.name == "trim" and overload.lowering == "trim_string":
                return self._evaluate_string_expression(expression.arguments[0]).strip()
            if expression.name == "trim_left" and overload.lowering == "trim_left_string":
                return self._evaluate_string_expression(expression.arguments[0]).lstrip()
            if expression.name == "trim_right" and overload.lowering == "trim_right_string":
                return self._evaluate_string_expression(expression.arguments[0]).rstrip()
            if expression.name == "substring" and overload.lowering == "substring_from":
                value = self._evaluate_string_expression(expression.arguments[0])
                start = self._integer_constant_value(expression.arguments[1])
                if start is None:
                    raise TypeError("substring start must be a compile-time int value")
                if start < 0 or start > len(value):
                    raise TypeError(f"substring start out of bounds: {start}")
                return value[start:]
            if expression.name == "substring" and overload.lowering == "substring_range":
                value = self._evaluate_string_expression(expression.arguments[0])
                start = self._integer_constant_value(expression.arguments[1])
                end = self._integer_constant_value(expression.arguments[2])
                if start is None or end is None:
                    raise TypeError("substring bounds must be compile-time int values")
                start, end = self._normalize_slice_bounds(start, end, len(value))
                return value[start:end]
            if expression.name == "slice" and overload.lowering == "slice_string":
                value = self._evaluate_string_expression(expression.arguments[0])
                start = self._integer_constant_value(expression.arguments[1])
                end = self._integer_constant_value(expression.arguments[2])
                if start is None or end is None:
                    raise TypeError("slice bounds must be compile-time int values")
                start, end = self._normalize_slice_bounds(start, end, len(value))
                if start < 0 or end < start or end > len(value):
                    raise TypeError(f"slice bounds out of range: {start}:{end}")
                return value[start:end]
            if expression.name == "char_at" and overload.lowering == "char_at":
                value = self._evaluate_string_expression(expression.arguments[0])
                index = self._integer_constant_value(expression.arguments[1])
                if index is None:
                    raise TypeError("char_at index must be a compile-time int value")
                if index < 0 or index >= len(value):
                    raise TypeError(f"char_at index out of bounds: {index}")
                return value[index]
            if expression.name == "last" and overload.lowering == "last_string":
                value = self._evaluate_string_expression(expression.arguments[0])
                return value[-1] if value else ""
            if expression.name == "last" and overload.lowering == "last_array":
                argument_type = argument_types[0]
                if argument_type == "string[]":
                    items = self._coerce_array_value(expression.arguments[0], "string[]").items
                    if not items:
                        raise TypeError("last(array) requires a non-empty compile-time array")
                    return self._evaluate_string_expression(items[-1])
            if expression.name == "replace" and overload.lowering == "replace_string":
                return self._evaluate_string_expression(expression.arguments[0]).replace(
                    self._evaluate_string_expression(expression.arguments[1]),
                    self._evaluate_string_expression(expression.arguments[2]),
                )
            if expression.name == "option_value" and overload.lowering == "option_value":
                args = self._coerce_array_value(expression.arguments[0], "string[]")
                option = self._evaluate_string_expression(expression.arguments[1])
                values = [self._evaluate_string_expression(item) for item in args.items]
                for index, value in enumerate(values):
                    if value == option:
                        if index + 1 < len(values):
                            return values[index + 1]
                        return ""
                    prefix = option + "="
                    if value.startswith(prefix):
                        return value[len(prefix) :]
                return ""
            if expression.name == "join" and overload.lowering == "join_strings":
                items = self._coerce_array_value(expression.arguments[0], "string[]")
                delimiter = self._evaluate_string_expression(expression.arguments[1])
                return delimiter.join(self._evaluate_string_expression(item) for item in items.items)
        if isinstance(expression, FunctionCallExpression):
            raise TypeError("Function call is not compile-time evaluable as a string")
        if isinstance(expression, BinaryExpression):
            if self._expression_type(expression) != "string":
                raise TypeError(f"Expected string expression for operator {expression.operator}")
            return self._evaluate_string_expression(expression.left) + self._evaluate_string_expression(expression.right)
        raise TypeError(f"Unsupported string expression node: {type(expression).__name__}")

    def _coerce_number_value(self, expression) -> NumberValue:
        if isinstance(expression, NumberLiteral):
            return NumberValue(expression.value, expression.scale)
        if isinstance(expression, IntegerLiteral):
            return NumberValue(expression.value, 0)
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is None:
                raise TypeError("Ternary num condition must be compile-time evaluable")
            return self._coerce_number_value(expression.when_true if condition else expression.when_false)
        if isinstance(expression, Identifier):
            variable_type = self.variable_types.get(expression.name)
            if variable_type == "num":
                value = self.number_variables.get(expression.name)
                if value is None:
                    raise TypeError(f"Unknown num variable: {expression.name}")
                return value
            if variable_type == "int":
                value = self.int_constants.get(expression.name)
                if value is None:
                    raise TypeError(f"Expected compile-time int variable: {expression.name}")
                return NumberValue(value, 0)
            raise TypeError(f"Expected num variable: {expression.name}")
        if isinstance(expression, BinaryExpression):
            left_type = self._expression_type(expression.left)
            right_type = self._expression_type(expression.right)
            if expression.operator in {"+", "-", "*", "/"} and {left_type, right_type}.issubset({"int", "num"}) and "num" in {left_type, right_type}:
                left = self._coerce_number_value(expression.left)
                right = self._coerce_number_value(expression.right)
                return self._apply_number_operator(left, expression.operator, right)
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "to_num" and overload.lowering == "to_num":
                return self._parse_number_string(self._evaluate_string_expression(expression.arguments[0]))
            if expression.name == "abs" and overload.lowering == "abs_num":
                number = self._coerce_number_value(expression.arguments[0])
                return NumberValue(abs(number.value), number.scale)
            if expression.name == "min" and overload.lowering == "min_num":
                return self._min_number_value(
                    self._coerce_number_value(expression.arguments[0]),
                    self._coerce_number_value(expression.arguments[1]),
                )
            if expression.name == "max" and overload.lowering == "max_num":
                return self._max_number_value(
                    self._coerce_number_value(expression.arguments[0]),
                    self._coerce_number_value(expression.arguments[1]),
                )
            if expression.name == "sqrt" and overload.lowering in {"sqrt_int", "sqrt_num"}:
                return self._sqrt_number_value(self._coerce_number_value(expression.arguments[0]))
            if expression.name == "round" and overload.lowering == "round_number":
                scale = self._integer_constant_value(expression.arguments[1])
                if scale is None:
                    raise TypeError("round scale must be a compile-time int value")
                return self._round_number_value(self._coerce_number_value(expression.arguments[0]), scale)
        if isinstance(expression, ArrayAccess):
            return self._coerce_number_value(self._resolve_array_element(expression))
        if isinstance(expression, FieldAccess):
            return self._coerce_number_value(self._resolve_field_value(expression))
        raise TypeError(f"Unsupported num expression node: {type(expression).__name__}")

    def _coerce_array_value(self, expression, expected_type: str | None = None) -> ArrayValue:
        if isinstance(expression, ArrayLiteral):
            if not expression.items:
                if expected_type is None:
                    raise TypeError("Empty array literals require an explicit array type")
                return ArrayValue(self._array_item_type(expected_type), [])
            item_type = self._array_item_type(expected_type) if expected_type is not None else self._expression_type(expression.items[0])
            items: list[object] = []
            for item in expression.items:
                if self._expression_type(item) != item_type:
                    raise TypeError("Array literal items must have the same type")
                items.append(item)
            return ArrayValue(item_type, items)
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is None:
                raise TypeError("Ternary array condition must be compile-time evaluable")
            return self._coerce_array_value(expression.when_true if condition else expression.when_false, expected_type)
        if isinstance(expression, Identifier):
            variable_type = self.variable_types.get(expression.name)
            if variable_type is None or not self._is_array_type(variable_type):
                raise TypeError(f"Expected array variable: {expression.name}")
            value = self.array_variables.get(expression.name)
            if value is None:
                raise TypeError(f"Unknown array variable: {expression.name}")
            if expected_type is not None and variable_type != expected_type:
                raise TypeError(f"Expected array variable of type {expected_type}, got {variable_type}")
            return value
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "split" and overload.lowering == "split_string":
                value = self._evaluate_string_expression(expression.arguments[0])
                delimiter = self._evaluate_string_expression(expression.arguments[1])
                if delimiter == "":
                    return ArrayValue("string", [StringLiteral(character) for character in value])
                return ArrayValue("string", [StringLiteral(item) for item in value.split(delimiter)])
            if expression.name == "split_lines" and overload.lowering == "split_lines":
                value = self._evaluate_string_expression(expression.arguments[0])
                return ArrayValue("string", [StringLiteral(item) for item in value.splitlines()])
            if expression.name == "slice" and overload.lowering == "slice_array":
                array_type = argument_types[0]
                values = self._coerce_array_value(expression.arguments[0], array_type)
                start = self._integer_constant_value(expression.arguments[1])
                end = self._integer_constant_value(expression.arguments[2])
                if start is None or end is None:
                    raise TypeError("array slice bounds must be compile-time int values")
                start, end = self._normalize_slice_bounds(start, end, len(values.items))
                if start < 0 or end < start or end > len(values.items):
                    raise TypeError(f"array slice bounds out of range: {start}:{end}")
                return ArrayValue(values.item_type, values.items[start:end])
            if expression.name == "range" and overload.lowering in {"range_int", "range_int_int"}:
                if overload.lowering == "range_int":
                    start = 0
                    end = self._integer_constant_value(expression.arguments[0])
                    if end is None:
                        raise TypeError("range end must be a compile-time int value")
                else:
                    start = self._integer_constant_value(expression.arguments[0])
                    end = self._integer_constant_value(expression.arguments[1])
                    if start is None or end is None:
                        raise TypeError("range bounds must be compile-time int values")
                return ArrayValue("int", [IntegerLiteral(value) for value in range(start, end)])
        raise TypeError(f"Unsupported array expression node: {type(expression).__name__}")

    def _array_constant_value(self, expression, expected_type: str | None = None) -> ArrayValue | None:
        try:
            return self._coerce_array_value(expression, expected_type)
        except TypeError:
            return None

    def _record_constant_value(self, type_name: str, expression) -> RecordInstance | None:
        try:
            record_instance = self._coerce_record_value(expression)
            if record_instance.type_name != type_name:
                return None
            return record_instance
        except TypeError:
            return None

    def _lower_file_expression(self, expression) -> str:
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "open" and overload.lowering == "open_file":
                return self._lower_string_expression(expression.arguments[0])
        raise TypeError(f"Unsupported file expression node: {type(expression).__name__}")

    def _integer_constant_value(self, expression) -> int | None:
        if isinstance(expression, IntegerLiteral):
            return expression.value
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is None:
                return None
            return self._integer_constant_value(expression.when_true if condition else expression.when_false)
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != "int":
                return None
            return self.int_constants.get(expression.name)
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            if expression.name == "hash" and len(argument_types) == 1 and argument_types[0] in self.enum_types:
                value = self._enum_constant_value(expression.arguments[0], argument_types[0])
                if value is None:
                    return None
                return self._hash_string_value(value)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "to_int" and overload.lowering == "to_int":
                try:
                    return int(self._evaluate_string_expression(expression.arguments[0]))
                except TypeError:
                    return None
            if expression.name == "hash" and overload.lowering == "hash_int":
                value = self._integer_constant_value(expression.arguments[0])
                if value is None:
                    return None
                return self._hash_string_value(str(value))
            if expression.name == "hash" and overload.lowering == "hash_num":
                try:
                    return self._hash_string_value(self._format_number_value(self._coerce_number_value(expression.arguments[0])))
                except TypeError:
                    return None
            if expression.name == "hash" and overload.lowering == "hash_string":
                try:
                    return self._hash_string_value(self._evaluate_string_expression(expression.arguments[0]))
                except TypeError:
                    return None
            if expression.name == "index_of" and overload.lowering == "index_of":
                try:
                    return self._evaluate_string_expression(expression.arguments[0]).find(
                        self._evaluate_string_expression(expression.arguments[1])
                    )
                except TypeError:
                    return None
            if expression.name == "length" and overload.lowering == "string_length":
                try:
                    return len(self._evaluate_string_expression(expression.arguments[0]))
                except TypeError:
                    return None
            if expression.name == "length" and overload.lowering == "array_length":
                array_type = self._expression_type(expression.arguments[0])
                array_value = self._array_constant_value(expression.arguments[0], array_type)
                if array_value is None:
                    return None
                return len(array_value.items)
            if expression.name == "length" and overload.lowering == "set_length":
                if isinstance(expression.arguments[0], SetLiteral):
                    item_values = [self._integer_constant_value(item) for item in expression.arguments[0].items]
                    if any(value is None for value in item_values):
                        return None
                    return len(set(item_values))
                return None
            if expression.name == "length" and overload.lowering == "map_length":
                if isinstance(expression.arguments[0], MapLiteral):
                    return len(expression.arguments[0].items)
                return None
            if expression.name == "sum" and overload.lowering == "sum_int_array":
                array_value = self._array_constant_value(expression.arguments[0], "int[]")
                if array_value is None:
                    return None
                total = 0
                for item in array_value.items:
                    integer_value = self._integer_constant_value(item)
                    if integer_value is None:
                        return None
                    total += integer_value
                return total
            if expression.name == "sum" and overload.lowering == "sum_bool_array":
                array_value = self._array_constant_value(expression.arguments[0], "bool[]")
                if array_value is None:
                    return None
                total = 0
                for item in array_value.items:
                    boolean_value = self._boolean_constant_value(item)
                    if boolean_value is None:
                        return None
                    total += 1 if boolean_value else 0
                return total
            if expression.name == "abs" and overload.lowering == "abs_int":
                value = self._integer_constant_value(expression.arguments[0])
                if value is None:
                    return None
                return abs(value)
            if expression.name == "min" and overload.lowering == "min_int":
                left = self._integer_constant_value(expression.arguments[0])
                right = self._integer_constant_value(expression.arguments[1])
                if left is None or right is None:
                    return None
                return min(left, right)
            if expression.name == "max" and overload.lowering == "max_int":
                left = self._integer_constant_value(expression.arguments[0])
                right = self._integer_constant_value(expression.arguments[1])
                if left is None or right is None:
                    return None
                return max(left, right)
            if expression.name == "last" and overload.lowering == "last_array":
                array_value = self._array_constant_value(expression.arguments[0], argument_types[0])
                if array_value is None or not array_value.items:
                    return None
                return self._integer_constant_value(array_value.items[-1])
            return None
        if isinstance(expression, FunctionCallExpression):
            return None
        if isinstance(expression, ArrayAccess):
            try:
                return self._integer_constant_value(self._resolve_array_element(expression))
            except TypeError:
                return None
        if isinstance(expression, FieldAccess):
            try:
                return self._integer_constant_value(self._resolve_field_value(expression))
            except TypeError:
                return None
        if isinstance(expression, BinaryExpression):
            left = self._integer_constant_value(expression.left)
            right = self._integer_constant_value(expression.right)
            if left is None or right is None:
                return None
            if expression.operator == "+":
                return left + right
            if expression.operator == "-":
                return left - right
            if expression.operator == "*":
                return left * right
            if expression.operator == "/":
                return self._signed_int_divide(left, right)
            if expression.operator == "%":
                return self._signed_int_remainder(left, right)
            if expression.operator == "&":
                return left & right
            if expression.operator == "|":
                return left | right
            if expression.operator == "^":
                return left ^ right
            if expression.operator == "<<":
                return self._shift_left_int(left, right)
            if expression.operator == ">>":
                return self._shift_right_int(left, right)
        return None

    def _boolean_constant_value(self, expression) -> bool | None:
        if isinstance(expression, BooleanLiteral):
            return expression.value
        if isinstance(expression, TernaryExpression):
            condition = self._boolean_constant_value(expression.condition)
            if condition is None:
                return None
            return self._boolean_constant_value(expression.when_true if condition else expression.when_false)
        if isinstance(expression, Identifier):
            if self.variable_types.get(expression.name) != "bool":
                return None
            return self.bool_variables.get(expression.name)
        if isinstance(expression, ArrayAccess):
            try:
                return self._boolean_constant_value(self._resolve_array_element(expression))
            except TypeError:
                return None
        if isinstance(expression, FieldAccess):
            try:
                return self._boolean_constant_value(self._resolve_field_value(expression))
            except TypeError:
                return None
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type(argument) for argument in expression.arguments)
            overload = resolve_builtin(expression.name, argument_types)
            if expression.name == "contains" and overload.lowering == "contains":
                try:
                    return self._evaluate_string_expression(expression.arguments[1]) in self._evaluate_string_expression(expression.arguments[0])
                except TypeError:
                    return None
            if expression.name == "contains" and overload.lowering in {
                "array_contains_int",
                "array_contains_string",
                "array_contains_bool",
                "set_contains_int",
                "map_contains_key_string_int",
            }:
                return None
            if expression.name == "starts_with" and overload.lowering == "starts_with":
                try:
                    return self._evaluate_string_expression(expression.arguments[0]).startswith(
                        self._evaluate_string_expression(expression.arguments[1])
                    )
                except TypeError:
                    return None
            if expression.name == "ends_with" and overload.lowering == "ends_with":
                try:
                    return self._evaluate_string_expression(expression.arguments[0]).endswith(
                        self._evaluate_string_expression(expression.arguments[1])
                    )
                except TypeError:
                    return None
            if expression.name == "starts_with_at" and overload.lowering == "starts_with_at":
                try:
                    value = self._evaluate_string_expression(expression.arguments[0])
                    prefix = self._evaluate_string_expression(expression.arguments[1])
                    offset = self._integer_constant_value(expression.arguments[2])
                    if offset is None:
                        return None
                    if offset < 0 or offset > len(value):
                        return False
                    return value.startswith(prefix, offset)
                except TypeError:
                    return None
            if expression.name == "has_flag" and overload.lowering == "has_flag":
                try:
                    args = self._coerce_array_value(expression.arguments[0], "string[]")
                    flag = self._evaluate_string_expression(expression.arguments[1])
                    return any(self._evaluate_string_expression(item) == flag for item in args.items)
                except TypeError:
                    return None
            if expression.name == "is_empty" and overload.lowering == "is_empty":
                argument_type = argument_types[0]
                if argument_type == "string":
                    try:
                        return self._evaluate_string_expression(expression.arguments[0]) == ""
                    except TypeError:
                        return None
                if self._is_array_type(argument_type):
                    array_value = self._array_constant_value(expression.arguments[0], argument_type)
                    if array_value is None:
                        return None
                    return len(array_value.items) == 0
                if self._is_set_type(argument_type):
                    if isinstance(expression.arguments[0], SetLiteral):
                        return len(expression.arguments[0].items) == 0
                    return None
                if self._is_map_type(argument_type):
                    if isinstance(expression.arguments[0], MapLiteral):
                        return len(expression.arguments[0].items) == 0
                    return None
                return None
            if expression.name == "is_digit" and overload.lowering == "is_digit":
                try:
                    value = self._evaluate_string_expression(expression.arguments[0])
                except TypeError:
                    return None
                return len(value) == 1 and value.isdigit()
            if expression.name == "is_alpha" and overload.lowering == "is_alpha":
                try:
                    value = self._evaluate_string_expression(expression.arguments[0])
                except TypeError:
                    return None
                return len(value) == 1 and value.isalpha()
            if expression.name == "is_alnum" and overload.lowering == "is_alnum":
                try:
                    value = self._evaluate_string_expression(expression.arguments[0])
                except TypeError:
                    return None
                return len(value) == 1 and value.isalnum()
            if expression.name == "is_whitespace" and overload.lowering == "is_whitespace":
                try:
                    value = self._evaluate_string_expression(expression.arguments[0])
                except TypeError:
                    return None
                return len(value) == 1 and value.isspace()
            if expression.name == "is_space" and overload.lowering == "is_space":
                try:
                    value = self._evaluate_string_expression(expression.arguments[0])
                except TypeError:
                    return None
                return len(value) == 1 and value.isspace()
        if isinstance(expression, UnaryExpression):
            if expression.operator != "!":
                return None
            operand = self._boolean_constant_value(expression.operand)
            if operand is None:
                return None
            return not operand
        if isinstance(expression, BinaryExpression) and self._expression_type(expression) == "bool":
            left_type = self._expression_type(expression.left)
            right_type = self._expression_type(expression.right)
            if expression.operator in {"in", "not in"}:
                if right_type == "set<int>":
                    if not isinstance(expression.right, SetLiteral):
                        return None
                    left = self._integer_constant_value(expression.left)
                    if left is None:
                        return None
                    values = [self._integer_constant_value(item) for item in expression.right.items]
                    if any(value is None for value in values):
                        return None
                    result = left in values
                    return result if expression.operator == "in" else not result
                if self._is_array_type(right_type):
                    array_value = self._array_constant_value(expression.right, right_type)
                    if array_value is None:
                        return None
                    if left_type == "int":
                        left = self._integer_constant_value(expression.left)
                        if left is None:
                            return None
                        result = any(self._integer_constant_value(item) == left for item in array_value.items)
                        return result if expression.operator == "in" else not result
                    if left_type == "string":
                        try:
                            left = self._evaluate_string_expression(expression.left)
                            result = any(self._evaluate_string_expression(item) == left for item in array_value.items)
                            return result if expression.operator == "in" else not result
                        except TypeError:
                            return None
                    if left_type == "bool":
                        left = self._boolean_constant_value(expression.left)
                        if left is None:
                            return None
                        result = any(self._boolean_constant_value(item) == left for item in array_value.items)
                        return result if expression.operator == "in" else not result
                    return None
            if expression.operator == "&&":
                left = self._boolean_constant_value(expression.left)
                if left is False:
                    return False
                right = self._boolean_constant_value(expression.right)
                if left is None or right is None:
                    return None
                return left and right
            if expression.operator == "||":
                left = self._boolean_constant_value(expression.left)
                if left is True:
                    return True
                right = self._boolean_constant_value(expression.right)
                if left is None or right is None:
                    return None
                return left or right
            if left_type == "bool" and right_type == "bool":
                left = self._boolean_constant_value(expression.left)
                right = self._boolean_constant_value(expression.right)
                if left is None or right is None:
                    return None
                if expression.operator == "==":
                    return left == right
                if expression.operator == "!=":
                    return left != right
            if left_type == "int" and right_type == "int":
                left = self._integer_constant_value(expression.left)
                right = self._integer_constant_value(expression.right)
                if left is None or right is None:
                    return None
                if expression.operator == "==":
                    return left == right
                if expression.operator == "!=":
                    return left != right
                if expression.operator == "<":
                    return left < right
                if expression.operator == "<=":
                    return left <= right
                if expression.operator == ">":
                    return left > right
                if expression.operator == ">=":
                    return left >= right
            if left_type == "string" and right_type == "string":
                try:
                    left = self._evaluate_string_expression(expression.left)
                    right = self._evaluate_string_expression(expression.right)
                except TypeError:
                    return None
                if expression.operator == "==":
                    return left == right
                if expression.operator == "!=":
                    return left != right
            if left_type in self.enum_types and right_type == left_type:
                left = self._enum_constant_value(expression.left, left_type)
                right = self._enum_constant_value(expression.right, right_type)
                if left is None or right is None:
                    return None
                if expression.operator == "==":
                    return left == right
                if expression.operator == "!=":
                    return left != right
        return None

    def _negate_condition(self, condition):
        if isinstance(condition, IRLogicalCondition):
            return IRLogicalCondition(
                self._negate_condition(condition.left),
                "||" if condition.operator == "&&" else "&&",
                self._negate_condition(condition.right),
            )
        inverted = {
            "==": "!=",
            "!=": "==",
            "<": ">=",
            "<=": ">",
            ">": "<=",
            ">=": "<",
        }.get(condition.operator)
        if inverted is None:
            raise TypeError(f"Unsupported negated comparison operator: {condition.operator}")
        return IRComparison(condition.left, inverted, condition.right)

    def _resolve_indexed_value(self, expression: ArrayAccess):
        target_type = self._expression_type(expression.target)
        if target_type == "string":
            value = self._evaluate_string_expression(expression.target)
            index = self._integer_constant_value(expression.index)
            if index is None:
                raise TypeError("String index must be a compile-time int value")
            if index < 0:
                index += len(value)
            if index < 0 or index >= len(value):
                raise TypeError(f"String index out of bounds: {index}")
            return StringLiteral(value[index])
        return self._resolve_array_element(expression)

    def _resolve_array_element(self, expression: ArrayAccess):
        array = self._coerce_array_value(expression.target)
        index = self._integer_constant_value(expression.index)
        if index is None:
            raise TypeError("Array index must be a compile-time int value")
        if index < 0:
            index += len(array.items)
        if index < 0 or index >= len(array.items):
            raise TypeError(f"Array index out of bounds: {index}")
        return array.items[index]

    @staticmethod
    def _normalize_slice_bounds(start: int, end: int, length: int) -> tuple[int, int]:
        if start < 0:
            start += length
        if end < 0:
            end += length
        return start, end

    def _intern_string(self, value: str) -> str:
        label = self.string_labels.get(value)
        if label is not None:
            return label

        label = f".str.{len(self.module.strings)}"
        self.module.strings.append(IRString(label, value))
        self.string_labels[value] = label
        return label

    def _register_functions(self, program: Program) -> None:
        for statement in program.statements:
            if not isinstance(statement, FunctionDeclaration):
                continue
            if statement.name in self.function_declarations:
                raise TypeError(f"Duplicate function declaration: {statement.name}")
            self.function_declarations[statement.name] = statement
            self.function_signatures[statement.name] = tuple(parameter.type_name for parameter in statement.parameters)
            if statement.return_type is not None:
                self.function_return_types[statement.name] = statement.return_type
        for statement in program.statements:
            if not isinstance(statement, FunctionDeclaration):
                continue
            self.function_return_types[statement.name] = self._infer_function_return_type(statement)
            if statement.cached:
                self._validate_cached_function(statement)
            if statement.name == "main":
                if statement.return_type != "int":
                    raise TypeError("main must declare return type int")
                if tuple(parameter.type_name for parameter in statement.parameters) != ("string[]",):
                    raise TypeError("main must have signature int main(string[] args)")
                self.module.entry_function_name = "main"

    def _validate_cached_function(self, statement: FunctionDeclaration) -> None:
        if statement.name == "main":
            raise TypeError("main cannot be cached")
        if statement.return_type != "int":
            raise TypeError(f"cached function {statement.name} must declare return type int")
        if not statement.parameters:
            raise TypeError(f"cached function {statement.name} must declare at least one parameter")
        if not all(self._is_cacheable_parameter_type(parameter.type_name) for parameter in statement.parameters):
            raise TypeError(
                f"cached function {statement.name} currently supports int, string, bool, enum, or record parameters with cacheable scalar, array, or nested record fields"
            )

    def _is_cacheable_parameter_type(self, type_name: str) -> bool:
        if type_name in {"int", "string", "bool"}:
            return True
        if type_name in self.enum_types:
            return True
        if type_name in self.record_types:
            return self._is_cacheable_record_type(type_name)
        return False

    def _is_cacheable_record_type(self, type_name: str) -> bool:
        return all(self._is_cacheable_record_field_type(field_type) for field_type in self.record_types[type_name].values())

    def _is_cacheable_record_field_type(self, type_name: str) -> bool:
        if type_name in {"int", "string", "bool"}:
            return True
        if type_name in self.enum_types:
            return True
        if self._is_array_type(type_name):
            return self._is_cacheable_record_field_type(self._array_item_type(type_name))
        if type_name in self.record_types:
            return self._is_cacheable_record_type(type_name)
        return False

    def _infer_function_return_type(self, statement: FunctionDeclaration) -> str:
        local_types = {parameter.name: parameter.type_name for parameter in statement.parameters}
        if self._body_guarantees_return(statement.body, local_types, statement.name, statement.return_type):
            return statement.return_type or "void"
        if statement.return_type == "void":
            return "void"
        if statement.name == "main" and statement.return_type == "int":
            return "int"
        if statement.return_type is not None:
            raise TypeError(f"Function {statement.name} declared return type {statement.return_type} but does not return a value")
        return "void"

    def _body_guarantees_return(
        self,
        statements: list,
        local_types: dict[str, str],
        function_name: str,
        declared_return_type: str | None,
    ) -> bool:
        scope_types = local_types.copy()
        for body_statement in statements:
            if isinstance(body_statement, VariableDeclaration):
                scope_types[body_statement.name] = body_statement.type_name
                continue
            if isinstance(body_statement, ReturnStatement):
                self._validate_return_statement_type(body_statement, scope_types, function_name, declared_return_type)
                return True
            if isinstance(body_statement, ThrowStatement):
                return True
            if isinstance(body_statement, IfStatement):
                then_returns = self._body_guarantees_return(body_statement.then_body, scope_types, function_name, declared_return_type)
                else_returns = bool(body_statement.else_body) and self._body_guarantees_return(
                    body_statement.else_body,
                    scope_types,
                    function_name,
                    declared_return_type,
                )
                if then_returns and else_returns:
                    return True
                continue
            if isinstance(body_statement, SwitchStatement):
                if not body_statement.default_body or not body_statement.cases:
                    continue
                case_returns = all(
                    self._body_guarantees_return(case.body, scope_types, function_name, declared_return_type)
                    for case in body_statement.cases
                )
                default_returns = self._body_guarantees_return(
                    body_statement.default_body,
                    scope_types,
                    function_name,
                    declared_return_type,
                )
                if case_returns and default_returns:
                    return True
                continue
            if isinstance(body_statement, TryCatchStatement):
                try_returns = self._body_guarantees_return(
                    body_statement.try_body,
                    scope_types,
                    function_name,
                    declared_return_type,
                )
                catch_scope = scope_types.copy()
                catch_scope[body_statement.catch_name] = "string"
                catch_returns = self._body_guarantees_return(
                    body_statement.catch_body,
                    catch_scope,
                    function_name,
                    declared_return_type,
                )
                if try_returns and catch_returns:
                    return True
        return False

    def _validate_return_statement_type(
        self,
        statement: ReturnStatement,
        local_types: dict[str, str],
        function_name: str,
        declared_return_type: str | None,
    ) -> None:
        if statement.value is None:
            if declared_return_type == "void":
                return
            raise TypeError(f"Function {function_name} declared return type {declared_return_type} but returns no value")
        if declared_return_type == "void":
            raise TypeError(f"Function {function_name} declared return type void but returns a value")
        inferred_type = self._expression_type_with_locals(statement.value, local_types, declared_return_type)
        if declared_return_type is not None and inferred_type != declared_return_type:
            raise TypeError(f"Function {function_name} declared return type {declared_return_type}, got {inferred_type}")

    @staticmethod
    def _instructions_terminate(instructions: list) -> bool:
        if not instructions:
            return False
        last_instruction = instructions[-1]
        if isinstance(last_instruction, IRReturn):
            return True
        if isinstance(last_instruction, IRIf):
            return IRGenerator._instructions_terminate(last_instruction.then_body) and IRGenerator._instructions_terminate(last_instruction.else_body)
        return False

    def _expression_type_with_locals(self, expression, local_types: dict[str, str], expected_type: str | None = None) -> str:
        if isinstance(expression, StringLiteral):
            return "string"
        if isinstance(expression, IntegerLiteral):
            return "int"
        if isinstance(expression, BooleanLiteral):
            return "bool"
        if isinstance(expression, NumberLiteral):
            return "num"
        if isinstance(expression, Identifier):
            variable_type = local_types.get(expression.name, self.variable_types.get(expression.name))
            if variable_type is None:
                raise TypeError(f"Unknown variable: {expression.name}")
            return variable_type
        if isinstance(expression, ArrayLiteral):
            if not expression.items and expected_type is not None and self._is_array_type(expected_type):
                return expected_type
            if not expression.items:
                raise TypeError("Empty array literals require an explicit surrounding array type")
            item_type = self._expression_type_with_locals(expression.items[0], local_types)
            for item in expression.items[1:]:
                if self._expression_type_with_locals(item, local_types) != item_type:
                    raise TypeError("Array literal items must have the same type")
            return f"{item_type}[]"
        if isinstance(expression, MapLiteral):
            if not expression.items and expected_type is not None and self._is_map_type(expected_type):
                return expected_type
            if not expression.items:
                raise TypeError("Cannot infer type of empty map literal")
            key_type = self._expression_type_with_locals(expression.items[0][0], local_types)
            value_type = self._expression_type_with_locals(expression.items[0][1], local_types)
            for key, value in expression.items[1:]:
                if self._expression_type_with_locals(key, local_types) != key_type or self._expression_type_with_locals(value, local_types) != value_type:
                    raise TypeError("Map literal entries must have consistent key and value types")
            return f"map<{key_type},{value_type}>"
        if isinstance(expression, ArrayAccess):
            target_type = self._expression_type_with_locals(expression.target, local_types)
            if target_type == "string":
                if self._expression_type_with_locals(expression.index, local_types) != "int":
                    raise TypeError("String index must be an int")
                return "string"
            if self._is_map_type(target_type):
                key_type, value_type = self._map_parts(target_type)
                if self._expression_type_with_locals(expression.index, local_types) != key_type:
                    raise TypeError(f"Map key must be {key_type}")
                return value_type
            if not target_type.endswith("[]"):
                raise TypeError(f"Expected array expression, got {target_type}")
            if self._expression_type_with_locals(expression.index, local_types) != "int":
                raise TypeError("Array index must be an int")
            return target_type.removesuffix("[]")
        if isinstance(expression, ConstructorCall):
            if expression.type_name not in self.record_types:
                raise TypeError(f"Unknown record type: {expression.type_name}")
            fields = self.record_types[expression.type_name]
            if len(expression.arguments) != len(fields):
                raise TypeError(f"Expected {len(fields)} constructor arguments for {expression.type_name}")
            for (field_name, field_type), argument in zip(fields.items(), expression.arguments, strict=True):
                if self._expression_type_with_locals(argument, local_types, field_type) != field_type:
                    raise TypeError(f"Expected {field_type} for field {field_name}")
            return expression.type_name
        if isinstance(expression, FieldAccess):
            if isinstance(expression.target, Identifier) and expression.target.name in self.enum_types:
                if expression.field_name not in self.enum_types[expression.target.name]:
                    raise TypeError(f"Unknown enum member {expression.field_name!r} on {expression.target.name}")
                return expression.target.name
            record_type = self._expression_type_with_locals(expression.target, local_types)
            if record_type not in self.record_types:
                raise TypeError("Expected record expression")
            field_type = self.record_types[record_type].get(expression.field_name)
            if field_type is None:
                raise TypeError(f"Unknown field {expression.field_name!r} on {record_type}")
            return field_type
        if isinstance(expression, TernaryExpression):
            if self._expression_type_with_locals(expression.condition, local_types) != "bool":
                raise TypeError("Ternary condition must be boolean")
            true_type = self._expression_type_with_locals(expression.when_true, local_types, expected_type)
            false_type = self._expression_type_with_locals(expression.when_false, local_types, expected_type)
            if true_type != false_type:
                raise TypeError(f"Ternary branches must have matching types, got {true_type} and {false_type}")
            return true_type
        if isinstance(expression, UnaryExpression):
            operand_type = self._expression_type_with_locals(expression.operand, local_types)
            if expression.operator == "!" and operand_type == "bool":
                return "bool"
            raise TypeError(f"Unsupported unary operator {expression.operator} for {operand_type}")
        if isinstance(expression, BinaryExpression):
            left_type = self._expression_type_with_locals(expression.left, local_types)
            right_type = self._expression_type_with_locals(expression.right, local_types)
            if expression.operator in {"in", "not in"}:
                if self._is_set_type(right_type):
                    if right_type == "set<int>" and left_type == "int":
                        return "bool"
                    raise TypeError(f"Unsupported operand types for {expression.operator}: {left_type}, {right_type}")
                if self._is_array_type(right_type):
                    if self._array_item_type(right_type) == left_type:
                        return "bool"
                    raise TypeError(f"Unsupported operand types for {expression.operator}: {left_type}, {right_type}")
                raise TypeError(f"Unsupported operand types for {expression.operator}: {left_type}, {right_type}")
            if expression.operator in {"&&", "||"} and left_type == "bool" and right_type == "bool":
                return "bool"
            if expression.operator in {"==", "!="} and left_type == "bool" and right_type == "bool":
                return "bool"
            if expression.operator in {"==", "!=", "<", "<=", ">", ">="} and left_type == "int" and right_type == "int":
                return "bool"
            if expression.operator in {"==", "!="} and left_type == "string" and right_type == "string":
                return "bool"
            if expression.operator in {"==", "!="} and left_type in self.enum_types and right_type == left_type:
                return "bool"
            if expression.operator in {"+", "-", "*", "/"} and {left_type, right_type}.issubset({"int", "num"}) and "num" in {left_type, right_type}:
                return "num"
            if expression.operator in {"+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"} and left_type == "int" and right_type == "int":
                return "int"
            if expression.operator == "+" and {left_type, right_type}.issubset({"string", "int", "num"}) and "string" in {left_type, right_type}:
                return "string"
            raise TypeError(f"Unsupported operand types for {expression.operator}: {left_type}, {right_type}")
        if isinstance(expression, BuiltinCallExpression):
            argument_types = tuple(self._expression_type_with_locals(argument, local_types) for argument in expression.arguments)
            return resolve_builtin(expression.name, argument_types).return_type
        if isinstance(expression, LambdaExpression):
            lambda_locals = local_types.copy()
            lambda_locals[expression.parameter_name] = expression.parameter_type
            return f"lambda<{expression.parameter_type},{self._lambda_return_type(expression, lambda_locals)}>"
        if isinstance(expression, MultiLambdaExpression):
            lambda_locals = local_types.copy()
            for parameter in expression.parameters:
                lambda_locals[parameter.name] = parameter.type_name
            parameter_types = ", ".join(parameter.type_name for parameter in expression.parameters)
            return f"lambda<{parameter_types},{self._callable_return_type(expression.parameters, expression.body, lambda_locals)}>"
        if isinstance(expression, FunctionCallExpression):
            signature = self.function_signatures.get(expression.name)
            if signature is None:
                raise TypeError(f"Unknown function: {expression.name}")
            if len(expression.arguments) != len(signature):
                raise TypeError(f"Argument mismatch for function {expression.name}: expected {signature}, got {len(expression.arguments)} arguments")
            argument_types = tuple(
                self._expression_type_with_locals(argument, local_types, arg_type)
                for argument, arg_type in zip(expression.arguments, signature, strict=True)
            )
            if argument_types != signature:
                raise TypeError(f"Argument mismatch for function {expression.name}: expected {signature}, got {argument_types}")
            return self.function_return_types.get(expression.name, "void")
        raise TypeError(f"Unsupported expression node: {type(expression).__name__}")

    def _lambda_return_type(self, expression: LambdaExpression, local_types: dict[str, str]) -> str:
        return self._callable_return_type(
            [FunctionParameter(expression.parameter_type, expression.parameter_name)],
            expression.body,
            local_types,
        )

    def _callable_return_type(
        self,
        parameters: list[FunctionParameter],
        body_expression,
        local_types: dict[str, str],
    ) -> str:
        scoped_locals = local_types.copy()
        for parameter in parameters:
            scoped_locals[parameter.name] = parameter.type_name
        if not isinstance(body_expression, list):
            return self._expression_type_with_locals(body_expression, scoped_locals)
        for statement in body_expression:
            if isinstance(statement, VariableDeclaration):
                scoped_locals[statement.name] = statement.type_name
                continue
            if isinstance(statement, ReturnStatement):
                return self._expression_type_with_locals(statement.value, scoped_locals)
            if isinstance(statement, ThrowStatement):
                return "void"
        raise TypeError("Lambda block must return a value")

    def _extract_lambda_body_expression(self, expression: LambdaExpression, return_type: str):
        if not isinstance(expression.body, list):
            return self._lower_typed_expression(expression.body, return_type)
        if len(expression.body) != 1 or not isinstance(expression.body[0], ReturnStatement):
            raise TypeError("Lambda block currently supports only a single return statement")
        return self._lower_typed_expression(expression.body[0].value, return_type)

    def _string_constant_value(self, expression) -> str | None:
        try:
            return self._evaluate_string_expression(expression)
        except TypeError:
            return None

    @staticmethod
    def _format_int_array_value(array_value: ArrayValue) -> str:
        items: list[str] = []
        for item in array_value.items:
            if not isinstance(item, IntegerLiteral):
                raise TypeError("Expected compile-time int array value")
            items.append(str(item.value))
        return "[" + ", ".join(items) + "]"

    def _format_string_array_value(self, array_value: ArrayValue) -> str:
        return "[" + ", ".join(f"'{self._evaluate_string_expression(item)}'" for item in array_value.items) + "]"

    def _format_bool_array_value(self, array_value: ArrayValue) -> str:
        items: list[str] = []
        for item in array_value.items:
            value = self._boolean_constant_value(item)
            if value is None:
                raise TypeError("Expected compile-time bool array value")
            items.append("true" if value else "false")
        return "[" + ", ".join(items) + "]"

    def _string_literal(self, value: str) -> str:
        return self._intern_string(value)

    @staticmethod
    def _signed_int_divide(left: int, right: int) -> int:
        if right == 0:
            raise ZeroDivisionError("integer division by zero")
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        return quotient

    @classmethod
    def _signed_int_remainder(cls, left: int, right: int) -> int:
        return left - cls._signed_int_divide(left, right) * right

    @staticmethod
    def _shift_left_int(left: int, right: int) -> int:
        if right < 0:
            raise ValueError("shift count must be non-negative")
        if right >= 64:
            return 0
        return left << right

    @staticmethod
    def _shift_right_int(left: int, right: int) -> int:
        if right < 0:
            raise ValueError("shift count must be non-negative")
        if right >= 64:
            return -1 if left < 0 else 0
        return left >> right

    def _lower_string_part(self, expression):
        expression_type = self._expression_type(expression)
        if expression_type == "string":
            return self._lower_string_expression(expression)
        if expression_type == "int":
            return IRIntToString(self._lower_integer_expression(expression))
        if expression_type == "num":
            return self._string_literal(self._format_number_value(self._coerce_number_value(expression)))
        raise TypeError(f"Unsupported string part type: {expression_type}")

    def _coerce_bool_value(self, expression) -> bool:
        value = self._boolean_constant_value(expression)
        if value is None:
            raise TypeError("Expected compile-time bool expression")
        return value

    @staticmethod
    def _contains_file_instruction(instructions: list) -> bool:
        for instruction in instructions:
            if isinstance(instruction, (IRDeclareFile, IRWriteLine)):
                return True
            if isinstance(instruction, IRForLoop) and IRGenerator._contains_file_instruction(instruction.body):
                return True
            if isinstance(instruction, IRIf):
                if IRGenerator._contains_file_instruction(instruction.then_body):
                    return True
                if IRGenerator._contains_file_instruction(instruction.else_body):
                    return True
        return False

    @staticmethod
    def _changes_existing_bindings(base_bindings: dict[str, object], branch_bindings: dict[str, object]) -> bool:
        sentinel = object()
        for name, value in base_bindings.items():
            if branch_bindings.get(name, sentinel) != value:
                return True
        return False

    def _invalidate_assigned_bindings(self, statement) -> None:
        for name in self._assigned_binding_names(statement):
            self.int_constants.pop(name, None)
            self.bool_variables.pop(name, None)
            self.string_variables.pop(name, None)
            self.number_variables.pop(name, None)
            self.array_variables.pop(name, None)
            self.record_variables.pop(name, None)
            self.enum_variables.pop(name, None)

    def _ensure_mutable_binding(self, name: str, action: str) -> None:
        if name in self.const_variables:
            raise TypeError(f"Cannot {action} const variable: {name}")

    @staticmethod
    def _contains_loop_control_statement(statements: list) -> bool:
        for statement in statements:
            if isinstance(statement, (ContinueStatement, BreakStatement)):
                return True
            if isinstance(statement, IfStatement):
                if IRGenerator._contains_loop_control_statement(statement.then_body):
                    return True
                if IRGenerator._contains_loop_control_statement(statement.else_body):
                    return True
                continue
            if isinstance(statement, ForStatement):
                if IRGenerator._contains_loop_control_statement(statement.body):
                    return True
                continue
            if isinstance(statement, WhileStatement):
                if IRGenerator._contains_loop_control_statement(statement.body):
                    return True
                continue
            if isinstance(statement, ForEachStatement):
                if IRGenerator._contains_loop_control_statement(statement.body):
                    return True
                continue
            if isinstance(statement, SwitchStatement):
                for case in statement.cases:
                    if IRGenerator._contains_loop_control_statement(case.body):
                        return True
                if IRGenerator._contains_loop_control_statement(statement.default_body):
                    return True
        return False

    def _assigned_binding_names(self, statement) -> set[str]:
        names: set[str] = set()
        if isinstance(statement, Assignment):
            names.add(statement.name)
        elif isinstance(statement, ArrayAssignment):
            if isinstance(statement.target.target, Identifier):
                names.add(statement.target.target.name)
        elif isinstance(statement, FieldAssignment):
            if isinstance(statement.target.target, Identifier):
                names.add(statement.target.target.name)
        elif isinstance(statement, BuiltinCallStatement):
            if statement.name in {"push", "pop", "insert", "remove_at", "clear", "add"} and statement.arguments:
                if isinstance(statement.arguments[0], Identifier):
                    names.add(statement.arguments[0].name)
        elif isinstance(statement, IfStatement):
            for body_statement in statement.then_body:
                names.update(self._assigned_binding_names(body_statement))
            for body_statement in statement.else_body:
                names.update(self._assigned_binding_names(body_statement))
        elif isinstance(statement, ForStatement):
            names.update(self._assigned_binding_names(statement.initializer))
            names.update(self._assigned_binding_names(statement.update))
            for body_statement in statement.body:
                names.update(self._assigned_binding_names(body_statement))
        elif isinstance(statement, WhileStatement):
            for body_statement in statement.body:
                names.update(self._assigned_binding_names(body_statement))
        elif isinstance(statement, ForEachStatement):
            for body_statement in statement.body:
                names.update(self._assigned_binding_names(body_statement))
        elif isinstance(statement, SwitchStatement):
            for case in statement.cases:
                for body_statement in case.body:
                    names.update(self._assigned_binding_names(body_statement))
            for body_statement in statement.default_body:
                names.update(self._assigned_binding_names(body_statement))
        return names

    @staticmethod
    def _restore_runtime_bindings(
        base_variable_types: dict[str, str],
        base_bindings: dict[str, object],
        loop_bindings: dict[str, object],
        matches_type,
    ) -> dict[str, object]:
        restored = base_bindings.copy()
        sentinel = object()
        for name, type_name in base_variable_types.items():
            if not matches_type(type_name):
                continue
            if loop_bindings.get(name, sentinel) != base_bindings.get(name, sentinel):
                restored.pop(name, None)
        return restored

    def _merge_if_int_constants(
        self,
        base_int_constants: dict[str, int],
        then_int_constants: dict[str, int],
        else_int_constants: dict[str, int],
    ) -> dict[str, int]:
        merged: dict[str, int] = {}
        sentinel = object()
        for name, type_name in self.variable_types.items():
            if type_name != "int":
                continue
            then_value = then_int_constants.get(name, sentinel)
            else_value = else_int_constants.get(name, sentinel)
            if then_value == else_value and then_value is not sentinel:
                merged[name] = then_value
                continue
            base_value = base_int_constants.get(name, sentinel)
            if base_value is not sentinel and then_value == base_value and else_value == base_value:
                merged[name] = base_value
        return merged

    @staticmethod
    def _merge_if_bindings(
        variable_types: dict[str, str],
        matches_type,
        base_bindings: dict[str, object],
        then_bindings: dict[str, object],
        else_bindings: dict[str, object],
    ) -> dict[str, object]:
        if isinstance(matches_type, str):
            match = lambda type_name: type_name == matches_type
        else:
            match = matches_type
        merged: dict[str, object] = {}
        sentinel = object()
        for name, type_name in variable_types.items():
            if not match(type_name):
                continue
            then_value = then_bindings.get(name, sentinel)
            else_value = else_bindings.get(name, sentinel)
            if then_value == else_value and then_value is not sentinel:
                merged[name] = then_value
                continue
            base_value = base_bindings.get(name, sentinel)
            if base_value is not sentinel and then_value == base_value and else_value == base_value:
                merged[name] = base_value
        return merged

    @staticmethod
    def _format_number_value(number: NumberValue) -> str:
        sign = "-" if number.value < 0 else ""
        digits = str(abs(number.value))
        if number.scale == 0:
            return f"{sign}{digits}"
        padded = digits.rjust(number.scale + 1, "0")
        split_at = len(padded) - number.scale
        return f"{sign}{padded[:split_at]}.{padded[split_at:]}"

    @staticmethod
    def _parse_number_string(value: str) -> NumberValue:
        sign = -1 if value.startswith("-") else 1
        digits = value[1:] if sign == -1 else value
        if "." not in digits:
            return NumberValue(sign * int(digits), 0)
        whole_part, fractional_part = digits.split(".", maxsplit=1)
        return NumberValue(sign * int(whole_part + fractional_part), len(fractional_part))

    @staticmethod
    def _round_number_value(number: NumberValue, scale: int) -> NumberValue:
        if scale < 0:
            raise TypeError("round scale must be non-negative")
        if scale >= number.scale:
            return NumberValue(number.value * (10 ** (scale - number.scale)), scale)

        factor = 10 ** (number.scale - scale)
        absolute_value = abs(number.value)
        quotient, remainder = divmod(absolute_value, factor)
        if remainder * 2 >= factor:
            quotient += 1
        if number.value < 0:
            quotient *= -1
        return NumberValue(quotient, scale)

    @staticmethod
    def _sqrt_number_value(number: NumberValue) -> NumberValue:
        if number.value < 0:
            raise TypeError("sqrt requires a non-negative value")
        decimal_value = Decimal(IRGenerator._format_number_value(number))
        try:
            with localcontext() as context:
                context.prec = 50
                root = decimal_value.sqrt()
        except InvalidOperation as error:
            raise TypeError("sqrt requires a valid numeric value") from error
        if root == root.to_integral():
            return NumberValue(int(root), 0)
        rounded = root.quantize(Decimal("0.000000000001"))
        formatted = format(rounded, "f").rstrip("0").rstrip(".")
        return IRGenerator._parse_number_string(formatted)

    @staticmethod
    def _min_number_value(left: NumberValue, right: NumberValue) -> NumberValue:
        target_scale = max(left.scale, right.scale)
        left_rescaled = IRGenerator._rescale_number(left, target_scale)
        right_rescaled = IRGenerator._rescale_number(right, target_scale)
        return left_rescaled if left_rescaled.value <= right_rescaled.value else right_rescaled

    @staticmethod
    def _max_number_value(left: NumberValue, right: NumberValue) -> NumberValue:
        target_scale = max(left.scale, right.scale)
        left_rescaled = IRGenerator._rescale_number(left, target_scale)
        right_rescaled = IRGenerator._rescale_number(right, target_scale)
        return left_rescaled if left_rescaled.value >= right_rescaled.value else right_rescaled

    @staticmethod
    def _apply_number_operator(left: NumberValue, operator: str, right: NumberValue) -> NumberValue:
        target_scale = max(left.scale, right.scale)
        if operator == "+":
            return NumberValue(
                IRGenerator._rescale_number(left, target_scale).value
                + IRGenerator._rescale_number(right, target_scale).value,
                target_scale,
            )
        if operator == "-":
            return NumberValue(
                IRGenerator._rescale_number(left, target_scale).value
                - IRGenerator._rescale_number(right, target_scale).value,
                target_scale,
            )
        if operator == "*":
            product = NumberValue(left.value * right.value, left.scale + right.scale)
            return IRGenerator._round_number_value(product, target_scale)
        if operator == "/":
            return IRGenerator._divide_number_values(left, right, target_scale)
        raise TypeError(f"Unsupported num operator: {operator}")

    @staticmethod
    def _rescale_number(number: NumberValue, scale: int) -> NumberValue:
        if scale < number.scale:
            return IRGenerator._round_number_value(number, scale)
        if scale == number.scale:
            return number
        return NumberValue(number.value * (10 ** (scale - number.scale)), scale)

    @staticmethod
    def _divide_number_values(left: NumberValue, right: NumberValue, scale: int) -> NumberValue:
        numerator = left.value * (10 ** (right.scale + scale))
        denominator = right.value * (10 ** left.scale)
        absolute_numerator = abs(numerator)
        absolute_denominator = abs(denominator)
        quotient, remainder = divmod(absolute_numerator, absolute_denominator)
        if remainder * 2 >= absolute_denominator:
            quotient += 1
        if (numerator < 0) != (denominator < 0):
            quotient *= -1
        return NumberValue(quotient, scale)

    @staticmethod
    def _hash_string_value(value: str) -> int:
        hashed = 5381
        for byte in value.encode("utf-8"):
            hashed = ((hashed * 33) + byte) & ((1 << 64) - 1)
        if hashed >= (1 << 63):
            hashed -= 1 << 64
        return hashed

    def _build_record_instance(self, type_name: str, expression) -> RecordInstance:
        if not isinstance(expression, ConstructorCall):
            raise TypeError(f"Expected constructor call for {type_name}")
        if expression.type_name != type_name:
            raise TypeError(f"Expected constructor {type_name}, got {expression.type_name}")
        fields = self.record_types[type_name]
        if len(expression.arguments) != len(fields):
            raise TypeError(f"Expected {len(fields)} constructor arguments for {type_name}")
        values: dict[str, object] = {}
        for (field_name, field_type), argument in zip(fields.items(), expression.arguments, strict=True):
            if self._expression_type(argument, field_type) != field_type:
                raise TypeError(f"Expected {field_type} for field {field_name}")
            values[field_name] = argument
        return RecordInstance(type_name, values)

    def _coerce_record_value(self, expression) -> RecordInstance:
        expression_type = self._expression_type(expression)
        if expression_type not in self.record_types:
            raise TypeError(f"Expected record expression, got {expression_type}")
        if isinstance(expression, Identifier):
            record_instance = self.record_variables.get(expression.name)
            if record_instance is None:
                raise TypeError(f"Unknown record variable: {expression.name}")
            return record_instance
        if isinstance(expression, ConstructorCall):
            return self._build_record_instance(expression.type_name, expression)
        if isinstance(expression, ArrayAccess):
            return self._coerce_record_value(self._resolve_array_element(expression))
        if isinstance(expression, FieldAccess):
            return self._coerce_record_value(self._resolve_field_value(expression))
        raise TypeError(f"Unsupported record expression node: {type(expression).__name__}")

    def _resolve_field_metadata(self, expression: FieldAccess) -> tuple[str, str]:
        record_type = self._expression_type(expression.target)
        if record_type not in self.record_types:
            raise TypeError("Expected record expression")
        return record_type, expression.field_name

    def _resolve_field_value(self, expression: FieldAccess):
        record_instance = self._coerce_record_value(expression.target)
        field_value = record_instance.field_values.get(expression.field_name)
        if field_value is None:
            raise TypeError(f"Unknown field {expression.field_name!r} on {record_instance.type_name}")
        return field_value

    def _enum_constant_value(self, expression, expected_type: str | None = None) -> str | None:
        expression_type = self._expression_type(expression)
        if expression_type not in self.enum_types:
            return None
        if expected_type is not None and expression_type != expected_type:
            raise TypeError(f"Expected enum expression of type {expected_type}, got {expression_type}")
        if isinstance(expression, Identifier):
            return self.enum_variables.get(expression.name)
        if isinstance(expression, FieldAccess) and isinstance(expression.target, Identifier) and expression.target.name in self.enum_types:
            return expression.field_name
        return None


def generate_ir(program: Program, foreign_modules: list[str] | None = None) -> IRModule:
    return IRGenerator(foreign_modules=foreign_modules).generate(program)
