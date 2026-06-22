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

from dataclasses import dataclass, field


class IRExpression:
    pass


@dataclass(slots=True)
class IRString:
    label: str
    value: str


@dataclass(slots=True)
class IRInteger(IRExpression):
    value: int


@dataclass(slots=True)
class IRBoolean(IRExpression):
    value: bool


@dataclass(slots=True)
class IRRecordTypeField:
    type_name: str
    name: str


@dataclass(slots=True)
class IRRecordType:
    name: str
    fields: list[IRRecordTypeField]


@dataclass(slots=True)
class IRVariable(IRExpression):
    name: str


@dataclass(slots=True)
class IRBinaryOperation(IRExpression):
    left: IRExpression
    operator: str
    right: IRExpression


@dataclass(slots=True)
class IRStringLiteral(IRExpression):
    label: str


@dataclass(slots=True)
class IRStringConcat(IRExpression):
    left: IRExpression
    right: IRExpression


@dataclass(slots=True)
class IRStringIndex(IRExpression):
    target: IRExpression | str
    index: IRExpression


@dataclass(slots=True)
class IRArrayLiteral(IRExpression):
    item_type: str
    items: list[IRExpression]


@dataclass(slots=True)
class IRArrayLength(IRExpression):
    target: IRExpression
    item_type: str


@dataclass(slots=True)
class IRArrayIndex(IRExpression):
    target: IRExpression
    index: IRExpression
    item_type: str


@dataclass(slots=True)
class IRArrayMap(IRExpression):
    target: IRExpression
    source_item_type: str
    result_item_type: str
    parameter_name: str
    body: IRExpression


@dataclass(slots=True)
class IRArrayFilter(IRExpression):
    target: IRExpression
    item_type: str
    parameter_name: str
    predicate: IRExpression


@dataclass(slots=True)
class IRArrayCollect(IRExpression):
    target: IRExpression
    item_type: str


@dataclass(slots=True)
class IRArraySort:
    target_name: str
    item_type: str
    comparator_name: str


@dataclass(slots=True)
class IRMapLiteral(IRExpression):
    key_type: str
    value_type: str
    items: list[tuple[IRExpression, IRExpression]]


@dataclass(slots=True)
class IRSetLiteral(IRExpression):
    item_type: str
    items: list[IRExpression]


@dataclass(slots=True)
class IRMapIndex(IRExpression):
    target: IRExpression
    key: IRExpression
    key_type: str
    value_type: str


@dataclass(slots=True)
class IRRecordConstruct(IRExpression):
    type_name: str
    fields: list[tuple[str, str, IRExpression]]


@dataclass(slots=True)
class IRRecordField(IRExpression):
    target: IRExpression
    type_name: str
    field_name: str
    field_type: str


@dataclass(slots=True)
class IRIntToString(IRExpression):
    value: IRExpression


@dataclass(slots=True)
class IRCallArgument:
    type_name: str
    value: IRExpression


@dataclass(slots=True)
class IRCallExpression(IRExpression):
    name: str
    arguments: list[IRCallArgument]
    return_type: str
    builtin: bool = False


@dataclass(slots=True)
class IRSelect(IRExpression):
    condition: "IRCondition"
    when_true: IRExpression
    when_false: IRExpression
    result_type: str


@dataclass(slots=True)
class IRComparison:
    left: IRExpression
    operator: str
    right: IRExpression


@dataclass(slots=True)
class IRLogicalCondition:
    left: "IRCondition"
    operator: str
    right: "IRCondition"


@dataclass(slots=True)
class IRDeclareInt:
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignInt:
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRDeclareBool:
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignBool:
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRDeclareString:
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignString:
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRDeclareArray:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRDeclareMap:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignMap:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignArray:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRArraySet:
    target_name: str
    item_type: str
    index: IRExpression
    value: IRExpression


@dataclass(slots=True)
class IRMapSet:
    target_name: str
    key_type: str
    value_type: str
    key: IRExpression
    value: IRExpression


@dataclass(slots=True)
class IRArrayPush:
    target_name: str
    item_type: str
    value: IRExpression


@dataclass(slots=True)
class IRArrayPop(IRExpression):
    target_name: str
    item_type: str


@dataclass(slots=True)
class IRArrayRemove(IRExpression):
    target_name: str
    item_type: str
    index: IRExpression


@dataclass(slots=True)
class IRArrayInsert:
    target_name: str
    item_type: str
    index: IRExpression
    value: IRExpression


@dataclass(slots=True)
class IRArrayClear:
    target_name: str


@dataclass(slots=True)
class IRPriorityQueueCreate(IRExpression):
    source: IRExpression
    item_type: str
    comparator_name: str


@dataclass(slots=True)
class IRDeclarePriorityQueue:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignPriorityQueue:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRDeclareRecord:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRAssignRecord:
    type_name: str
    name: str
    value: IRExpression


@dataclass(slots=True)
class IRSetRecordField:
    target_name: str
    type_name: str
    field_name: str
    field_type: str
    value: IRExpression


@dataclass(slots=True)
class IRPrintString:
    value: IRExpression


@dataclass(slots=True)
class IRPrintInt:
    value: IRExpression


@dataclass(slots=True)
class IRDeclareFile:
    name: str
    path: IRExpression


@dataclass(slots=True)
class IRWriteLine:
    file_name: str
    value: IRExpression


@dataclass(slots=True)
class IRWriteLines:
    file_name: str
    value: IRExpression


@dataclass(slots=True)
class IRCloseFile:
    file_name: str


@dataclass(slots=True)
class IRForLoop:
    initializer: IRDeclareInt | IRAssignInt
    condition: "IRCondition"
    update: IRAssignInt
    body: list["IRInstruction"]


@dataclass(slots=True)
class IRWhileLoop:
    condition: "IRCondition"
    body: list["IRInstruction"]


@dataclass(slots=True)
class IRIf:
    condition: "IRCondition"
    then_body: list["IRInstruction"]
    else_body: list["IRInstruction"]


@dataclass(slots=True)
class IRContinue:
    pass


@dataclass(slots=True)
class IRBreak:
    pass


@dataclass(slots=True)
class IRThrow:
    value: IRExpression


@dataclass(slots=True)
class IRTryCatch:
    catch_name: str
    try_body: list["IRInstruction"]
    catch_body: list["IRInstruction"]


IRCondition = IRComparison | IRLogicalCondition


@dataclass(slots=True)
class IRFunctionParameter:
    type_name: str
    name: str


@dataclass(slots=True)
class IRFunctionCall:
    name: str
    arguments: list[IRCallArgument]
    return_type: str = "void"


@dataclass(slots=True)
class IRReturn:
    value: IRExpression | None
    return_type: str


@dataclass(slots=True)
class IRFunctionDefinition:
    name: str
    parameters: list[IRFunctionParameter]
    body: list["IRInstruction"]
    return_type: str = "void"
    cached: bool = False


IRInstruction = (
    IRDeclareInt
    | IRAssignInt
    | IRDeclareBool
    | IRAssignBool
    | IRDeclareString
    | IRAssignString
    | IRDeclareArray
    | IRDeclareMap
    | IRAssignMap
    | IRAssignArray
    | IRArraySet
    | IRMapSet
    | IRArrayPush
    | IRArraySort
    | IRDeclareRecord
    | IRAssignRecord
    | IRSetRecordField
    | IRPrintString
    | IRPrintInt
    | IRDeclareFile
    | IRWriteLine
    | IRWriteLines
    | IRForLoop
    | IRWhileLoop
    | IRIf
    | IRContinue
    | IRBreak
    | IRThrow
    | IRTryCatch
    | IRFunctionCall
    | IRReturn
)


@dataclass(slots=True)
class IRModule:
    strings: list[IRString] = field(default_factory=list)
    record_types: list[IRRecordType] = field(default_factory=list)
    functions: list[IRFunctionDefinition] = field(default_factory=list)
    instructions: list[IRInstruction] = field(default_factory=list)
    entry_function_name: str | None = None
    foreign_modules: list[str] = field(default_factory=list)
