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

from .ir import (
    IRArrayClear,
    IRArrayCollect,
    IRArrayIndex,
    IRArrayFilter,
    IRArrayInsert,
    IRArrayLength,
    IRArrayLiteral,
    IRArrayMap,
    IRArrayPop,
    IRArrayPush,
    IRArrayRemove,
    IRArraySort,
    IRArraySet,
    IRMapSet,
    IRAssignInt,
    IRAssignMap,
    IRAssignPriorityQueue,
    IRAssignArray,
    IRAssignBool,
    IRAssignRecord,
    IRAssignString,
    IRBinaryOperation,
    IRBoolean,
    IRCallArgument,
    IRCallExpression,
    IRComparison,
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
    IRReturn,
    IRSelect,
    IRPriorityQueueCreate,
    IRSetRecordField,
    IRSetLiteral,
    IRString,
    IRStringIndex,
    IRStringConcat,
    IRStringLiteral,
    IRThrow,
    IRTryCatch,
    IRVariable,
    IRWhileLoop,
    IRWriteLine,
)
from .foreign_modules import foreign_module_functions


class LLVMEmitter:
    RC_HEADER_TYPE_NAME = "%tb.rc.header"
    ARRAY_TYPE_NAME = "%tb.array"
    SET_TYPE_NAME = "%tb.set"
    MAP_TYPE_NAME = "%tb.map"
    PRIORITY_QUEUE_TYPE_NAME = "%tb.prio_q"
    CACHE_TYPE_NAME = "%tb.cache"
    ARENA_CHUNK_TYPE_NAME = "%tb.arena.chunk"
    ARENA_MARK_TYPE_NAME = "%tb.arena.mark"
    ARENA_INITIAL_CHUNK_BYTES = 1024 * 1024
    ARENA_MAX_BYTES = 256 * 1024 * 1024
    INT_FORMAT_LABEL = ".fmt.int"
    INT_FORMAT_BYTES = b"%lld\n\0"
    FILE_MODE_LABEL = ".fmt.file.mode"
    FILE_MODE_BYTES = b"w\0"
    FILE_READ_MODE_LABEL = ".fmt.file.read.mode"
    FILE_READ_MODE_BYTES = b"rb\0"
    FILE_LINE_FORMAT_LABEL = ".fmt.file.line"
    FILE_LINE_FORMAT_BYTES = b"%s\n\0"
    INT_TO_STRING_FORMAT_LABEL = ".fmt.int.to_string"
    INT_TO_STRING_FORMAT_BYTES = b"%lld\0"
    NEWLINE_LABEL = ".tb.newline"
    NEWLINE_BYTES = b"\n\0"
    UNCAUGHT_EXCEPTION_FORMAT_LABEL = ".tb.exception.uncaught"
    UNCAUGHT_EXCEPTION_FORMAT_BYTES = b"Unhandled exception: %s\n\0"
    BOOL_TRUE_LABEL = ".tb.bool.true"
    BOOL_TRUE_BYTES = b"true\0"
    BOOL_FALSE_LABEL = ".tb.bool.false"
    BOOL_FALSE_BYTES = b"false\0"
    RC_HEADER_SIZE = 16
    RC_KIND_STRING = 1
    RC_KIND_ARRAY = 2
    RC_KIND_RECORD = 3
    RC_KIND_SET = 4
    RC_KIND_MAP = 5
    RC_KIND_PRIORITY_QUEUE = 6
    RC_FLAGS_MAGIC = 0x54420000
    RC_FLAGS_MAGIC_MASK = 0xFFFF0000
    RC_ARRAY_RELEASE_NONE = 0
    RC_ARRAY_RELEASE_PTRS = 1
    RC_SET_RELEASE_NONE = 0
    RC_SET_RELEASE_PTRS = 1
    RC_MAP_RELEASE_NONE = 0
    RC_MAP_RELEASE_PTRS = 1
    RC_MAP_KEY_SHIFT = 8
    RC_MAP_VALUE_SHIFT = 0
    RC_PQ_ITEM_NONE = 0
    RC_PQ_ITEM_PTR = 1
    RC_PQ_ITEM_STRING = 2

    def emit(self, module: IRModule) -> str:
        self.entry_function_name = module.entry_function_name
        self.function_symbol_names = {
            function.name: ("@__tb_user_main" if function.name == self.entry_function_name else f"@{function.name}")
            for function in module.functions
        }
        self.global_variable_types: dict[str, str] = {}
        self.global_variable_symbols: dict[str, str] = {}
        self.global_file_symbols: dict[str, str] = {}
        self.global_instructions = module.instructions.copy() if self.entry_function_name is not None else []
        self.global_init_mode = False
        lines = [
            "declare i32 @printf(ptr, ...)",
            "declare i32 @puts(ptr)",
            "declare ptr @fopen(ptr, ptr)",
            "declare i32 @fprintf(ptr, ptr, ...)",
            "declare i32 @fclose(ptr)",
            "declare ptr @memmove(ptr, ptr, i64)",
            "declare void @free(ptr)",
            "declare i64 @strlen(ptr)",
            "declare ptr @malloc(i64)",
            "declare ptr @memcpy(ptr, ptr, i64)",
            "declare void @qsort(ptr, i64, i64, ptr)",
            "declare i64 @fread(ptr, i64, i64, ptr)",
            "declare i32 @fseek(ptr, i64, i32)",
            "declare i64 @ftell(ptr)",
            "declare i32 @gettimeofday(ptr, ptr)",
            "declare i32 @strcmp(ptr, ptr)",
            "declare ptr @strstr(ptr, ptr)",
            "declare i64 @strtoll(ptr, ptr, i32)",
            "declare i32 @snprintf(ptr, i64, ptr, ...)",
            "declare i64 @llvm.ctpop.i64(i64)",
            "declare void @abort() noreturn",
        ]
        for function in foreign_module_functions(module.foreign_modules):
            if function.llvm_declaration not in lines:
                lines.append(function.llvm_declaration)

        lines.append("")
        lines.append(f"{self.RC_HEADER_TYPE_NAME} = type {{ i64, i32, i32 }}")
        lines.append(f"{self.ARRAY_TYPE_NAME} = type {{ i64, i64, ptr }}")
        lines.append(f"{self.SET_TYPE_NAME} = type {{ i64, i64, ptr, i64, ptr, ptr }}")
        lines.append(f"{self.MAP_TYPE_NAME} = type {{ i64, i64, ptr, ptr, ptr }}")
        lines.append(f"{self.PRIORITY_QUEUE_TYPE_NAME} = type {{ ptr, ptr, i64, i32 }}")
        lines.append(f"{self.CACHE_TYPE_NAME} = type {{ i64, i64, ptr, ptr, ptr }}")
        lines.append(f"{self.ARENA_CHUNK_TYPE_NAME} = type {{ ptr, ptr, i64, i64 }}")
        lines.append(f"{self.ARENA_MARK_TYPE_NAME} = type {{ ptr, i64, i64 }}")
        lines.append("@__tb_arena_head = internal global ptr null")
        lines.append("@__tb_arena_current = internal global ptr null")
        lines.append("@__tb_arena_total = internal global i64 0")
        lines.append("@__tb_exception_pending = internal global i1 false")
        lines.append("@__tb_exception_message = internal global ptr null")
        lines.append("@__tb_stat_array_new_calls = internal global i64 0")
        lines.append("@__tb_stat_array_new_bytes = internal global i64 0")
        lines.append("@__tb_stat_array_grow_calls = internal global i64 0")
        lines.append("@__tb_stat_array_grow_old_bytes = internal global i64 0")
        lines.append("@__tb_stat_array_grow_new_bytes = internal global i64 0")
        lines.append("@__tb_stat_array_push_calls = internal global i64 0")
        lines.append("@__tb_stat_string_new_calls = internal global i64 0")
        lines.append("@__tb_stat_string_new_bytes = internal global i64 0")
        lines.append("@__tb_stat_string_clone_calls = internal global i64 0")
        lines.append("@__tb_stat_string_clone_bytes = internal global i64 0")
        lines.append("@__tb_stat_string_copy_range_calls = internal global i64 0")
        lines.append("@__tb_stat_string_copy_range_bytes = internal global i64 0")
        lines.append('@__tb_runtime_stats_path = private unnamed_addr constant [21 x i8] c"tb_runtime_stats.txt\\00"')
        lines.append('@__tb_runtime_stats_mode = private unnamed_addr constant [2 x i8] c"w\\00"')
        lines.append('@__tb_runtime_stats_fmt_array_new_calls = private unnamed_addr constant [22 x i8] c"array_new_calls=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_array_new_bytes = private unnamed_addr constant [22 x i8] c"array_new_bytes=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_array_grow_calls = private unnamed_addr constant [23 x i8] c"array_grow_calls=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_array_grow_old_bytes = private unnamed_addr constant [27 x i8] c"array_grow_old_bytes=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_array_grow_new_bytes = private unnamed_addr constant [27 x i8] c"array_grow_new_bytes=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_array_push_calls = private unnamed_addr constant [23 x i8] c"array_push_calls=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_string_new_calls = private unnamed_addr constant [23 x i8] c"string_new_calls=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_string_new_bytes = private unnamed_addr constant [23 x i8] c"string_new_bytes=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_string_clone_calls = private unnamed_addr constant [25 x i8] c"string_clone_calls=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_string_clone_bytes = private unnamed_addr constant [25 x i8] c"string_clone_bytes=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_string_copy_range_calls = private unnamed_addr constant [30 x i8] c"string_copy_range_calls=%lld\\0A\\00"')
        lines.append('@__tb_runtime_stats_fmt_string_copy_range_bytes = private unnamed_addr constant [30 x i8] c"string_copy_range_bytes=%lld\\0A\\00"')
        self.record_types = {record_type.name: record_type for record_type in module.record_types}
        self.record_type_ids = {record_type.name: index + 1 for index, record_type in enumerate(module.record_types)}
        self.sort_comparator_helpers: dict[tuple[str, str], str] = {}
        self.enum_types: dict[str, list[str]] = {}
        self.generic_set_helper_types: set[str] = set()
        self.generic_map_helper_types: set[tuple[str, str]] = set()
        self.record_field_indices = {
            record_type.name: {field.name: index for index, field in enumerate(record_type.fields)}
            for record_type in module.record_types
        }
        for record_type in module.record_types:
            field_types = ", ".join(self._llvm_type_for(field.type_name) for field in record_type.fields) or "i8"
            lines.append(f"%record.{record_type.name} = type {{ {field_types} }}")
        lines.append("")
        for string in module.strings:
            encoded = self._encode_string_literal(string.value)
            lines.append(
                f"@{string.label} = private unnamed_addr constant [{len(encoded)} x i8] c\"{self._escape_bytes(encoded)}\""
            )
        for function in module.functions:
            if function.cached:
                lines.append(f"@{self._cached_cache_symbol(function.name)} = internal global ptr null")
        for instruction in self.global_instructions:
            if isinstance(instruction, IRDeclareInt):
                self.global_variable_types[instruction.name] = "int"
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global i64 0")
            elif isinstance(instruction, IRDeclareBool):
                self.global_variable_types[instruction.name] = "bool"
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global i1 false")
            elif isinstance(instruction, IRDeclareString):
                self.global_variable_types[instruction.name] = "string"
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global ptr null")
            elif isinstance(instruction, IRDeclareMap):
                self.global_variable_types[instruction.name] = instruction.type_name
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global ptr null")
            elif isinstance(instruction, IRDeclareArray):
                self.global_variable_types[instruction.name] = instruction.type_name
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global ptr null")
            elif isinstance(instruction, IRDeclarePriorityQueue):
                self.global_variable_types[instruction.name] = instruction.type_name
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global ptr null")
            elif isinstance(instruction, IRDeclareRecord):
                self.global_variable_types[instruction.name] = instruction.type_name
                self.global_variable_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global ptr null")
            elif isinstance(instruction, IRDeclareFile):
                self.global_file_symbols[instruction.name] = self._global_symbol(instruction.name)
                lines.append(f"@{self._global_symbol(instruction.name)} = internal global ptr null")
        lines.append(
            f"@{self.INT_FORMAT_LABEL} = private unnamed_addr constant [{len(self.INT_FORMAT_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.INT_FORMAT_BYTES)}"'
        )
        lines.append(
            f"@{self.FILE_MODE_LABEL} = private unnamed_addr constant [{len(self.FILE_MODE_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.FILE_MODE_BYTES)}"'
        )
        lines.append(
            f"@{self.FILE_READ_MODE_LABEL} = private unnamed_addr constant [{len(self.FILE_READ_MODE_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.FILE_READ_MODE_BYTES)}"'
        )
        lines.append(
            f"@{self.FILE_LINE_FORMAT_LABEL} = private unnamed_addr constant [{len(self.FILE_LINE_FORMAT_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.FILE_LINE_FORMAT_BYTES)}"'
        )
        lines.append(
            f"@{self.INT_TO_STRING_FORMAT_LABEL} = private unnamed_addr constant [{len(self.INT_TO_STRING_FORMAT_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.INT_TO_STRING_FORMAT_BYTES)}"'
        )
        lines.append(
            f"@{self.NEWLINE_LABEL} = private unnamed_addr constant [{len(self.NEWLINE_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.NEWLINE_BYTES)}"'
        )
        lines.append(
            f"@{self.BOOL_TRUE_LABEL} = private unnamed_addr constant [{len(self.BOOL_TRUE_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.BOOL_TRUE_BYTES)}"'
        )
        lines.append(
            f"@{self.BOOL_FALSE_LABEL} = private unnamed_addr constant [{len(self.BOOL_FALSE_BYTES)} x i8] "
            f'c"{self._escape_bytes(self.BOOL_FALSE_BYTES)}"'
        )

        lines.append("")
        string_lengths = {string.label: len(self._encode_string_literal(string.value)) for string in module.strings}
        self.string_lengths = string_lengths
        lines.extend(self._emit_runtime_helpers())
        lines.append("")

        for function in module.functions:
            lines.extend(self._emit_function_definition(function, string_lengths))
        lines.append("")

        if self.entry_function_name is None:
            lines.append("define i32 @main() {")
            lines.append("entry:")
            main_entry_index = len(lines)
            self._reset_function_state()
            self.function_exception_label = self._next_label("exc.unwind")
            terminated = False
            for instruction in module.instructions:
                terminated = self._emit_instruction(instruction, lines, string_lengths)
                if terminated:
                    break
            lines[main_entry_index:main_entry_index] = self.alloca_lines
            if not terminated:
                self._emit_close_open_files(lines)
                lines.append("  call void @tb_dump_runtime_stats()")
                lines.append("  call void @tb_arena_destroy()")
                lines.append("  ret i32 0")
            if self.exception_dispatch_used:
                lines.append(f"{self.function_exception_label}:")
                self._emit_close_open_files(lines)
                lines.append("  call void @tb_report_uncaught_exception()")
                lines.append("  call void @tb_clear_exception()")
                lines.append("  call void @tb_dump_runtime_stats()")
                lines.append("  call void @tb_arena_destroy()")
                lines.append("  ret i32 1")
            lines.append("}")
        else:
            lines.extend(self._emit_entry_wrapper())
        if self.sort_comparator_helpers:
            lines.append("")
            lines.extend(self._emit_sort_comparator_helpers())
        generic_set_types = sorted(self.generic_set_helper_types)
        generic_map_types = sorted(self.generic_map_helper_types)
        if generic_set_types:
            lines.append("")
            for item_type in generic_set_types:
                lines.extend(self._emit_generic_set_helpers(item_type))
        if generic_map_types:
            lines.append("")
            for key_type, value_type in generic_map_types:
                lines.extend(self._emit_generic_map_helpers(key_type, value_type))
        return "\n".join(lines) + "\n"

    @staticmethod
    def _global_symbol(name: str) -> str:
        return f"__tb_global_{name}"

    @staticmethod
    def _encode_string_literal(value: str) -> bytes:
        return value.encode("utf-8") + b"\0"

    @staticmethod
    def _escape_bytes(data: bytes) -> str:
        parts: list[str] = []
        for byte in data:
            if 32 <= byte <= 126 and byte not in {34, 92}:
                parts.append(chr(byte))
            else:
                parts.append(f"\\{byte:02X}")
        return "".join(parts)

    def _emit_runtime_helpers(self) -> list[str]:
        helpers = [
            "define private void @tb_dump_runtime_stats() {",
            "entry:",
            "  %path.ptr = getelementptr inbounds [21 x i8], ptr @__tb_runtime_stats_path, i64 0, i64 0",
            "  %mode.ptr = getelementptr inbounds [2 x i8], ptr @__tb_runtime_stats_mode, i64 0, i64 0",
            "  %file = call ptr @fopen(ptr %path.ptr, ptr %mode.ptr)",
            "  %file.null = icmp eq ptr %file, null",
            "  br i1 %file.null, label %done, label %write",
            "write:",
            "  %array.new.calls = load i64, ptr @__tb_stat_array_new_calls",
            "  %array.new.bytes = load i64, ptr @__tb_stat_array_new_bytes",
            "  %array.grow.calls = load i64, ptr @__tb_stat_array_grow_calls",
            "  %array.grow.old.bytes = load i64, ptr @__tb_stat_array_grow_old_bytes",
            "  %array.grow.new.bytes = load i64, ptr @__tb_stat_array_grow_new_bytes",
            "  %array.push.calls = load i64, ptr @__tb_stat_array_push_calls",
            "  %string.new.calls = load i64, ptr @__tb_stat_string_new_calls",
            "  %string.new.bytes = load i64, ptr @__tb_stat_string_new_bytes",
            "  %string.clone.calls = load i64, ptr @__tb_stat_string_clone_calls",
            "  %string.clone.bytes = load i64, ptr @__tb_stat_string_clone_bytes",
            "  %string.copy.range.calls = load i64, ptr @__tb_stat_string_copy_range_calls",
            "  %string.copy.range.bytes = load i64, ptr @__tb_stat_string_copy_range_bytes",
            "  %fmt.array.new.calls = getelementptr inbounds [22 x i8], ptr @__tb_runtime_stats_fmt_array_new_calls, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.array.new.calls, i64 %array.new.calls)",
            "  %fmt.array.new.bytes = getelementptr inbounds [22 x i8], ptr @__tb_runtime_stats_fmt_array_new_bytes, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.array.new.bytes, i64 %array.new.bytes)",
            "  %fmt.array.grow.calls = getelementptr inbounds [23 x i8], ptr @__tb_runtime_stats_fmt_array_grow_calls, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.array.grow.calls, i64 %array.grow.calls)",
            "  %fmt.array.grow.old.bytes = getelementptr inbounds [27 x i8], ptr @__tb_runtime_stats_fmt_array_grow_old_bytes, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.array.grow.old.bytes, i64 %array.grow.old.bytes)",
            "  %fmt.array.grow.new.bytes = getelementptr inbounds [27 x i8], ptr @__tb_runtime_stats_fmt_array_grow_new_bytes, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.array.grow.new.bytes, i64 %array.grow.new.bytes)",
            "  %fmt.array.push.calls = getelementptr inbounds [23 x i8], ptr @__tb_runtime_stats_fmt_array_push_calls, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.array.push.calls, i64 %array.push.calls)",
            "  %fmt.string.new.calls = getelementptr inbounds [23 x i8], ptr @__tb_runtime_stats_fmt_string_new_calls, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.string.new.calls, i64 %string.new.calls)",
            "  %fmt.string.new.bytes = getelementptr inbounds [23 x i8], ptr @__tb_runtime_stats_fmt_string_new_bytes, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.string.new.bytes, i64 %string.new.bytes)",
            "  %fmt.string.clone.calls = getelementptr inbounds [25 x i8], ptr @__tb_runtime_stats_fmt_string_clone_calls, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.string.clone.calls, i64 %string.clone.calls)",
            "  %fmt.string.clone.bytes = getelementptr inbounds [25 x i8], ptr @__tb_runtime_stats_fmt_string_clone_bytes, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.string.clone.bytes, i64 %string.clone.bytes)",
            "  %fmt.string.copy.range.calls = getelementptr inbounds [30 x i8], ptr @__tb_runtime_stats_fmt_string_copy_range_calls, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.string.copy.range.calls, i64 %string.copy.range.calls)",
            "  %fmt.string.copy.range.bytes = getelementptr inbounds [30 x i8], ptr @__tb_runtime_stats_fmt_string_copy_range_bytes, i64 0, i64 0",
            "  call i32 (ptr, ptr, ...) @fprintf(ptr %file, ptr %fmt.string.copy.range.bytes, i64 %string.copy.range.bytes)",
            "  call i32 @fclose(ptr %file)",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_reset_runtime_stats() {",
            "entry:",
            "  store i64 0, ptr @__tb_stat_array_new_calls",
            "  store i64 0, ptr @__tb_stat_array_new_bytes",
            "  store i64 0, ptr @__tb_stat_array_grow_calls",
            "  store i64 0, ptr @__tb_stat_array_grow_old_bytes",
            "  store i64 0, ptr @__tb_stat_array_grow_new_bytes",
            "  store i64 0, ptr @__tb_stat_array_push_calls",
            "  store i64 0, ptr @__tb_stat_string_new_calls",
            "  store i64 0, ptr @__tb_stat_string_new_bytes",
            "  store i64 0, ptr @__tb_stat_string_clone_calls",
            "  store i64 0, ptr @__tb_stat_string_clone_bytes",
            "  store i64 0, ptr @__tb_stat_string_copy_range_calls",
            "  store i64 0, ptr @__tb_stat_string_copy_range_bytes",
            "  ret void",
            "}",
            "",
            "define private void @tb_abort_oom() {",
            "entry:",
            "  call void @abort()",
            "  unreachable",
            "}",
            "",
            "define private ptr @tb_retain(ptr %value) {",
            "entry:",
            "  %is.null = icmp eq ptr %value, null",
            "  br i1 %is.null, label %done, label %retain",
            "retain:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            f"  %magic = and i32 %flags, {self.RC_FLAGS_MAGIC_MASK}",
            f"  %is.managed = icmp eq i32 %magic, {self.RC_FLAGS_MAGIC}",
            "  br i1 %is.managed, label %retain.managed, label %done",
            "retain.managed:",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 0",
            "  %refcount = load i64, ptr %refcount.ptr",
            "  %next.refcount = add i64 %refcount, 1",
            "  store i64 %next.refcount, ptr %refcount.ptr",
            "  br label %done",
            "done:",
            "  ret ptr %value",
            "}",
            "",
            "define private void @tb_release(ptr %value) {",
            "entry:",
            "  %is.null = icmp eq ptr %value, null",
            "  br i1 %is.null, label %done, label %release",
            "release:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            f"  %magic = and i32 %flags, {self.RC_FLAGS_MAGIC_MASK}",
            f"  %is.managed = icmp eq i32 %magic, {self.RC_FLAGS_MAGIC}",
            "  br i1 %is.managed, label %release.managed, label %done",
            "release.managed:",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 0",
            "  %refcount = load i64, ptr %refcount.ptr",
            "  %next.refcount = sub i64 %refcount, 1",
            "  store i64 %next.refcount, ptr %refcount.ptr",
            "  %is.zero = icmp eq i64 %next.refcount, 0",
            "  br i1 %is.zero, label %destroy, label %done",
            "destroy:",
            "  call void @tb_destroy_refcounted(ptr %value)",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_set_exception(ptr %message) {",
            "entry:",
            "  %old.pending = load i1, ptr @__tb_exception_pending",
            "  br i1 %old.pending, label %release.old, label %store.new",
            "release.old:",
            "  %old.message = load ptr, ptr @__tb_exception_message",
            "  call void @tb_release(ptr %old.message)",
            "  br label %store.new",
            "store.new:",
            "  %cloned = call ptr @tb_string_clone(ptr %message)",
            "  store ptr %cloned, ptr @__tb_exception_message",
            "  store i1 true, ptr @__tb_exception_pending",
            "  ret void",
            "}",
            "",
            "define private void @tb_clear_exception() {",
            "entry:",
            "  %pending = load i1, ptr @__tb_exception_pending",
            "  br i1 %pending, label %clear, label %done",
            "clear:",
            "  %message = load ptr, ptr @__tb_exception_message",
            "  call void @tb_release(ptr %message)",
            "  store ptr null, ptr @__tb_exception_message",
            "  store i1 false, ptr @__tb_exception_pending",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            f"@{self.UNCAUGHT_EXCEPTION_FORMAT_LABEL} = private unnamed_addr constant [{len(self.UNCAUGHT_EXCEPTION_FORMAT_BYTES)} x i8] c\"{self._escape_bytes(self.UNCAUGHT_EXCEPTION_FORMAT_BYTES)}\"",
            "define private void @tb_report_uncaught_exception() {",
            "entry:",
            "  %pending = load i1, ptr @__tb_exception_pending",
            "  br i1 %pending, label %report, label %done",
            "report:",
            f"  %fmt = getelementptr inbounds [{len(self.UNCAUGHT_EXCEPTION_FORMAT_BYTES)} x i8], ptr @{self.UNCAUGHT_EXCEPTION_FORMAT_LABEL}, i32 0, i32 0",
            "  %message = load ptr, ptr @__tb_exception_message",
            "  call i32 (ptr, ...) @printf(ptr %fmt, ptr %message)",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_destroy_refcounted(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %kind.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 1",
            "  %kind = load i32, ptr %kind.ptr",
            f"  %is.string = icmp eq i32 %kind, {self.RC_KIND_STRING}",
            f"  %is.array = icmp eq i32 %kind, {self.RC_KIND_ARRAY}",
            f"  %is.record = icmp eq i32 %kind, {self.RC_KIND_RECORD}",
            f"  %is.set = icmp eq i32 %kind, {self.RC_KIND_SET}",
            f"  %is.map = icmp eq i32 %kind, {self.RC_KIND_MAP}",
            f"  %is.pq = icmp eq i32 %kind, {self.RC_KIND_PRIORITY_QUEUE}",
            "  br i1 %is.string, label %destroy.string, label %check.array",
            "check.array:",
            "  br i1 %is.array, label %destroy.array, label %check.record",
            "check.record:",
            "  br i1 %is.record, label %destroy.record, label %check.set",
            "check.set:",
            "  br i1 %is.set, label %destroy.set, label %check.map",
            "check.map:",
            "  br i1 %is.map, label %destroy.map, label %check.pq",
            "check.pq:",
            "  br i1 %is.pq, label %destroy.pq, label %unknown",
            "destroy.string:",
            "  call void @tb_destroy_string(ptr %value)",
            "  ret void",
            "destroy.array:",
            "  call void @tb_destroy_array(ptr %value)",
            "  ret void",
            "destroy.record:",
            "  call void @tb_destroy_record(ptr %value)",
            "  ret void",
            "destroy.set:",
            "  call void @tb_destroy_set(ptr %value)",
            "  ret void",
            "destroy.map:",
            "  call void @tb_destroy_map(ptr %value)",
            "  ret void",
            "destroy.pq:",
            "  call void @tb_destroy_priority_queue(ptr %value)",
            "  ret void",
            "unknown:",
            "  call void @abort()",
            "  unreachable",
            "}",
            "",
            "define private void @tb_destroy_string(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            "  call void @free(ptr %header)",
            "  ret void",
            "}",
            "",
            "define private void @tb_destroy_array(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            f"  %array.flags = and i32 %flags, {0xFFFF}",
            f"  %release.ptrs = icmp eq i32 %array.flags, {self.RC_ARRAY_RELEASE_PTRS}",
            "  br i1 %release.ptrs, label %release.loop, label %free",
            "release.loop:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %value, i32 0, i32 0",
            f"  %data.ptr.release = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %value, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data.release = load ptr, ptr %data.ptr.release",
            "  br label %release.iter",
            "release.iter:",
            "  %index = phi i64 [ 0, %release.loop ], [ %next.index, %release.body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %release.body, label %free",
            "release.body:",
            "  %slot = getelementptr inbounds ptr, ptr %data.release, i64 %index",
            "  %item = load ptr, ptr %slot",
            "  call void @tb_release(ptr %item)",
            "  %next.index = add i64 %index, 1",
            "  br label %release.iter",
            "free:",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %value, i32 0, i32 2",
            "  %data = load ptr, ptr %data.ptr",
            "  call void @free(ptr %data)",
            "  call void @free(ptr %header)",
            "  ret void",
            "}",
            "",
            "define private void @tb_destroy_record(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            f"  %record.id = and i32 %flags, {0xFFFF}",
        ]
        for record_type in self.record_types.values():
            record_id = self.record_type_ids[record_type.name]
            helpers.extend(
                [
                    f"  %is.{record_type.name} = icmp eq i32 %record.id, {record_id}",
                    f"  br i1 %is.{record_type.name}, label %destroy.{record_type.name}, label %check.{record_type.name}",
                    f"destroy.{record_type.name}:",
                    f"  call void {self._record_destroy_symbol(record_type.name)}(ptr %value)",
                    "  ret void",
                    f"check.{record_type.name}:",
                ]
            )
        helpers.extend(
            [
            "  call void @abort()",
            "  unreachable",
            "}",
            "",
            "define private void @tb_destroy_set(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            f"  %set.flags = and i32 %flags, {0xFFFF}",
            f"  %release.ptrs = icmp eq i32 %set.flags, {self.RC_SET_RELEASE_PTRS}",
            "  br i1 %release.ptrs, label %release.loop, label %free",
            "release.loop:",
            f"  %len.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %value, i32 0, i32 0",
            f"  %data.ptr.release = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %value, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data.release = load ptr, ptr %data.ptr.release",
            "  br label %release.iter",
            "release.iter:",
            "  %index = phi i64 [ 0, %release.loop ], [ %next.index, %release.body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %release.body, label %free",
            "release.body:",
            "  %slot = getelementptr inbounds ptr, ptr %data.release, i64 %index",
            "  %item = load ptr, ptr %slot",
            "  call void @tb_release(ptr %item)",
            "  %next.index = add i64 %index, 1",
            "  br label %release.iter",
            "free:",
            f"  %data.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %value, i32 0, i32 2",
            f"  %hashes.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %value, i32 0, i32 4",
            f"  %index.values.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %value, i32 0, i32 5",
            "  %data = load ptr, ptr %data.ptr",
            "  %hashes = load ptr, ptr %hashes.ptr",
            "  %index.values = load ptr, ptr %index.values.ptr",
            "  call void @free(ptr %data)",
            "  call void @free(ptr %hashes)",
            "  call void @free(ptr %index.values)",
            "  call void @free(ptr %header)",
            "  ret void",
            "}",
            "",
            "define private void @tb_destroy_map(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            f"  %key.flags = lshr i32 %flags, {self.RC_MAP_KEY_SHIFT}",
            f"  %key.release = and i32 %key.flags, {self.RC_MAP_RELEASE_PTRS}",
            f"  %value.flags = lshr i32 %flags, {self.RC_MAP_VALUE_SHIFT}",
            f"  %value.release = and i32 %value.flags, {self.RC_MAP_RELEASE_PTRS}",
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %value, i32 0, i32 0",
            f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %value, i32 0, i32 2",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %value, i32 0, i32 3",
            f"  %index.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %value, i32 0, i32 4",
            "  %len = load i64, ptr %len.ptr",
            "  %keys = load ptr, ptr %keys.ptr",
            "  %values = load ptr, ptr %values.ptr",
            "  %index = load ptr, ptr %index.ptr",
            f"  %needs.release = or i32 %key.release, %value.release",
            f"  %should.release = icmp ne i32 %needs.release, {self.RC_MAP_RELEASE_NONE}",
            "  br i1 %should.release, label %release.loop, label %free",
            "release.loop:",
            "  %index.iter = phi i64 [ 0, %entry ], [ %next.index, %release.advance ]",
            "  %more = icmp slt i64 %index.iter, %len",
            "  br i1 %more, label %release.body, label %free",
            "release.body:",
            f"  %release.keys = icmp eq i32 %key.release, {self.RC_MAP_RELEASE_PTRS}",
            "  br i1 %release.keys, label %release.key, label %release.value.check",
            "release.key:",
            "  %key.slot = getelementptr inbounds ptr, ptr %keys, i64 %index.iter",
            "  %key.item = load ptr, ptr %key.slot",
            "  call void @tb_release(ptr %key.item)",
            "  br label %release.value.check",
            "release.value.check:",
            f"  %release.values = icmp eq i32 %value.release, {self.RC_MAP_RELEASE_PTRS}",
            "  br i1 %release.values, label %release.value, label %release.advance",
            "release.value:",
            "  %value.slot = getelementptr inbounds ptr, ptr %values, i64 %index.iter",
            "  %value.item = load ptr, ptr %value.slot",
            "  call void @tb_release(ptr %value.item)",
            "  br label %release.advance",
            "release.advance:",
            "  %next.index = add i64 %index.iter, 1",
            "  br label %release.loop",
            "free:",
            f"  %index.hashes.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %index, i32 0, i32 2",
            f"  %index.keys.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %index, i32 0, i32 3",
            f"  %index.values.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %index, i32 0, i32 4",
            "  %index.hashes = load ptr, ptr %index.hashes.ptr",
            "  %index.keys = load ptr, ptr %index.keys.ptr",
            "  %index.values = load ptr, ptr %index.values.ptr",
            "  call void @free(ptr %keys)",
            "  call void @free(ptr %values)",
            "  call void @free(ptr %index.hashes)",
            "  call void @free(ptr %index.keys)",
            "  call void @free(ptr %index.values)",
            "  call void @free(ptr %index)",
            "  call void @free(ptr %header)",
            "  ret void",
            "}",
            "",
            "define private void @tb_destroy_priority_queue(ptr %value) {",
            "entry:",
            f"  %header = getelementptr inbounds i8, ptr %value, i64 -{self.RC_HEADER_SIZE}",
            f"  %array.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %value, i32 0, i32 0",
            "  %array = load ptr, ptr %array.ptr",
            "  call void @tb_release(ptr %array)",
            "  call void @free(ptr %header)",
            "  ret void",
            "}",
            "",
            "define private ptr @tb_string_new(i64 %length) {",
            "entry:",
            f"  %total.size = add i64 %length, {self.RC_HEADER_SIZE + 1}",
            "  %allocation = call ptr @malloc(i64 %total.size)",
            "  %is.null = icmp eq ptr %allocation, null",
            "  br i1 %is.null, label %fail, label %init",
            "fail:",
            "  call void @tb_abort_oom()",
            "  unreachable",
            "init:",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 0",
            f"  %kind.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 1",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 2",
            "  store i64 1, ptr %refcount.ptr",
            f"  store i32 {self.RC_KIND_STRING}, ptr %kind.ptr",
            f"  store i32 {self.RC_FLAGS_MAGIC}, ptr %flags.ptr",
            f"  %payload = getelementptr inbounds i8, ptr %allocation, i64 {self.RC_HEADER_SIZE}",
            "  %terminator = getelementptr inbounds i8, ptr %payload, i64 %length",
            "  store i8 0, ptr %terminator",
            "  %string.new.calls = load i64, ptr @__tb_stat_string_new_calls",
            "  %string.new.calls.next = add i64 %string.new.calls, 1",
            "  store i64 %string.new.calls.next, ptr @__tb_stat_string_new_calls",
            "  %string.new.bytes = load i64, ptr @__tb_stat_string_new_bytes",
            "  %string.new.bytes.next = add i64 %string.new.bytes, %length",
            "  store i64 %string.new.bytes.next, ptr @__tb_stat_string_new_bytes",
            "  ret ptr %payload",
            "}",
            "",
            "define private ptr @tb_string_clone(ptr %source) {",
            "entry:",
            "  %is.null = icmp eq ptr %source, null",
            "  br i1 %is.null, label %null, label %copy",
            "null:",
            "  ret ptr null",
            "copy:",
            "  %length = call i64 @strlen(ptr %source)",
            "  %buffer = call ptr @tb_string_new(i64 %length)",
            "  %string.clone.calls = load i64, ptr @__tb_stat_string_clone_calls",
            "  %string.clone.calls.next = add i64 %string.clone.calls, 1",
            "  store i64 %string.clone.calls.next, ptr @__tb_stat_string_clone_calls",
            "  %string.clone.bytes = load i64, ptr @__tb_stat_string_clone_bytes",
            "  %string.clone.bytes.next = add i64 %string.clone.bytes, %length",
            "  store i64 %string.clone.bytes.next, ptr @__tb_stat_string_clone_bytes",
            "  call ptr @memcpy(ptr %buffer, ptr %source, i64 %length)",
            "  %terminator = getelementptr inbounds i8, ptr %buffer, i64 %length",
            "  store i8 0, ptr %terminator",
            "  ret ptr %buffer",
            "}",
            "",
            "define private ptr @tb_arena_new_chunk(i64 %minimum) {",
            "entry:",
            "  %current = load ptr, ptr @__tb_arena_current",
            "  %has.current = icmp ne ptr %current, null",
            "  br i1 %has.current, label %use.current, label %use.initial",
            "use.current:",
            f"  %current.cap.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %current, i32 0, i32 2",
            "  %current.cap = load i64, ptr %current.cap.ptr",
            "  %grown.cap = mul i64 %current.cap, 2",
            "  br label %choose",
            "use.initial:",
            "  br label %choose",
            "choose:",
            f"  %base.capacity = phi i64 [ {self.ARENA_INITIAL_CHUNK_BYTES}, %use.initial ], [ %grown.cap, %use.current ]",
            "  %base.fits = icmp uge i64 %base.capacity, %minimum",
            "  %capacity = select i1 %base.fits, i64 %base.capacity, i64 %minimum",
            "  %total = load i64, ptr @__tb_arena_total",
            f"  %within.limit = icmp ule i64 %total, {self.ARENA_MAX_BYTES}",
            "  br i1 %within.limit, label %remaining, label %fail",
            "remaining:",
            f"  %remaining.bytes = sub i64 {self.ARENA_MAX_BYTES}, %total",
            "  %fits.limit = icmp ule i64 %capacity, %remaining.bytes",
            "  br i1 %fits.limit, label %alloc, label %fail",
            "alloc:",
            "  %data = call ptr @malloc(i64 %capacity)",
            "  %chunk = call ptr @malloc(i64 32)",
            f"  %next.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 1",
            f"  %cap.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 2",
            f"  %used.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 3",
            "  store ptr null, ptr %next.ptr",
            "  store ptr %data, ptr %data.ptr",
            "  store i64 %capacity, ptr %cap.ptr",
            "  store i64 0, ptr %used.ptr",
            "  %head = load ptr, ptr @__tb_arena_head",
            "  %head.is.null = icmp eq ptr %head, null",
            "  br i1 %head.is.null, label %store.head, label %append",
            "store.head:",
            "  store ptr %chunk, ptr @__tb_arena_head",
            "  br label %set.current",
            "append:",
            f"  %current.next.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %current, i32 0, i32 0",
            "  store ptr %chunk, ptr %current.next.ptr",
            "  br label %set.current",
            "set.current:",
            "  store ptr %chunk, ptr @__tb_arena_current",
            "  %next.total = add i64 %total, %capacity",
            "  store i64 %next.total, ptr @__tb_arena_total",
            "  ret ptr %chunk",
            "fail:",
            "  call void @tb_abort_oom()",
            "  unreachable",
            "}",
            "",
            "define private ptr @tb_alloc(i64 %size) {",
            "entry:",
            "  %size.is.zero = icmp eq i64 %size, 0",
            "  %requested = select i1 %size.is.zero, i64 1, i64 %size",
            "  %aligned.plus = add i64 %requested, 7",
            "  %aligned = and i64 %aligned.plus, -8",
            "  %current = load ptr, ptr @__tb_arena_current",
            "  %has.current = icmp ne ptr %current, null",
            "  br i1 %has.current, label %check, label %grow",
            "check:",
            f"  %check.used.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %current, i32 0, i32 3",
            f"  %check.cap.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %current, i32 0, i32 2",
            "  %check.used = load i64, ptr %check.used.ptr",
            "  %check.cap = load i64, ptr %check.cap.ptr",
            "  %check.next.used = add i64 %check.used, %aligned",
            "  %fits.current = icmp ule i64 %check.next.used, %check.cap",
            "  br i1 %fits.current, label %alloc.from.chunk, label %grow",
            "grow:",
            "  %grown.chunk = call ptr @tb_arena_new_chunk(i64 %aligned)",
            "  br label %alloc.from.chunk",
            "alloc.from.chunk:",
            "  %chunk = phi ptr [ %current, %check ], [ %grown.chunk, %grow ]",
            f"  %chunk.data.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 1",
            f"  %chunk.used.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 3",
            "  %chunk.data = load ptr, ptr %chunk.data.ptr",
            "  %chunk.used = load i64, ptr %chunk.used.ptr",
            "  %result = getelementptr inbounds i8, ptr %chunk.data, i64 %chunk.used",
            "  %chunk.next.used = add i64 %chunk.used, %aligned",
            "  store i64 %chunk.next.used, ptr %chunk.used.ptr",
            "  ret ptr %result",
            "}",
            "",
            "define private void @tb_arena_mark(ptr %mark) {",
            "entry:",
            f"  %mark.chunk.ptr = getelementptr inbounds {self.ARENA_MARK_TYPE_NAME}, ptr %mark, i32 0, i32 0",
            f"  %mark.used.ptr = getelementptr inbounds {self.ARENA_MARK_TYPE_NAME}, ptr %mark, i32 0, i32 1",
            f"  %mark.total.ptr = getelementptr inbounds {self.ARENA_MARK_TYPE_NAME}, ptr %mark, i32 0, i32 2",
            "  %current = load ptr, ptr @__tb_arena_current",
            "  %total = load i64, ptr @__tb_arena_total",
            "  %has.current = icmp ne ptr %current, null",
            "  br i1 %has.current, label %capture, label %empty",
            "capture:",
            f"  %current.used.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %current, i32 0, i32 3",
            "  %current.used = load i64, ptr %current.used.ptr",
            "  store ptr %current, ptr %mark.chunk.ptr",
            "  store i64 %current.used, ptr %mark.used.ptr",
            "  store i64 %total, ptr %mark.total.ptr",
            "  ret void",
            "empty:",
            "  store ptr null, ptr %mark.chunk.ptr",
            "  store i64 0, ptr %mark.used.ptr",
            "  store i64 %total, ptr %mark.total.ptr",
            "  ret void",
            "}",
            "",
            "define private void @tb_arena_reset(ptr %mark) {",
            "entry:",
            f"  %mark.chunk.ptr = getelementptr inbounds {self.ARENA_MARK_TYPE_NAME}, ptr %mark, i32 0, i32 0",
            f"  %mark.used.ptr = getelementptr inbounds {self.ARENA_MARK_TYPE_NAME}, ptr %mark, i32 0, i32 1",
            f"  %mark.total.ptr = getelementptr inbounds {self.ARENA_MARK_TYPE_NAME}, ptr %mark, i32 0, i32 2",
            "  %mark.chunk = load ptr, ptr %mark.chunk.ptr",
            "  %mark.used = load i64, ptr %mark.used.ptr",
            "  %mark.total = load i64, ptr %mark.total.ptr",
            "  %has.chunk = icmp ne ptr %mark.chunk, null",
            "  br i1 %has.chunk, label %restore, label %clear",
            "clear:",
            "  call void @tb_arena_destroy()",
            "  ret void",
            "restore:",
            f"  %restore.next.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %mark.chunk, i32 0, i32 0",
            f"  %restore.used.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %mark.chunk, i32 0, i32 3",
            "  %restore.next = load ptr, ptr %restore.next.ptr",
            "  br label %free.loop",
            "free.loop:",
            "  %free.chunk = phi ptr [ %restore.next, %restore ], [ %free.next, %free.body ]",
            "  %free.is.null = icmp eq ptr %free.chunk, null",
            "  br i1 %free.is.null, label %done, label %free.body",
            "free.body:",
            f"  %free.next.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %free.chunk, i32 0, i32 0",
            f"  %free.data.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %free.chunk, i32 0, i32 1",
            "  %free.next = load ptr, ptr %free.next.ptr",
            "  %free.data = load ptr, ptr %free.data.ptr",
            "  call void @free(ptr %free.data)",
            "  call void @free(ptr %free.chunk)",
            "  br label %free.loop",
            "done:",
            "  store ptr null, ptr %restore.next.ptr",
            "  store i64 %mark.used, ptr %restore.used.ptr",
            "  store ptr %mark.chunk, ptr @__tb_arena_current",
            "  store i64 %mark.total, ptr @__tb_arena_total",
            "  ret void",
            "}",
            "",
            "define private ptr @tb_heap_alloc(i64 %size) {",
            "entry:",
            "  %size.is.zero = icmp eq i64 %size, 0",
            "  %requested = select i1 %size.is.zero, i64 1, i64 %size",
            "  %allocation = call ptr @malloc(i64 %requested)",
            "  %is.null = icmp eq ptr %allocation, null",
            "  br i1 %is.null, label %fail, label %done",
            "fail:",
            "  call void @tb_abort_oom()",
            "  unreachable",
            "done:",
            "  ret ptr %allocation",
            "}",
            "",
            "define private ptr @tb_heap_grow_copy(ptr %old, i64 %old_size, i64 %new_size) {",
            "entry:",
            "  %new = call ptr @tb_heap_alloc(i64 %new_size)",
            "  call ptr @memcpy(ptr %new, ptr %old, i64 %old_size)",
            "  call void @free(ptr %old)",
            "  ret ptr %new",
            "}",
            "",
            "define private ptr @tb_grow_copy(ptr %old, i64 %old_size, i64 %new_size) {",
            "entry:",
            "  %new = call ptr @tb_alloc(i64 %new_size)",
            "  call ptr @memcpy(ptr %new, ptr %old, i64 %old_size)",
            "  ret ptr %new",
            "}",
            "",
            "define private void @tb_arena_destroy() {",
            "entry:",
            "  %head = load ptr, ptr @__tb_arena_head",
            "  br label %loop",
            "loop:",
            "  %chunk = phi ptr [ %head, %entry ], [ %next, %body ]",
            "  %is.null = icmp eq ptr %chunk, null",
            "  br i1 %is.null, label %done, label %body",
            "body:",
            f"  %next.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARENA_CHUNK_TYPE_NAME}, ptr %chunk, i32 0, i32 1",
            "  %next = load ptr, ptr %next.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  call void @free(ptr %data)",
            "  call void @free(ptr %chunk)",
            "  br label %loop",
            "done:",
            "  store ptr null, ptr @__tb_arena_head",
            "  store ptr null, ptr @__tb_arena_current",
            "  store i64 0, ptr @__tb_arena_total",
            "  ret void",
            "}",
            "",
            "define private ptr @tb_array_new(i64 %initial_capacity, i64 %elem_size, i32 %release_mode) {",
            "entry:",
            "  %capacity.is_zero = icmp eq i64 %initial_capacity, 0",
            "  %capacity = select i1 %capacity.is_zero, i64 4, i64 %initial_capacity",
            f"  %total.size = add i64 24, {self.RC_HEADER_SIZE}",
            "  %allocation = call ptr @tb_heap_alloc(i64 %total.size)",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 0",
            f"  %kind.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 1",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 2",
            "  store i64 1, ptr %refcount.ptr",
            f"  store i32 {self.RC_KIND_ARRAY}, ptr %kind.ptr",
            f"  %array.flags = or i32 {self.RC_FLAGS_MAGIC}, %release_mode",
            "  store i32 %array.flags, ptr %flags.ptr",
            f"  %array = getelementptr inbounds i8, ptr %allocation, i64 {self.RC_HEADER_SIZE}",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 1",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %data.size = mul i64 %capacity, %elem_size",
            "  %data = call ptr @tb_heap_alloc(i64 %data.size)",
            "  %array.new.calls = load i64, ptr @__tb_stat_array_new_calls",
            "  %array.new.calls.next = add i64 %array.new.calls, 1",
            "  store i64 %array.new.calls.next, ptr @__tb_stat_array_new_calls",
            "  %array.new.bytes = load i64, ptr @__tb_stat_array_new_bytes",
            "  %array.new.bytes.next = add i64 %array.new.bytes, %data.size",
            "  store i64 %array.new.bytes.next, ptr @__tb_stat_array_new_bytes",
            "  store i64 0, ptr %len.ptr",
            "  store i64 %capacity, ptr %cap.ptr",
            "  store ptr %data, ptr %data.ptr",
            "  ret ptr %array",
            "}",
            "",
            "define private ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size) {",
            "entry:",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %data = load ptr, ptr %data.ptr",
            "  %offset = mul i64 %index, %elem_size",
            "  %element = getelementptr inbounds i8, ptr %data, i64 %offset",
            "  ret ptr %element",
            "}",
            "",
            "define private void @tb_array_reserve_for_push(ptr %array, i64 %elem_size) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 1",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %cap = load i64, ptr %cap.ptr",
            "  %has.capacity = icmp slt i64 %len, %cap",
            "  br i1 %has.capacity, label %done, label %grow",
            "grow:",
            "  %cap.is_zero = icmp eq i64 %cap, 0",
            "  %doubled = mul i64 %cap, 2",
            "  %new.cap = select i1 %cap.is_zero, i64 4, i64 %doubled",
            "  %old.data = load ptr, ptr %data.ptr",
            "  %old.size = mul i64 %cap, %elem_size",
            "  %new.size = mul i64 %new.cap, %elem_size",
            "  %new.data = call ptr @tb_heap_grow_copy(ptr %old.data, i64 %old.size, i64 %new.size)",
            "  %array.grow.calls = load i64, ptr @__tb_stat_array_grow_calls",
            "  %array.grow.calls.next = add i64 %array.grow.calls, 1",
            "  store i64 %array.grow.calls.next, ptr @__tb_stat_array_grow_calls",
            "  %array.grow.old.bytes = load i64, ptr @__tb_stat_array_grow_old_bytes",
            "  %array.grow.old.bytes.next = add i64 %array.grow.old.bytes, %old.size",
            "  store i64 %array.grow.old.bytes.next, ptr @__tb_stat_array_grow_old_bytes",
            "  %array.grow.new.bytes = load i64, ptr @__tb_stat_array_grow_new_bytes",
            "  %array.grow.new.bytes.next = add i64 %array.grow.new.bytes, %new.size",
            "  store i64 %array.grow.new.bytes.next, ptr @__tb_stat_array_grow_new_bytes",
            "  store i64 %new.cap, ptr %cap.ptr",
            "  store ptr %new.data, ptr %data.ptr",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_array_push(ptr %array, ptr %value_ptr, i64 %elem_size) {",
            "entry:",
            "  call void @tb_array_reserve_for_push(ptr %array, i64 %elem_size)",
            "  %array.push.calls = load i64, ptr @__tb_stat_array_push_calls",
            "  %array.push.calls.next = add i64 %array.push.calls, 1",
            "  store i64 %array.push.calls.next, ptr @__tb_stat_array_push_calls",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %slot = call ptr @tb_array_element_ptr(ptr %array, i64 %len, i64 %elem_size)",
            "  call ptr @memcpy(ptr %slot, ptr %value_ptr, i64 %elem_size)",
            "  %next.len = add i64 %len, 1",
            "  store i64 %next.len, ptr %len.ptr",
            "  ret void",
            "}",
            "",
            "define private void @tb_array_set(ptr %array, i64 %index, ptr %value_ptr, i64 %elem_size) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 1",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %required = add i64 %index, 1",
            "  %cap = load i64, ptr %cap.ptr",
            "  %has.capacity = icmp sge i64 %cap, %required",
            "  br i1 %has.capacity, label %store_value, label %grow",
            "grow:",
            "  %cap.is_zero = icmp eq i64 %cap, 0",
            "  %doubled = mul i64 %cap, 2",
            "  %grown.cap = select i1 %cap.is_zero, i64 4, i64 %doubled",
            "  %grown.enough = icmp sge i64 %grown.cap, %required",
            "  %new.cap = select i1 %grown.enough, i64 %grown.cap, i64 %required",
            "  %old.data = load ptr, ptr %data.ptr",
            "  %old.size = mul i64 %cap, %elem_size",
            "  %new.size = mul i64 %new.cap, %elem_size",
            "  %new.data = call ptr @tb_heap_grow_copy(ptr %old.data, i64 %old.size, i64 %new.size)",
            "  store i64 %new.cap, ptr %cap.ptr",
            "  store ptr %new.data, ptr %data.ptr",
            "  br label %store_value",
            "store_value:",
            "  %old.value.slot = alloca ptr",
            "  store ptr null, ptr %old.value.slot",
            f"  %header = getelementptr inbounds i8, ptr %array, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            "  %array.flags = and i32 %flags, 65535",
            f"  %releases.ptrs = icmp eq i32 %array.flags, {self.RC_ARRAY_RELEASE_PTRS}",
            "  %len = load i64, ptr %len.ptr",
            "  %replaces = icmp slt i64 %index, %len",
            "  %needs.release = and i1 %releases.ptrs, %replaces",
            "  br i1 %needs.release, label %release.old, label %write.new",
            "release.old:",
            "  %old.slot = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  %old.value = load ptr, ptr %old.slot",
            "  store ptr %old.value, ptr %old.value.slot",
            "  br label %write.new",
            "write.new:",
            "  %slot = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  call ptr @memcpy(ptr %slot, ptr %value_ptr, i64 %elem_size)",
            "  %needs.extend = icmp slt i64 %len, %required",
            "  %next.len = select i1 %needs.extend, i64 %required, i64 %len",
            "  store i64 %next.len, ptr %len.ptr",
            "  br i1 %needs.release, label %release.done, label %done",
            "release.done:",
            "  %old.value.release = load ptr, ptr %old.value.slot",
            "  call void @tb_release(ptr %old.value.release)",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_abort_bounds() {",
            "entry:",
            "  call void @abort()",
            "  unreachable",
            "}",
            "",
            "define private void @tb_array_insert(ptr %array, i64 %index, ptr %value_ptr, i64 %elem_size) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %index.non_negative = icmp sge i64 %index, 0",
            "  %index.within_len = icmp sle i64 %index, %len",
            "  %index.valid = and i1 %index.non_negative, %index.within_len",
            "  br i1 %index.valid, label %valid, label %fail",
            "fail:",
            "  call void @tb_abort_bounds()",
            "  unreachable",
            "valid:",
            "  call void @tb_array_reserve_for_push(ptr %array, i64 %elem_size)",
            "  %items.to.move = sub i64 %len, %index",
            "  %has.tail = icmp sgt i64 %items.to.move, 0",
            "  br i1 %has.tail, label %shift, label %store",
            "shift:",
            "  %src = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  %next.index = add i64 %index, 1",
            "  %dst = call ptr @tb_array_element_ptr(ptr %array, i64 %next.index, i64 %elem_size)",
            "  %move.bytes = mul i64 %items.to.move, %elem_size",
            "  call ptr @memmove(ptr %dst, ptr %src, i64 %move.bytes)",
            "  br label %store",
            "store:",
            "  %slot = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  call ptr @memcpy(ptr %slot, ptr %value_ptr, i64 %elem_size)",
            "  %next.len = add i64 %len, 1",
            "  store i64 %next.len, ptr %len.ptr",
            "  ret void",
            "}",
            "",
            "define private void @tb_array_pop(ptr %array, ptr %out_ptr, i64 %elem_size) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %has.items = icmp sgt i64 %len, 0",
            "  br i1 %has.items, label %valid, label %fail",
            "fail:",
            "  call void @tb_abort_bounds()",
            "  unreachable",
            "valid:",
            "  %index = sub i64 %len, 1",
            "  %slot = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  call ptr @memcpy(ptr %out_ptr, ptr %slot, i64 %elem_size)",
            "  store i64 %index, ptr %len.ptr",
            "  ret void",
            "}",
            "",
            "define private void @tb_array_remove(ptr %array, i64 %index, ptr %out_ptr, i64 %elem_size) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %has.items = icmp sgt i64 %len, 0",
            "  %index.non_negative = icmp sge i64 %index, 0",
            "  %index.before_end = icmp slt i64 %index, %len",
            "  %index.in_range = and i1 %index.non_negative, %index.before_end",
            "  %valid = and i1 %has.items, %index.in_range",
            "  br i1 %valid, label %body, label %fail",
            "fail:",
            "  call void @tb_abort_bounds()",
            "  unreachable",
            "body:",
            "  %slot = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  call ptr @memcpy(ptr %out_ptr, ptr %slot, i64 %elem_size)",
            "  %last.index = sub i64 %len, 1",
            "  %has.tail = icmp slt i64 %index, %last.index",
            "  br i1 %has.tail, label %shift, label %shrink",
            "shift:",
            "  %src.index = add i64 %index, 1",
            "  %src = call ptr @tb_array_element_ptr(ptr %array, i64 %src.index, i64 %elem_size)",
            "  %dst = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            "  %items.to.move = sub i64 %last.index, %index",
            "  %move.bytes = mul i64 %items.to.move, %elem_size",
            "  call ptr @memmove(ptr %dst, ptr %src, i64 %move.bytes)",
            "  br label %shrink",
            "shrink:",
            "  store i64 %last.index, ptr %len.ptr",
            "  ret void",
            "}",
            "",
            "define private void @tb_array_clear(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            f"  %header = getelementptr inbounds i8, ptr %array, i64 -{self.RC_HEADER_SIZE}",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %header, i32 0, i32 2",
            "  %flags = load i32, ptr %flags.ptr",
            "  %array.flags = and i32 %flags, 65535",
            f"  %release.ptrs = icmp eq i32 %array.flags, {self.RC_ARRAY_RELEASE_PTRS}",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br i1 %release.ptrs, label %release.loop, label %clear",
            "release.loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %release.body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %release.body, label %clear",
            "release.body:",
            "  %slot = getelementptr inbounds ptr, ptr %data, i64 %index",
            "  %item = load ptr, ptr %slot",
            "  call void @tb_release(ptr %item)",
            "  %next.index = add i64 %index, 1",
            "  br label %release.loop",
            "clear:",
            "  store i64 0, ptr %len.ptr",
            "  ret void",
            "}",
            "",
            "define private void @tb_array_sort(ptr %array, i64 %elem_size, ptr %cmp) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %needs.sort = icmp sgt i64 %len, 1",
            "  br i1 %needs.sort, label %sort, label %done",
            "sort:",
            "  call void @qsort(ptr %data, i64 %len, i64 %elem_size, ptr %cmp)",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private ptr @tb_pq_new(ptr %source, i64 %elem_size, i32 %item_mode, ptr %cmp) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %source, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %release.ptrs = icmp ne i32 %item_mode, 0",
            f"  %release_mode = select i1 %release.ptrs, i32 {self.RC_ARRAY_RELEASE_PTRS}, i32 {self.RC_ARRAY_RELEASE_NONE}",
            f"  %allocation = call ptr @tb_heap_alloc(i64 {self.RC_HEADER_SIZE + 32})",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 0",
            f"  %kind.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 1",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 2",
            f"  store i64 1, ptr %refcount.ptr",
            f"  store i32 {self.RC_KIND_PRIORITY_QUEUE}, ptr %kind.ptr",
            f"  %pq.flags = or i32 {self.RC_FLAGS_MAGIC}, %item_mode",
            "  store i32 %pq.flags, ptr %flags.ptr",
            f"  %pq = getelementptr inbounds i8, ptr %allocation, i64 {self.RC_HEADER_SIZE}",
            f"  %pq.array.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 0",
            f"  %pq.cmp.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 1",
            f"  %pq.elem_size.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 2",
            f"  %pq.item_mode.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 3",
            "  %array = call ptr @tb_array_new(i64 %len, i64 %elem_size, i32 %release_mode)",
            "  store ptr %array, ptr %pq.array.ptr",
            "  store ptr %cmp, ptr %pq.cmp.ptr",
            "  store i64 %elem_size, ptr %pq.elem_size.ptr",
            "  store i32 %item_mode, ptr %pq.item_mode.ptr",
            "  br label %copy.loop",
            "copy.loop:",
            "  %copy.index = phi i64 [ 0, %entry ], [ %copy.next, %copy.next.body ]",
            "  %copy.more = icmp slt i64 %copy.index, %len",
            "  br i1 %copy.more, label %copy.body, label %copy.done",
            "copy.body:",
            "  %copy.item = call ptr @tb_array_element_ptr(ptr %source, i64 %copy.index, i64 %elem_size)",
            "  %copy.mode.is.string = icmp eq i32 %item_mode, 2",
            "  br i1 %copy.mode.is.string, label %copy.clone, label %copy.check.ptr",
            "copy.clone:",
            "  %copy.string.slot = alloca ptr",
            "  %copy.string.value = load ptr, ptr %copy.item",
            "  %copy.string.owned = call ptr @tb_retain(ptr %copy.string.value)",
            "  store ptr %copy.string.owned, ptr %copy.string.slot",
            "  call void @tb_array_push(ptr %array, ptr %copy.string.slot, i64 %elem_size)",
            "  br label %copy.next.body",
            "copy.check.ptr:",
            "  %copy.mode.is.ptr = icmp eq i32 %item_mode, 1",
            "  br i1 %copy.mode.is.ptr, label %copy.retain, label %copy.raw",
            "copy.retain:",
            "  %copy.ptr.slot = alloca ptr",
            "  %copy.ptr.value = load ptr, ptr %copy.item",
            "  %copy.ptr.owned = call ptr @tb_retain(ptr %copy.ptr.value)",
            "  store ptr %copy.ptr.owned, ptr %copy.ptr.slot",
            "  call void @tb_array_push(ptr %array, ptr %copy.ptr.slot, i64 %elem_size)",
            "  br label %copy.next.body",
            "copy.raw:",
            "  call void @tb_array_push(ptr %array, ptr %copy.item, i64 %elem_size)",
            "  br label %copy.next.body",
            "copy.next.body:",
            "  %copy.next = add i64 %copy.index, 1",
            "  br label %copy.loop",
            "copy.done:",
            "  %needs.sort = icmp sgt i64 %len, 1",
            "  br i1 %needs.sort, label %sort, label %done",
            "sort:",
            "  call void @tb_array_sort(ptr %array, i64 %elem_size, ptr %cmp)",
            "  br label %done",
            "done:",
            "  ret ptr %pq",
            "}",
            "",
            "define private void @tb_pq_push(ptr %pq, ptr %value) {",
            "entry:",
            f"  %pq.array.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 0",
            f"  %pq.cmp.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 1",
            f"  %pq.elem_size.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 2",
            f"  %pq.item_mode.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 3",
            "  %array = load ptr, ptr %pq.array.ptr",
            "  %cmp = load ptr, ptr %pq.cmp.ptr",
            "  %elem_size = load i64, ptr %pq.elem_size.ptr",
            "  %item_mode = load i32, ptr %pq.item_mode.ptr",
            "  %push.mode.is.string = icmp eq i32 %item_mode, 2",
            "  br i1 %push.mode.is.string, label %push.clone, label %push.check.ptr",
            "push.clone:",
            "  %push.string.slot = alloca ptr",
            "  %push.string.value = load ptr, ptr %value",
            "  %push.string.owned = call ptr @tb_retain(ptr %push.string.value)",
            "  store ptr %push.string.owned, ptr %push.string.slot",
            "  call void @tb_array_push(ptr %array, ptr %push.string.slot, i64 %elem_size)",
            "  br label %push.sort",
            "push.check.ptr:",
            "  %push.mode.is.ptr = icmp eq i32 %item_mode, 1",
            "  br i1 %push.mode.is.ptr, label %push.retain, label %push.raw",
            "push.retain:",
            "  %push.ptr.slot = alloca ptr",
            "  %push.ptr.value = load ptr, ptr %value",
            "  %push.ptr.owned = call ptr @tb_retain(ptr %push.ptr.value)",
            "  store ptr %push.ptr.owned, ptr %push.ptr.slot",
            "  call void @tb_array_push(ptr %array, ptr %push.ptr.slot, i64 %elem_size)",
            "  br label %push.sort",
            "push.raw:",
            "  call void @tb_array_push(ptr %array, ptr %value, i64 %elem_size)",
            "  br label %push.sort",
            "push.sort:",
            "  call void @tb_array_sort(ptr %array, i64 %elem_size, ptr %cmp)",
            "  ret void",
            "}",
            "",
            "define private void @tb_pq_pop(ptr %pq, ptr %out) {",
            "entry:",
            f"  %pq.array.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 0",
            f"  %pq.elem_size.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 2",
            "  %array = load ptr, ptr %pq.array.ptr",
            "  %elem_size = load i64, ptr %pq.elem_size.ptr",
            "  call void @tb_array_remove(ptr %array, i64 0, ptr %out, i64 %elem_size)",
            "  ret void",
            "}",
            "",
            "define private i1 @tb_pq_is_empty(ptr %pq) {",
            "entry:",
            f"  %pq.array.ptr = getelementptr inbounds {self.PRIORITY_QUEUE_TYPE_NAME}, ptr %pq, i32 0, i32 0",
            "  %array = load ptr, ptr %pq.array.ptr",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %empty = icmp eq i64 %len, 0",
            "  ret i1 %empty",
            "}",
            "",
            "define private ptr @tb_array_collect(ptr %arrays, i64 %elem_size, i32 %release_mode) {",
            "entry:",
            "  %collect.item.slot = alloca ptr",
            f"  %outer.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %arrays, i32 0, i32 0",
            f"  %outer.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %arrays, i32 0, i32 2",
            "  %outer.len = load i64, ptr %outer.len.ptr",
            "  %outer.data = load ptr, ptr %outer.data.ptr",
            "  %total.slot = alloca i64",
            "  %outer.index.slot = alloca i64",
            "  %inner.index.slot = alloca i64",
            "  store i64 0, ptr %total.slot",
            "  store i64 0, ptr %outer.index.slot",
            "  br label %collect.sum.loop",
            "collect.sum.loop:",
            "  %sum.outer.index = load i64, ptr %outer.index.slot",
            "  %sum.outer.more = icmp slt i64 %sum.outer.index, %outer.len",
            "  br i1 %sum.outer.more, label %collect.sum.body, label %collect.sum.done",
            "collect.sum.body:",
            "  %sum.inner.slot = getelementptr inbounds ptr, ptr %outer.data, i64 %sum.outer.index",
            "  %sum.inner.array = load ptr, ptr %sum.inner.slot",
            f"  %sum.inner.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %sum.inner.array, i32 0, i32 0",
            "  %sum.inner.len = load i64, ptr %sum.inner.len.ptr",
            "  %sum.total = load i64, ptr %total.slot",
            "  %sum.total.next = add i64 %sum.total, %sum.inner.len",
            "  store i64 %sum.total.next, ptr %total.slot",
            "  %sum.outer.next = add i64 %sum.outer.index, 1",
            "  store i64 %sum.outer.next, ptr %outer.index.slot",
            "  br label %collect.sum.loop",
            "collect.sum.done:",
            "  %total.len = load i64, ptr %total.slot",
            "  %result = call ptr @tb_array_new(i64 %total.len, i64 %elem_size, i32 %release_mode)",
            "  store i64 0, ptr %outer.index.slot",
            "  br label %collect.outer.loop",
            "collect.outer.loop:",
            "  %outer.index = load i64, ptr %outer.index.slot",
            "  %outer.more = icmp slt i64 %outer.index, %outer.len",
            "  br i1 %outer.more, label %collect.outer.body, label %collect.done",
            "collect.outer.body:",
            "  %inner.slot = getelementptr inbounds ptr, ptr %outer.data, i64 %outer.index",
            "  %inner.array = load ptr, ptr %inner.slot",
            f"  %inner.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %inner.array, i32 0, i32 0",
            f"  %inner.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %inner.array, i32 0, i32 2",
            "  %inner.len = load i64, ptr %inner.len.ptr",
            "  %inner.data = load ptr, ptr %inner.data.ptr",
            "  store i64 0, ptr %inner.index.slot",
            "  br label %collect.inner.loop",
            "collect.inner.loop:",
            "  %inner.index = load i64, ptr %inner.index.slot",
            "  %inner.more = icmp slt i64 %inner.index, %inner.len",
            "  br i1 %inner.more, label %collect.inner.body, label %collect.inner.done",
            "collect.inner.body:",
            "  %inner.value.ptr = call ptr @tb_array_element_ptr(ptr %inner.array, i64 %inner.index, i64 %elem_size)",
            f"  %collect.release.ptrs = icmp eq i32 %release_mode, {self.RC_ARRAY_RELEASE_PTRS}",
            "  br i1 %collect.release.ptrs, label %collect.retain, label %collect.push.raw",
            "collect.retain:",
            "  %collect.item.value = load ptr, ptr %inner.value.ptr",
            "  %collect.item.owned = call ptr @tb_retain(ptr %collect.item.value)",
            "  store ptr %collect.item.owned, ptr %collect.item.slot",
            "  call void @tb_array_push(ptr %result, ptr %collect.item.slot, i64 %elem_size)",
            "  br label %collect.after.push",
            "collect.push.raw:",
            "  call void @tb_array_push(ptr %result, ptr %inner.value.ptr, i64 %elem_size)",
            "  br label %collect.after.push",
            "collect.after.push:",
            "  %inner.next = add i64 %inner.index, 1",
            "  store i64 %inner.next, ptr %inner.index.slot",
            "  br label %collect.inner.loop",
            "collect.inner.done:",
            "  %outer.next = add i64 %outer.index, 1",
            "  store i64 %outer.next, ptr %outer.index.slot",
            "  br label %collect.outer.loop",
            "collect.done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_array_slice(ptr %array, i64 %start, i64 %end, i64 %elem_size, i32 %release_mode) {",
            "entry:",
            "  %slice.item.slot = alloca ptr",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %start.neg = icmp slt i64 %start, 0",
            "  %start.from.end = add i64 %len, %start",
            "  %actual.start = select i1 %start.neg, i64 %start.from.end, i64 %start",
            "  %end.neg = icmp slt i64 %end, 0",
            "  %end.from.end = add i64 %len, %end",
            "  %actual.end = select i1 %end.neg, i64 %end.from.end, i64 %end",
            "  %count.raw = sub i64 %actual.end, %actual.start",
            "  %has.items = icmp sgt i64 %count.raw, 0",
            "  %capacity = select i1 %has.items, i64 %count.raw, i64 0",
            "  %result = call ptr @tb_array_new(i64 %capacity, i64 %elem_size, i32 %release_mode)",
            "  br i1 %has.items, label %loop, label %done",
            "loop:",
            "  %index = phi i64 [ %actual.start, %entry ], [ %next.index, %slice.after.push ]",
            "  %more = icmp slt i64 %index, %actual.end",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %source.ptr = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 %elem_size)",
            f"  %slice.release.ptrs = icmp eq i32 %release_mode, {self.RC_ARRAY_RELEASE_PTRS}",
            "  br i1 %slice.release.ptrs, label %slice.retain, label %slice.push.raw",
            "slice.retain:",
            "  %slice.item.value = load ptr, ptr %source.ptr",
            "  %slice.item.owned = call ptr @tb_retain(ptr %slice.item.value)",
            "  store ptr %slice.item.owned, ptr %slice.item.slot",
            "  call void @tb_array_push(ptr %result, ptr %slice.item.slot, i64 %elem_size)",
            "  br label %slice.after.push",
            "slice.push.raw:",
            "  call void @tb_array_push(ptr %result, ptr %source.ptr, i64 %elem_size)",
            "  br label %slice.after.push",
            "slice.after.push:",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_string_array_slice(ptr %array, i64 %start, i64 %end) {",
            "entry:",
            "  %slice.item.slot = alloca ptr",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            "  %len = load i64, ptr %len.ptr",
            "  %start.neg = icmp slt i64 %start, 0",
            "  %start.from.end = add i64 %len, %start",
            "  %actual.start = select i1 %start.neg, i64 %start.from.end, i64 %start",
            "  %end.neg = icmp slt i64 %end, 0",
            "  %end.from.end = add i64 %len, %end",
            "  %actual.end = select i1 %end.neg, i64 %end.from.end, i64 %end",
            "  %count.raw = sub i64 %actual.end, %actual.start",
            "  %has.items = icmp sgt i64 %count.raw, 0",
            "  %capacity = select i1 %has.items, i64 %count.raw, i64 0",
            f"  %result = call ptr @tb_array_new(i64 %capacity, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            "  br i1 %has.items, label %loop, label %done",
            "loop:",
            "  %index = phi i64 [ %actual.start, %entry ], [ %next.index, %body ]",
            "  %more = icmp slt i64 %index, %actual.end",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %source.ptr = call ptr @tb_array_element_ptr(ptr %array, i64 %index, i64 8)",
            "  %source.value = load ptr, ptr %source.ptr",
            "  %slice.item.owned = call ptr @tb_retain(ptr %source.value)",
            "  store ptr %slice.item.owned, ptr %slice.item.slot",
            "  call void @tb_array_push(ptr %result, ptr %slice.item.slot, i64 8)",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_range(i64 %start, i64 %end) {",
            "entry:",
            "  %tmp.value = alloca i64",
            "  %count = sub i64 %end, %start",
            "  %has.values = icmp sgt i64 %count, 0",
            "  %capacity = select i1 %has.values, i64 %count, i64 0",
            f"  %result = call ptr @tb_array_new(i64 %capacity, i64 8, i32 {self.RC_ARRAY_RELEASE_NONE})",
            "  br i1 %has.values, label %loop, label %done",
            "loop:",
            "  %value = phi i64 [ %start, %entry ], [ %next.value, %advance ]",
            "  %more = icmp slt i64 %value, %end",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  store i64 %value, ptr %tmp.value",
            "  call void @tb_array_push(ptr %result, ptr %tmp.value, i64 8)",
            "  %next.value = add i64 %value, 1",
            "  br label %advance",
            "advance:",
            "  br label %loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_int_to_string(i64 %value) {",
            "entry:",
            f"  %fmt = getelementptr inbounds [{len(self.INT_TO_STRING_FORMAT_BYTES)} x i8], ptr @{self.INT_TO_STRING_FORMAT_LABEL}, i32 0, i32 0",
            "  %len32 = call i32 (ptr, i64, ptr, ...) @snprintf(ptr null, i64 0, ptr %fmt, i64 %value)",
            "  %len64 = sext i32 %len32 to i64",
            "  %size = add i64 %len64, 1",
            "  %buffer = call ptr @tb_string_new(i64 %len64)",
            "  call i32 (ptr, i64, ptr, ...) @snprintf(ptr %buffer, i64 %size, ptr %fmt, i64 %value)",
            "  ret ptr %buffer",
            "}",
            "",
            "define private i64 @tb_int_string_length(i64 %value) {",
            "entry:",
            f"  %fmt = getelementptr inbounds [{len(self.INT_TO_STRING_FORMAT_BYTES)} x i8], ptr @{self.INT_TO_STRING_FORMAT_LABEL}, i32 0, i32 0",
            "  %len32 = call i32 (ptr, i64, ptr, ...) @snprintf(ptr null, i64 0, ptr %fmt, i64 %value)",
            "  %len64 = sext i32 %len32 to i64",
            "  ret i64 %len64",
            "}",
            "",
            "define private i64 @tb_shift_left(i64 %value, i64 %amount) {",
            "entry:",
            "  %is.negative = icmp slt i64 %amount, 0",
            "  br i1 %is.negative, label %abort.neg, label %check.range",
            "abort.neg:",
            "  call void @abort()",
            "  unreachable",
            "check.range:",
            "  %too.large = icmp sge i64 %amount, 64",
            "  br i1 %too.large, label %return.zero, label %shift",
            "return.zero:",
            "  ret i64 0",
            "shift:",
            "  %shifted = shl i64 %value, %amount",
            "  ret i64 %shifted",
            "}",
            "",
            "define private i64 @tb_shift_right(i64 %value, i64 %amount) {",
            "entry:",
            "  %is.negative = icmp slt i64 %amount, 0",
            "  br i1 %is.negative, label %abort.neg, label %check.range",
            "abort.neg:",
            "  call void @abort()",
            "  unreachable",
            "check.range:",
            "  %too.large = icmp sge i64 %amount, 64",
            "  br i1 %too.large, label %saturate, label %shift",
            "saturate:",
            "  %value.is.negative = icmp slt i64 %value, 0",
            "  %saturated = select i1 %value.is.negative, i64 -1, i64 0",
            "  ret i64 %saturated",
            "shift:",
            "  %shifted = ashr i64 %value, %amount",
            "  ret i64 %shifted",
            "}",
            "",
            "define private ptr @tb_cache_wrap_string(ptr %value) {",
            "entry:",
            "  %value.len = call i64 @strlen(ptr %value)",
            "  %len.text = call ptr @tb_int_to_string(i64 %value.len)",
            "  %len.text.len = call i64 @strlen(ptr %len.text)",
            "  %total.len = add i64 %len.text.len, 1",
            "  %total.with.value = add i64 %total.len, %value.len",
            "  %buffer = call ptr @tb_string_new(i64 %total.with.value)",
            "  call ptr @memcpy(ptr %buffer, ptr %len.text, i64 %len.text.len)",
            "  call void @tb_release(ptr %len.text)",
            "  %sep.ptr = getelementptr inbounds i8, ptr %buffer, i64 %len.text.len",
            "  store i8 35, ptr %sep.ptr",
            "  %value.dst = getelementptr inbounds i8, ptr %buffer, i64 %total.len",
            "  call ptr @memcpy(ptr %value.dst, ptr %value, i64 %value.len)",
            "  %term.ptr = getelementptr inbounds i8, ptr %buffer, i64 %total.with.value",
            "  store i8 0, ptr %term.ptr",
            "  ret ptr %buffer",
            "}",
            "",
            "define private ptr @tb_int_array_to_string(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %has.items = icmp sgt i64 %len, 0",
            "  br i1 %has.items, label %measure.loop, label %empty",
            "empty:",
            "  %empty.size = add i64 2, 1",
            "  %empty.buffer = call ptr @tb_string_new(i64 2)",
            "  store i8 91, ptr %empty.buffer",
            "  %empty.close = getelementptr inbounds i8, ptr %empty.buffer, i64 1",
            "  store i8 93, ptr %empty.close",
            "  %empty.term = getelementptr inbounds i8, ptr %empty.buffer, i64 2",
            "  store i8 0, ptr %empty.term",
            "  ret ptr %empty.buffer",
            "measure.loop:",
            "  %measure.index = phi i64 [ 0, %entry ], [ %measure.next, %measure.body ]",
            "  %measure.total = phi i64 [ 0, %entry ], [ %measure.total.next, %measure.body ]",
            "  %measure.more = icmp slt i64 %measure.index, %len",
            "  br i1 %measure.more, label %measure.body, label %measure.done",
            "measure.body:",
            "  %measure.slot = getelementptr inbounds i64, ptr %data, i64 %measure.index",
            "  %measure.item = load i64, ptr %measure.slot",
            "  %measure.text.len = call i64 @tb_int_string_length(i64 %measure.item)",
            "  %measure.has.sep = icmp sgt i64 %measure.index, 0",
            "  %measure.sep.len = select i1 %measure.has.sep, i64 2, i64 0",
            "  %measure.with.sep = add i64 %measure.total, %measure.sep.len",
            "  %measure.total.next = add i64 %measure.with.sep, %measure.text.len",
            "  %measure.next = add i64 %measure.index, 1",
            "  br label %measure.loop",
            "measure.done:",
            "  %body.len = add i64 %measure.total, 2",
            "  %buffer.size = add i64 %body.len, 1",
            "  %buffer = call ptr @tb_string_new(i64 %body.len)",
            "  store i8 91, ptr %buffer",
            "  br label %copy.loop",
            "copy.loop:",
            "  %copy.index = phi i64 [ 0, %measure.done ], [ %copy.next, %copy.value ]",
            "  %copy.offset = phi i64 [ 1, %measure.done ], [ %copy.offset.next, %copy.value ]",
            "  %copy.more = icmp slt i64 %copy.index, %len",
            "  br i1 %copy.more, label %copy.body, label %copy.done",
            "copy.body:",
            "  %copy.has.sep = icmp sgt i64 %copy.index, 0",
            "  br i1 %copy.has.sep, label %copy.sep, label %copy.value",
            "copy.sep:",
            "  %copy.sep.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
            "  store i8 44, ptr %copy.sep.dst",
            "  %copy.space.dst = getelementptr inbounds i8, ptr %copy.sep.dst, i64 1",
            "  store i8 32, ptr %copy.space.dst",
            "  %copy.offset.after.sep = add i64 %copy.offset, 2",
            "  br label %copy.value",
            "copy.value:",
            "  %copy.value.offset = phi i64 [ %copy.offset, %copy.body ], [ %copy.offset.after.sep, %copy.sep ]",
            "  %copy.slot = getelementptr inbounds i64, ptr %data, i64 %copy.index",
            "  %copy.item = load i64, ptr %copy.slot",
            "  %copy.text = call ptr @tb_int_to_string(i64 %copy.item)",
            "  %copy.text.len = call i64 @strlen(ptr %copy.text)",
            "  %copy.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.value.offset",
            "  call ptr @memcpy(ptr %copy.dst, ptr %copy.text, i64 %copy.text.len)",
            "  call void @tb_release(ptr %copy.text)",
            "  %copy.offset.next = add i64 %copy.value.offset, %copy.text.len",
            "  %copy.next = add i64 %copy.index, 1",
            "  br label %copy.loop",
            "copy.done:",
            "  %copy.close.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
            "  store i8 93, ptr %copy.close.dst",
            "  %copy.term = getelementptr inbounds i8, ptr %copy.close.dst, i64 1",
            "  store i8 0, ptr %copy.term",
            "  ret ptr %buffer",
            "}",
            "",
            "define private ptr @tb_string_array_to_string(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %has.items = icmp sgt i64 %len, 0",
            "  br i1 %has.items, label %measure.loop, label %empty",
            "empty:",
            "  %empty.size = add i64 2, 1",
            "  %empty.buffer = call ptr @tb_string_new(i64 2)",
            "  store i8 91, ptr %empty.buffer",
            "  %empty.close = getelementptr inbounds i8, ptr %empty.buffer, i64 1",
            "  store i8 93, ptr %empty.close",
            "  %empty.term = getelementptr inbounds i8, ptr %empty.buffer, i64 2",
            "  store i8 0, ptr %empty.term",
            "  ret ptr %empty.buffer",
            "measure.loop:",
            "  %measure.index = phi i64 [ 0, %entry ], [ %measure.next, %measure.body ]",
            "  %measure.total = phi i64 [ 0, %entry ], [ %measure.total.next, %measure.body ]",
            "  %measure.more = icmp slt i64 %measure.index, %len",
            "  br i1 %measure.more, label %measure.body, label %measure.done",
            "measure.body:",
            "  %measure.slot = getelementptr inbounds ptr, ptr %data, i64 %measure.index",
            "  %measure.item = load ptr, ptr %measure.slot",
            "  %measure.text.len = call i64 @strlen(ptr %measure.item)",
            "  %measure.has.sep = icmp sgt i64 %measure.index, 0",
            "  %measure.sep.len = select i1 %measure.has.sep, i64 2, i64 0",
            "  %measure.with.sep = add i64 %measure.total, %measure.sep.len",
            "  %measure.with.open = add i64 %measure.with.sep, 1",
            "  %measure.with.value = add i64 %measure.with.open, %measure.text.len",
            "  %measure.total.next = add i64 %measure.with.value, 1",
            "  %measure.next = add i64 %measure.index, 1",
            "  br label %measure.loop",
            "measure.done:",
            "  %body.len = add i64 %measure.total, 2",
            "  %buffer.size = add i64 %body.len, 1",
            "  %buffer = call ptr @tb_string_new(i64 %body.len)",
            "  store i8 91, ptr %buffer",
            "  br label %copy.loop",
            "copy.loop:",
            "  %copy.index = phi i64 [ 0, %measure.done ], [ %copy.next, %copy.value.done ]",
            "  %copy.offset = phi i64 [ 1, %measure.done ], [ %copy.offset.next, %copy.value.done ]",
            "  %copy.more = icmp slt i64 %copy.index, %len",
            "  br i1 %copy.more, label %copy.body, label %copy.done",
            "copy.body:",
            "  %copy.has.sep = icmp sgt i64 %copy.index, 0",
            "  br i1 %copy.has.sep, label %copy.sep, label %copy.value",
            "copy.sep:",
            "  %copy.sep.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
            "  store i8 44, ptr %copy.sep.dst",
            "  %copy.space.dst = getelementptr inbounds i8, ptr %copy.sep.dst, i64 1",
            "  store i8 32, ptr %copy.space.dst",
            "  %copy.offset.after.sep = add i64 %copy.offset, 2",
            "  br label %copy.value",
            "copy.value:",
            "  %copy.value.offset = phi i64 [ %copy.offset, %copy.body ], [ %copy.offset.after.sep, %copy.sep ]",
            "  %copy.slot = getelementptr inbounds ptr, ptr %data, i64 %copy.index",
            "  %copy.item = load ptr, ptr %copy.slot",
            "  %copy.text.len = call i64 @strlen(ptr %copy.item)",
            "  %copy.open.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.value.offset",
            "  store i8 39, ptr %copy.open.dst",
            "  %copy.text.dst = getelementptr inbounds i8, ptr %copy.open.dst, i64 1",
            "  call ptr @memcpy(ptr %copy.text.dst, ptr %copy.item, i64 %copy.text.len)",
            "  %copy.quote.offset = add i64 %copy.value.offset, %copy.text.len",
            "  %copy.quote.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.quote.offset",
            "  %copy.quote.ptr = getelementptr inbounds i8, ptr %copy.quote.dst, i64 1",
            "  store i8 39, ptr %copy.quote.ptr",
            "  %copy.offset.next = add i64 %copy.quote.offset, 2",
            "  %copy.next = add i64 %copy.index, 1",
            "  br label %copy.value.done",
            "copy.value.done:",
            "  br label %copy.loop",
            "copy.done:",
            "  %copy.close.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
            "  store i8 93, ptr %copy.close.dst",
            "  %copy.term = getelementptr inbounds i8, ptr %copy.close.dst, i64 1",
            "  store i8 0, ptr %copy.term",
            "  ret ptr %buffer",
            "}",
            "",
            "define private ptr @tb_bool_array_to_string(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %has.items = icmp sgt i64 %len, 0",
            "  br i1 %has.items, label %measure.loop, label %empty",
            "empty:",
            "  %empty.size = add i64 2, 1",
            "  %empty.buffer = call ptr @tb_string_new(i64 2)",
            "  store i8 91, ptr %empty.buffer",
            "  %empty.close = getelementptr inbounds i8, ptr %empty.buffer, i64 1",
            "  store i8 93, ptr %empty.close",
            "  %empty.term = getelementptr inbounds i8, ptr %empty.buffer, i64 2",
            "  store i8 0, ptr %empty.term",
            "  ret ptr %empty.buffer",
            "measure.loop:",
            "  %measure.index = phi i64 [ 0, %entry ], [ %measure.next, %measure.body ]",
            "  %measure.total = phi i64 [ 0, %entry ], [ %measure.total.next, %measure.body ]",
            "  %measure.more = icmp slt i64 %measure.index, %len",
            "  br i1 %measure.more, label %measure.body, label %measure.done",
            "measure.body:",
            "  %measure.slot = getelementptr inbounds i1, ptr %data, i64 %measure.index",
            "  %measure.item = load i1, ptr %measure.slot",
            "  %measure.text.len = select i1 %measure.item, i64 4, i64 5",
            "  %measure.has.sep = icmp sgt i64 %measure.index, 0",
            "  %measure.sep.len = select i1 %measure.has.sep, i64 2, i64 0",
            "  %measure.with.sep = add i64 %measure.total, %measure.sep.len",
            "  %measure.total.next = add i64 %measure.with.sep, %measure.text.len",
            "  %measure.next = add i64 %measure.index, 1",
            "  br label %measure.loop",
            "measure.done:",
            "  %body.len = add i64 %measure.total, 2",
            "  %buffer.size = add i64 %body.len, 1",
            "  %buffer = call ptr @tb_string_new(i64 %body.len)",
            "  store i8 91, ptr %buffer",
            "  br label %copy.loop",
            "copy.loop:",
            "  %copy.index = phi i64 [ 0, %measure.done ], [ %copy.next, %copy.value ]",
            "  %copy.offset = phi i64 [ 1, %measure.done ], [ %copy.offset.next, %copy.value ]",
            "  %copy.more = icmp slt i64 %copy.index, %len",
            "  br i1 %copy.more, label %copy.body, label %copy.done",
            "copy.body:",
            "  %copy.has.sep = icmp sgt i64 %copy.index, 0",
            "  br i1 %copy.has.sep, label %copy.sep, label %copy.value",
            "copy.sep:",
            "  %copy.sep.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
            "  store i8 44, ptr %copy.sep.dst",
            "  %copy.space.dst = getelementptr inbounds i8, ptr %copy.sep.dst, i64 1",
            "  store i8 32, ptr %copy.space.dst",
            "  %copy.offset.after.sep = add i64 %copy.offset, 2",
            "  br label %copy.value",
            "copy.value:",
            "  %copy.value.offset = phi i64 [ %copy.offset, %copy.body ], [ %copy.offset.after.sep, %copy.sep ]",
            "  %copy.slot = getelementptr inbounds i1, ptr %data, i64 %copy.index",
            "  %copy.item = load i1, ptr %copy.slot",
            f"  %copy.true.ptr = getelementptr inbounds [{len(self.BOOL_TRUE_BYTES)} x i8], ptr @{self.BOOL_TRUE_LABEL}, i32 0, i32 0",
            f"  %copy.false.ptr = getelementptr inbounds [{len(self.BOOL_FALSE_BYTES)} x i8], ptr @{self.BOOL_FALSE_LABEL}, i32 0, i32 0",
            "  %copy.text = select i1 %copy.item, ptr %copy.true.ptr, ptr %copy.false.ptr",
            "  %copy.text.len = select i1 %copy.item, i64 4, i64 5",
            "  %copy.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.value.offset",
            "  call ptr @memcpy(ptr %copy.dst, ptr %copy.text, i64 %copy.text.len)",
            "  %copy.offset.next = add i64 %copy.value.offset, %copy.text.len",
            "  %copy.next = add i64 %copy.index, 1",
            "  br label %copy.loop",
            "copy.done:",
            "  %copy.close.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
            "  store i8 93, ptr %copy.close.dst",
            "  %copy.term = getelementptr inbounds i8, ptr %copy.close.dst, i64 1",
            "  store i8 0, ptr %copy.term",
            "  ret ptr %buffer",
            "}",
            "",
            "define private i64 @tb_set_hash_value(i64 %value) {",
            "entry:",
            "  %hash = call i64 @tb_hash_int(i64 %value)",
            "  %shifted = shl i64 %hash, 1",
            "  %tagged = or i64 %shifted, 1",
            "  ret i64 %tagged",
            "}",
            "",
            "define private ptr @tb_set_new(i64 %initial_capacity, i32 %release_mode) {",
            "entry:",
            "  %capacity.is_zero = icmp eq i64 %initial_capacity, 0",
            "  %capacity = select i1 %capacity.is_zero, i64 4, i64 %initial_capacity",
            "  %index.base = mul i64 %capacity, 2",
            "  %index.small = icmp slt i64 %index.base, 8",
            "  %index.capacity = select i1 %index.small, i64 8, i64 %index.base",
            f"  %total.size = add i64 48, {self.RC_HEADER_SIZE}",
            "  %allocation = call ptr @tb_heap_alloc(i64 %total.size)",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 0",
            f"  %kind.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 1",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 2",
            "  store i64 1, ptr %refcount.ptr",
            f"  store i32 {self.RC_KIND_SET}, ptr %kind.ptr",
            f"  %set.flags = or i32 {self.RC_FLAGS_MAGIC}, %release_mode",
            "  store i32 %set.flags, ptr %flags.ptr",
            f"  %set = getelementptr inbounds i8, ptr %allocation, i64 {self.RC_HEADER_SIZE}",
            f"  %len.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 1",
            f"  %data.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 2",
            f"  %index.cap.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 3",
            f"  %hashes.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 4",
            f"  %index.values.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 5",
            "  %data.size = mul i64 %capacity, 8",
            "  %index.size = mul i64 %index.capacity, 8",
            "  %data = call ptr @tb_heap_alloc(i64 %data.size)",
            "  %hashes = call ptr @tb_heap_alloc(i64 %index.size)",
            "  %index.values = call ptr @tb_heap_alloc(i64 %index.size)",
            "  br label %init.loop",
            "init.loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %init.body ]",
            "  %more = icmp slt i64 %index, %index.capacity",
            "  br i1 %more, label %init.body, label %init.done",
            "init.body:",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %index",
            "  store i64 0, ptr %hash.slot",
            "  %next.index = add i64 %index, 1",
            "  br label %init.loop",
            "init.done:",
            "  store i64 0, ptr %len.ptr",
            "  store i64 %capacity, ptr %cap.ptr",
            "  store ptr %data, ptr %data.ptr",
            "  store i64 %index.capacity, ptr %index.cap.ptr",
            "  store ptr %hashes, ptr %hashes.ptr",
            "  store ptr %index.values, ptr %index.values.ptr",
            "  ret ptr %set",
            "}",
            "",
            "define private i64 @tb_set_find_slot(ptr %set, i64 %hash, i64 %value) {",
            "entry:",
            f"  %index.cap.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 3",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 4",
            f"  %index.values.ptr.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 5",
            "  %index.cap = load i64, ptr %index.cap.ptr",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %index.values = load ptr, ptr %index.values.ptr.ptr",
            "  %start = urem i64 %hash, %index.cap",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ %start, %entry ], [ %next.index, %next ]",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %index",
            "  %current.hash = load i64, ptr %hash.slot",
            "  %is.empty = icmp eq i64 %current.hash, 0",
            "  br i1 %is.empty, label %found, label %check.hash",
            "check.hash:",
            "  %same.hash = icmp eq i64 %current.hash, %hash",
            "  br i1 %same.hash, label %check.value, label %next",
            "check.value:",
            "  %value.slot = getelementptr inbounds i64, ptr %index.values, i64 %index",
            "  %current.value = load i64, ptr %value.slot",
            "  %is.match = icmp eq i64 %current.value, %value",
            "  br i1 %is.match, label %found, label %next",
            "next:",
            "  %index.plus = add i64 %index, 1",
            "  %next.index = urem i64 %index.plus, %index.cap",
            "  br label %loop",
            "found:",
            "  ret i64 %index",
            "}",
            "",
            "define private void @tb_set_insert_index(ptr %set, i64 %hash, i64 %value) {",
            "entry:",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 4",
            f"  %index.values.ptr.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 5",
            "  %slot.index = call i64 @tb_set_find_slot(ptr %set, i64 %hash, i64 %value)",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %index.values = load ptr, ptr %index.values.ptr.ptr",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index",
            "  %value.slot = getelementptr inbounds i64, ptr %index.values, i64 %slot.index",
            "  store i64 %hash, ptr %hash.slot",
            "  store i64 %value, ptr %value.slot",
            "  ret void",
            "}",
            "",
            "define private void @tb_set_reserve_for_add(ptr %set) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 2",
            f"  %index.cap.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 3",
            f"  %hashes.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 4",
            f"  %index.values.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 5",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %index.cap = load i64, ptr %index.cap.ptr",
            "  %next.len = add i64 %len, 1",
            "  %next.used.twice = mul i64 %next.len, 2",
            "  %has.capacity = icmp slt i64 %next.used.twice, %index.cap",
            "  br i1 %has.capacity, label %done, label %grow",
            "grow:",
            "  %index.cap.is_zero = icmp eq i64 %index.cap, 0",
            "  %index.doubled = mul i64 %index.cap, 2",
            "  %new.index.cap = select i1 %index.cap.is_zero, i64 8, i64 %index.doubled",
            "  %new.index.size = mul i64 %new.index.cap, 8",
            "  %old.hashes = load ptr, ptr %hashes.ptr",
            "  %old.index.values = load ptr, ptr %index.values.ptr",
            "  %new.hashes = call ptr @tb_heap_alloc(i64 %new.index.size)",
            "  %new.index.values = call ptr @tb_heap_alloc(i64 %new.index.size)",
            "  br label %init.loop",
            "init.loop:",
            "  %init.index = phi i64 [ 0, %grow ], [ %init.next, %init.body ]",
            "  %init.more = icmp slt i64 %init.index, %new.index.cap",
            "  br i1 %init.more, label %init.body, label %init.done",
            "init.body:",
            "  %init.slot = getelementptr inbounds i64, ptr %new.hashes, i64 %init.index",
            "  store i64 0, ptr %init.slot",
            "  %init.next = add i64 %init.index, 1",
            "  br label %init.loop",
            "init.done:",
            "  store i64 %new.index.cap, ptr %index.cap.ptr",
            "  store ptr %new.hashes, ptr %hashes.ptr",
            "  store ptr %new.index.values, ptr %index.values.ptr",
            "  br label %rehash.loop",
            "rehash.loop:",
            "  %rehash.index = phi i64 [ 0, %init.done ], [ %rehash.next.index, %rehash.body ]",
            "  %rehash.more = icmp slt i64 %rehash.index, %len",
            "  br i1 %rehash.more, label %rehash.body, label %grow.done",
            "rehash.body:",
            "  %value.slot = getelementptr inbounds i64, ptr %data, i64 %rehash.index",
            "  %value = load i64, ptr %value.slot",
            "  %hash = call i64 @tb_set_hash_value(i64 %value)",
            "  call void @tb_set_insert_index(ptr %set, i64 %hash, i64 %value)",
            "  %rehash.next.index = add i64 %rehash.index, 1",
            "  br label %rehash.loop",
            "grow.done:",
            "  call void @free(ptr %old.hashes)",
            "  call void @free(ptr %old.index.values)",
            "  ret void",
            "done:",
            "  ret void",
            "}",
            "",
            "define private i1 @tb_set_contains_int(ptr %set, i64 %value) {",
            "entry:",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.SET_TYPE_NAME}, ptr %set, i32 0, i32 4",
            "  %hash = call i64 @tb_set_hash_value(i64 %value)",
            "  %slot.index = call i64 @tb_set_find_slot(ptr %set, i64 %hash, i64 %value)",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index",
            "  %current.hash = load i64, ptr %hash.slot",
            "  %present = icmp ne i64 %current.hash, 0",
            "  ret i1 %present",
            "}",
            "",
            "define private i1 @tb_array_contains_int(ptr %array, i64 %value) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %advance ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %missing",
            "body:",
            "  %slot = getelementptr inbounds i64, ptr %data, i64 %index",
            "  %item = load i64, ptr %slot",
            "  %match = icmp eq i64 %item, %value",
            "  br i1 %match, label %found, label %advance",
            "advance:",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "found:",
            "  ret i1 true",
            "missing:",
            "  ret i1 false",
            "}",
            "",
            "define private i1 @tb_array_contains_bool(ptr %array, i1 %value) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %advance ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %missing",
            "body:",
            "  %slot = getelementptr inbounds i1, ptr %data, i64 %index",
            "  %item = load i1, ptr %slot",
            "  %match = icmp eq i1 %item, %value",
            "  br i1 %match, label %found, label %advance",
            "advance:",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "found:",
            "  ret i1 true",
            "missing:",
            "  ret i1 false",
            "}",
            "",
            "define private i1 @tb_array_contains_string(ptr %array, ptr %value) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %advance ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %missing",
            "body:",
            "  %slot = getelementptr inbounds ptr, ptr %data, i64 %index",
            "  %item = load ptr, ptr %slot",
            "  %cmp = call i32 @strcmp(ptr %item, ptr %value)",
            "  %match = icmp eq i32 %cmp, 0",
            "  br i1 %match, label %found, label %advance",
            "advance:",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "found:",
            "  ret i1 true",
            "missing:",
            "  ret i1 false",
            "}",
            "",
            "define private void @tb_set_add_int(ptr %set, i64 %value) {",
            "entry:",
            "  %value.slot = alloca i64",
            "  %present = call i1 @tb_set_contains_int(ptr %set, i64 %value)",
            "  br i1 %present, label %done, label %insert",
            "insert:",
            "  call void @tb_set_reserve_for_add(ptr %set)",
            "  %hash = call i64 @tb_set_hash_value(i64 %value)",
            "  call void @tb_set_insert_index(ptr %set, i64 %hash, i64 %value)",
            "  store i64 %value, ptr %value.slot",
            "  call void @tb_array_push(ptr %set, ptr %value.slot, i64 8)",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private ptr @tb_to_set_int_array(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            f"  %result = call ptr @tb_set_new(i64 %len, i32 {self.RC_SET_RELEASE_NONE})",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %slot = getelementptr inbounds i64, ptr %data, i64 %index",
            "  %item = load i64, ptr %slot",
            "  call void @tb_set_add_int(ptr %result, i64 %item)",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_set_union_int(ptr %left, ptr %right) {",
            "entry:",
            f"  %left.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %left, i32 0, i32 0",
            f"  %right.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %right, i32 0, i32 0",
            f"  %left.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %left, i32 0, i32 2",
            f"  %right.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %right, i32 0, i32 2",
            "  %left.len = load i64, ptr %left.len.ptr",
            "  %right.len = load i64, ptr %right.len.ptr",
            "  %left.data = load ptr, ptr %left.data.ptr",
            "  %right.data = load ptr, ptr %right.data.ptr",
            "  %capacity = add i64 %left.len, %right.len",
            f"  %result = call ptr @tb_set_new(i64 %capacity, i32 {self.RC_SET_RELEASE_NONE})",
            "  br label %left.loop",
            "left.loop:",
            "  %left.index = phi i64 [ 0, %entry ], [ %left.next, %left.body ]",
            "  %left.more = icmp slt i64 %left.index, %left.len",
            "  br i1 %left.more, label %left.body, label %right.loop",
            "left.body:",
            "  %left.slot = getelementptr inbounds i64, ptr %left.data, i64 %left.index",
            "  %left.item = load i64, ptr %left.slot",
            "  call void @tb_set_add_int(ptr %result, i64 %left.item)",
            "  %left.next = add i64 %left.index, 1",
            "  br label %left.loop",
            "right.loop:",
            "  %right.index = phi i64 [ 0, %left.loop ], [ %right.next, %right.body ]",
            "  %right.more = icmp slt i64 %right.index, %right.len",
            "  br i1 %right.more, label %right.body, label %done",
            "right.body:",
            "  %right.slot = getelementptr inbounds i64, ptr %right.data, i64 %right.index",
            "  %right.item = load i64, ptr %right.slot",
            "  call void @tb_set_add_int(ptr %result, i64 %right.item)",
            "  %right.next = add i64 %right.index, 1",
            "  br label %right.loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_int_set_to_string(ptr %set) {",
            "entry:",
            "  %text = call ptr @tb_int_array_to_string(ptr %set)",
            "  %len = call i64 @strlen(ptr %text)",
            "  store i8 123, ptr %text",
            "  %close.offset = sub i64 %len, 1",
            "  %close.ptr = getelementptr inbounds i8, ptr %text, i64 %close.offset",
            "  store i8 125, ptr %close.ptr",
            "  ret ptr %text",
            "}",
            "",
            "define private i64 @tb_hash_string(ptr %value) {",
            "entry:",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %body ]",
            "  %hash = phi i64 [ 5381, %entry ], [ %next.hash, %body ]",
            "  %char.ptr = getelementptr inbounds i8, ptr %value, i64 %index",
            "  %char = load i8, ptr %char.ptr",
            "  %done = icmp eq i8 %char, 0",
            "  br i1 %done, label %exit, label %body",
            "body:",
            "  %char.ext = zext i8 %char to i64",
            "  %hash.mul = mul i64 %hash, 33",
            "  %next.hash = add i64 %hash.mul, %char.ext",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "exit:",
            "  ret i64 %hash",
            "}",
            "",
            "define private i64 @tb_hash_int(i64 %value) {",
            "entry:",
            "  %mix1.shift = lshr i64 %value, 33",
            "  %mix1 = xor i64 %value, %mix1.shift",
            "  %mix2 = mul i64 %mix1, -49064778989728563",
            "  %mix2.shift = lshr i64 %mix2, 33",
            "  %mix3 = xor i64 %mix2, %mix2.shift",
            "  %mix4 = mul i64 %mix3, -4265267296055464877",
            "  %mix4.shift = lshr i64 %mix4, 33",
            "  %hash = xor i64 %mix4, %mix4.shift",
            "  ret i64 %hash",
            "}",
            "",
            "define private ptr @tb_string_copy_range(ptr %start, i64 %length) {",
            "entry:",
            "  %size = add i64 %length, 1",
            "  %buffer = call ptr @tb_string_new(i64 %length)",
            "  %string.copy.range.calls = load i64, ptr @__tb_stat_string_copy_range_calls",
            "  %string.copy.range.calls.next = add i64 %string.copy.range.calls, 1",
            "  store i64 %string.copy.range.calls.next, ptr @__tb_stat_string_copy_range_calls",
            "  %string.copy.range.bytes = load i64, ptr @__tb_stat_string_copy_range_bytes",
            "  %string.copy.range.bytes.next = add i64 %string.copy.range.bytes, %length",
            "  store i64 %string.copy.range.bytes.next, ptr @__tb_stat_string_copy_range_bytes",
            "  call ptr @memcpy(ptr %buffer, ptr %start, i64 %length)",
            "  %terminator = getelementptr inbounds i8, ptr %buffer, i64 %length",
            "  store i8 0, ptr %terminator",
            "  ret ptr %buffer",
            "}",
            "",
            "define private i1 @tb_starts_with(ptr %source, ptr %prefix) {",
            "entry:",
            "  %found = call ptr @strstr(ptr %source, ptr %prefix)",
            "  %matches = icmp eq ptr %found, %source",
            "  ret i1 %matches",
            "}",
            "",
            "define private i1 @tb_starts_with_at(ptr %source, ptr %prefix, i64 %offset) {",
            "entry:",
            "  %start = getelementptr inbounds i8, ptr %source, i64 %offset",
            "  %found = call ptr @strstr(ptr %start, ptr %prefix)",
            "  %matches = icmp eq ptr %found, %start",
            "  ret i1 %matches",
            "}",
            "",
            "define private i1 @tb_ends_with(ptr %source, ptr %suffix) {",
            "entry:",
            "  %source.len = call i64 @strlen(ptr %source)",
            "  %suffix.len = call i64 @strlen(ptr %suffix)",
            "  %too.long = icmp sgt i64 %suffix.len, %source.len",
            "  br i1 %too.long, label %no, label %check",
            "check:",
            "  %start.offset = sub i64 %source.len, %suffix.len",
            "  %start = getelementptr inbounds i8, ptr %source, i64 %start.offset",
            "  %cmp = call i32 @strcmp(ptr %start, ptr %suffix)",
            "  %matches = icmp eq i32 %cmp, 0",
            "  ret i1 %matches",
            "no:",
            "  ret i1 0",
            "}",
            "",
            "define private ptr @tb_slice(ptr %source, i64 %start, i64 %end) {",
            "entry:",
            "  %len = call i64 @strlen(ptr %source)",
            "  %start.neg = icmp slt i64 %start, 0",
            "  %start.from.end = add i64 %len, %start",
            "  %actual.start = select i1 %start.neg, i64 %start.from.end, i64 %start",
            "  %end.neg = icmp slt i64 %end, 0",
            "  %end.from.end = add i64 %len, %end",
            "  %actual.end = select i1 %end.neg, i64 %end.from.end, i64 %end",
            "  %has.range = icmp sgt i64 %actual.end, %actual.start",
            "  br i1 %has.range, label %copy, label %empty",
            "copy:",
            "  %start.ptr = getelementptr inbounds i8, ptr %source, i64 %actual.start",
            "  %length = sub i64 %actual.end, %actual.start",
            "  %result = call ptr @tb_string_copy_range(ptr %start.ptr, i64 %length)",
            "  ret ptr %result",
            "empty:",
            "  %result.empty = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %result.empty",
            "}",
            "",
            "define private ptr @tb_char_at(ptr %source, i64 %index) {",
            "entry:",
            "  %len = call i64 @strlen(ptr %source)",
            "  %negative = icmp slt i64 %index, 0",
            "  %normalized = add i64 %len, %index",
            "  %actual.index = select i1 %negative, i64 %normalized, i64 %index",
            "  %before.start = icmp slt i64 %actual.index, 0",
            "  %after.end = icmp sge i64 %actual.index, %len",
            "  %out.of.bounds = or i1 %before.start, %after.end",
            "  br i1 %out.of.bounds, label %empty, label %copy",
            "empty:",
            "  %empty.result = call ptr @tb_string_new(i64 0)",
            "  store i8 0, ptr %empty.result",
            "  ret ptr %empty.result",
            "copy:",
            "  %char.ptr = getelementptr inbounds i8, ptr %source, i64 %actual.index",
            "  %result = call ptr @tb_string_copy_range(ptr %char.ptr, i64 1)",
            "  ret ptr %result",
            "}",
            "",
            "define private i1 @tb_is_digit(ptr %source) {",
            "entry:",
            "  %first = load i8, ptr %source",
            "  %second.ptr = getelementptr inbounds i8, ptr %source, i64 1",
            "  %second = load i8, ptr %second.ptr",
            "  %single = icmp eq i8 %second, 0",
            "  %ge.zero = icmp uge i8 %first, 48",
            "  %le.nine = icmp ule i8 %first, 57",
            "  %digit = and i1 %ge.zero, %le.nine",
            "  %result = and i1 %single, %digit",
            "  ret i1 %result",
            "}",
            "",
            "define private i1 @tb_is_alpha(ptr %source) {",
            "entry:",
            "  %first = load i8, ptr %source",
            "  %second.ptr = getelementptr inbounds i8, ptr %source, i64 1",
            "  %second = load i8, ptr %second.ptr",
            "  %single = icmp eq i8 %second, 0",
            "  %ge.upper = icmp uge i8 %first, 65",
            "  %le.upper = icmp ule i8 %first, 90",
            "  %upper = and i1 %ge.upper, %le.upper",
            "  %ge.lower = icmp uge i8 %first, 97",
            "  %le.lower = icmp ule i8 %first, 122",
            "  %lower = and i1 %ge.lower, %le.lower",
            "  %alpha = or i1 %upper, %lower",
            "  %result = and i1 %single, %alpha",
            "  ret i1 %result",
            "}",
            "",
            "define private i1 @tb_is_alnum(ptr %source) {",
            "entry:",
            "  %first = load i8, ptr %source",
            "  %second.ptr = getelementptr inbounds i8, ptr %source, i64 1",
            "  %second = load i8, ptr %second.ptr",
            "  %single = icmp eq i8 %second, 0",
            "  %ge.zero = icmp uge i8 %first, 48",
            "  %le.nine = icmp ule i8 %first, 57",
            "  %digit = and i1 %ge.zero, %le.nine",
            "  %ge.upper = icmp uge i8 %first, 65",
            "  %le.upper = icmp ule i8 %first, 90",
            "  %upper = and i1 %ge.upper, %le.upper",
            "  %ge.lower = icmp uge i8 %first, 97",
            "  %le.lower = icmp ule i8 %first, 122",
            "  %lower = and i1 %ge.lower, %le.lower",
            "  %alpha.part = or i1 %upper, %lower",
            "  %alnum = or i1 %digit, %alpha.part",
            "  %result = and i1 %single, %alnum",
            "  ret i1 %result",
            "}",
            "",
            "define private i1 @tb_is_whitespace(ptr %source) {",
            "entry:",
            "  %first = load i8, ptr %source",
            "  %second.ptr = getelementptr inbounds i8, ptr %source, i64 1",
            "  %second = load i8, ptr %second.ptr",
            "  %single = icmp eq i8 %second, 0",
            "  %is.space = icmp eq i8 %first, 32",
            "  %is.tab = icmp eq i8 %first, 9",
            "  %space.or.tab = or i1 %is.space, %is.tab",
            "  %is.newline = icmp eq i8 %first, 10",
            "  %space.or.newline = or i1 %space.or.tab, %is.newline",
            "  %is.return = icmp eq i8 %first, 13",
            "  %space.or.return = or i1 %space.or.newline, %is.return",
            "  %is.vertical = icmp eq i8 %first, 11",
            "  %space.or.vertical = or i1 %space.or.return, %is.vertical",
            "  %is.formfeed = icmp eq i8 %first, 12",
            "  %whitespace = or i1 %space.or.vertical, %is.formfeed",
            "  %result = and i1 %single, %whitespace",
            "  ret i1 %result",
            "}",
            "",
            "define private ptr @tb_trim(ptr %source) {",
            "entry:",
            "  %len = call i64 @strlen(ptr %source)",
            "  %has.chars = icmp sgt i64 %len, 0",
            "  br i1 %has.chars, label %left.loop, label %empty",
            "empty:",
            "  %empty.result = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %empty.result",
            "left.loop:",
            "  %left = phi i64 [ 0, %entry ], [ %left.next, %left.ws ]",
            "  %left.more = icmp slt i64 %left, %len",
            "  br i1 %left.more, label %left.body, label %all.whitespace",
            "left.body:",
            "  %left.ptr = getelementptr inbounds i8, ptr %source, i64 %left",
            "  %left.char = load i8, ptr %left.ptr",
            "  %left.is.space = icmp eq i8 %left.char, 32",
            "  %left.is.tab = icmp eq i8 %left.char, 9",
            "  %left.space.or.tab = or i1 %left.is.space, %left.is.tab",
            "  %left.is.newline = icmp eq i8 %left.char, 10",
            "  %left.space.or.newline = or i1 %left.space.or.tab, %left.is.newline",
            "  %left.is.return = icmp eq i8 %left.char, 13",
            "  %left.space.or.return = or i1 %left.space.or.newline, %left.is.return",
            "  %left.is.vertical = icmp eq i8 %left.char, 11",
            "  %left.space.or.vertical = or i1 %left.space.or.return, %left.is.vertical",
            "  %left.is.formfeed = icmp eq i8 %left.char, 12",
            "  %left.whitespace = or i1 %left.space.or.vertical, %left.is.formfeed",
            "  br i1 %left.whitespace, label %left.ws, label %right.init",
            "left.ws:",
            "  %left.next = add i64 %left, 1",
            "  br label %left.loop",
            "all.whitespace:",
            "  %whitespace.result = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %whitespace.result",
            "right.init:",
            "  %right.start = sub i64 %len, 1",
            "  br label %right.loop",
            "right.loop:",
            "  %right = phi i64 [ %right.start, %right.init ], [ %right.prev, %right.ws ]",
            "  %right.ptr = getelementptr inbounds i8, ptr %source, i64 %right",
            "  %right.char = load i8, ptr %right.ptr",
            "  %right.is.space = icmp eq i8 %right.char, 32",
            "  %right.is.tab = icmp eq i8 %right.char, 9",
            "  %right.space.or.tab = or i1 %right.is.space, %right.is.tab",
            "  %right.is.newline = icmp eq i8 %right.char, 10",
            "  %right.space.or.newline = or i1 %right.space.or.tab, %right.is.newline",
            "  %right.is.return = icmp eq i8 %right.char, 13",
            "  %right.space.or.return = or i1 %right.space.or.newline, %right.is.return",
            "  %right.is.vertical = icmp eq i8 %right.char, 11",
            "  %right.space.or.vertical = or i1 %right.space.or.return, %right.is.vertical",
            "  %right.is.formfeed = icmp eq i8 %right.char, 12",
            "  %right.whitespace = or i1 %right.space.or.vertical, %right.is.formfeed",
            "  br i1 %right.whitespace, label %right.ws, label %copy",
            "right.ws:",
            "  %right.prev = sub i64 %right, 1",
            "  br label %right.loop",
            "copy:",
            "  %trim.start = getelementptr inbounds i8, ptr %source, i64 %left",
            "  %trim.end = add i64 %right, 1",
            "  %trim.len = sub i64 %trim.end, %left",
            "  %trim.result = call ptr @tb_string_copy_range(ptr %trim.start, i64 %trim.len)",
            "  ret ptr %trim.result",
            "}",
            "",
            "define private ptr @tb_trim_left(ptr %source) {",
            "entry:",
            "  %len = call i64 @strlen(ptr %source)",
            "  %has.chars = icmp sgt i64 %len, 0",
            "  br i1 %has.chars, label %left.loop, label %empty",
            "empty:",
            "  %empty.result = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %empty.result",
            "left.loop:",
            "  %left = phi i64 [ 0, %entry ], [ %left.next, %left.ws ]",
            "  %left.more = icmp slt i64 %left, %len",
            "  br i1 %left.more, label %left.body, label %all.whitespace",
            "left.body:",
            "  %left.ptr = getelementptr inbounds i8, ptr %source, i64 %left",
            "  %left.char = load i8, ptr %left.ptr",
            "  %left.is.space = icmp eq i8 %left.char, 32",
            "  %left.is.tab = icmp eq i8 %left.char, 9",
            "  %left.space.or.tab = or i1 %left.is.space, %left.is.tab",
            "  %left.is.newline = icmp eq i8 %left.char, 10",
            "  %left.space.or.newline = or i1 %left.space.or.tab, %left.is.newline",
            "  %left.is.return = icmp eq i8 %left.char, 13",
            "  %left.space.or.return = or i1 %left.space.or.newline, %left.is.return",
            "  %left.is.vertical = icmp eq i8 %left.char, 11",
            "  %left.space.or.vertical = or i1 %left.space.or.return, %left.is.vertical",
            "  %left.is.formfeed = icmp eq i8 %left.char, 12",
            "  %left.whitespace = or i1 %left.space.or.vertical, %left.is.formfeed",
            "  br i1 %left.whitespace, label %left.ws, label %copy",
            "left.ws:",
            "  %left.next = add i64 %left, 1",
            "  br label %left.loop",
            "all.whitespace:",
            "  %whitespace.result = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %whitespace.result",
            "copy:",
            "  %trim.start = getelementptr inbounds i8, ptr %source, i64 %left",
            "  %trim.len = sub i64 %len, %left",
            "  %trim.result = call ptr @tb_string_copy_range(ptr %trim.start, i64 %trim.len)",
            "  ret ptr %trim.result",
            "}",
            "",
            "define private ptr @tb_trim_right(ptr %source) {",
            "entry:",
            "  %len = call i64 @strlen(ptr %source)",
            "  %has.chars = icmp sgt i64 %len, 0",
            "  br i1 %has.chars, label %right.init, label %empty",
            "empty:",
            "  %empty.result = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %empty.result",
            "right.init:",
            "  %right.start = sub i64 %len, 1",
            "  br label %right.loop",
            "right.loop:",
            "  %right = phi i64 [ %right.start, %right.init ], [ %right.prev, %step.left ]",
            "  %right.ptr = getelementptr inbounds i8, ptr %source, i64 %right",
            "  %right.char = load i8, ptr %right.ptr",
            "  %right.is.space = icmp eq i8 %right.char, 32",
            "  %right.is.tab = icmp eq i8 %right.char, 9",
            "  %right.space.or.tab = or i1 %right.is.space, %right.is.tab",
            "  %right.is.newline = icmp eq i8 %right.char, 10",
            "  %right.space.or.newline = or i1 %right.space.or.tab, %right.is.newline",
            "  %right.is.return = icmp eq i8 %right.char, 13",
            "  %right.space.or.return = or i1 %right.space.or.newline, %right.is.return",
            "  %right.is.vertical = icmp eq i8 %right.char, 11",
            "  %right.space.or.vertical = or i1 %right.space.or.return, %right.is.vertical",
            "  %right.is.formfeed = icmp eq i8 %right.char, 12",
            "  %right.whitespace = or i1 %right.space.or.vertical, %right.is.formfeed",
            "  br i1 %right.whitespace, label %right.ws, label %copy",
            "right.ws:",
            "  %at.start = icmp eq i64 %right, 0",
            "  br i1 %at.start, label %all.whitespace, label %step.left",
            "step.left:",
            "  %right.prev = sub i64 %right, 1",
            "  br label %right.loop",
            "all.whitespace:",
            "  %whitespace.result = call ptr @tb_string_copy_range(ptr %source, i64 0)",
            "  ret ptr %whitespace.result",
            "copy:",
            "  %trim.len = add i64 %right, 1",
            "  %trim.result = call ptr @tb_string_copy_range(ptr %source, i64 %trim.len)",
            "  ret ptr %trim.result",
            "}",
            "",
            "define private ptr @tb_split(ptr %source, ptr %delimiter) {",
            "entry:",
            "  %tmp.item = alloca ptr",
            "  %delimiter.len = call i64 @strlen(ptr %delimiter)",
            "  %delimiter.empty = icmp eq i64 %delimiter.len, 0",
            "  br i1 %delimiter.empty, label %split_chars.init, label %count.loop",
            "split_chars.init:",
            "  %source.len = call i64 @strlen(ptr %source)",
            f"  %result.chars = call ptr @tb_array_new(i64 %source.len, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            "  br label %chars.loop",
            "count.loop:",
            "  %count.current = phi ptr [ %source, %entry ], [ %count.next.start, %count.body ]",
            "  %match.count = phi i64 [ 0, %entry ], [ %match.count.next, %count.body ]",
            "  %count.found = call ptr @strstr(ptr %count.current, ptr %delimiter)",
            "  %count.is_null = icmp eq ptr %count.found, null",
            "  br i1 %count.is_null, label %count.done, label %count.body",
            "count.body:",
            "  %match.count.next = add i64 %match.count, 1",
            "  %count.next.start = getelementptr inbounds i8, ptr %count.found, i64 %delimiter.len",
            "  br label %count.loop",
            "count.done:",
            "  %capacity = add i64 %match.count, 1",
            f"  %result = call ptr @tb_array_new(i64 %capacity, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            "  br label %loop",
            "chars.loop:",
            "  %char.index = phi i64 [ 0, %split_chars.init ], [ %char.next, %chars.body ]",
            "  %char.more = icmp slt i64 %char.index, %source.len",
            "  br i1 %char.more, label %chars.body, label %done",
            "chars.body:",
            "  %char.ptr = getelementptr inbounds i8, ptr %source, i64 %char.index",
            "  %char.text = call ptr @tb_string_copy_range(ptr %char.ptr, i64 1)",
            "  store ptr %char.text, ptr %tmp.item",
            "  call void @tb_array_push(ptr %result.chars, ptr %tmp.item, i64 8)",
            "  %char.next = add i64 %char.index, 1",
            "  br label %chars.loop",
            "loop:",
            "  %current = phi ptr [ %source, %count.done ], [ %next.start, %emit_token ]",
            "  %found = call ptr @strstr(ptr %current, ptr %delimiter)",
            "  %is_null = icmp eq ptr %found, null",
            "  br i1 %is_null, label %emit_tail, label %emit_token",
            "emit_token:",
            "  %current.int = ptrtoint ptr %current to i64",
            "  %found.int = ptrtoint ptr %found to i64",
            "  %token.len = sub i64 %found.int, %current.int",
            "  %token = call ptr @tb_string_copy_range(ptr %current, i64 %token.len)",
            "  store ptr %token, ptr %tmp.item",
            "  call void @tb_array_push(ptr %result, ptr %tmp.item, i64 8)",
            "  %next.start = getelementptr inbounds i8, ptr %found, i64 %delimiter.len",
            "  br label %loop",
            "emit_tail:",
            "  %tail.len = call i64 @strlen(ptr %current)",
            "  %tail = call ptr @tb_string_copy_range(ptr %current, i64 %tail.len)",
            "  store ptr %tail, ptr %tmp.item",
            "  call void @tb_array_push(ptr %result, ptr %tmp.item, i64 8)",
            "  br label %done",
            "done:",
            "  %return.value = phi ptr [ %result.chars, %chars.loop ], [ %result, %emit_tail ]",
            "  ret ptr %return.value",
            "}",
            "",
            "define private ptr @tb_split_lines(ptr %source) {",
            "entry:",
            "  %tmp.line = alloca ptr",
            "  %source.len = call i64 @strlen(ptr %source)",
            "  %has.chars = icmp sgt i64 %source.len, 0",
            "  br i1 %has.chars, label %count.loop, label %empty",
            "empty:",
            f"  %result.empty = call ptr @tb_array_new(i64 0, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            "  ret ptr %result.empty",
            "count.loop:",
            "  %count.index = phi i64 [ 0, %entry ], [ %count.next, %count.body ]",
            "  %line.count = phi i64 [ 0, %entry ], [ %line.count.next, %count.body ]",
            "  %count.more = icmp slt i64 %count.index, %source.len",
            "  br i1 %count.more, label %count.body, label %count.done",
            "count.body:",
            "  %count.char.ptr = getelementptr inbounds i8, ptr %source, i64 %count.index",
            "  %count.char = load i8, ptr %count.char.ptr",
            "  %count.is.newline = icmp eq i8 %count.char, 10",
            "  %count.incremented = add i64 %line.count, 1",
            "  %line.count.next = select i1 %count.is.newline, i64 %count.incremented, i64 %line.count",
            "  %count.next = add i64 %count.index, 1",
            "  br label %count.loop",
            "count.done:",
            "  %last.char.ptr = getelementptr inbounds i8, ptr %source, i64 %source.len",
            "  %last.char.slot = getelementptr inbounds i8, ptr %last.char.ptr, i64 -1",
            "  %last.char = load i8, ptr %last.char.slot",
            "  %ends.newline = icmp eq i8 %last.char, 10",
            "  %capacity.plus.tail = add i64 %line.count, 1",
            "  %capacity = select i1 %ends.newline, i64 %line.count, i64 %capacity.plus.tail",
            f"  %result = call ptr @tb_array_new(i64 %capacity, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %count.done ], [ %next.index, %continue ], [ %next.index, %after.emit ]",
            "  %line.start = phi i64 [ 0, %count.done ], [ %line.start, %continue ], [ %next.index, %after.emit ]",
            "  %more = icmp slt i64 %index, %source.len",
            "  br i1 %more, label %body, label %tail.check",
            "body:",
            "  %char.ptr = getelementptr inbounds i8, ptr %source, i64 %index",
            "  %char = load i8, ptr %char.ptr",
            "  %is.newline = icmp eq i8 %char, 10",
            "  %next.index = add i64 %index, 1",
            "  br i1 %is.newline, label %emit.line, label %continue",
            "continue:",
            "  br label %loop",
            "emit.line:",
            "  %line.len.raw = sub i64 %index, %line.start",
            "  %line.has.chars = icmp sgt i64 %line.len.raw, 0",
            "  br i1 %line.has.chars, label %emit.line.check.cr, label %emit.line.copy",
            "emit.line.check.cr:",
            "  %prev.index = sub i64 %index, 1",
            "  %prev.ptr = getelementptr inbounds i8, ptr %source, i64 %prev.index",
            "  %prev.char = load i8, ptr %prev.ptr",
            "  %ends.cr = icmp eq i8 %prev.char, 13",
            "  %line.len.minus.cr = sub i64 %line.len.raw, 1",
            "  %trimmed.line.len = select i1 %ends.cr, i64 %line.len.minus.cr, i64 %line.len.raw",
            "  br label %emit.line.copy",
            "emit.line.copy:",
            "  %line.len = phi i64 [ 0, %emit.line ], [ %trimmed.line.len, %emit.line.check.cr ]",
            "  %line.ptr = getelementptr inbounds i8, ptr %source, i64 %line.start",
            "  %line.text = call ptr @tb_string_copy_range(ptr %line.ptr, i64 %line.len)",
            "  store ptr %line.text, ptr %tmp.line",
            "  call void @tb_array_push(ptr %result, ptr %tmp.line, i64 8)",
            "  br label %after.emit",
            "after.emit:",
            "  br label %loop",
            "tail.check:",
            "  %has.tail = icmp slt i64 %line.start, %source.len",
            "  br i1 %has.tail, label %emit.tail, label %done",
            "emit.tail:",
            "  %tail.len.raw = sub i64 %source.len, %line.start",
            "  %tail.has.chars = icmp sgt i64 %tail.len.raw, 0",
            "  br i1 %tail.has.chars, label %emit.tail.check.cr, label %emit.tail.copy",
            "emit.tail.check.cr:",
            "  %tail.last.index = sub i64 %source.len, 1",
            "  %tail.last.ptr = getelementptr inbounds i8, ptr %source, i64 %tail.last.index",
            "  %tail.last.char = load i8, ptr %tail.last.ptr",
            "  %tail.ends.cr = icmp eq i8 %tail.last.char, 13",
            "  %tail.len.minus.cr = sub i64 %tail.len.raw, 1",
            "  %trimmed.tail.len = select i1 %tail.ends.cr, i64 %tail.len.minus.cr, i64 %tail.len.raw",
            "  br label %emit.tail.copy",
            "emit.tail.copy:",
            "  %tail.len = phi i64 [ 0, %emit.tail ], [ %trimmed.tail.len, %emit.tail.check.cr ]",
            "  %tail.ptr = getelementptr inbounds i8, ptr %source, i64 %line.start",
            "  %tail.text = call ptr @tb_string_copy_range(ptr %tail.ptr, i64 %tail.len)",
            "  store ptr %tail.text, ptr %tmp.line",
            "  call void @tb_array_push(ptr %result, ptr %tmp.line, i64 8)",
            "  br label %done",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_join_strings(ptr %array, ptr %delimiter) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %delimiter.len = call i64 @strlen(ptr %delimiter)",
            "  %has.items = icmp sgt i64 %len, 0",
            "  br i1 %has.items, label %measure.loop, label %empty",
            "empty:",
            "  %empty.text = call ptr @tb_string_copy_range(ptr %delimiter, i64 0)",
            "  ret ptr %empty.text",
            "measure.loop:",
            "  %measure.index = phi i64 [ 0, %entry ], [ %measure.next, %measure.body ]",
            "  %measure.total = phi i64 [ 0, %entry ], [ %measure.total.next, %measure.body ]",
            "  %measure.more = icmp slt i64 %measure.index, %len",
            "  br i1 %measure.more, label %measure.body, label %measure.done",
            "measure.body:",
            "  %measure.slot = getelementptr inbounds ptr, ptr %data, i64 %measure.index",
            "  %measure.item = load ptr, ptr %measure.slot",
            "  %measure.item.len = call i64 @strlen(ptr %measure.item)",
            "  %measure.total.with.item = add i64 %measure.total, %measure.item.len",
            "  %measure.total.next = add i64 %measure.total.with.item, %delimiter.len",
            "  %measure.next = add i64 %measure.index, 1",
            "  br label %measure.loop",
            "measure.done:",
            "  %join.total = sub i64 %measure.total, %delimiter.len",
            "  %join.size = add i64 %join.total, 1",
            "  %join.buffer = call ptr @tb_string_new(i64 %join.total)",
            "  br label %copy.loop",
            "copy.loop:",
            "  %copy.index = phi i64 [ 0, %measure.done ], [ %copy.next, %copy.after.delimiter ]",
            "  %copy.offset = phi i64 [ 0, %measure.done ], [ %copy.offset.after.delimiter, %copy.after.delimiter ]",
            "  %copy.more = icmp slt i64 %copy.index, %len",
            "  br i1 %copy.more, label %copy.body, label %copy.done",
            "copy.body:",
            "  %copy.slot = getelementptr inbounds ptr, ptr %data, i64 %copy.index",
            "  %copy.item = load ptr, ptr %copy.slot",
            "  %copy.item.len = call i64 @strlen(ptr %copy.item)",
            "  %copy.dst = getelementptr inbounds i8, ptr %join.buffer, i64 %copy.offset",
            "  call ptr @memcpy(ptr %copy.dst, ptr %copy.item, i64 %copy.item.len)",
            "  %copy.offset.after.item = add i64 %copy.offset, %copy.item.len",
            "  %copy.next = add i64 %copy.index, 1",
            "  %copy.has.more = icmp slt i64 %copy.next, %len",
            "  br i1 %copy.has.more, label %copy.delimiter, label %copy.done",
            "copy.delimiter:",
            "  %copy.delimiter.dst = getelementptr inbounds i8, ptr %join.buffer, i64 %copy.offset.after.item",
            "  call ptr @memcpy(ptr %copy.delimiter.dst, ptr %delimiter, i64 %delimiter.len)",
            "  %copy.offset.after.delimiter = add i64 %copy.offset.after.item, %delimiter.len",
            "  br label %copy.after.delimiter",
            "copy.after.delimiter:",
            "  br label %copy.loop",
            "copy.done:",
            "  %join.terminator = getelementptr inbounds i8, ptr %join.buffer, i64 %join.total",
            "  store i8 0, ptr %join.terminator",
            "  ret ptr %join.buffer",
            "}",
            "",
            "define private ptr @tb_replace(ptr %source, ptr %from, ptr %to) {",
            "entry:",
            "  %from.len = call i64 @strlen(ptr %from)",
            "  %from.empty = icmp eq i64 %from.len, 0",
            "  br i1 %from.empty, label %copy, label %replace",
            "copy:",
            "  %source.len = call i64 @strlen(ptr %source)",
            "  %source.copy = call ptr @tb_string_copy_range(ptr %source, i64 %source.len)",
            "  ret ptr %source.copy",
            "replace:",
            "  %parts = call ptr @tb_split(ptr %source, ptr %from)",
            "  %joined = call ptr @tb_join_strings(ptr %parts, ptr %to)",
            "  call void @tb_release(ptr %parts)",
            "  ret ptr %joined",
            "}",
            "",
            "define private i64 @tb_sum_int_array(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %body ]",
            "  %sum = phi i64 [ 0, %entry ], [ %sum.next, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %slot = getelementptr inbounds i64, ptr %data, i64 %index",
            "  %item = load i64, ptr %slot",
            "  %sum.next = add i64 %sum, %item",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret i64 %sum",
            "}",
            "",
            "define private i64 @tb_sum_bool_array(ptr %array) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %body ]",
            "  %sum = phi i64 [ 0, %entry ], [ %sum.next, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %slot = getelementptr inbounds i1, ptr %data, i64 %index",
            "  %item = load i1, ptr %slot",
            "  %item64 = zext i1 %item to i64",
            "  %sum.next = add i64 %sum, %item64",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret i64 %sum",
            "}",
            "",
            "define private ptr @tb_map_int_array(ptr %array, ptr %mapper) {",
            "entry:",
            "  %tmp.value = alloca i64",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            f"  %result = call ptr @tb_array_new(i64 %len, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %slot = getelementptr inbounds i64, ptr %data, i64 %index",
            "  %item = load i64, ptr %slot",
            "  %mapped = call i64 %mapper(i64 %item)",
            "  store i64 %mapped, ptr %tmp.value",
            "  call void @tb_array_push(ptr %result, ptr %tmp.value, i64 8)",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_map_ptr_array_to_bool(ptr %array, ptr %mapper) {",
            "entry:",
            "  %tmp.value = alloca i1",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            f"  %result = call ptr @tb_array_new(i64 %len, i64 1, i32 {self.RC_ARRAY_RELEASE_NONE})",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %slot = getelementptr inbounds ptr, ptr %data, i64 %index",
            "  %item = load ptr, ptr %slot",
            "  %mapped = call i1 %mapper(ptr %item)",
            "  store i1 %mapped, ptr %tmp.value",
            "  call void @tb_array_push(ptr %result, ptr %tmp.value, i64 1)",
            "  %next = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_read_file(ptr %path) {",
            "entry:",
            f"  %mode = getelementptr inbounds [{len(self.FILE_READ_MODE_BYTES)} x i8], ptr @{self.FILE_READ_MODE_LABEL}, i32 0, i32 0",
            "  %file = call ptr @fopen(ptr %path, ptr %mode)",
            "  %is_null = icmp eq ptr %file, null",
            "  br i1 %is_null, label %return_null, label %read",
            "read:",
            "  call i32 @fseek(ptr %file, i64 0, i32 2)",
            "  %size = call i64 @ftell(ptr %file)",
            "  call i32 @fseek(ptr %file, i64 0, i32 0)",
            "  %alloc.size = add i64 %size, 1",
            "  %buffer = call ptr @tb_string_new(i64 %size)",
            "  %bytes.read = call i64 @fread(ptr %buffer, i64 1, i64 %size, ptr %file)",
            "  %terminator = getelementptr inbounds i8, ptr %buffer, i64 %bytes.read",
            "  store i8 0, ptr %terminator",
            "  call i32 @fclose(ptr %file)",
            "  ret ptr %buffer",
            "return_null:",
            "  ret ptr null",
            "}",
            "",
            "define private ptr @tb_read_lines(ptr %path) {",
            "entry:",
            "  %content = call ptr @tb_read_file(ptr %path)",
            "  %lines = call ptr @tb_split_lines(ptr %content)",
            "  call void @tb_release(ptr %content)",
            "  ret ptr %lines",
            "}",
            "",
            "%tb_timeval = type { i64, i64 }",
            "",
            "define private i64 @tb_time_ms() {",
            "entry:",
            "  %tv = alloca %tb_timeval",
            "  %status = call i32 @gettimeofday(ptr %tv, ptr null)",
            "  %sec.ptr = getelementptr inbounds %tb_timeval, ptr %tv, i32 0, i32 0",
            "  %usec.ptr = getelementptr inbounds %tb_timeval, ptr %tv, i32 0, i32 1",
            "  %sec = load i64, ptr %sec.ptr",
            "  %usec = load i64, ptr %usec.ptr",
            "  %sec.ms = mul i64 %sec, 1000",
            "  %usec.ms = sdiv i64 %usec, 1000",
            "  %total = add i64 %sec.ms, %usec.ms",
            "  ret i64 %total",
            "}",
            "",
            "define private ptr @tb_map_new(i64 %initial_capacity, i32 %key_release_mode, i32 %value_release_mode) {",
            "entry:",
            "  %capacity.is_zero = icmp eq i64 %initial_capacity, 0",
            "  %capacity = select i1 %capacity.is_zero, i64 4, i64 %initial_capacity",
            "  %total.size = add i64 40, 16",
            "  %allocation = call ptr @tb_heap_alloc(i64 %total.size)",
            f"  %refcount.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 0",
            f"  %kind.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 1",
            f"  %flags.ptr = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr %allocation, i32 0, i32 2",
            "  store i64 1, ptr %refcount.ptr",
            f"  store i32 {self.RC_KIND_MAP}, ptr %kind.ptr",
            f"  %key.flags = shl i32 %key_release_mode, {self.RC_MAP_KEY_SHIFT}",
            f"  %value.flags = shl i32 %value_release_mode, {self.RC_MAP_VALUE_SHIFT}",
            "  %map.flags.release = or i32 %key.flags, %value.flags",
            f"  %map.flags = or i32 {self.RC_FLAGS_MAGIC}, %map.flags.release",
            "  store i32 %map.flags, ptr %flags.ptr",
            f"  %map = getelementptr inbounds i8, ptr %allocation, i64 {self.RC_HEADER_SIZE}",
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 1",
            f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            f"  %index.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 4",
            "  %data.size = mul i64 %capacity, 8",
            "  %keys = call ptr @tb_heap_alloc(i64 %data.size)",
            "  %values = call ptr @tb_heap_alloc(i64 %data.size)",
            "  %index = call ptr @tb_cache_new(i64 %capacity)",
            "  store i64 0, ptr %len.ptr",
            "  store i64 %capacity, ptr %cap.ptr",
            "  store ptr %keys, ptr %keys.ptr",
            "  store ptr %values, ptr %values.ptr",
            "  store ptr %index, ptr %index.ptr",
            "  ret ptr %map",
            "}",
            "",
            "define private void @tb_map_reserve_for_put(ptr %map) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 1",
            f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            "  %len = load i64, ptr %len.ptr",
            "  %cap = load i64, ptr %cap.ptr",
            "  %has.capacity = icmp slt i64 %len, %cap",
            "  br i1 %has.capacity, label %done, label %grow",
            "grow:",
            "  %cap.is_zero = icmp eq i64 %cap, 0",
            "  %doubled = mul i64 %cap, 2",
            "  %new.cap = select i1 %cap.is_zero, i64 4, i64 %doubled",
            "  %old.keys = load ptr, ptr %keys.ptr",
            "  %old.values = load ptr, ptr %values.ptr",
            "  %old.size = mul i64 %cap, 8",
            "  %new.size = mul i64 %new.cap, 8",
            "  %new.keys = call ptr @tb_heap_grow_copy(ptr %old.keys, i64 %old.size, i64 %new.size)",
            "  %new.values = call ptr @tb_heap_grow_copy(ptr %old.values, i64 %old.size, i64 %new.size)",
            "  store i64 %new.cap, ptr %cap.ptr",
            "  store ptr %new.keys, ptr %keys.ptr",
            "  store ptr %new.values, ptr %values.ptr",
            "  br label %done",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_map_put_string_int(ptr %map, ptr %key, i64 %value) {",
            "entry:",
            f"  %index.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 4",
            "  %index = load ptr, ptr %index.ptr",
            "  %has = call i1 @tb_cache_has_string_int(ptr %index, ptr %key)",
            "  br i1 %has, label %update, label %insert",
            "update:",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            "  %slot.index = call i64 @tb_cache_get_string_int(ptr %index, ptr %key)",
            "  %values = load ptr, ptr %values.ptr",
            "  %value.slot = getelementptr inbounds i64, ptr %values, i64 %slot.index",
            "  store i64 %value, ptr %value.slot",
            "  ret void",
            "insert:",
            "  call void @tb_map_reserve_for_put(ptr %map)",
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
            f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
            f"  %values.ptr.insert = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            "  %len = load i64, ptr %len.ptr",
            "  %keys = load ptr, ptr %keys.ptr",
            "  %values.insert = load ptr, ptr %values.ptr.insert",
            "  %key.slot = getelementptr inbounds ptr, ptr %keys, i64 %len",
            "  %value.slot.insert = getelementptr inbounds i64, ptr %values.insert, i64 %len",
            "  %key.owned = call ptr @tb_retain(ptr %key)",
            "  store ptr %key.owned, ptr %key.slot",
            "  store i64 %value, ptr %value.slot.insert",
            "  call void @tb_cache_put_string_int(ptr %index, ptr %key.owned, i64 %len)",
            "  %next.len = add i64 %len, 1",
            "  store i64 %next.len, ptr %len.ptr",
            "  ret void",
            "}",
            "",
            "define private i64 @tb_map_get_string_int(ptr %map, ptr %key) {",
            "entry:",
            f"  %index.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 4",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            "  %index = load ptr, ptr %index.ptr",
            "  %has = call i1 @tb_cache_has_string_int(ptr %index, ptr %key)",
            "  br i1 %has, label %found, label %missing",
            "found:",
            "  %slot.index = call i64 @tb_cache_get_string_int(ptr %index, ptr %key)",
            "  %values = load ptr, ptr %values.ptr",
            "  %value.slot = getelementptr inbounds i64, ptr %values, i64 %slot.index",
            "  %value = load i64, ptr %value.slot",
            "  ret i64 %value",
            "missing:",
            "  ret i64 0",
            "}",
            "",
            "define private i1 @tb_map_has_string_int(ptr %map, ptr %key) {",
            "entry:",
            f"  %index.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 4",
            "  %index = load ptr, ptr %index.ptr",
            "  %has = call i1 @tb_cache_has_string_int(ptr %index, ptr %key)",
            "  ret i1 %has",
            "}",
            "",
            "define private i64 @tb_cache_hash_key(ptr %key) {",
            "entry:",
            "  %hash = call i64 @tb_hash_string(ptr %key)",
            "  %shifted = shl i64 %hash, 1",
            "  %tagged = or i64 %shifted, 1",
            "  ret i64 %tagged",
            "}",
            "",
            "define private ptr @tb_cache_new(i64 %initial_capacity) {",
            "entry:",
            "  %capacity.is_zero = icmp eq i64 %initial_capacity, 0",
            "  %capacity = select i1 %capacity.is_zero, i64 8, i64 %initial_capacity",
            "  %cache = call ptr @tb_heap_alloc(i64 40)",
            f"  %len.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 1",
            f"  %hashes.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 2",
            f"  %keys.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 3",
            f"  %values.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 4",
            "  %data.size = mul i64 %capacity, 8",
            "  %hashes = call ptr @tb_heap_alloc(i64 %data.size)",
            "  %keys = call ptr @tb_heap_alloc(i64 %data.size)",
            "  %values = call ptr @tb_heap_alloc(i64 %data.size)",
            "  br label %init.loop",
            "init.loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %init.body ]",
            "  %more = icmp slt i64 %index, %capacity",
            "  br i1 %more, label %init.body, label %init.done",
            "init.body:",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %index",
            "  store i64 0, ptr %hash.slot",
            "  %next.index = add i64 %index, 1",
            "  br label %init.loop",
            "init.done:",
            "  store i64 0, ptr %len.ptr",
            "  store i64 %capacity, ptr %cap.ptr",
            "  store ptr %hashes, ptr %hashes.ptr",
            "  store ptr %keys, ptr %keys.ptr",
            "  store ptr %values, ptr %values.ptr",
            "  ret ptr %cache",
            "}",
            "",
            "define private i64 @tb_cache_find_slot(ptr %cache, i64 %hash, ptr %key) {",
            "entry:",
            f"  %cap.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 1",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 2",
            f"  %keys.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 3",
            "  %cap = load i64, ptr %cap.ptr",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %keys = load ptr, ptr %keys.ptr.ptr",
            "  %start = urem i64 %hash, %cap",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ %start, %entry ], [ %next.index, %next ]",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %index",
            "  %current.hash = load i64, ptr %hash.slot",
            "  %is.empty = icmp eq i64 %current.hash, 0",
            "  br i1 %is.empty, label %found, label %check.hash",
            "check.hash:",
            "  %same.hash = icmp eq i64 %current.hash, %hash",
            "  br i1 %same.hash, label %check.key, label %next",
            "check.key:",
            "  %key.slot = getelementptr inbounds ptr, ptr %keys, i64 %index",
            "  %current.key = load ptr, ptr %key.slot",
            "  %cmp = call i32 @strcmp(ptr %current.key, ptr %key)",
            "  %is.match = icmp eq i32 %cmp, 0",
            "  br i1 %is.match, label %found, label %next",
            "next:",
            "  %index.plus = add i64 %index, 1",
            "  %next.index = urem i64 %index.plus, %cap",
            "  br label %loop",
            "found:",
            "  ret i64 %index",
            "}",
            "",
            "define private void @tb_cache_reserve_for_put(ptr %cache) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 0",
            f"  %cap.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 1",
            f"  %hashes.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 2",
            f"  %keys.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 3",
            f"  %values.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 4",
            "  %len = load i64, ptr %len.ptr",
            "  %cap = load i64, ptr %cap.ptr",
            "  %used.twice = mul i64 %len, 2",
            "  %has.capacity = icmp slt i64 %used.twice, %cap",
            "  br i1 %has.capacity, label %done, label %grow",
            "grow:",
            "  %cap.is.zero = icmp eq i64 %cap, 0",
            "  %doubled = mul i64 %cap, 2",
            "  %new.cap = select i1 %cap.is.zero, i64 8, i64 %doubled",
            "  %old.hashes = load ptr, ptr %hashes.ptr",
            "  %old.keys = load ptr, ptr %keys.ptr",
            "  %old.values = load ptr, ptr %values.ptr",
            "  %new.size = mul i64 %new.cap, 8",
            "  %new.hashes = call ptr @tb_heap_alloc(i64 %new.size)",
            "  %new.keys = call ptr @tb_heap_alloc(i64 %new.size)",
            "  %new.values = call ptr @tb_heap_alloc(i64 %new.size)",
            "  br label %init.loop",
            "init.loop:",
            "  %init.index = phi i64 [ 0, %grow ], [ %init.next, %init.body ]",
            "  %init.more = icmp slt i64 %init.index, %new.cap",
            "  br i1 %init.more, label %init.body, label %init.done",
            "init.body:",
            "  %init.slot = getelementptr inbounds i64, ptr %new.hashes, i64 %init.index",
            "  store i64 0, ptr %init.slot",
            "  %init.next = add i64 %init.index, 1",
            "  br label %init.loop",
            "init.done:",
            "  store i64 %new.cap, ptr %cap.ptr",
            "  store ptr %new.hashes, ptr %hashes.ptr",
            "  store ptr %new.keys, ptr %keys.ptr",
            "  store ptr %new.values, ptr %values.ptr",
            "  store i64 0, ptr %len.ptr",
            "  br label %rehash.loop",
            "rehash.loop:",
            "  %rehash.index = phi i64 [ 0, %init.done ], [ %rehash.next.index, %rehash.advance ]",
            "  %rehash.more = icmp slt i64 %rehash.index, %cap",
            "  br i1 %rehash.more, label %rehash.body, label %grow.done",
            "rehash.body:",
            "  %old.hash.slot = getelementptr inbounds i64, ptr %old.hashes, i64 %rehash.index",
            "  %old.hash = load i64, ptr %old.hash.slot",
            "  %occupied = icmp ne i64 %old.hash, 0",
            "  br i1 %occupied, label %rehash.insert, label %rehash.advance",
            "rehash.insert:",
            "  %old.key.slot = getelementptr inbounds ptr, ptr %old.keys, i64 %rehash.index",
            "  %old.key = load ptr, ptr %old.key.slot",
            "  %old.value.slot = getelementptr inbounds i64, ptr %old.values, i64 %rehash.index",
            "  %old.value = load i64, ptr %old.value.slot",
            "  call void @tb_cache_put_string_int(ptr %cache, ptr %old.key, i64 %old.value)",
            "  br label %rehash.advance",
            "rehash.advance:",
            "  %rehash.next.index = add i64 %rehash.index, 1",
            "  br label %rehash.loop",
            "grow.done:",
            "  call void @free(ptr %old.hashes)",
            "  call void @free(ptr %old.keys)",
            "  call void @free(ptr %old.values)",
            "  ret void",
            "done:",
            "  ret void",
            "}",
            "",
            "define private void @tb_cache_put_string_int(ptr %cache, ptr %key, i64 %value) {",
            "entry:",
            "  call void @tb_cache_reserve_for_put(ptr %cache)",
            f"  %len.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 0",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 2",
            f"  %keys.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 3",
            f"  %values.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 4",
            "  %hash = call i64 @tb_cache_hash_key(ptr %key)",
            "  %slot.index = call i64 @tb_cache_find_slot(ptr %cache, i64 %hash, ptr %key)",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %keys = load ptr, ptr %keys.ptr.ptr",
            "  %values = load ptr, ptr %values.ptr.ptr",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index",
            "  %current.hash = load i64, ptr %hash.slot",
            "  %is.empty = icmp eq i64 %current.hash, 0",
            "  br i1 %is.empty, label %insert, label %update",
            "insert:",
            "  %key.slot = getelementptr inbounds ptr, ptr %keys, i64 %slot.index",
            "  %value.slot = getelementptr inbounds i64, ptr %values, i64 %slot.index",
            "  store i64 %hash, ptr %hash.slot",
            "  store ptr %key, ptr %key.slot",
            "  store i64 %value, ptr %value.slot",
            "  %len = load i64, ptr %len.ptr",
            "  %next.len = add i64 %len, 1",
            "  store i64 %next.len, ptr %len.ptr",
            "  ret void",
            "update:",
            "  %value.slot.update = getelementptr inbounds i64, ptr %values, i64 %slot.index",
            "  store i64 %value, ptr %value.slot.update",
            "  ret void",
            "}",
            "",
            "define private i64 @tb_cache_get_string_int(ptr %cache, ptr %key) {",
            "entry:",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 2",
            f"  %values.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 4",
            "  %hash = call i64 @tb_cache_hash_key(ptr %key)",
            "  %slot.index = call i64 @tb_cache_find_slot(ptr %cache, i64 %hash, ptr %key)",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index",
            "  %current.hash = load i64, ptr %hash.slot",
            "  %is.empty = icmp eq i64 %current.hash, 0",
            "  br i1 %is.empty, label %missing, label %found",
            "found:",
            "  %values = load ptr, ptr %values.ptr.ptr",
            "  %value.slot = getelementptr inbounds i64, ptr %values, i64 %slot.index",
            "  %value = load i64, ptr %value.slot",
            "  ret i64 %value",
            "missing:",
            "  ret i64 0",
            "}",
            "",
            "define private i1 @tb_cache_has_string_int(ptr %cache, ptr %key) {",
            "entry:",
            f"  %hashes.ptr.ptr = getelementptr inbounds {self.CACHE_TYPE_NAME}, ptr %cache, i32 0, i32 2",
            "  %hash = call i64 @tb_cache_hash_key(ptr %key)",
            "  %slot.index = call i64 @tb_cache_find_slot(ptr %cache, i64 %hash, ptr %key)",
            "  %hashes = load ptr, ptr %hashes.ptr.ptr",
            "  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index",
            "  %current.hash = load i64, ptr %hash.slot",
            "  %is.empty = icmp eq i64 %current.hash, 0",
            "  %is.present = xor i1 %is.empty, true",
            "  ret i1 %is.present",
            "}",
            "",
            "define private ptr @tb_map_keys_string_int(ptr %map) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
            f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %keys = load ptr, ptr %keys.ptr",
            f"  %result = call ptr @tb_array_new(i64 %len, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            f"  %result.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result, i32 0, i32 0",
            f"  %result.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result, i32 0, i32 2",
            "  %result.data = load ptr, ptr %result.data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %source.slot = getelementptr inbounds ptr, ptr %keys, i64 %index",
            "  %key = load ptr, ptr %source.slot",
            "  %key.owned = call ptr @tb_retain(ptr %key)",
            "  %target.slot = getelementptr inbounds ptr, ptr %result.data, i64 %index",
            "  store ptr %key.owned, ptr %target.slot",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  store i64 %len, ptr %result.len.ptr",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_map_values_string_int(ptr %map) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            "  %len = load i64, ptr %len.ptr",
            "  %values = load ptr, ptr %values.ptr",
            f"  %result = call ptr @tb_array_new(i64 %len, i64 8, i32 {self.RC_ARRAY_RELEASE_NONE})",
            f"  %result.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result, i32 0, i32 0",
            f"  %result.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result, i32 0, i32 2",
            "  %result.data = load ptr, ptr %result.data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %body ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %source.slot = getelementptr inbounds i64, ptr %values, i64 %index",
            "  %value = load i64, ptr %source.slot",
            "  %text = call ptr @tb_int_to_string(i64 %value)",
            "  %target.slot = getelementptr inbounds ptr, ptr %result.data, i64 %index",
            "  store ptr %text, ptr %target.slot",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  store i64 %len, ptr %result.len.ptr",
            "  ret ptr %result",
            "}",
            "",
            "define private ptr @tb_args_from_argv(i64 %argc, ptr %argv) {",
            "entry:",
            f"  %args = call ptr @tb_array_new(i64 %argc, i64 8, i32 {self.RC_ARRAY_RELEASE_PTRS})",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %args, i32 0, i32 0",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %body ]",
            "  %more = icmp slt i64 %index, %argc",
            "  br i1 %more, label %body, label %done",
            "body:",
            "  %argv.slot = getelementptr inbounds ptr, ptr %argv, i64 %index",
            "  %arg = load ptr, ptr %argv.slot",
            "  %arg.owned = call ptr @tb_retain(ptr %arg)",
            "  %element = call ptr @tb_array_element_ptr(ptr %args, i64 %index, i64 8)",
            "  store ptr %arg.owned, ptr %element",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "done:",
            "  store i64 %argc, ptr %len.ptr",
            "  ret ptr %args",
            "}",
            "",
            "define private i1 @tb_has_flag(ptr %args, ptr %flag) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %args, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %args, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %next ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %missing",
            "body:",
            "  %slot = getelementptr inbounds ptr, ptr %data, i64 %index",
            "  %arg = load ptr, ptr %slot",
            "  %cmp = call i32 @strcmp(ptr %arg, ptr %flag)",
            "  %matches = icmp eq i32 %cmp, 0",
            "  br i1 %matches, label %found, label %next",
            "next:",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "found:",
            "  ret i1 1",
            "missing:",
            "  ret i1 0",
            "}",
            "",
            "define private ptr @tb_option_value(ptr %args, ptr %option) {",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %args, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %args, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %option.len = call i64 @strlen(ptr %option)",
            "  br label %loop",
            "loop:",
            "  %index = phi i64 [ 0, %entry ], [ %next.index, %next ]",
            "  %more = icmp slt i64 %index, %len",
            "  br i1 %more, label %body, label %missing",
            "body:",
            "  %slot = getelementptr inbounds ptr, ptr %data, i64 %index",
            "  %arg = load ptr, ptr %slot",
            "  %cmp = call i32 @strcmp(ptr %arg, ptr %option)",
            "  %exact = icmp eq i32 %cmp, 0",
            "  br i1 %exact, label %exact.match, label %check.inline",
            "exact.match:",
            "  %value.index = add i64 %index, 1",
            "  %has.value = icmp slt i64 %value.index, %len",
            "  br i1 %has.value, label %return.next, label %missing",
            "return.next:",
            "  %value.slot = getelementptr inbounds ptr, ptr %data, i64 %value.index",
            "  %value = load ptr, ptr %value.slot",
            "  ret ptr %value",
            "check.inline:",
            "  %arg.len = call i64 @strlen(ptr %arg)",
            "  %long.enough = icmp sgt i64 %arg.len, %option.len",
            "  br i1 %long.enough, label %check.prefix, label %next",
            "check.prefix:",
            "  %prefix = call i1 @tb_starts_with(ptr %arg, ptr %option)",
            "  br i1 %prefix, label %check.equals, label %next",
            "check.equals:",
            "  %equals.ptr = getelementptr inbounds i8, ptr %arg, i64 %option.len",
            "  %equals.byte = load i8, ptr %equals.ptr",
            "  %is.equals = icmp eq i8 %equals.byte, 61",
            "  br i1 %is.equals, label %return.inline, label %next",
            "return.inline:",
            "  %inline.value = getelementptr inbounds i8, ptr %equals.ptr, i64 1",
            "  ret ptr %inline.value",
            "next:",
            "  %next.index = add i64 %index, 1",
            "  br label %loop",
            "missing:",
            "  %empty = call ptr @tb_string_copy_range(ptr %option, i64 0)",
            "  ret ptr %empty",
            "}",
        ]
        )
        helpers.extend(self._emit_record_destroy_helpers())
        helpers.extend(self._emit_cache_array_helpers())
        helpers.extend(self._emit_record_cache_key_helpers())
        helpers.extend(self._emit_record_hash_helpers())
        return helpers

    def _emit_record_destroy_helpers(self) -> list[str]:
        helpers: list[str] = []
        for record_type in self.record_types.values():
            helpers.extend(self._emit_record_destroy_helper(record_type))
        return helpers

    def _emit_record_destroy_helper(self, record_type: IRRecordType) -> list[str]:
        helpers = [
            f"define private void {self._record_destroy_symbol(record_type.name)}(ptr %record) {{",
            "entry:",
        ]
        for index, field in enumerate(record_type.fields):
            if not self._record_field_needs_release(field.type_name):
                continue
            field_pointer = f"%field.ptr.{index}"
            field_value = f"%field.value.{index}"
            helpers.extend(
                [
                    f"  {field_pointer} = getelementptr inbounds %record.{record_type.name}, ptr %record, i32 0, i32 {index}",
                    f"  {field_value} = load ptr, ptr {field_pointer}",
                    f"  call void @tb_release(ptr {field_value})",
                ]
            )
        helpers.extend(
            [
                f"  %header = getelementptr inbounds i8, ptr %record, i64 -{self.RC_HEADER_SIZE}",
                "  call void @free(ptr %header)",
                "  ret void",
                "}",
                "",
            ]
        )
        return helpers

    def _emit_cache_array_helpers(self) -> list[str]:
        helpers: list[str] = []
        for array_type in sorted(self._collect_cache_array_types()):
            if array_type in {"int[]", "string[]", "bool[]"}:
                continue
            helpers.extend(self._emit_cache_array_helper(array_type))
        return helpers

    def _collect_cache_array_types(self) -> set[str]:
        collected: set[str] = set()
        visited_records: set[str] = set()
        for record_name in self.record_types:
            self._collect_cache_array_types_for_type(record_name, collected, visited_records)
        return collected

    def _collect_cache_array_types_for_type(self, type_name: str, collected: set[str], visited_records: set[str]) -> None:
        if self._is_array_type(type_name):
            if type_name in collected:
                return
            collected.add(type_name)
            self._collect_cache_array_types_for_type(self._array_item_type(type_name), collected, visited_records)
            return
        if type_name not in self.record_types or type_name in visited_records:
            return
        visited_records.add(type_name)
        for field in self.record_types[type_name].fields:
            self._collect_cache_array_types_for_type(field.type_name, collected, visited_records)

    def _emit_cache_array_helper(self, array_type: str) -> list[str]:
        item_type = self._array_item_type(array_type)
        item_llvm_type = self._llvm_type_for(item_type)
        lines = [
            f"define private ptr {self._cache_array_string_symbol(array_type)}(ptr %array) {{",
            "entry:",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %array, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
            "  %has.items = icmp sgt i64 %len, 0",
            "  br i1 %has.items, label %measure.loop, label %empty",
            "empty:",
            "  %empty.buffer = call ptr @tb_string_new(i64 0)",
            "  store i8 0, ptr %empty.buffer",
            "  ret ptr %empty.buffer",
            "measure.loop:",
            "  %measure.index = phi i64 [ 0, %entry ], [ %measure.next, %measure.body ]",
            "  %measure.total = phi i64 [ 0, %entry ], [ %measure.total.next, %measure.body ]",
            "  %measure.more = icmp slt i64 %measure.index, %len",
            "  br i1 %measure.more, label %measure.body, label %measure.done",
            "measure.body:",
            f"  %measure.slot = getelementptr inbounds {item_llvm_type}, ptr %data, i64 %measure.index",
            f"  %measure.item = load {item_llvm_type}, ptr %measure.slot",
        ]
        measure_text = self._emit_cache_stringify_value(item_type, "%measure.item", lines, "measure")
        lines.append(f"  %measure.wrap = call ptr @tb_cache_wrap_string(ptr {measure_text})")
        if self._cache_stringify_needs_release(item_type):
            lines.append(f"  call void @tb_release(ptr {measure_text})")
        lines.append("  %measure.wrap.len = call i64 @strlen(ptr %measure.wrap)")
        lines.append("  %measure.total.next = add i64 %measure.total, %measure.wrap.len")
        lines.append("  call void @tb_release(ptr %measure.wrap)")
        lines.extend(
            [
                "  %measure.next = add i64 %measure.index, 1",
                "  br label %measure.loop",
                "measure.done:",
                "  %buffer.size = add i64 %measure.total, 1",
                "  %buffer = call ptr @tb_string_new(i64 %measure.total)",
                "  br label %copy.loop",
                "copy.loop:",
                "  %copy.index = phi i64 [ 0, %measure.done ], [ %copy.next, %copy.body ]",
                "  %copy.offset = phi i64 [ 0, %measure.done ], [ %copy.offset.next, %copy.body ]",
                "  %copy.more = icmp slt i64 %copy.index, %len",
                "  br i1 %copy.more, label %copy.body, label %copy.done",
                "copy.body:",
                f"  %copy.slot = getelementptr inbounds {item_llvm_type}, ptr %data, i64 %copy.index",
                f"  %copy.item = load {item_llvm_type}, ptr %copy.slot",
            ]
        )
        copy_text = self._emit_cache_stringify_value(item_type, "%copy.item", lines, "copy")
        lines.append(f"  %copy.wrap = call ptr @tb_cache_wrap_string(ptr {copy_text})")
        if self._cache_stringify_needs_release(item_type):
            lines.append(f"  call void @tb_release(ptr {copy_text})")
        lines.extend(
            [
                "  %copy.wrap.len = call i64 @strlen(ptr %copy.wrap)",
                "  %copy.dst = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
                "  call ptr @memcpy(ptr %copy.dst, ptr %copy.wrap, i64 %copy.wrap.len)",
                "  call void @tb_release(ptr %copy.wrap)",
                "  %copy.offset.next = add i64 %copy.offset, %copy.wrap.len",
                "  %copy.next = add i64 %copy.index, 1",
                "  br label %copy.loop",
                "copy.done:",
                "  %term = getelementptr inbounds i8, ptr %buffer, i64 %copy.offset",
                "  store i8 0, ptr %term",
                "  ret ptr %buffer",
                "}",
                "",
            ]
        )
        return lines

    def _emit_record_cache_key_helpers(self) -> list[str]:
        helpers: list[str] = []
        for record_type in self.record_types.values():
            helpers.extend(self._emit_record_cache_key_helper(record_type))
        return helpers

    def _emit_record_cache_key_helper(self, record_type: IRRecordType) -> list[str]:
        lines = [
            f"define private ptr {self._record_cache_key_symbol(record_type.name)}(ptr %record) {{",
            "entry:",
        ]
        if not record_type.fields:
            lines.extend(
                [
                    "  %empty = call ptr @tb_string_new(i64 0)",
                    "  store i8 0, ptr %empty",
                    "  ret ptr %empty",
                    "}",
                    "",
                ]
            )
            return lines

        field_lengths: list[str] = []
        for index, field in enumerate(record_type.fields):
            field_pointer = f"%field.ptr.{index}"
            field_value = f"%field.value.{index}"
            lines.append(
                f"  {field_pointer} = getelementptr inbounds %record.{record_type.name}, ptr %record, i32 0, i32 {index}"
            )
            lines.append(f"  {field_value} = load {self._llvm_type_for(field.type_name)}, ptr {field_pointer}")
            if field.type_name == "int":
                text_name = f"%field.text.{index}"
                key_name = f"%field.key.{index}"
                lines.append(f"  {text_name} = call ptr @tb_int_to_string(i64 {field_value})")
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name == "bool":
                bool_int = f"%field.bool.{index}"
                text_name = f"%field.text.{index}"
                key_name = f"%field.key.{index}"
                lines.append(f"  {bool_int} = zext i1 {field_value} to i64")
                lines.append(f"  {text_name} = call ptr @tb_int_to_string(i64 {bool_int})")
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name == "string" or field.type_name in self.enum_types:
                key_name = f"%field.key.{index}"
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {field_value})")
            elif self._is_array_type(field.type_name):
                text_name = f"%field.text.{index}"
                key_name = f"%field.key.{index}"
                lines.append(f"  {text_name} = call ptr {self._cache_array_string_symbol_for_type(field.type_name)}(ptr {field_value})")
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name in self.record_types:
                key_name = f"%field.key.{index}"
                lines.append(f"  {key_name} = call ptr {self._record_cache_key_symbol(field.type_name)}(ptr {field_value})")
            else:
                raise TypeError(f"Unsupported cached record field type: {field.type_name}")
            key_length = f"%field.key.len.{index}"
            lines.append(f"  {key_length} = call i64 @strlen(ptr {key_name})")
            lines.append(f"  call void @tb_release(ptr {key_name})")
            field_lengths.append(key_length)

        total_length = field_lengths[0]
        for index, key_length in enumerate(field_lengths[1:], start=1):
            next_total = f"%key.total.{index}"
            lines.append(f"  {next_total} = add i64 {total_length}, {key_length}")
            total_length = next_total
        buffer_size = "%key.buffer.size"
        buffer_name = "%key.buffer"
        lines.append(f"  {buffer_size} = add i64 {total_length}, 1")
        lines.append(f"  {buffer_name} = call ptr @tb_string_new(i64 {total_length})")

        current_offset = "0"
        for index, field in enumerate(record_type.fields):
            field_pointer = f"%copy.field.ptr.{index}"
            field_value = f"%copy.field.value.{index}"
            lines.append(
                f"  {field_pointer} = getelementptr inbounds %record.{record_type.name}, ptr %record, i32 0, i32 {index}"
            )
            lines.append(f"  {field_value} = load {self._llvm_type_for(field.type_name)}, ptr {field_pointer}")
            if field.type_name == "int":
                text_name = f"%copy.field.text.{index}"
                key_name = f"%copy.field.key.{index}"
                lines.append(f"  {text_name} = call ptr @tb_int_to_string(i64 {field_value})")
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name == "bool":
                bool_int = f"%copy.field.bool.{index}"
                text_name = f"%copy.field.text.{index}"
                key_name = f"%copy.field.key.{index}"
                lines.append(f"  {bool_int} = zext i1 {field_value} to i64")
                lines.append(f"  {text_name} = call ptr @tb_int_to_string(i64 {bool_int})")
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name == "string" or field.type_name in self.enum_types:
                key_name = f"%copy.field.key.{index}"
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {field_value})")
            elif self._is_array_type(field.type_name):
                text_name = f"%copy.field.text.{index}"
                key_name = f"%copy.field.key.{index}"
                lines.append(f"  {text_name} = call ptr {self._cache_array_string_symbol_for_type(field.type_name)}(ptr {field_value})")
                lines.append(f"  {key_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name in self.record_types:
                key_name = f"%copy.field.key.{index}"
                lines.append(f"  {key_name} = call ptr {self._record_cache_key_symbol(field.type_name)}(ptr {field_value})")
            else:
                raise TypeError(f"Unsupported cached record field type: {field.type_name}")
            key_length = field_lengths[index]
            destination = f"%key.dst.{index}"
            lines.append(f"  {destination} = getelementptr inbounds i8, ptr {buffer_name}, i64 {current_offset}")
            lines.append(f"  call ptr @memcpy(ptr {destination}, ptr {key_name}, i64 {key_length})")
            lines.append(f"  call void @tb_release(ptr {key_name})")
            if index + 1 < len(field_lengths):
                next_offset = f"%key.offset.{index}"
                lines.append(f"  {next_offset} = add i64 {current_offset}, {key_length}")
                current_offset = next_offset

        terminator = "%key.term"
        lines.append(f"  {terminator} = getelementptr inbounds i8, ptr {buffer_name}, i64 {total_length}")
        lines.append(f"  store i8 0, ptr {terminator}")
        lines.append(f"  ret ptr {buffer_name}")
        lines.append("}")
        lines.append("")
        return lines

    def _emit_record_hash_helpers(self) -> list[str]:
        helpers: list[str] = []
        for record_type in self.record_types.values():
            helpers.extend(self._emit_record_hash_helper(record_type))
        return helpers

    def _emit_record_hash_helper(self, record_type: IRRecordType) -> list[str]:
        lines = [
            f"define private i64 {self._record_hash_symbol(record_type.name)}(ptr %record) {{",
            "entry:",
            f"  %arena.mark = alloca {self.ARENA_MARK_TYPE_NAME}",
            "  call void @tb_arena_mark(ptr %arena.mark)",
        ]
        current_hash = "5381"
        if not record_type.fields:
            lines.append("  call void @tb_arena_reset(ptr %arena.mark)")
            lines.append("  ret i64 5381")
            lines.append("}")
            lines.append("")
            return lines
        for index, field in enumerate(record_type.fields):
            field_pointer = f"%field.ptr.{index}"
            field_value = f"%field.value.{index}"
            field_hash = f"%field.hash.{index}"
            mixed_hash = f"%hash.mul.{index}"
            next_hash = f"%hash.{index}"
            lines.append(
                f"  {field_pointer} = getelementptr inbounds %record.{record_type.name}, ptr %record, i32 0, i32 {index}"
            )
            lines.append(f"  {field_value} = load {self._llvm_type_for(field.type_name)}, ptr {field_pointer}")
            if field.type_name == "int":
                lines.append(f"  {field_hash} = call i64 @tb_hash_int(i64 {field_value})")
            elif field.type_name == "bool":
                bool_int = f"%field.bool.{index}"
                lines.append(f"  {bool_int} = zext i1 {field_value} to i64")
                lines.append(f"  {field_hash} = call i64 @tb_hash_int(i64 {bool_int})")
            elif field.type_name == "string" or field.type_name in self.enum_types:
                lines.append(f"  {field_hash} = call i64 @tb_hash_string(ptr {field_value})")
            elif self._is_array_type(field.type_name):
                text_name = f"%field.text.{index}"
                lines.append(f"  {text_name} = call ptr {self._cache_array_string_symbol_for_type(field.type_name)}(ptr {field_value})")
                lines.append(f"  {field_hash} = call i64 @tb_hash_string(ptr {text_name})")
                lines.append(f"  call void @tb_release(ptr {text_name})")
            elif field.type_name in self.record_types:
                lines.append(f"  {field_hash} = call i64 {self._record_hash_symbol(field.type_name)}(ptr {field_value})")
            else:
                raise TypeError(f"Unsupported cached record field type: {field.type_name}")
            lines.append(f"  {mixed_hash} = mul i64 {current_hash}, 33")
            lines.append(f"  {next_hash} = add i64 {mixed_hash}, {field_hash}")
            current_hash = next_hash
        lines.append("  call void @tb_arena_reset(ptr %arena.mark)")
        lines.append(f"  ret i64 {current_hash}")
        lines.append("}")
        lines.append("")
        return lines

    def _emit_generic_set_helpers(self, item_type: str) -> list[str]:
        if item_type == "int":
            return []
        item_llvm_type = self._llvm_type_for(item_type)
        contains_symbol = self._generic_set_contains_symbol(item_type)
        add_symbol = self._generic_set_add_symbol(item_type)
        union_symbol = self._generic_set_union_symbol(item_type)
        lines = [
            f"define private i1 {contains_symbol}(ptr %set, {item_llvm_type} %value) {{",
            "entry:",
            f"  %arena.mark = alloca {self.ARENA_MARK_TYPE_NAME}",
            "  call void @tb_arena_mark(ptr %arena.mark)",
            f"  %len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %set, i32 0, i32 0",
            f"  %data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %set, i32 0, i32 2",
            "  %len = load i64, ptr %len.ptr",
            "  %data = load ptr, ptr %data.ptr",
        ]
        needle_text = self._emit_cache_stringify_value(item_type, "%value", lines, "set.contains.needle")
        release_needle = self._cache_stringify_needs_release(item_type)
        lines.extend(
            [
                "  br label %loop",
                "loop:",
                "  %index = phi i64 [ 0, %entry ], [ %next, %advance ]",
                "  %more = icmp slt i64 %index, %len",
                "  br i1 %more, label %body, label %missing",
                "body:",
                f"  %slot = getelementptr inbounds {item_llvm_type}, ptr %data, i64 %index",
                f"  %item = load {item_llvm_type}, ptr %slot",
            ]
        )
        current_text = self._emit_cache_stringify_value(item_type, "%item", lines, "set.contains.item")
        release_current = self._cache_stringify_needs_release(item_type)
        lines.extend(
            [
                f"  %cmp = call i32 @strcmp(ptr {current_text}, ptr {needle_text})",
                *( [f"  call void @tb_release(ptr {current_text})"] if release_current else [] ),
                "  %match = icmp eq i32 %cmp, 0",
                "  br i1 %match, label %found, label %advance",
                "advance:",
                "  %next = add i64 %index, 1",
                "  br label %loop",
                "found:",
                *( [f"  call void @tb_release(ptr {needle_text})"] if release_needle else [] ),
                "  call void @tb_arena_reset(ptr %arena.mark)",
                "  ret i1 true",
                "missing:",
                *( [f"  call void @tb_release(ptr {needle_text})"] if release_needle else [] ),
                "  call void @tb_arena_reset(ptr %arena.mark)",
                "  ret i1 false",
                "}",
                "",
                f"define private void {add_symbol}(ptr %set, {item_llvm_type} %value) {{",
                "entry:",
                f"  %present = call i1 {contains_symbol}(ptr %set, {item_llvm_type} %value)",
                "  br i1 %present, label %release.duplicate, label %insert",
                "insert:",
                "  %value.slot = alloca " + item_llvm_type,
                f"  store {item_llvm_type} %value, ptr %value.slot",
                f"  call void @tb_array_push(ptr %set, ptr %value.slot, i64 {self._element_size(item_type)})",
                "  br label %done",
                "release.duplicate:",
                *(["  call void @tb_release(ptr %value)"] if self._type_needs_managed_storage(item_type) else []),
                "  br label %done",
                "done:",
                "  ret void",
                "}",
                "",
                f"define private ptr {union_symbol}(ptr %left, ptr %right) {{",
                "entry:",
                f"  %left.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %left, i32 0, i32 0",
                f"  %right.len.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %right, i32 0, i32 0",
                f"  %left.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %left, i32 0, i32 2",
                f"  %right.data.ptr = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %right, i32 0, i32 2",
                "  %left.len = load i64, ptr %left.len.ptr",
                "  %right.len = load i64, ptr %right.len.ptr",
                "  %left.data = load ptr, ptr %left.data.ptr",
                "  %right.data = load ptr, ptr %right.data.ptr",
                "  %capacity = add i64 %left.len, %right.len",
                f"  %result = call ptr @tb_set_new(i64 %capacity, i32 {self.RC_SET_RELEASE_PTRS if self._set_release_mode(item_type) == self.RC_SET_RELEASE_PTRS else self.RC_SET_RELEASE_NONE})",
                "  br label %left.loop",
                "left.loop:",
                "  %left.index = phi i64 [ 0, %entry ], [ %left.next, %left.body ]",
                "  %left.more = icmp slt i64 %left.index, %left.len",
                "  br i1 %left.more, label %left.body, label %right.loop",
                "left.body:",
                f"  %left.slot = getelementptr inbounds {item_llvm_type}, ptr %left.data, i64 %left.index",
                f"  %left.item = load {item_llvm_type}, ptr %left.slot",
                *([f"  %left.item.owned = call ptr @tb_retain(ptr %left.item)"] if item_type == "string" else []),
                *([f"  %left.item.owned = call ptr @tb_retain(ptr %left.item)"] if self._type_needs_managed_storage(item_type) and item_type != "string" else []),
                f"  call void {add_symbol}(ptr %result, {item_llvm_type} {'%left.item.owned' if self._type_needs_managed_storage(item_type) else '%left.item'})",
                "  %left.next = add i64 %left.index, 1",
                "  br label %left.loop",
                "right.loop:",
                "  %right.index = phi i64 [ 0, %left.loop ], [ %right.next, %right.body ]",
                "  %right.more = icmp slt i64 %right.index, %right.len",
                "  br i1 %right.more, label %right.body, label %done.union",
                "right.body:",
                f"  %right.slot = getelementptr inbounds {item_llvm_type}, ptr %right.data, i64 %right.index",
                f"  %right.item = load {item_llvm_type}, ptr %right.slot",
                *([f"  %right.item.owned = call ptr @tb_retain(ptr %right.item)"] if item_type == "string" else []),
                *([f"  %right.item.owned = call ptr @tb_retain(ptr %right.item)"] if self._type_needs_managed_storage(item_type) and item_type != "string" else []),
                f"  call void {add_symbol}(ptr %result, {item_llvm_type} {'%right.item.owned' if self._type_needs_managed_storage(item_type) else '%right.item'})",
                "  %right.next = add i64 %right.index, 1",
                "  br label %right.loop",
                "done.union:",
                "  ret ptr %result",
                "}",
                "",
            ]
        )
        return lines

    def _emit_generic_map_helpers(self, key_type: str, value_type: str) -> list[str]:
        if (key_type, value_type) == ("string", "int"):
            return []
        key_llvm_type = self._llvm_type_for(key_type)
        value_llvm_type = self._llvm_type_for(value_type)
        put_symbol = self._generic_map_put_symbol(key_type, value_type)
        get_symbol = self._generic_map_get_symbol(key_type, value_type)
        has_symbol = self._generic_map_has_symbol(key_type, value_type)
        keys_symbol = self._generic_map_keys_symbol(key_type, value_type)
        values_symbol = self._generic_map_values_symbol(key_type, value_type)
        key_needs_cache_stringify = self._cache_stringify_needs_release(key_type)
        key_needs_release = self._map_release_mode(key_type) == self.RC_MAP_RELEASE_PTRS
        value_needs_release = self._map_release_mode(value_type) == self.RC_MAP_RELEASE_PTRS
        key_store_value = "%key.insert.owned" if key_type == "string" else "%key"
        value_store_value = "%value.update.owned" if value_type == "string" else "%value"
        value_insert_store_value = "%value.insert.owned" if value_type == "string" else "%value"
        key_copy_value = "%keys.item.owned" if key_needs_release else "%keys.item"
        value_copy_value = "%values.item.owned" if value_needs_release else "%values.item"
        lines = [
            f"define private void {put_symbol}(ptr %map, {key_llvm_type} %key, {value_llvm_type} %value) {{",
            "entry:",
            *([f"  %arena.mark = alloca {self.ARENA_MARK_TYPE_NAME}", "  call void @tb_arena_mark(ptr %arena.mark)"] if key_needs_cache_stringify else []),
            f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
            f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
            f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
            "  %len = load i64, ptr %len.ptr",
            "  %keys = load ptr, ptr %keys.ptr",
            "  %values = load ptr, ptr %values.ptr",
        ]
        needle_text = self._emit_cache_stringify_value(key_type, "%key", lines, "map.put.needle")
        release_put_needle = self._cache_stringify_needs_release(key_type)
        lines.extend(
            [
                "  br label %loop",
                "loop:",
                "  %index = phi i64 [ 0, %entry ], [ %next, %advance ]",
                "  %more = icmp slt i64 %index, %len",
                "  br i1 %more, label %body, label %insert",
                "body:",
                f"  %key.slot = getelementptr inbounds {key_llvm_type}, ptr %keys, i64 %index",
                f"  %current.key = load {key_llvm_type}, ptr %key.slot",
            ]
        )
        current_text = self._emit_cache_stringify_value(key_type, "%current.key", lines, "map.put.key")
        release_put_current = self._cache_stringify_needs_release(key_type)
        lines.extend(
            [
                f"  %cmp = call i32 @strcmp(ptr {current_text}, ptr {needle_text})",
                *( [f"  call void @tb_release(ptr {current_text})"] if release_put_current else [] ),
                "  %match = icmp eq i32 %cmp, 0",
                "  br i1 %match, label %update, label %advance",
                "advance:",
                "  %next = add i64 %index, 1",
                "  br label %loop",
                "update:",
                f"  %value.slot.update = getelementptr inbounds {value_llvm_type}, ptr %values, i64 %index",
                *([f"  %value.old = load {value_llvm_type}, ptr %value.slot.update"] if value_needs_release else []),
                *(["  call void @tb_release(ptr %value.old)"] if value_needs_release else []),
                *([f"  %value.update.owned = call ptr @tb_retain(ptr %value)"] if value_type == "string" else []),
                f"  store {value_llvm_type} {value_store_value}, ptr %value.slot.update",
                *( [f"  call void @tb_release(ptr {needle_text})"] if release_put_needle else [] ),
                *(["  call void @tb_arena_reset(ptr %arena.mark)"] if key_needs_cache_stringify else []),
                "  ret void",
                "insert:",
                "  call void @tb_map_reserve_for_put(ptr %map)",
                "  %len.insert = load i64, ptr %len.ptr",
                "  %keys.insert = load ptr, ptr %keys.ptr",
                "  %values.insert = load ptr, ptr %values.ptr",
                *([f"  %key.insert.owned = call ptr @tb_retain(ptr %key)"] if key_type == "string" else []),
                *([f"  %value.insert.owned = call ptr @tb_retain(ptr %value)"] if value_type == "string" else []),
                f"  %key.slot.insert = getelementptr inbounds {key_llvm_type}, ptr %keys.insert, i64 %len.insert",
                f"  %value.slot.insert = getelementptr inbounds {value_llvm_type}, ptr %values.insert, i64 %len.insert",
                f"  store {key_llvm_type} {key_store_value}, ptr %key.slot.insert",
                f"  store {value_llvm_type} {value_insert_store_value}, ptr %value.slot.insert",
                "  %next.len = add i64 %len.insert, 1",
                "  store i64 %next.len, ptr %len.ptr",
                *( [f"  call void @tb_release(ptr {needle_text})"] if release_put_needle else [] ),
                *(["  call void @tb_arena_reset(ptr %arena.mark)"] if key_needs_cache_stringify else []),
                "  ret void",
                "}",
                "",
                f"define private {value_llvm_type} {get_symbol}(ptr %map, {key_llvm_type} %key) {{",
                "entry:",
                *([f"  %arena.mark.get = alloca {self.ARENA_MARK_TYPE_NAME}", "  call void @tb_arena_mark(ptr %arena.mark.get)"] if key_needs_cache_stringify else []),
                f"  %len.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
                f"  %keys.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
                f"  %values.ptr = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
                "  %len = load i64, ptr %len.ptr",
                "  %keys = load ptr, ptr %keys.ptr",
                "  %values = load ptr, ptr %values.ptr",
            ]
        )
        get_text = self._emit_cache_stringify_value(key_type, "%key", lines, "map.get.needle")
        release_get_needle = self._cache_stringify_needs_release(key_type)
        lines.extend(
            [
                "  br label %loop.get",
                "loop.get:",
                "  %index.get = phi i64 [ 0, %entry ], [ %next.get, %advance.get ]",
                "  %more.get = icmp slt i64 %index.get, %len",
                "  br i1 %more.get, label %body.get, label %missing.get",
                "body.get:",
                f"  %key.slot.get = getelementptr inbounds {key_llvm_type}, ptr %keys, i64 %index.get",
                f"  %current.key.get = load {key_llvm_type}, ptr %key.slot.get",
            ]
        )
        current_get_text = self._emit_cache_stringify_value(key_type, "%current.key.get", lines, "map.get.key")
        release_get_current = self._cache_stringify_needs_release(key_type)
        lines.extend(
            [
                f"  %cmp.get = call i32 @strcmp(ptr {current_get_text}, ptr {get_text})",
                *( [f"  call void @tb_release(ptr {current_get_text})"] if release_get_current else [] ),
                "  %match.get = icmp eq i32 %cmp.get, 0",
                "  br i1 %match.get, label %found.get, label %advance.get",
                "advance.get:",
                "  %next.get = add i64 %index.get, 1",
                "  br label %loop.get",
                "found.get:",
                f"  %value.slot.get = getelementptr inbounds {value_llvm_type}, ptr %values, i64 %index.get",
                f"  %value.get = load {value_llvm_type}, ptr %value.slot.get",
                *( [f"  call void @tb_release(ptr {get_text})"] if release_get_needle else [] ),
                *(["  call void @tb_arena_reset(ptr %arena.mark.get)"] if key_needs_cache_stringify else []),
                f"  ret {value_llvm_type} %value.get",
                "missing.get:",
                *( [f"  call void @tb_release(ptr {get_text})"] if release_get_needle else [] ),
                *(["  call void @tb_arena_reset(ptr %arena.mark.get)"] if key_needs_cache_stringify else []),
                f"  ret {value_llvm_type} zeroinitializer",
                "}",
                "",
                f"define private i1 {has_symbol}(ptr %map, {key_llvm_type} %key) {{",
                "entry:",
                *([f"  %arena.mark.has = alloca {self.ARENA_MARK_TYPE_NAME}", "  call void @tb_arena_mark(ptr %arena.mark.has)"] if key_needs_cache_stringify else []),
                f"  %len.ptr.has = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
                f"  %keys.ptr.has = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
                "  %len.has = load i64, ptr %len.ptr.has",
                "  %keys.has = load ptr, ptr %keys.ptr.has",
            ]
        )
        has_text = self._emit_cache_stringify_value(key_type, "%key", lines, "map.has.needle")
        release_has_needle = self._cache_stringify_needs_release(key_type)
        lines.extend(
            [
                "  br label %loop.has",
                "loop.has:",
                "  %index.has = phi i64 [ 0, %entry ], [ %next.has, %advance.has ]",
                "  %more.has = icmp slt i64 %index.has, %len.has",
                "  br i1 %more.has, label %body.has, label %missing.has",
                "body.has:",
                f"  %key.slot.has = getelementptr inbounds {key_llvm_type}, ptr %keys.has, i64 %index.has",
                f"  %current.key.has = load {key_llvm_type}, ptr %key.slot.has",
            ]
        )
        current_has_text = self._emit_cache_stringify_value(key_type, "%current.key.has", lines, "map.has.key")
        release_has_current = self._cache_stringify_needs_release(key_type)
        lines.extend(
            [
                f"  %cmp.has = call i32 @strcmp(ptr {current_has_text}, ptr {has_text})",
                *( [f"  call void @tb_release(ptr {current_has_text})"] if release_has_current else [] ),
                "  %match.has = icmp eq i32 %cmp.has, 0",
                "  br i1 %match.has, label %found.has, label %advance.has",
                "advance.has:",
                "  %next.has = add i64 %index.has, 1",
                "  br label %loop.has",
                "found.has:",
                *( [f"  call void @tb_release(ptr {has_text})"] if release_has_needle else [] ),
                *(["  call void @tb_arena_reset(ptr %arena.mark.has)"] if key_needs_cache_stringify else []),
                "  ret i1 true",
                "missing.has:",
                *( [f"  call void @tb_release(ptr {has_text})"] if release_has_needle else [] ),
                *(["  call void @tb_arena_reset(ptr %arena.mark.has)"] if key_needs_cache_stringify else []),
                "  ret i1 false",
                "}",
                "",
                f"define private ptr {keys_symbol}(ptr %map) {{",
                "entry:",
                f"  %len.ptr.keys = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
                f"  %keys.ptr.keys = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 2",
                "  %len.keys = load i64, ptr %len.ptr.keys",
                "  %keys.src = load ptr, ptr %keys.ptr.keys",
                f"  %result.keys = call ptr @tb_array_new(i64 %len.keys, i64 {self._element_size(key_type)}, i32 {self._array_release_mode(key_type)})",
                f"  %result.data.ptr.keys = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result.keys, i32 0, i32 2",
                f"  %result.len.ptr.keys = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result.keys, i32 0, i32 0",
                "  %result.data.keys = load ptr, ptr %result.data.ptr.keys",
                "  br label %keys.loop",
                "keys.loop:",
                "  %keys.index = phi i64 [ 0, %entry ], [ %keys.next, %keys.body ]",
                "  %keys.more = icmp slt i64 %keys.index, %len.keys",
                "  br i1 %keys.more, label %keys.body, label %keys.done",
                "keys.body:",
                f"  %keys.src.slot = getelementptr inbounds {key_llvm_type}, ptr %keys.src, i64 %keys.index",
                f"  %keys.item = load {key_llvm_type}, ptr %keys.src.slot",
                *([f"  %keys.item.owned = call ptr @tb_retain(ptr %keys.item)"] if key_type == "string" else []),
                *([f"  %keys.item.owned = call ptr @tb_retain(ptr %keys.item)"] if key_needs_release and key_type != "string" else []),
                f"  %keys.dst.slot = getelementptr inbounds {key_llvm_type}, ptr %result.data.keys, i64 %keys.index",
                f"  store {key_llvm_type} {key_copy_value}, ptr %keys.dst.slot",
                "  %keys.next = add i64 %keys.index, 1",
                "  br label %keys.loop",
                "keys.done:",
                "  store i64 %len.keys, ptr %result.len.ptr.keys",
                "  ret ptr %result.keys",
                "}",
                "",
                f"define private ptr {values_symbol}(ptr %map) {{",
                "entry:",
                f"  %len.ptr.values = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 0",
                f"  %values.ptr.values = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr %map, i32 0, i32 3",
                "  %len.values = load i64, ptr %len.ptr.values",
                "  %values.src = load ptr, ptr %values.ptr.values",
                f"  %result.values = call ptr @tb_array_new(i64 %len.values, i64 {self._element_size(value_type)}, i32 {self._array_release_mode(value_type)})",
                f"  %result.data.ptr.values = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result.values, i32 0, i32 2",
                f"  %result.len.ptr.values = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr %result.values, i32 0, i32 0",
                "  %result.data.values = load ptr, ptr %result.data.ptr.values",
                "  br label %values.loop",
                "values.loop:",
                "  %values.index = phi i64 [ 0, %entry ], [ %values.next, %values.body ]",
                "  %values.more = icmp slt i64 %values.index, %len.values",
                "  br i1 %values.more, label %values.body, label %values.done",
                "values.body:",
                f"  %values.src.slot = getelementptr inbounds {value_llvm_type}, ptr %values.src, i64 %values.index",
                f"  %values.item = load {value_llvm_type}, ptr %values.src.slot",
                *([f"  %values.item.owned = call ptr @tb_retain(ptr %values.item)"] if value_type == "string" else []),
                *([f"  %values.item.owned = call ptr @tb_retain(ptr %values.item)"] if value_needs_release and value_type != "string" else []),
                f"  %values.dst.slot = getelementptr inbounds {value_llvm_type}, ptr %result.data.values, i64 %values.index",
                f"  store {value_llvm_type} {value_copy_value}, ptr %values.dst.slot",
                "  %values.next = add i64 %values.index, 1",
                "  br label %values.loop",
                "values.done:",
                "  store i64 %len.values, ptr %result.len.ptr.values",
                "  ret ptr %result.values",
                "}",
                "",
            ]
        )
        return lines

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
    def _is_priority_queue_type(type_name: str) -> bool:
        return type_name.startswith("prio_q<") and type_name.endswith(">")

    @staticmethod
    def _is_map_type(type_name: str) -> bool:
        return type_name.startswith("map<") and type_name.endswith(">")

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

    def _element_size(self, type_name: str) -> int:
        if type_name == "bool":
            return 1
        if type_name == "num":
            raise TypeError("Runtime num arrays are not supported")
        return 8

    def _array_release_mode(self, item_type: str) -> int:
        if (
            item_type == "string"
            or self._is_array_type(item_type)
            or self._is_set_type(item_type)
            or self._is_map_type(item_type)
            or item_type in self.record_types
        ):
            return self.RC_ARRAY_RELEASE_PTRS
        return self.RC_ARRAY_RELEASE_NONE

    def _set_release_mode(self, item_type: str) -> int:
        if (
            item_type == "string"
            or self._is_array_type(item_type)
            or self._is_set_type(item_type)
            or self._is_map_type(item_type)
            or item_type in self.record_types
        ):
            return self.RC_SET_RELEASE_PTRS
        return self.RC_SET_RELEASE_NONE

    def _map_release_mode(self, type_name: str) -> int:
        if (
            type_name == "string"
            or self._is_array_type(type_name)
            or self._is_set_type(type_name)
            or self._is_map_type(type_name)
            or type_name in self.record_types
        ):
            return self.RC_MAP_RELEASE_PTRS
        return self.RC_MAP_RELEASE_NONE

    def _priority_queue_item_mode(self, type_name: str) -> int:
        if type_name == "string":
            return self.RC_PQ_ITEM_STRING
        if self._is_array_type(type_name) or self._is_set_type(type_name) or self._is_map_type(type_name) or self._is_priority_queue_type(type_name) or type_name in self.record_types:
            return self.RC_PQ_ITEM_PTR
        return self.RC_PQ_ITEM_NONE

    def _record_field_needs_release(self, type_name: str) -> bool:
        return (
            type_name == "string"
            or self._is_array_type(type_name)
            or self._is_set_type(type_name)
            or self._is_map_type(type_name)
            or self._is_priority_queue_type(type_name)
            or type_name in self.record_types
        )

    def _type_needs_managed_storage(self, type_name: str) -> bool:
        return (
            type_name == "string"
            or self._is_array_type(type_name)
            or self._is_set_type(type_name)
            or self._is_map_type(type_name)
            or self._is_priority_queue_type(type_name)
            or type_name in self.record_types
        )

    def _emit_array_expression(self, expression, lines: list[str], string_lengths: dict[str, int], expected_type: str | None = None) -> str:
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            variable_type = self.variable_types.get(expression.name)
            if slot_name is None or variable_type is None or (not self._is_array_type(variable_type) and not self._is_set_type(variable_type)):
                slot_name = self.global_variable_symbols.get(expression.name)
                variable_type = self.global_variable_types.get(expression.name)
                if slot_name is None or variable_type is None or (not self._is_array_type(variable_type) and not self._is_set_type(variable_type)):
                    raise TypeError(f"Unknown array variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRArrayLiteral):
            array_name = self._next_temp("array")
            initial_capacity = max(len(expression.items), 4)
            lines.append(
                f"  {array_name} = call ptr @tb_array_new(i64 {initial_capacity}, i64 {self._element_size(expression.item_type)}, i32 {self._array_release_mode(expression.item_type)})"
            )
            for item in expression.items:
                value_pointer = self._emit_value_pointer(expression.item_type, item, lines, string_lengths, own_for_storage=True)
                lines.append(
                    f"  call void @tb_array_push(ptr {array_name}, ptr {value_pointer}, i64 {self._element_size(expression.item_type)})"
                )
            return array_name
        if isinstance(expression, IRSetLiteral):
            set_name = self._next_temp("set")
            initial_capacity = max(len(expression.items), 4)
            lines.append(f"  {set_name} = call ptr @tb_set_new(i64 {initial_capacity}, i32 {self._set_release_mode(expression.item_type)})")
            for item in expression.items:
                value = self._emit_owned_storage_value(expression.item_type, item, lines, string_lengths)
                lines.append(f"  call void {self._generic_set_add_symbol(expression.item_type)}(ptr {set_name}, {self._llvm_type_for(expression.item_type)} {value})")
            return set_name
        if isinstance(expression, IRArrayMap):
            result_array = self._next_temp("map")
            index_label = self._next_label("map_loop")
            body_label = self._next_label("map_body")
            done_label = self._next_label("map_done")
            parameter_slot = self._next_temp("map_arg")
            parameter_llvm_type = self._llvm_type_for(expression.source_item_type)
            previous_slot = self.variable_slots.get(expression.parameter_name)
            previous_type = self.variable_types.get(expression.parameter_name)
            self.variable_slots[expression.parameter_name] = parameter_slot
            self.variable_types[expression.parameter_name] = expression.source_item_type
            self.alloca_lines.append(f"  {parameter_slot} = alloca {parameter_llvm_type}")
            source_array = self._emit_array_expression(
                expression.target,
                lines,
                string_lengths,
                f"{expression.source_item_type}[]",
            )
            source_len_ptr = self._next_temp("len")
            source_len = self._next_temp("len")
            source_data_ptr = self._next_temp("data")
            source_data = self._next_temp("data")
            lines.append(f"  {source_len_ptr} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {source_array}, i32 0, i32 0")
            lines.append(f"  {source_len} = load i64, ptr {source_len_ptr}")
            lines.append(f"  {source_data_ptr} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {source_array}, i32 0, i32 2")
            lines.append(f"  {source_data} = load ptr, ptr {source_data_ptr}")
            lines.append(
                f"  {result_array} = call ptr @tb_array_new(i64 {source_len}, i64 {self._element_size(expression.result_item_type)}, i32 {self._array_release_mode(expression.result_item_type)})"
            )
            index_slot = self._next_temp("map_index")
            self.alloca_lines.append(f"  {index_slot} = alloca i64")
            lines.append(f"  store i64 0, ptr {index_slot}")
            lines.append(f"  br label %{index_label}")
            lines.append(f"{index_label}:")
            index_value = self._next_temp("map_index")
            lines.append(f"  {index_value} = load i64, ptr {index_slot}")
            more_value = self._next_temp("map_more")
            lines.append(f"  {more_value} = icmp slt i64 {index_value}, {source_len}")
            lines.append(f"  br i1 {more_value}, label %{body_label}, label %{done_label}")
            lines.append(f"{body_label}:")
            source_slot = self._next_temp("map_slot")
            source_item = self._next_temp("map_item")
            lines.append(f"  {source_slot} = getelementptr inbounds {parameter_llvm_type}, ptr {source_data}, i64 {index_value}")
            lines.append(f"  {source_item} = load {parameter_llvm_type}, ptr {source_slot}")
            lines.append(f"  store {parameter_llvm_type} {source_item}, ptr {parameter_slot}")
            mapped_pointer = self._emit_value_pointer(expression.result_item_type, expression.body, lines, string_lengths, own_for_storage=True)
            lines.append(
                f"  call void @tb_array_push(ptr {result_array}, ptr {mapped_pointer}, i64 {self._element_size(expression.result_item_type)})"
            )
            next_value = self._next_temp("map_next")
            lines.append(f"  {next_value} = add i64 {index_value}, 1")
            lines.append(f"  store i64 {next_value}, ptr {index_slot}")
            lines.append(f"  br label %{index_label}")
            lines.append(f"{done_label}:")
            if previous_slot is None:
                self.variable_slots.pop(expression.parameter_name, None)
            else:
                self.variable_slots[expression.parameter_name] = previous_slot
            if previous_type is None:
                self.variable_types.pop(expression.parameter_name, None)
            else:
                self.variable_types[expression.parameter_name] = previous_type
            return result_array
        if isinstance(expression, IRArrayCollect):
            source_array = self._emit_array_expression(
                expression.target,
                lines,
                string_lengths,
                f"{expression.item_type}[][]",
            )
            result_array = self._next_temp("collect")
            lines.append(
                f"  {result_array} = call ptr @tb_array_collect(ptr {source_array}, i64 {self._element_size(expression.item_type)}, i32 {self._array_release_mode(expression.item_type)})"
            )
            return result_array
        if isinstance(expression, IRArrayFilter):
            result_array = self._next_temp("filter")
            index_label = self._next_label("filter_loop")
            body_label = self._next_label("filter_body")
            keep_label = self._next_label("filter_keep")
            next_label = self._next_label("filter_next")
            done_label = self._next_label("filter_done")
            parameter_slot = self._next_temp("filter_arg")
            parameter_llvm_type = self._llvm_type_for(expression.item_type)
            previous_slot = self.variable_slots.get(expression.parameter_name)
            previous_type = self.variable_types.get(expression.parameter_name)
            self.variable_slots[expression.parameter_name] = parameter_slot
            self.variable_types[expression.parameter_name] = expression.item_type
            self.alloca_lines.append(f"  {parameter_slot} = alloca {parameter_llvm_type}")
            source_array = self._emit_array_expression(expression.target, lines, string_lengths, f"{expression.item_type}[]")
            source_len_ptr = self._next_temp("len")
            source_len = self._next_temp("len")
            source_data_ptr = self._next_temp("data")
            source_data = self._next_temp("data")
            lines.append(f"  {source_len_ptr} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {source_array}, i32 0, i32 0")
            lines.append(f"  {source_len} = load i64, ptr {source_len_ptr}")
            lines.append(f"  {source_data_ptr} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {source_array}, i32 0, i32 2")
            lines.append(f"  {source_data} = load ptr, ptr {source_data_ptr}")
            lines.append(
                f"  {result_array} = call ptr @tb_array_new(i64 {source_len}, i64 {self._element_size(expression.item_type)}, i32 {self._array_release_mode(expression.item_type)})"
            )
            index_slot = self._next_temp("filter_index")
            self.alloca_lines.append(f"  {index_slot} = alloca i64")
            lines.append(f"  store i64 0, ptr {index_slot}")
            lines.append(f"  br label %{index_label}")
            lines.append(f"{index_label}:")
            index_value = self._next_temp("filter_index")
            lines.append(f"  {index_value} = load i64, ptr {index_slot}")
            more_value = self._next_temp("filter_more")
            lines.append(f"  {more_value} = icmp slt i64 {index_value}, {source_len}")
            lines.append(f"  br i1 {more_value}, label %{body_label}, label %{done_label}")
            lines.append(f"{body_label}:")
            source_slot = self._next_temp("filter_slot")
            source_item = self._next_temp("filter_item")
            lines.append(f"  {source_slot} = getelementptr inbounds {parameter_llvm_type}, ptr {source_data}, i64 {index_value}")
            lines.append(f"  {source_item} = load {parameter_llvm_type}, ptr {source_slot}")
            lines.append(f"  store {parameter_llvm_type} {source_item}, ptr {parameter_slot}")
            predicate = self._emit_boolean_expression(expression.predicate, lines)
            lines.append(f"  br i1 {predicate}, label %{keep_label}, label %{next_label}")
            lines.append(f"{keep_label}:")
            keep_ptr = self._emit_value_pointer(expression.item_type, IRVariable(expression.parameter_name), lines, string_lengths, own_for_storage=True)
            lines.append(
                f"  call void @tb_array_push(ptr {result_array}, ptr {keep_ptr}, i64 {self._element_size(expression.item_type)})"
            )
            lines.append(f"  br label %{next_label}")
            lines.append(f"{next_label}:")
            next_value = self._next_temp("filter_next")
            lines.append(f"  {next_value} = add i64 {index_value}, 1")
            lines.append(f"  store i64 {next_value}, ptr {index_slot}")
            lines.append(f"  br label %{index_label}")
            lines.append(f"{done_label}:")
            if previous_slot is None:
                self.variable_slots.pop(expression.parameter_name, None)
            else:
                self.variable_slots[expression.parameter_name] = previous_slot
            if previous_type is None:
                self.variable_types.pop(expression.parameter_name, None)
            else:
                self.variable_types[expression.parameter_name] = previous_type
            return result_array
        if isinstance(expression, IRCallExpression) and (self._is_array_type(expression.return_type) or self._is_set_type(expression.return_type)):
            return self._emit_call_expression(expression, lines, string_lengths)
        if isinstance(expression, IRMapIndex) and (self._is_array_type(expression.value_type) or self._is_set_type(expression.value_type)):
            return self._emit_map_index_value(expression, expression.value_type, lines, string_lengths)
        if isinstance(expression, IRArrayPop) and self._is_array_type(expression.item_type):
            return self._emit_array_remove_value(expression, lines, string_lengths, pop_last=True)
        if isinstance(expression, IRArrayRemove) and self._is_array_type(expression.item_type):
            return self._emit_array_remove_value(expression, lines, string_lengths)
        if isinstance(expression, IRArrayIndex) and self._is_array_type(expression.item_type):
            element_pointer = self._emit_array_element_pointer(expression.target, expression.index, expression.item_type, lines, string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {element_pointer}")
            return temp_name
        if isinstance(expression, IRRecordField) and self._is_array_type(expression.field_type):
            field_pointer = self._emit_record_field_pointer(expression, lines, string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {field_pointer}")
            return temp_name
        raise TypeError(f"Unsupported array IR expression: {type(expression).__name__}")

    def _emit_priority_queue_expression(self, expression, lines: list[str], string_lengths: dict[str, int], expected_type: str | None = None) -> str:
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            variable_type = self.variable_types.get(expression.name)
            if slot_name is None or variable_type is None or not self._is_priority_queue_type(variable_type):
                slot_name = self.global_variable_symbols.get(expression.name)
                variable_type = self.global_variable_types.get(expression.name)
                if slot_name is None or variable_type is None or not self._is_priority_queue_type(variable_type):
                    raise TypeError(f"Unknown priority queue variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRPriorityQueueCreate):
            source_array = self._emit_array_expression(expression.source, lines, string_lengths, f"{expression.item_type}[]")
            temp_name = self._next_temp("pq")
            comparator_symbol = self._sort_comparator_symbol(expression.item_type, expression.comparator_name)
            lines.append(
                f"  {temp_name} = call ptr @tb_pq_new(ptr {source_array}, i64 {self._element_size(expression.item_type)}, i32 {self._priority_queue_item_mode(expression.item_type)}, ptr {comparator_symbol})"
            )
            return temp_name
        if isinstance(expression, IRCallExpression) and self._is_priority_queue_type(expression.return_type):
            return self._emit_call_expression(expression, lines, string_lengths)
        raise TypeError(f"Unsupported priority queue IR expression: {type(expression).__name__}")

    def _emit_map_expression(self, expression, lines: list[str], string_lengths: dict[str, int], expected_type: str | None = None) -> str:
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            variable_type = self.variable_types.get(expression.name)
            if slot_name is None or variable_type is None or not self._is_map_type(variable_type):
                slot_name = self.global_variable_symbols.get(expression.name)
                variable_type = self.global_variable_types.get(expression.name)
                if slot_name is None or variable_type is None or not self._is_map_type(variable_type):
                    raise TypeError(f"Unknown map variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRMapLiteral):
            map_name = self._next_temp("map")
            initial_capacity = max(len(expression.items), 4)
            lines.append(
                f"  {map_name} = call ptr @tb_map_new(i64 {initial_capacity}, i32 {self._map_release_mode(expression.key_type)}, i32 {self._map_release_mode(expression.value_type)})"
            )
            for key, value in expression.items:
                if (expression.key_type, expression.value_type) == ("string", "int"):
                    key_value = self._emit_value_expression(expression.key_type, key, lines, string_lengths)
                    value_value = self._emit_value_expression(expression.value_type, value, lines, string_lengths)
                else:
                    key_value = self._emit_owned_storage_value(expression.key_type, key, lines, string_lengths)
                    value_value = self._emit_owned_storage_value(expression.value_type, value, lines, string_lengths)
                lines.append(
                    f"  call void {self._generic_map_put_symbol(expression.key_type, expression.value_type)}"
                    f"(ptr {map_name}, {self._llvm_type_for(expression.key_type)} {key_value}, {self._llvm_type_for(expression.value_type)} {value_value})"
                )
            return map_name
        if isinstance(expression, IRCallExpression) and self._is_map_type(expression.return_type):
            return self._emit_call_expression(expression, lines, string_lengths)
        raise TypeError(f"Unsupported map IR expression: {type(expression).__name__}")

    def _emit_record_expression(self, expression, lines: list[str], string_lengths: dict[str, int], expected_type: str | None = None) -> str:
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            variable_type = self.variable_types.get(expression.name)
            if slot_name is None or variable_type is None or variable_type not in self.record_types:
                slot_name = self.global_variable_symbols.get(expression.name)
                variable_type = self.global_variable_types.get(expression.name)
                if slot_name is None or variable_type is None or variable_type not in self.record_types:
                    raise TypeError(f"Unknown record variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRRecordConstruct):
            size_ptr = self._next_temp("size")
            size = self._next_temp("size")
            total_size = self._next_temp("size")
            allocation = self._next_temp("record.alloc")
            refcount_ptr = self._next_temp("record.refcount")
            kind_ptr = self._next_temp("record.kind")
            flags_ptr = self._next_temp("record.flags")
            record_flags = self._next_temp("record.flags")
            record_pointer = self._next_temp("record")
            record_type_name = f"%record.{expression.type_name}"
            lines.append(f"  {size_ptr} = getelementptr inbounds {record_type_name}, ptr null, i32 1")
            lines.append(f"  {size} = ptrtoint ptr {size_ptr} to i64")
            lines.append(f"  {total_size} = add i64 {size}, {self.RC_HEADER_SIZE}")
            lines.append(f"  {allocation} = call ptr @tb_heap_alloc(i64 {total_size})")
            lines.append(f"  {refcount_ptr} = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr {allocation}, i32 0, i32 0")
            lines.append(f"  {kind_ptr} = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr {allocation}, i32 0, i32 1")
            lines.append(f"  {flags_ptr} = getelementptr inbounds {self.RC_HEADER_TYPE_NAME}, ptr {allocation}, i32 0, i32 2")
            lines.append(f"  store i64 1, ptr {refcount_ptr}")
            lines.append(f"  store i32 {self.RC_KIND_RECORD}, ptr {kind_ptr}")
            lines.append(f"  {record_flags} = or i32 {self.RC_FLAGS_MAGIC}, {self.record_type_ids[expression.type_name]}")
            lines.append(f"  store i32 {record_flags}, ptr {flags_ptr}")
            lines.append(f"  {record_pointer} = getelementptr inbounds i8, ptr {allocation}, i64 {self.RC_HEADER_SIZE}")
            for field_name, field_type, field_value in expression.fields:
                field_pointer = self._next_temp("field")
                field_index = self.record_field_indices[expression.type_name][field_name]
                lines.append(
                    f"  {field_pointer} = getelementptr inbounds {record_type_name}, ptr {record_pointer}, i32 0, i32 {field_index}"
                )
                value = self._emit_owned_storage_value(field_type, field_value, lines, string_lengths)
                lines.append(f"  store {self._llvm_type_for(field_type)} {value}, ptr {field_pointer}")
            return record_pointer
        if isinstance(expression, IRCallExpression) and expression.return_type in self.record_types:
            return self._emit_call_expression(expression, lines, string_lengths)
        if isinstance(expression, IRMapIndex) and expression.value_type in self.record_types:
            return self._emit_map_index_value(expression, expression.value_type, lines, string_lengths)
        if isinstance(expression, IRArrayPop) and expression.item_type in self.record_types:
            return self._emit_array_remove_value(expression, lines, string_lengths, pop_last=True)
        if isinstance(expression, IRArrayRemove) and expression.item_type in self.record_types:
            return self._emit_array_remove_value(expression, lines, string_lengths)
        if isinstance(expression, IRArrayIndex) and expression.item_type in self.record_types:
            element_pointer = self._emit_array_element_pointer(expression.target, expression.index, expression.item_type, lines, string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {element_pointer}")
            return temp_name
        if isinstance(expression, IRRecordField) and expression.field_type in self.record_types:
            field_pointer = self._emit_record_field_pointer(expression, lines, string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {field_pointer}")
            return temp_name
        raise TypeError(f"Unsupported record IR expression: {type(expression).__name__}")

    def _emit_value_expression(self, type_name: str, expression, lines: list[str], string_lengths: dict[str, int]) -> str:
        if type_name == "int":
            return self._emit_integer_expression(expression, lines)
        if type_name == "bool":
            return self._emit_boolean_expression(expression, lines)
        if type_name == "string":
            return self._emit_string_expression(expression, lines, string_lengths)
        if self._is_map_type(type_name):
            return self._emit_map_expression(expression, lines, string_lengths, type_name)
        if self._is_set_type(type_name):
            return self._emit_array_expression(expression, lines, string_lengths, type_name)
        if self._is_priority_queue_type(type_name):
            return self._emit_priority_queue_expression(expression, lines, string_lengths, type_name)
        if self._is_array_type(type_name):
            return self._emit_array_expression(expression, lines, string_lengths, type_name)
        if type_name in self.record_types:
            return self._emit_record_expression(expression, lines, string_lengths, type_name)
        raise TypeError(f"Unsupported runtime value type: {type_name}")

    def _emit_value_pointer(
        self,
        type_name: str,
        expression,
        lines: list[str],
        string_lengths: dict[str, int],
        own_for_storage: bool = False,
    ) -> str:
        pointer = self._next_temp("value")
        self.alloca_lines.append(f"  {pointer} = alloca {self._llvm_type_for(type_name)}")
        value = (
            self._emit_owned_storage_value(type_name, expression, lines, string_lengths)
            if own_for_storage
            else self._emit_value_expression(type_name, expression, lines, string_lengths)
        )
        lines.append(f"  store {self._llvm_type_for(type_name)} {value}, ptr {pointer}")
        return pointer

    def _emit_array_element_pointer(self, target, index, item_type: str, lines: list[str], string_lengths: dict[str, int]) -> str:
        array_pointer = self._emit_array_expression(target, lines, string_lengths)
        index_value = self._emit_integer_expression(index, lines)
        len_pointer = self._next_temp("len")
        length = self._next_temp("len")
        is_negative = self._next_temp("neg")
        normalized = self._next_temp("idx")
        actual_index = self._next_temp("idx")
        element_pointer = self._next_temp("elem")
        lines.append(f"  {len_pointer} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {array_pointer}, i32 0, i32 0")
        lines.append(f"  {length} = load i64, ptr {len_pointer}")
        lines.append(f"  {is_negative} = icmp slt i64 {index_value}, 0")
        lines.append(f"  {normalized} = add i64 {length}, {index_value}")
        lines.append(f"  {actual_index} = select i1 {is_negative}, i64 {normalized}, i64 {index_value}")
        lines.append(
            f"  {element_pointer} = call ptr @tb_array_element_ptr(ptr {array_pointer}, i64 {actual_index}, i64 {self._element_size(item_type)})"
        )
        return element_pointer

    def _emit_record_field_pointer(self, expression: IRRecordField, lines: list[str], string_lengths: dict[str, int]) -> str:
        record_pointer = self._emit_record_expression(expression.target, lines, string_lengths, expression.type_name)
        field_pointer = self._next_temp("field")
        field_index = self.record_field_indices[expression.type_name][expression.field_name]
        lines.append(
            f"  {field_pointer} = getelementptr inbounds %record.{expression.type_name}, ptr {record_pointer}, i32 0, i32 {field_index}"
        )
        return field_pointer

    def _emit_map_index_value(self, expression: IRMapIndex, value_type: str, lines: list[str], string_lengths: dict[str, int]) -> str:
        map_pointer = self._emit_map_expression(expression.target, lines, string_lengths)
        key_value = self._emit_value_expression(expression.key_type, expression.key, lines, string_lengths)
        temp_name = self._next_temp("mapget")
        lines.append(
            f"  {temp_name} = call {self._llvm_type_for(value_type)} {self._generic_map_get_symbol(expression.key_type, value_type)}"
            f"(ptr {map_pointer}, {self._llvm_type_for(expression.key_type)} {key_value})"
        )
        return temp_name

    def _emit_integer_expression(self, expression, lines: list[str]) -> str:
        if isinstance(expression, IRInteger):
            return str(expression.value)
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            if slot_name is None or self.variable_types.get(expression.name) != "int":
                slot_name = self.global_variable_symbols.get(expression.name)
                if slot_name is None or self.global_variable_types.get(expression.name) != "int":
                    raise TypeError(f"Unknown int variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load i64, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRArrayLength):
            array_pointer = self._emit_array_expression(expression.target, lines, self.string_lengths)
            len_pointer = self._next_temp("len")
            length = self._next_temp("len")
            lines.append(f"  {len_pointer} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {array_pointer}, i32 0, i32 0")
            lines.append(f"  {length} = load i64, ptr {len_pointer}")
            return length
        if isinstance(expression, IRArrayIndex) and expression.item_type == "int":
            element_pointer = self._emit_array_element_pointer(expression.target, expression.index, "int", lines, self.string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load i64, ptr {element_pointer}")
            return temp_name
        if isinstance(expression, IRArrayPop) and expression.item_type == "int":
            return self._emit_array_remove_value(expression, lines, self.string_lengths, pop_last=True)
        if isinstance(expression, IRArrayRemove) and expression.item_type == "int":
            return self._emit_array_remove_value(expression, lines, self.string_lengths)
        if isinstance(expression, IRMapIndex) and expression.value_type == "int":
            return self._emit_map_index_value(expression, "int", lines, self.string_lengths)
        if isinstance(expression, IRRecordField) and expression.field_type == "int":
            field_pointer = self._emit_record_field_pointer(expression, lines, self.string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load i64, ptr {field_pointer}")
            return temp_name
        if isinstance(expression, IRBinaryOperation):
            left = self._emit_integer_expression(expression.left, lines)
            right = self._emit_integer_expression(expression.right, lines)
            temp_name = self._next_temp("tmp")
            if expression.operator == "<<":
                lines.append(f"  {temp_name} = call i64 @tb_shift_left(i64 {left}, i64 {right})")
                return temp_name
            if expression.operator == ">>":
                lines.append(f"  {temp_name} = call i64 @tb_shift_right(i64 {left}, i64 {right})")
                return temp_name
            operation = {
                "+": "add",
                "-": "sub",
                "*": "mul",
                "/": "sdiv",
                "%": "srem",
                "&": "and",
                "|": "or",
                "^": "xor",
            }.get(expression.operator)
            if operation is None:
                raise TypeError(f"Unsupported integer operator: {expression.operator}")
            lines.append(f"  {temp_name} = {operation} i64 {left}, {right}")
            return temp_name
        if isinstance(expression, IRCallExpression) and expression.return_type == "int":
            return self._emit_call_expression(expression, lines)
        if isinstance(expression, IRSelect) and expression.result_type == "int":
            condition_value = self._emit_condition(expression.condition, lines)
            when_true = self._emit_integer_expression(expression.when_true, lines)
            when_false = self._emit_integer_expression(expression.when_false, lines)
            temp_name = self._next_temp("select")
            lines.append(f"  {temp_name} = select i1 {condition_value}, i64 {when_true}, i64 {when_false}")
            return temp_name
        raise TypeError(f"Unsupported int IR expression: {type(expression).__name__}")

    def _emit_boolean_expression(self, expression, lines: list[str]) -> str:
        if isinstance(expression, IRBoolean):
            return "1" if expression.value else "0"
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            if slot_name is None or self.variable_types.get(expression.name) != "bool":
                slot_name = self.global_variable_symbols.get(expression.name)
                if slot_name is None or self.global_variable_types.get(expression.name) != "bool":
                    raise TypeError(f"Unknown bool variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load i1, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRArrayIndex) and expression.item_type == "bool":
            element_pointer = self._emit_array_element_pointer(expression.target, expression.index, "bool", lines, self.string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load i1, ptr {element_pointer}")
            return temp_name
        if isinstance(expression, IRMapIndex) and expression.value_type == "bool":
            return self._emit_map_index_value(expression, "bool", lines, self.string_lengths)
        if isinstance(expression, IRArrayPop) and expression.item_type == "bool":
            return self._emit_array_remove_value(expression, lines, self.string_lengths, pop_last=True)
        if isinstance(expression, IRArrayRemove) and expression.item_type == "bool":
            return self._emit_array_remove_value(expression, lines, self.string_lengths)
        if isinstance(expression, IRRecordField) and expression.field_type == "bool":
            field_pointer = self._emit_record_field_pointer(expression, lines, self.string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load i1, ptr {field_pointer}")
            return temp_name
        if isinstance(expression, IRCallExpression) and expression.return_type == "bool":
            return self._emit_call_expression(expression, lines)
        if isinstance(expression, IRSelect) and expression.result_type == "bool":
            condition_value = self._emit_condition(expression.condition, lines)
            when_true = self._emit_boolean_expression(expression.when_true, lines)
            when_false = self._emit_boolean_expression(expression.when_false, lines)
            temp_name = self._next_temp("select")
            lines.append(f"  {temp_name} = select i1 {condition_value}, i1 {when_true}, i1 {when_false}")
            return temp_name
        raise TypeError(f"Unsupported bool IR expression: {type(expression).__name__}")

    def _emit_string_expression(self, expression, lines: list[str], string_lengths: dict[str, int]) -> str:
        if isinstance(expression, str):
            return self._string_literal_pointer(expression, lines, string_lengths)
        if isinstance(expression, IRStringLiteral):
            return self._string_literal_pointer(expression.label, lines, string_lengths)
        if isinstance(expression, IRVariable):
            slot_name = self.variable_slots.get(expression.name)
            variable_type = self.variable_types.get(expression.name)
            if slot_name is None or (variable_type != "string" and variable_type not in getattr(self, "enum_types", {})):
                slot_name = self.global_variable_symbols.get(expression.name)
                variable_type = self.global_variable_types.get(expression.name)
                if slot_name is None or (variable_type != "string" and variable_type not in getattr(self, "enum_types", {})):
                    raise TypeError(f"Unknown string variable: {expression.name}")
                slot_name = f"@{slot_name}"
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {slot_name}")
            return temp_name
        if isinstance(expression, IRArrayIndex) and (expression.item_type == "string" or expression.item_type in getattr(self, "enum_types", {})):
            element_pointer = self._emit_array_element_pointer(expression.target, expression.index, expression.item_type, lines, string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {element_pointer}")
            return temp_name
        if isinstance(expression, IRMapIndex) and (expression.value_type == "string" or expression.value_type in getattr(self, "enum_types", {})):
            return self._emit_map_index_value(expression, expression.value_type, lines, string_lengths)
        if isinstance(expression, IRArrayPop) and (expression.item_type == "string" or expression.item_type in getattr(self, "enum_types", {})):
            return self._emit_array_remove_value(expression, lines, string_lengths, pop_last=True)
        if isinstance(expression, IRArrayRemove) and (expression.item_type == "string" or expression.item_type in getattr(self, "enum_types", {})):
            return self._emit_array_remove_value(expression, lines, string_lengths)
        if isinstance(expression, IRRecordField) and (expression.field_type == "string" or expression.field_type in getattr(self, "enum_types", {})):
            field_pointer = self._emit_record_field_pointer(expression, lines, string_lengths)
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load ptr, ptr {field_pointer}")
            return temp_name
        if isinstance(expression, IRStringConcat):
            left = self._emit_string_expression(expression.left, lines, string_lengths)
            right = self._emit_string_expression(expression.right, lines, string_lengths)
            left_length = self._next_temp("strlen")
            right_length = self._next_temp("strlen")
            total_length = self._next_temp("strlen")
            total_size = self._next_temp("size")
            buffer = self._next_temp("buf")
            right_destination = self._next_temp("dst")
            terminator = self._next_temp("term")
            lines.append(f"  {left_length} = call i64 @strlen(ptr {left})")
            lines.append(f"  {right_length} = call i64 @strlen(ptr {right})")
            lines.append(f"  {total_length} = add i64 {left_length}, {right_length}")
            lines.append(f"  {total_size} = add i64 {total_length}, 1")
            lines.append(f"  {buffer} = call ptr @tb_string_new(i64 {total_length})")
            lines.append(f"  call ptr @memcpy(ptr {buffer}, ptr {left}, i64 {left_length})")
            lines.append(f"  {right_destination} = getelementptr inbounds i8, ptr {buffer}, i64 {left_length}")
            lines.append(f"  call ptr @memcpy(ptr {right_destination}, ptr {right}, i64 {right_length})")
            lines.append(f"  {terminator} = getelementptr inbounds i8, ptr {buffer}, i64 {total_length}")
            lines.append(f"  store i8 0, ptr {terminator}")
            return buffer
        if isinstance(expression, IRIntToString):
            value = self._emit_integer_expression(expression.value, lines)
            buffer = self._next_temp("buf")
            lines.append(f"  {buffer} = call ptr @tb_int_to_string(i64 {value})")
            return buffer
        if isinstance(expression, IRStringIndex):
            source = self._emit_string_expression(expression.target, lines, string_lengths)
            index = self._emit_integer_expression(expression.index, lines)
            buffer = self._next_temp("buf")
            lines.append(f"  {buffer} = call ptr @tb_char_at(ptr {source}, i64 {index})")
            return buffer
        if isinstance(expression, IRCallExpression) and expression.return_type == "string":
            return self._emit_call_expression(expression, lines, string_lengths)
        if isinstance(expression, IRSelect) and expression.result_type == "string":
            condition_value = self._emit_condition(expression.condition, lines)
            when_true = self._emit_string_expression(expression.when_true, lines, string_lengths)
            when_false = self._emit_string_expression(expression.when_false, lines, string_lengths)
            temp_name = self._next_temp("select")
            lines.append(f"  {temp_name} = select i1 {condition_value}, ptr {when_true}, ptr {when_false}")
            return temp_name
        raise TypeError(f"Unsupported string IR expression: {type(expression).__name__}")

    def _string_literal_pointer(self, label: str, lines: list[str], string_lengths: dict[str, int]) -> str:
        string_length = string_lengths[label]
        pointer_name = self._next_temp("ptr")
        lines.append(f"  {pointer_name} = getelementptr inbounds [{string_length} x i8], ptr @{label}, i32 0, i32 0")
        return pointer_name

    def _emit_call_expression(self, expression: IRCallExpression, lines: list[str], string_lengths: dict[str, int] | None = None) -> str:
        active_string_lengths = self.string_lengths if string_lengths is None else string_lengths
        if expression.builtin:
            return self._emit_builtin_call(expression, lines, active_string_lengths)
        if expression.name == "tb_set_union":
            item_type = expression.arguments[0].type_name[4:-1]
            left = self._emit_array_expression(expression.arguments[0].value, lines, active_string_lengths, expression.arguments[0].type_name)
            right = self._emit_array_expression(expression.arguments[1].value, lines, active_string_lengths, expression.arguments[1].type_name)
            temp_name = self._next_temp("setunion")
            lines.append(f"  {temp_name} = call ptr {self._generic_set_union_symbol(item_type)}(ptr {left}, ptr {right})")
            return temp_name
        if expression.name == "tb_pq_pop":
            result_pointer = self._next_temp("pq.pop")
            llvm_type = self._llvm_type_for(expression.return_type)
            lines.append(f"  {result_pointer} = alloca {llvm_type}")
            queue_pointer = self._emit_priority_queue_expression(
                expression.arguments[0].value,
                lines,
                active_string_lengths,
                expression.arguments[0].type_name,
            )
            lines.append(f"  call void @tb_pq_pop(ptr {queue_pointer}, ptr {result_pointer})")
            temp_name = self._next_temp("load")
            lines.append(f"  {temp_name} = load {llvm_type}, ptr {result_pointer}")
            return temp_name
        arguments = ", ".join(self._emit_call_argument(argument, lines, active_string_lengths) for argument in expression.arguments)
        temp_name = self._next_temp("call")
        lines.append(f"  {temp_name} = call {self._llvm_type_for(expression.return_type)} {self._function_symbol(expression.name)}({arguments})")
        self._emit_exception_dispatch_if_pending(lines)
        return temp_name

    def _emit_array_remove_value(self, expression, lines: list[str], string_lengths: dict[str, int], pop_last: bool = False) -> str:
        llvm_type = self._llvm_type_for(expression.item_type)
        result_pointer = self._next_temp("value")
        lines.append(f"  {result_pointer} = alloca {llvm_type}")
        array_pointer = self._emit_array_expression(IRVariable(expression.target_name), lines, string_lengths)
        if pop_last:
            lines.append(
                f"  call void @tb_array_pop(ptr {array_pointer}, ptr {result_pointer}, i64 {self._element_size(expression.item_type)})"
            )
        else:
            index = self._emit_integer_expression(expression.index, lines)
            lines.append(
                f"  call void @tb_array_remove(ptr {array_pointer}, i64 {index}, ptr {result_pointer}, i64 {self._element_size(expression.item_type)})"
            )
        temp_name = self._next_temp("load")
        lines.append(f"  {temp_name} = load {llvm_type}, ptr {result_pointer}")
        return temp_name

    def _emit_builtin_call(self, expression: IRCallExpression, lines: list[str], string_lengths: dict[str, int]) -> str:
        if expression.name == "to_int":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("toint")
            lines.append(f"  {temp_name} = call i64 @strtoll(ptr {source}, ptr null, i32 10)")
            return temp_name
        if expression.name == "to_set":
            source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "int[]")
            temp_name = self._next_temp("toset")
            lines.append(f"  {temp_name} = call ptr @tb_to_set_int_array(ptr {source})")
            return temp_name
        if expression.name == "read_file":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("readfile")
            lines.append(f"  {temp_name} = call ptr @tb_read_file(ptr {source})")
            return temp_name
        if expression.name == "read_lines":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("readlines")
            lines.append(f"  {temp_name} = call ptr @tb_read_lines(ptr {source})")
            return temp_name
        if expression.name == "time_ms":
            temp_name = self._next_temp("timems")
            lines.append(f"  {temp_name} = call i64 @tb_time_ms()")
            return temp_name
        if expression.name == "range":
            if len(expression.arguments) == 1:
                start = "0"
                end = self._emit_integer_expression(expression.arguments[0].value, lines)
            else:
                start = self._emit_integer_expression(expression.arguments[0].value, lines)
                end = self._emit_integer_expression(expression.arguments[1].value, lines)
            temp_name = self._next_temp("range")
            lines.append(f"  {temp_name} = call ptr @tb_range(i64 {start}, i64 {end})")
            return temp_name
        if expression.name == "hash":
            argument_type = expression.arguments[0].type_name
            temp_name = self._next_temp("hash")
            if argument_type == "string":
                source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
                lines.append(f"  {temp_name} = call i64 @tb_hash_string(ptr {source})")
                return temp_name
            if argument_type == "int":
                value = self._emit_integer_expression(expression.arguments[0].value, lines)
                lines.append(f"  {temp_name} = call i64 @tb_hash_int(i64 {value})")
                return temp_name
            raise TypeError(f"Unsupported runtime hash argument type: {argument_type}")
        if expression.name == "abs":
            value = self._emit_integer_expression(expression.arguments[0].value, lines)
            is_negative = self._next_temp("absneg")
            negated = self._next_temp("absval")
            temp_name = self._next_temp("abs")
            lines.append(f"  {is_negative} = icmp slt i64 {value}, 0")
            lines.append(f"  {negated} = sub i64 0, {value}")
            lines.append(f"  {temp_name} = select i1 {is_negative}, i64 {negated}, i64 {value}")
            return temp_name
        if expression.name == "popcount":
            value = self._emit_integer_expression(expression.arguments[0].value, lines)
            temp_name = self._next_temp("popcount")
            lines.append(f"  {temp_name} = call i64 @llvm.ctpop.i64(i64 {value})")
            return temp_name
        if expression.name in {"min", "max"}:
            left = self._emit_integer_expression(expression.arguments[0].value, lines)
            right = self._emit_integer_expression(expression.arguments[1].value, lines)
            compare_name = self._next_temp("cmp")
            temp_name = self._next_temp(expression.name)
            predicate = "sle" if expression.name == "min" else "sge"
            lines.append(f"  {compare_name} = icmp {predicate} i64 {left}, {right}")
            lines.append(f"  {temp_name} = select i1 {compare_name}, i64 {left}, i64 {right}")
            return temp_name
        if expression.name == "index_of":
            haystack = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            needle = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            found = self._next_temp("found")
            is_null = self._next_temp("null")
            haystack_int = self._next_temp("ptr")
            found_int = self._next_temp("ptr")
            distance = self._next_temp("idx")
            result = self._next_temp("idx")
            lines.append(f"  {found} = call ptr @strstr(ptr {haystack}, ptr {needle})")
            lines.append(f"  {is_null} = icmp eq ptr {found}, null")
            lines.append(f"  {haystack_int} = ptrtoint ptr {haystack} to i64")
            lines.append(f"  {found_int} = ptrtoint ptr {found} to i64")
            lines.append(f"  {distance} = sub i64 {found_int}, {haystack_int}")
            lines.append(f"  {result} = select i1 {is_null}, i64 -1, i64 {distance}")
            return result
        if expression.name == "trim":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("trim")
            lines.append(f"  {temp_name} = call ptr @tb_trim(ptr {source})")
            return temp_name
        if expression.name == "trim_left":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("trimleft")
            lines.append(f"  {temp_name} = call ptr @tb_trim_left(ptr {source})")
            return temp_name
        if expression.name == "trim_right":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("trimright")
            lines.append(f"  {temp_name} = call ptr @tb_trim_right(ptr {source})")
            return temp_name
        if expression.name == "contains":
            container_type = expression.arguments[0].type_name
            temp_name = self._next_temp("contains")
            if container_type == "set<int>":
                source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "set<int>")
                value = self._emit_integer_expression(expression.arguments[1].value, lines)
                lines.append(f"  {temp_name} = call i1 @tb_set_contains_int(ptr {source}, i64 {value})")
                return temp_name
            if self._is_set_type(container_type):
                item_type = container_type[4:-1]
                source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, container_type)
                value = self._emit_value_expression(item_type, expression.arguments[1].value, lines, string_lengths)
                lines.append(
                    f"  {temp_name} = call i1 {self._generic_set_contains_symbol(item_type)}"
                    f"(ptr {source}, {self._llvm_type_for(item_type)} {value})"
                )
                return temp_name
            if container_type == "int[]":
                source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "int[]")
                value = self._emit_integer_expression(expression.arguments[1].value, lines)
                lines.append(f"  {temp_name} = call i1 @tb_array_contains_int(ptr {source}, i64 {value})")
                return temp_name
            if container_type == "bool[]":
                source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "bool[]")
                value = self._emit_boolean_expression(expression.arguments[1].value, lines)
                lines.append(f"  {temp_name} = call i1 @tb_array_contains_bool(ptr {source}, i1 {value})")
                return temp_name
            if container_type == "string[]":
                source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "string[]")
                value = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
                lines.append(f"  {temp_name} = call i1 @tb_array_contains_string(ptr {source}, ptr {value})")
                return temp_name
            if container_type == "map<string,int>":
                source = self._emit_map_expression(expression.arguments[0].value, lines, string_lengths, "map<string,int>")
                value = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
                lines.append(f"  {temp_name} = call i1 @tb_map_has_string_int(ptr {source}, ptr {value})")
                return temp_name
            if self._is_map_type(container_type):
                key_type, value_type = self._map_parts(container_type)
                source = self._emit_map_expression(expression.arguments[0].value, lines, string_lengths, container_type)
                value = self._emit_value_expression(key_type, expression.arguments[1].value, lines, string_lengths)
                lines.append(
                    f"  {temp_name} = call i1 {self._generic_map_has_symbol(key_type, value_type)}"
                    f"(ptr {source}, {self._llvm_type_for(key_type)} {value})"
                )
                return temp_name
            raise TypeError(f"Unsupported contains container type: {container_type}")
        if expression.name == "length":
            if expression.arguments[0].type_name == "string":
                source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
                temp_name = self._next_temp("strlen")
                lines.append(f"  {temp_name} = call i64 @strlen(ptr {source})")
                return temp_name
            if self._is_map_type(expression.arguments[0].type_name):
                map_pointer = self._emit_map_expression(expression.arguments[0].value, lines, string_lengths, expression.arguments[0].type_name)
                len_pointer = self._next_temp("len")
                temp_name = self._next_temp("len")
                lines.append(f"  {len_pointer} = getelementptr inbounds {self.MAP_TYPE_NAME}, ptr {map_pointer}, i32 0, i32 0")
                lines.append(f"  {temp_name} = load i64, ptr {len_pointer}")
                return temp_name
            array_pointer = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths)
            len_pointer = self._next_temp("len")
            temp_name = self._next_temp("len")
            lines.append(f"  {len_pointer} = getelementptr inbounds {self.ARRAY_TYPE_NAME}, ptr {array_pointer}, i32 0, i32 0")
            lines.append(f"  {temp_name} = load i64, ptr {len_pointer}")
            return temp_name
        if expression.name == "split":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            delimiter = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            temp_name = self._next_temp("split")
            lines.append(f"  {temp_name} = call ptr @tb_split(ptr {source}, ptr {delimiter})")
            return temp_name
        if expression.name == "split_lines":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("splitlines")
            lines.append(f"  {temp_name} = call ptr @tb_split_lines(ptr {source})")
            return temp_name
        if expression.name == "keys":
            source = self._emit_map_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("mapkeys")
            key_type, value_type = self._map_parts(expression.arguments[0].type_name)
            lines.append(f"  {temp_name} = call ptr {self._generic_map_keys_symbol(key_type, value_type)}(ptr {source})")
            return temp_name
        if expression.name == "values":
            source = self._emit_map_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("mapvalues")
            key_type, value_type = self._map_parts(expression.arguments[0].type_name)
            lines.append(f"  {temp_name} = call ptr {self._generic_map_values_symbol(key_type, value_type)}(ptr {source})")
            return temp_name
        if expression.name == "join":
            array = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "string[]")
            delimiter = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            temp_name = self._next_temp("join")
            lines.append(f"  {temp_name} = call ptr @tb_join_strings(ptr {array}, ptr {delimiter})")
            return temp_name
        if expression.name == "sum":
            array_type = expression.arguments[0].type_name
            array = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, array_type)
            temp_name = self._next_temp("sum")
            if array_type == "int[]":
                lines.append(f"  {temp_name} = call i64 @tb_sum_int_array(ptr {array})")
                return temp_name
            if array_type == "bool[]":
                lines.append(f"  {temp_name} = call i64 @tb_sum_bool_array(ptr {array})")
                return temp_name
            raise TypeError(f"Unsupported sum array type: {array_type}")
            return temp_name
        if expression.name == "substring":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            start = self._emit_integer_expression(expression.arguments[1].value, lines)
            if len(expression.arguments) == 3:
                end = self._emit_integer_expression(expression.arguments[2].value, lines)
                temp_name = self._next_temp("substring")
                lines.append(f"  {temp_name} = call ptr @tb_slice(ptr {source}, i64 {start}, i64 {end})")
                return temp_name
            start_pointer = self._next_temp("substr")
            substring_length = self._next_temp("strlen")
            allocation_size = self._next_temp("size")
            buffer = self._next_temp("buf")
            terminator = self._next_temp("term")
            lines.append(f"  {start_pointer} = getelementptr inbounds i8, ptr {source}, i64 {start}")
            lines.append(f"  {substring_length} = call i64 @strlen(ptr {start_pointer})")
            lines.append(f"  {allocation_size} = add i64 {substring_length}, 1")
            lines.append(f"  {buffer} = call ptr @tb_string_new(i64 {substring_length})")
            lines.append(f"  call ptr @memcpy(ptr {buffer}, ptr {start_pointer}, i64 {substring_length})")
            lines.append(f"  {terminator} = getelementptr inbounds i8, ptr {buffer}, i64 {substring_length}")
            lines.append(f"  store i8 0, ptr {terminator}")
            return buffer
        if expression.name == "slice":
            if self._is_array_type(expression.arguments[0].type_name):
                array_type = expression.arguments[0].type_name
                source = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, array_type)
                start = self._emit_integer_expression(expression.arguments[1].value, lines)
                end = self._emit_integer_expression(expression.arguments[2].value, lines)
                temp_name = self._next_temp("slice")
                item_type = self._array_item_type(array_type)
                if item_type == "string":
                    lines.append(f"  {temp_name} = call ptr @tb_string_array_slice(ptr {source}, i64 {start}, i64 {end})")
                else:
                    lines.append(
                        f"  {temp_name} = call ptr @tb_array_slice(ptr {source}, i64 {start}, i64 {end}, i64 {self._element_size(item_type)}, i32 {self._array_release_mode(item_type)})"
                    )
                return temp_name
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            start = self._emit_integer_expression(expression.arguments[1].value, lines)
            end = self._emit_integer_expression(expression.arguments[2].value, lines)
            temp_name = self._next_temp("slice")
            lines.append(f"  {temp_name} = call ptr @tb_slice(ptr {source}, i64 {start}, i64 {end})")
            return temp_name
        if expression.name == "char_at":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            index = self._emit_integer_expression(expression.arguments[1].value, lines)
            temp_name = self._next_temp("charat")
            lines.append(f"  {temp_name} = call ptr @tb_char_at(ptr {source}, i64 {index})")
            return temp_name
        if expression.name == "replace":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            old = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            new = self._emit_string_expression(expression.arguments[2].value, lines, string_lengths)
            temp_name = self._next_temp("replace")
            lines.append(f"  {temp_name} = call ptr @tb_replace(ptr {source}, ptr {old}, ptr {new})")
            return temp_name
        if expression.name == "starts_with":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            prefix = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            temp_name = self._next_temp("startswith")
            lines.append(f"  {temp_name} = call i1 @tb_starts_with(ptr {source}, ptr {prefix})")
            return temp_name
        if expression.name == "starts_with_at":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            prefix = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            offset = self._emit_integer_expression(expression.arguments[2].value, lines)
            temp_name = self._next_temp("startswithat")
            lines.append(f"  {temp_name} = call i1 @tb_starts_with_at(ptr {source}, ptr {prefix}, i64 {offset})")
            return temp_name
        if expression.name == "ends_with":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            suffix = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            temp_name = self._next_temp("endswith")
            lines.append(f"  {temp_name} = call i1 @tb_ends_with(ptr {source}, ptr {suffix})")
            return temp_name
        if expression.name == "has_flag":
            args = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "string[]")
            flag = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            temp_name = self._next_temp("hasflag")
            lines.append(f"  {temp_name} = call i1 @tb_has_flag(ptr {args}, ptr {flag})")
            return temp_name
        if expression.name == "option_value":
            args = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "string[]")
            option = self._emit_string_expression(expression.arguments[1].value, lines, string_lengths)
            temp_name = self._next_temp("optionvalue")
            lines.append(f"  {temp_name} = call ptr @tb_option_value(ptr {args}, ptr {option})")
            return temp_name
        if expression.name == "is_digit":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("isdigit")
            lines.append(f"  {temp_name} = call i1 @tb_is_digit(ptr {source})")
            return temp_name
        if expression.name == "is_alpha":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("isalpha")
            lines.append(f"  {temp_name} = call i1 @tb_is_alpha(ptr {source})")
            return temp_name
        if expression.name == "is_alnum":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("isalnum")
            lines.append(f"  {temp_name} = call i1 @tb_is_alnum(ptr {source})")
            return temp_name
        if expression.name == "is_whitespace":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("iswhitespace")
            lines.append(f"  {temp_name} = call i1 @tb_is_whitespace(ptr {source})")
            return temp_name
        if expression.name == "is_space":
            source = self._emit_string_expression(expression.arguments[0].value, lines, string_lengths)
            temp_name = self._next_temp("isspace")
            lines.append(f"  {temp_name} = call i1 @tb_is_whitespace(ptr {source})")
            return temp_name
        if expression.name == "strcmp":
            left_expression = expression.arguments[0].value
            right_expression = expression.arguments[1].value
            indexed_expression = left_expression if isinstance(left_expression, IRStringIndex) else right_expression if isinstance(right_expression, IRStringIndex) else None
            literal_pointer = None
            if isinstance(left_expression, IRStringIndex):
                literal_pointer = self._single_char_literal_pointer(right_expression, lines, string_lengths)
            elif isinstance(right_expression, IRStringIndex):
                literal_pointer = self._single_char_literal_pointer(left_expression, lines, string_lengths)
            if indexed_expression is not None and literal_pointer is not None:
                source = self._emit_string_expression(indexed_expression.target, lines, string_lengths)
                index = self._emit_integer_expression(indexed_expression.index, lines)
                source_length = self._next_temp("strlen")
                is_negative = self._next_temp("neg")
                normalized = self._next_temp("idx")
                actual_index = self._next_temp("idx")
                before_start = self._next_temp("oob")
                after_end = self._next_temp("oob")
                out_of_bounds = self._next_temp("oob")
                in_bounds_label = self._next_label("strcmp_char_in_bounds")
                out_of_bounds_label = self._next_label("strcmp_char_oob")
                done_label = self._next_label("strcmp_char_done")
                compare_i64 = self._next_temp("strcmp")
                lines.append(f"  {source_length} = call i64 @strlen(ptr {source})")
                lines.append(f"  {is_negative} = icmp slt i64 {index}, 0")
                lines.append(f"  {normalized} = add i64 {source_length}, {index}")
                lines.append(f"  {actual_index} = select i1 {is_negative}, i64 {normalized}, i64 {index}")
                lines.append(f"  {before_start} = icmp slt i64 {actual_index}, 0")
                lines.append(f"  {after_end} = icmp sge i64 {actual_index}, {source_length}")
                lines.append(f"  {out_of_bounds} = or i1 {before_start}, {after_end}")
                lines.append(f"  br i1 {out_of_bounds}, label %{out_of_bounds_label}, label %{in_bounds_label}")
                lines.append(f"{out_of_bounds_label}:")
                lines.append(f"  br label %{done_label}")
                lines.append(f"{in_bounds_label}:")
                source_char_ptr = self._next_temp("char")
                source_char = self._next_temp("char")
                literal_char = self._next_temp("char")
                source_value = self._next_temp("char")
                literal_value = self._next_temp("char")
                compare_diff = self._next_temp("strcmp")
                lines.append(f"  {source_char_ptr} = getelementptr inbounds i8, ptr {source}, i64 {actual_index}")
                lines.append(f"  {source_char} = load i8, ptr {source_char_ptr}")
                lines.append(f"  {literal_char} = load i8, ptr {literal_pointer}")
                lines.append(f"  {source_value} = zext i8 {source_char} to i64")
                lines.append(f"  {literal_value} = zext i8 {literal_char} to i64")
                lines.append(f"  {compare_diff} = sub i64 {source_value}, {literal_value}")
                lines.append(f"  br label %{done_label}")
                lines.append(f"{done_label}:")
                lines.append(f"  {compare_i64} = phi i64 [ -1, %{out_of_bounds_label} ], [ {compare_diff}, %{in_bounds_label} ]")
                return compare_i64
            release_left = self._string_expression_needs_release(left_expression)
            release_right = self._string_expression_needs_release(right_expression)
            left = self._emit_string_expression(left_expression, lines, string_lengths)
            right = self._emit_string_expression(right_expression, lines, string_lengths)
            compare_i32 = self._next_temp("strcmp")
            compare_i64 = self._next_temp("strcmp")
            lines.append(f"  {compare_i32} = call i32 @strcmp(ptr {left}, ptr {right})")
            if release_left:
                lines.append(f"  call void @tb_release(ptr {left})")
            if release_right:
                lines.append(f"  call void @tb_release(ptr {right})")
            lines.append(f"  {compare_i64} = sext i32 {compare_i32} to i64")
            return compare_i64
        if expression.name == "array_to_string_int":
            array = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "int[]")
            temp_name = self._next_temp("arraystr")
            lines.append(f"  {temp_name} = call ptr @tb_int_array_to_string(ptr {array})")
            return temp_name
        if expression.name == "array_to_string_string":
            array = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "string[]")
            temp_name = self._next_temp("arraystr")
            lines.append(f"  {temp_name} = call ptr @tb_string_array_to_string(ptr {array})")
            return temp_name
        if expression.name == "array_to_string_bool":
            array = self._emit_array_expression(expression.arguments[0].value, lines, string_lengths, "bool[]")
            temp_name = self._next_temp("arraystr")
            lines.append(f"  {temp_name} = call ptr @tb_bool_array_to_string(ptr {array})")
            return temp_name
        raise TypeError(f"Unsupported builtin runtime call: {expression.name}")

    def _emit_call_argument(self, argument: IRCallArgument, lines: list[str], string_lengths: dict[str, int]) -> str:
        if argument.type_name == "int":
            return f"i64 {self._emit_integer_expression(argument.value, lines)}"
        if argument.type_name == "bool":
            return f"i1 {self._emit_boolean_expression(argument.value, lines)}"
        if argument.type_name == "string":
            return f"ptr {self._emit_string_expression(argument.value, lines, string_lengths)}"
        if self._is_map_type(argument.type_name):
            return f"ptr {self._emit_map_expression(argument.value, lines, string_lengths, argument.type_name)}"
        if self._is_priority_queue_type(argument.type_name):
            return f"ptr {self._emit_priority_queue_expression(argument.value, lines, string_lengths, argument.type_name)}"
        if self._is_set_type(argument.type_name):
            return f"ptr {self._emit_array_expression(argument.value, lines, string_lengths, argument.type_name)}"
        if self._is_array_type(argument.type_name):
            return f"ptr {self._emit_array_expression(argument.value, lines, string_lengths, argument.type_name)}"
        if argument.type_name in self.record_types:
            return f"ptr {self._emit_record_expression(argument.value, lines, string_lengths, argument.type_name)}"
        raise TypeError(f"Unsupported call argument type: {argument.type_name}")

    def _emit_clone_string(self, value: str, lines: list[str]) -> str:
        cloned = self._next_temp("str.clone")
        lines.append(f"  {cloned} = call ptr @tb_string_clone(ptr {value})")
        return cloned

    def _current_exception_target_label(self) -> str | None:
        if self.exception_handler_labels:
            return self.exception_handler_labels[-1]
        return self.function_exception_label

    def _emit_exception_dispatch_if_pending(self, lines: list[str]) -> None:
        target_label = self._current_exception_target_label()
        if target_label is None:
            return
        self.exception_dispatch_used = True
        pending = self._next_temp("exc.pending")
        continue_label = self._next_label("exc.cont")
        lines.append(f"  {pending} = load i1, ptr @__tb_exception_pending")
        lines.append(f"  br i1 {pending}, label %{target_label}, label %{continue_label}")
        lines.append(f"{continue_label}:")

    def _single_char_literal_pointer(
        self,
        expression,
        lines: list[str],
        string_lengths: dict[str, int],
    ) -> str | None:
        if isinstance(expression, str):
            label = expression
        elif isinstance(expression, IRStringLiteral):
            label = expression.label
        else:
            return None
        if string_lengths.get(label) != 2:
            return None
        return self._string_literal_pointer(label, lines, string_lengths)

    def _string_expression_needs_release(self, expression) -> bool:
        if isinstance(expression, (IRStringConcat, IRIntToString, IRStringIndex)):
            return True
        if isinstance(expression, IRCallExpression) and expression.return_type == "string":
            return True
        if isinstance(expression, IRArrayPop) and expression.item_type == "string":
            return True
        if isinstance(expression, IRArrayRemove) and expression.item_type == "string":
            return True
        return False

    def _emit_release_owned_string_locals(self, lines: list[str], skip_slot: str | None = None) -> None:
        for slot_name in self.owned_string_slots:
            if slot_name == skip_slot:
                continue
            current = self._next_temp("str.release")
            lines.append(f"  {current} = load ptr, ptr {slot_name}")
            lines.append(f"  call void @tb_release(ptr {current})")

    def _emit_retain_heap_value(self, value: str, lines: list[str], prefix: str) -> str:
        retained = self._next_temp(prefix)
        lines.append(f"  {retained} = call ptr @tb_retain(ptr {value})")
        return retained

    def _emit_release_owned_array_locals(self, lines: list[str], skip_slot: str | None = None) -> None:
        for slot_name in self.owned_array_slots:
            if slot_name == skip_slot:
                continue
            current = self._next_temp("array.release")
            lines.append(f"  {current} = load ptr, ptr {slot_name}")
            lines.append(f"  call void @tb_release(ptr {current})")

    def _emit_release_owned_record_locals(self, lines: list[str], skip_slot: str | None = None) -> None:
        for slot_name in self.owned_record_slots:
            if slot_name == skip_slot:
                continue
            current = self._next_temp("record.release")
            lines.append(f"  {current} = load ptr, ptr {slot_name}")
            lines.append(f"  call void @tb_release(ptr {current})")

    def _emit_release_owned_map_locals(self, lines: list[str], skip_slot: str | None = None) -> None:
        for slot_name in self.owned_map_slots:
            if slot_name == skip_slot:
                continue
            current = self._next_temp("map.release")
            lines.append(f"  {current} = load ptr, ptr {slot_name}")
            lines.append(f"  call void @tb_release(ptr {current})")

    def _emit_release_owned_priority_queue_locals(self, lines: list[str], skip_slot: str | None = None) -> None:
        for slot_name in self.owned_priority_queue_slots:
            if slot_name == skip_slot:
                continue
            current = self._next_temp("pq.release")
            lines.append(f"  {current} = load ptr, ptr {slot_name}")
            lines.append(f"  call void @tb_release(ptr {current})")

    @staticmethod
    def _array_expression_is_borrowed(expression) -> bool:
        return (
            isinstance(expression, IRVariable)
            or (isinstance(expression, IRMapIndex) and (LLVMEmitter._is_array_type(expression.value_type) or LLVMEmitter._is_set_type(expression.value_type)))
            or (isinstance(expression, IRArrayIndex) and (LLVMEmitter._is_array_type(expression.item_type) or LLVMEmitter._is_set_type(expression.item_type)))
            or (isinstance(expression, IRRecordField) and (LLVMEmitter._is_array_type(expression.field_type) or LLVMEmitter._is_set_type(expression.field_type)))
        )

    def _record_expression_is_borrowed(self, expression) -> bool:
        return (
            isinstance(expression, IRVariable)
            or (isinstance(expression, IRMapIndex) and expression.value_type in self.record_types)
            or (isinstance(expression, IRArrayIndex) and expression.item_type in self.record_types)
            or (isinstance(expression, IRRecordField) and expression.field_type in self.record_types)
        )

    @staticmethod
    def _map_expression_is_borrowed(expression) -> bool:
        return (
            isinstance(expression, IRVariable)
            or (isinstance(expression, IRMapIndex) and LLVMEmitter._is_map_type(expression.value_type))
            or (isinstance(expression, IRArrayIndex) and LLVMEmitter._is_map_type(expression.item_type))
            or (isinstance(expression, IRRecordField) and LLVMEmitter._is_map_type(expression.field_type))
        )

    @staticmethod
    def _priority_queue_expression_is_borrowed(expression) -> bool:
        return (
            isinstance(expression, IRVariable)
            or (isinstance(expression, IRMapIndex) and LLVMEmitter._is_priority_queue_type(expression.value_type))
            or (isinstance(expression, IRArrayIndex) and LLVMEmitter._is_priority_queue_type(expression.item_type))
            or (isinstance(expression, IRRecordField) and LLVMEmitter._is_priority_queue_type(expression.field_type))
        )

    def _value_expression_is_borrowed(self, type_name: str, expression) -> bool:
        if type_name == "string":
            return True
        if self._is_array_type(type_name) or self._is_set_type(type_name):
            return self._array_expression_is_borrowed(expression)
        if self._is_map_type(type_name):
            return self._map_expression_is_borrowed(expression)
        if self._is_priority_queue_type(type_name):
            return self._priority_queue_expression_is_borrowed(expression)
        if type_name in self.record_types:
            return self._record_expression_is_borrowed(expression)
        return False

    def _emit_owned_storage_value(self, type_name: str, expression, lines: list[str], string_lengths: dict[str, int]) -> str:
        value = self._emit_value_expression(type_name, expression, lines, string_lengths)
        if type_name == "string":
            return self._emit_clone_string(value, lines)
        if self._type_needs_managed_storage(type_name) and self._value_expression_is_borrowed(type_name, expression):
            return self._emit_retain_heap_value(value, lines, "store.own")
        return value

    def _emit_instruction(self, instruction, lines: list[str], string_lengths: dict[str, int]) -> bool:
        if isinstance(instruction, IRDeclareInt):
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = "int"
                self.alloca_lines.append(f"  {slot_name} = alloca i64")
            value = self._emit_integer_expression(instruction.value, lines)
            lines.append(f"  store i64 {value}, ptr {slot_name}")
            return False
        if isinstance(instruction, IRAssignInt):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None or self.variable_types.get(instruction.name) != "int":
                slot_name = self.global_variable_symbols.get(instruction.name)
                if slot_name is None or self.global_variable_types.get(instruction.name) != "int":
                    raise TypeError(f"Unknown int variable: {instruction.name}")
                slot_name = f"@{slot_name}"
            value = self._emit_integer_expression(instruction.value, lines)
            lines.append(f"  store i64 {value}, ptr {slot_name}")
            return False
        if isinstance(instruction, IRDeclareBool):
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = "bool"
                self.alloca_lines.append(f"  {slot_name} = alloca i1")
            value = self._emit_boolean_expression(instruction.value, lines)
            lines.append(f"  store i1 {value}, ptr {slot_name}")
            return False
        if isinstance(instruction, IRAssignBool):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = "bool"
                self.alloca_lines.append(f"  {slot_name} = alloca i1")
            elif self.variable_types.get(instruction.name) != "bool":
                raise TypeError(f"Unknown bool variable: {instruction.name}")
            value = self._emit_boolean_expression(instruction.value, lines)
            lines.append(f"  store i1 {value}, ptr {slot_name}")
            return False
        if isinstance(instruction, IRDeclareString):
            previous = None
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = "string"
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_string_slots.append(slot_name)
            elif not self.global_init_mode:
                previous = self._next_temp("str.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_string_expression(instruction.value, lines, string_lengths)
            if not self.global_init_mode:
                value = self._emit_clone_string(value, lines)
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRAssignString):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = "string"
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_string_slots.append(slot_name)
            elif self.variable_types.get(instruction.name) != "string":
                raise TypeError(f"Unknown string variable: {instruction.name}")
            if not self.global_init_mode:
                previous = self._next_temp("str.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_string_expression(instruction.value, lines, string_lengths)
            if not self.global_init_mode:
                value = self._emit_clone_string(value, lines)
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if not self.global_init_mode:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRDeclareMap):
            previous = None
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_map_slots.append(slot_name)
            elif not self.global_init_mode:
                previous = self._next_temp("map.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_map_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if not self.global_init_mode and self._map_expression_is_borrowed(instruction.value):
                value = self._emit_retain_heap_value(value, lines, "map.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRDeclarePriorityQueue):
            previous = None
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_priority_queue_slots.append(slot_name)
            elif not self.global_init_mode:
                previous = self._next_temp("pq.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_priority_queue_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if not self.global_init_mode and self._priority_queue_expression_is_borrowed(instruction.value):
                value = self._emit_retain_heap_value(value, lines, "pq.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRAssignMap):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_map_slots.append(slot_name)
            elif self.variable_types.get(instruction.name) != instruction.type_name:
                raise TypeError(f"Unknown map variable: {instruction.name}")
            previous = None
            if not self.global_init_mode:
                previous = self._next_temp("map.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_map_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if not self.global_init_mode and self._map_expression_is_borrowed(instruction.value):
                value = self._emit_retain_heap_value(value, lines, "map.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRAssignPriorityQueue):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_priority_queue_slots.append(slot_name)
            elif self.variable_types.get(instruction.name) != instruction.type_name:
                raise TypeError(f"Unknown priority queue variable: {instruction.name}")
            previous = None
            if not self.global_init_mode:
                previous = self._next_temp("pq.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_priority_queue_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if not self.global_init_mode and self._priority_queue_expression_is_borrowed(instruction.value):
                value = self._emit_retain_heap_value(value, lines, "pq.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRDeclareArray):
            previous = None
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                if self._is_array_type(instruction.type_name) or self._is_set_type(instruction.type_name):
                    self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                    self.owned_array_slots.append(slot_name)
            elif not self.global_init_mode and (self._is_array_type(instruction.type_name) or self._is_set_type(instruction.type_name)):
                previous = self._next_temp("array.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_array_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if (
                not self.global_init_mode
                and (self._is_array_type(instruction.type_name) or self._is_set_type(instruction.type_name))
                and self._array_expression_is_borrowed(instruction.value)
            ):
                value = self._emit_retain_heap_value(value, lines, "array.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRAssignArray):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                if self._is_array_type(instruction.type_name) or self._is_set_type(instruction.type_name):
                    self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                    self.owned_array_slots.append(slot_name)
            elif self.variable_types.get(instruction.name) != instruction.type_name:
                raise TypeError(f"Unknown array variable: {instruction.name}")
            previous = None
            if not self.global_init_mode and (self._is_array_type(instruction.type_name) or self._is_set_type(instruction.type_name)):
                previous = self._next_temp("array.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_array_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if (
                not self.global_init_mode
                and (self._is_array_type(instruction.type_name) or self._is_set_type(instruction.type_name))
                and self._array_expression_is_borrowed(instruction.value)
            ):
                value = self._emit_retain_heap_value(value, lines, "array.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRArraySet):
            value_pointer = self._emit_value_pointer(instruction.item_type, instruction.value, lines, string_lengths, own_for_storage=True)
            array_pointer = self._emit_array_expression(IRVariable(instruction.target_name), lines, string_lengths)
            index = self._emit_integer_expression(instruction.index, lines)
            lines.append(
                f"  call void @tb_array_set(ptr {array_pointer}, i64 {index}, ptr {value_pointer}, i64 {self._element_size(instruction.item_type)})"
            )
            return False
        if isinstance(instruction, IRMapSet):
            map_type = f"map<{instruction.key_type},{instruction.value_type}>"
            map_pointer = self._emit_map_expression(IRVariable(instruction.target_name), lines, string_lengths, map_type)
            key_value = self._emit_value_expression(instruction.key_type, instruction.key, lines, string_lengths)
            value_value = self._emit_owned_storage_value(instruction.value_type, instruction.value, lines, string_lengths)
            lines.append(
                f"  call void {self._generic_map_put_symbol(instruction.key_type, instruction.value_type)}"
                f"(ptr {map_pointer}, {self._llvm_type_for(instruction.key_type)} {key_value}, {self._llvm_type_for(instruction.value_type)} {value_value})"
            )
            return False
        if isinstance(instruction, IRArrayPush):
            value_pointer = self._emit_value_pointer(instruction.item_type, instruction.value, lines, string_lengths, own_for_storage=True)
            array_pointer = self._emit_array_expression(IRVariable(instruction.target_name), lines, string_lengths)
            lines.append(
                f"  call void @tb_array_push(ptr {array_pointer}, ptr {value_pointer}, i64 {self._element_size(instruction.item_type)})"
            )
            return False
        if isinstance(instruction, IRArrayInsert):
            value_pointer = self._emit_value_pointer(instruction.item_type, instruction.value, lines, string_lengths, own_for_storage=True)
            array_pointer = self._emit_array_expression(IRVariable(instruction.target_name), lines, string_lengths)
            index = self._emit_integer_expression(instruction.index, lines)
            lines.append(
                f"  call void @tb_array_insert(ptr {array_pointer}, i64 {index}, ptr {value_pointer}, i64 {self._element_size(instruction.item_type)})"
            )
            return False
        if isinstance(instruction, IRArrayClear):
            array_pointer = self._emit_array_expression(IRVariable(instruction.target_name), lines, string_lengths)
            lines.append(f"  call void @tb_array_clear(ptr {array_pointer})")
            return False
        if isinstance(instruction, IRArrayPop):
            discarded = self._emit_array_remove_value(instruction, lines, string_lengths, pop_last=True)
            if self._type_needs_managed_storage(instruction.item_type):
                lines.append(f"  call void @tb_release(ptr {discarded})")
            return False
        if isinstance(instruction, IRArrayRemove):
            discarded = self._emit_array_remove_value(instruction, lines, string_lengths)
            if self._type_needs_managed_storage(instruction.item_type):
                lines.append(f"  call void @tb_release(ptr {discarded})")
            return False
        if isinstance(instruction, IRArraySort):
            array_pointer = self._emit_array_expression(IRVariable(instruction.target_name), lines, string_lengths, f"{instruction.item_type}[]")
            comparator_symbol = self._sort_comparator_symbol(instruction.item_type, instruction.comparator_name)
            lines.append(
                f"  call void @tb_array_sort(ptr {array_pointer}, i64 {self._element_size(instruction.item_type)}, ptr {comparator_symbol})"
            )
            return False
        if isinstance(instruction, IRDeclareRecord):
            previous = None
            slot_name = self.variable_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_record_slots.append(slot_name)
            elif not self.global_init_mode:
                previous = self._next_temp("record.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_record_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if not self.global_init_mode and self._record_expression_is_borrowed(instruction.value):
                value = self._emit_retain_heap_value(value, lines, "record.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRAssignRecord):
            slot_name = self.variable_slots.get(instruction.name)
            if slot_name is None and instruction.name in self.global_variable_symbols:
                slot_name = f"@{self.global_variable_symbols[instruction.name]}"
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.variable_slots[instruction.name] = slot_name
                self.variable_types[instruction.name] = instruction.type_name
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
                self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
                self.owned_record_slots.append(slot_name)
            elif self.variable_types.get(instruction.name) != instruction.type_name:
                raise TypeError(f"Unknown record variable: {instruction.name}")
            previous = None
            if not self.global_init_mode:
                previous = self._next_temp("record.old")
                lines.append(f"  {previous} = load ptr, ptr {slot_name}")
            value = self._emit_record_expression(instruction.value, lines, string_lengths, instruction.type_name)
            if not self.global_init_mode and self._record_expression_is_borrowed(instruction.value):
                value = self._emit_retain_heap_value(value, lines, "record.retain")
            lines.append(f"  store ptr {value}, ptr {slot_name}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRSetRecordField):
            field_pointer = self._emit_record_field_pointer(
                IRRecordField(IRVariable(instruction.target_name), instruction.type_name, instruction.field_name, instruction.field_type),
                lines,
                string_lengths,
            )
            previous = None
            if self._record_field_needs_release(instruction.field_type):
                previous = self._next_temp("field.old")
                lines.append(f"  {previous} = load {self._llvm_type_for(instruction.field_type)}, ptr {field_pointer}")
            value = self._emit_owned_storage_value(instruction.field_type, instruction.value, lines, string_lengths)
            lines.append(f"  store {self._llvm_type_for(instruction.field_type)} {value}, ptr {field_pointer}")
            if previous is not None:
                lines.append(f"  call void @tb_release(ptr {previous})")
            return False
        if isinstance(instruction, IRPrintString):
            value = self._emit_string_expression(instruction.value, lines, string_lengths)
            lines.append(f"  call i32 @puts(ptr {value})")
            return False
        if isinstance(instruction, IRPrintInt):
            format_pointer = self._next_temp("fmt")
            lines.append(
                f"  {format_pointer} = getelementptr inbounds [{len(self.INT_FORMAT_BYTES)} x i8], "
                f"ptr @{self.INT_FORMAT_LABEL}, i32 0, i32 0"
            )
            value = self._emit_integer_expression(instruction.value, lines)
            lines.append(f"  call i32 (ptr, ...) @printf(ptr {format_pointer}, i64 {value})")
            return False
        if isinstance(instruction, IRDeclareFile):
            slot_name = self.file_slots.get(instruction.name)
            if self.global_init_mode and instruction.name in self.global_file_symbols:
                slot_name = f"@{self.global_file_symbols[instruction.name]}"
                self.open_file_slots.append(slot_name)
            elif slot_name is None:
                slot_name = f"%{instruction.name}"
                self.file_slots[instruction.name] = slot_name
                self.open_file_slots.append(slot_name)
                self.alloca_lines.append(f"  {slot_name} = alloca ptr")
            path_pointer = self._emit_string_expression(instruction.path, lines, string_lengths)
            mode_pointer = self._next_temp("mode")
            file_handle = self._next_temp("file")
            lines.append(
                f"  {mode_pointer} = getelementptr inbounds [{len(self.FILE_MODE_BYTES)} x i8], ptr @{self.FILE_MODE_LABEL}, i32 0, i32 0"
            )
            lines.append(f"  {file_handle} = call ptr @fopen(ptr {path_pointer}, ptr {mode_pointer})")
            lines.append(f"  store ptr {file_handle}, ptr {slot_name}")
            return False
        if isinstance(instruction, IRWriteLine):
            slot_name = self.file_slots.get(instruction.file_name)
            if slot_name is None:
                global_slot = self.global_file_symbols.get(instruction.file_name)
                if global_slot is None:
                    raise TypeError(f"Unknown file variable: {instruction.file_name}")
                slot_name = f"@{global_slot}"
            file_handle = self._next_temp("file")
            format_pointer = self._next_temp("fmt")
            string_pointer = self._emit_string_expression(instruction.value, lines, string_lengths)
            lines.append(f"  {file_handle} = load ptr, ptr {slot_name}")
            lines.append(
                f"  {format_pointer} = getelementptr inbounds [{len(self.FILE_LINE_FORMAT_BYTES)} x i8], ptr @{self.FILE_LINE_FORMAT_LABEL}, i32 0, i32 0"
            )
            lines.append(f"  call i32 (ptr, ptr, ...) @fprintf(ptr {file_handle}, ptr {format_pointer}, ptr {string_pointer})")
            return False
        if isinstance(instruction, IRForLoop):
            return self._emit_for_loop(instruction, lines, string_lengths)
        if isinstance(instruction, IRWhileLoop):
            return self._emit_while_loop(instruction, lines, string_lengths)
        if isinstance(instruction, IRIf):
            return self._emit_if_statement(instruction, lines, string_lengths)
        if isinstance(instruction, IRContinue):
            if not self.continue_labels:
                raise TypeError("continue used outside loop")
            lines.append(f"  br label %{self.continue_labels[-1]}")
            return True
        if isinstance(instruction, IRBreak):
            if not self.break_labels:
                raise TypeError("break used outside loop")
            lines.append(f"  br label %{self.break_labels[-1]}")
            return True
        if isinstance(instruction, IRThrow):
            value = self._emit_string_expression(instruction.value, lines, string_lengths)
            release_value = self._string_expression_needs_release(instruction.value)
            lines.append(f"  call void @tb_set_exception(ptr {value})")
            if release_value:
                lines.append(f"  call void @tb_release(ptr {value})")
            target_label = self._current_exception_target_label()
            if target_label is None:
                raise TypeError("throw used outside an exception-aware function context")
            self.exception_dispatch_used = True
            lines.append(f"  br label %{target_label}")
            return True
        if isinstance(instruction, IRTryCatch):
            return self._emit_try_catch_statement(instruction, lines, string_lengths)
        if isinstance(instruction, IRFunctionCall):
            if instruction.name == "dump_runtime_activity":
                lines.append("  call void @tb_dump_runtime_stats()")
                return False
            if instruction.name == "reset_runtime_activity":
                lines.append("  call void @tb_reset_runtime_stats()")
                return False
            if instruction.name == "tb_pq_push":
                queue_pointer = self._emit_priority_queue_expression(
                    instruction.arguments[0].value,
                    lines,
                    string_lengths,
                    instruction.arguments[0].type_name,
                )
                value_pointer = self._emit_value_pointer(
                    instruction.arguments[1].type_name,
                    instruction.arguments[1].value,
                    lines,
                    string_lengths,
                    own_for_storage=False,
                )
                lines.append(f"  call void @tb_pq_push(ptr {queue_pointer}, ptr {value_pointer})")
                return False
            if instruction.name == "tb_set_add":
                set_type = instruction.arguments[0].type_name
                item_type = instruction.arguments[1].type_name
                set_pointer = self._emit_array_expression(instruction.arguments[0].value, lines, string_lengths, set_type)
                value = self._emit_owned_storage_value(item_type, instruction.arguments[1].value, lines, string_lengths)
                lines.append(
                    f"  call void {self._generic_set_add_symbol(item_type)}"
                    f"(ptr {set_pointer}, {self._llvm_type_for(item_type)} {value})"
                )
                return False
            arguments = ", ".join(self._emit_call_argument(argument, lines, string_lengths) for argument in instruction.arguments)
            return_type = self._llvm_type_for(instruction.return_type)
            if instruction.return_type == "void":
                lines.append(f"  call void {self._function_symbol(instruction.name)}({arguments})")
                self._emit_exception_dispatch_if_pending(lines)
            else:
                temp_name = self._next_temp("call")
                lines.append(f"  {temp_name} = call {return_type} {self._function_symbol(instruction.name)}({arguments})")
                self._emit_exception_dispatch_if_pending(lines)
            return False
        if isinstance(instruction, IRReturn):
            if instruction.return_type == "int":
                value = self._emit_integer_expression(instruction.value, lines)
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_priority_queue_locals(lines)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append(f"  ret i64 {value}")
                return True
            if instruction.return_type == "bool":
                value = self._emit_boolean_expression(instruction.value, lines)
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_priority_queue_locals(lines)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append(f"  ret i1 {value}")
                return True
            if instruction.return_type == "string":
                skip_slot = None
                if isinstance(instruction.value, IRVariable):
                    slot_name = self.variable_slots.get(instruction.value.name)
                    if slot_name in self.owned_string_slots:
                        skip_slot = slot_name
                        value = self._next_temp("str.ret")
                        lines.append(f"  {value} = load ptr, ptr {slot_name}")
                    else:
                        value = self._emit_string_expression(instruction.value, lines, string_lengths)
                        value = self._emit_clone_string(value, lines)
                else:
                    value = self._emit_string_expression(instruction.value, lines, string_lengths)
                    value = self._emit_clone_string(value, lines)
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_priority_queue_locals(lines)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines, skip_slot=skip_slot)
                self._emit_close_open_files(lines)
                lines.append(f"  ret ptr {value}")
                return True
            if self._is_array_type(instruction.return_type) or self._is_set_type(instruction.return_type):
                skip_slot = None
                if isinstance(instruction.value, IRVariable):
                    slot_name = self.variable_slots.get(instruction.value.name)
                    if slot_name in self.owned_array_slots:
                        skip_slot = slot_name
                        value = self._next_temp("array.ret")
                        lines.append(f"  {value} = load ptr, ptr {slot_name}")
                    else:
                        value = self._emit_array_expression(instruction.value, lines, string_lengths, instruction.return_type)
                        value = self._emit_retain_heap_value(value, lines, "array.ret")
                else:
                    value = self._emit_array_expression(instruction.value, lines, string_lengths, instruction.return_type)
                    if self._array_expression_is_borrowed(instruction.value):
                        value = self._emit_retain_heap_value(value, lines, "array.ret")
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_priority_queue_locals(lines)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines, skip_slot=skip_slot)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append(f"  ret ptr {value}")
                return True
            if self._is_map_type(instruction.return_type):
                skip_slot = None
                if isinstance(instruction.value, IRVariable):
                    slot_name = self.variable_slots.get(instruction.value.name)
                    if slot_name in self.owned_map_slots:
                        skip_slot = slot_name
                        value = self._next_temp("map.ret")
                        lines.append(f"  {value} = load ptr, ptr {slot_name}")
                    else:
                        value = self._emit_map_expression(instruction.value, lines, string_lengths, instruction.return_type)
                        value = self._emit_retain_heap_value(value, lines, "map.ret")
                else:
                    value = self._emit_map_expression(instruction.value, lines, string_lengths, instruction.return_type)
                    if self._map_expression_is_borrowed(instruction.value):
                        value = self._emit_retain_heap_value(value, lines, "map.ret")
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_priority_queue_locals(lines)
                self._emit_release_owned_map_locals(lines, skip_slot=skip_slot)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append(f"  ret ptr {value}")
                return True
            if self._is_priority_queue_type(instruction.return_type):
                skip_slot = None
                if isinstance(instruction.value, IRVariable):
                    slot_name = self.variable_slots.get(instruction.value.name)
                    if slot_name in self.owned_priority_queue_slots:
                        skip_slot = slot_name
                        value = self._next_temp("pq.ret")
                        lines.append(f"  {value} = load ptr, ptr {slot_name}")
                    else:
                        value = self._emit_priority_queue_expression(instruction.value, lines, string_lengths, instruction.return_type)
                        value = self._emit_retain_heap_value(value, lines, "pq.ret")
                else:
                    value = self._emit_priority_queue_expression(instruction.value, lines, string_lengths, instruction.return_type)
                    if self._priority_queue_expression_is_borrowed(instruction.value):
                        value = self._emit_retain_heap_value(value, lines, "pq.ret")
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_priority_queue_locals(lines, skip_slot=skip_slot)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append(f"  ret ptr {value}")
                return True
            if instruction.return_type in self.record_types:
                skip_slot = None
                if isinstance(instruction.value, IRVariable):
                    slot_name = self.variable_slots.get(instruction.value.name)
                    if slot_name in self.owned_record_slots:
                        skip_slot = slot_name
                        value = self._next_temp("record.ret")
                        lines.append(f"  {value} = load ptr, ptr {slot_name}")
                    else:
                        value = self._emit_record_expression(instruction.value, lines, string_lengths, instruction.return_type)
                        value = self._emit_retain_heap_value(value, lines, "record.ret")
                else:
                    value = self._emit_record_expression(instruction.value, lines, string_lengths, instruction.return_type)
                    if self._record_expression_is_borrowed(instruction.value):
                        value = self._emit_retain_heap_value(value, lines, "record.ret")
                self._emit_release_owned_record_locals(lines, skip_slot=skip_slot)
                self._emit_release_owned_priority_queue_locals(lines)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append(f"  ret ptr {value}")
                return True
            if instruction.return_type == "void":
                self._emit_release_owned_record_locals(lines)
                self._emit_release_owned_map_locals(lines)
                self._emit_release_owned_array_locals(lines)
                self._emit_release_owned_string_locals(lines)
                self._emit_close_open_files(lines)
                lines.append("  ret void")
                return True
            raise TypeError(f"Unsupported return type: {instruction.return_type}")
        raise TypeError(f"Unsupported IR instruction: {type(instruction).__name__}")

    def _emit_for_loop(self, instruction: IRForLoop, lines: list[str], string_lengths: dict[str, int]) -> bool:
        self._emit_instruction(instruction.initializer, lines, string_lengths)
        condition_label = self._next_label("for.cond")
        body_label = self._next_label("for.body")
        update_label = self._next_label("for.update")
        end_label = self._next_label("for.end")

        lines.append(f"  br label %{condition_label}")
        lines.append(f"{condition_label}:")
        condition_value = self._emit_condition(instruction.condition, lines)
        lines.append(f"  br i1 {condition_value}, label %{body_label}, label %{end_label}")
        lines.append(f"{body_label}:")
        terminated = False
        self.continue_labels.append(update_label)
        self.break_labels.append(end_label)
        try:
            for body_instruction in instruction.body:
                terminated = self._emit_instruction(body_instruction, lines, string_lengths)
                if terminated:
                    break
        finally:
            self.continue_labels.pop()
            self.break_labels.pop()
        if not terminated:
            lines.append(f"  br label %{update_label}")
            lines.append(f"{update_label}:")
            self._emit_instruction(instruction.update, lines, string_lengths)
            lines.append(f"  br label %{condition_label}")
        lines.append(f"{end_label}:")
        return False

    def _emit_while_loop(self, instruction: IRWhileLoop, lines: list[str], string_lengths: dict[str, int]) -> bool:
        condition_label = self._next_label("while.cond")
        body_label = self._next_label("while.body")
        end_label = self._next_label("while.end")

        lines.append(f"  br label %{condition_label}")
        lines.append(f"{condition_label}:")
        condition_value = self._emit_condition(instruction.condition, lines)
        lines.append(f"  br i1 {condition_value}, label %{body_label}, label %{end_label}")
        lines.append(f"{body_label}:")
        terminated = False
        self.continue_labels.append(condition_label)
        self.break_labels.append(end_label)
        try:
            for body_instruction in instruction.body:
                terminated = self._emit_instruction(body_instruction, lines, string_lengths)
                if terminated:
                    break
        finally:
            self.continue_labels.pop()
            self.break_labels.pop()
        if not terminated:
            lines.append(f"  br label %{condition_label}")
        lines.append(f"{end_label}:")
        return False

    def _emit_if_statement(self, instruction: IRIf, lines: list[str], string_lengths: dict[str, int]) -> bool:
        then_label = self._next_label("if.then")
        else_label = self._next_label("if.else")
        end_label = self._next_label("if.end")

        condition_value = self._emit_condition(instruction.condition, lines)
        lines.append(f"  br i1 {condition_value}, label %{then_label}, label %{else_label}")
        lines.append(f"{then_label}:")
        then_terminated = False
        for then_instruction in instruction.then_body:
            then_terminated = self._emit_instruction(then_instruction, lines, string_lengths)
            if then_terminated:
                break
        if not then_terminated:
            lines.append(f"  br label %{end_label}")
        lines.append(f"{else_label}:")
        else_terminated = False
        for else_instruction in instruction.else_body:
            else_terminated = self._emit_instruction(else_instruction, lines, string_lengths)
            if else_terminated:
                break
        if not else_terminated:
            lines.append(f"  br label %{end_label}")
        lines.append(f"{end_label}:")
        return then_terminated and else_terminated

    def _emit_try_catch_statement(self, instruction: IRTryCatch, lines: list[str], string_lengths: dict[str, int]) -> bool:
        catch_label = self._next_label("catch")
        end_label = self._next_label("try.end")
        catch_slot = self._next_temp(f"{instruction.catch_name}.catch")
        previous_slot = self.variable_slots.get(instruction.catch_name)
        previous_type = self.variable_types.get(instruction.catch_name)

        self.alloca_lines.append(f"  {catch_slot} = alloca ptr")
        self.alloca_lines.append(f"  store ptr null, ptr {catch_slot}")
        self.variable_slots[instruction.catch_name] = catch_slot
        self.variable_types[instruction.catch_name] = "string"
        if catch_slot not in self.owned_string_slots:
            self.owned_string_slots.append(catch_slot)

        terminated = False
        self.exception_handler_labels.append(catch_label)
        try:
            for try_instruction in instruction.try_body:
                terminated = self._emit_instruction(try_instruction, lines, string_lengths)
                if terminated:
                    break
        finally:
            self.exception_handler_labels.pop()

        if not terminated:
            lines.append(f"  br label %{end_label}")

        lines.append(f"{catch_label}:")
        message = self._next_temp("exc.msg")
        cloned = self._next_temp("exc.msg.clone")
        old_value = self._next_temp("exc.catch.old")
        lines.append(f"  {message} = load ptr, ptr @__tb_exception_message")
        lines.append(f"  {cloned} = call ptr @tb_string_clone(ptr {message})")
        lines.append(f"  {old_value} = load ptr, ptr {catch_slot}")
        lines.append(f"  store ptr {cloned}, ptr {catch_slot}")
        lines.append(f"  call void @tb_release(ptr {old_value})")
        lines.append("  call void @tb_clear_exception()")

        catch_terminated = False
        for catch_instruction in instruction.catch_body:
            catch_terminated = self._emit_instruction(catch_instruction, lines, string_lengths)
            if catch_terminated:
                break
        if not catch_terminated:
            lines.append(f"  br label %{end_label}")

        lines.append(f"{end_label}:")
        if previous_slot is None:
            self.variable_slots.pop(instruction.catch_name, None)
            self.variable_types.pop(instruction.catch_name, None)
        else:
            self.variable_slots[instruction.catch_name] = previous_slot
            if previous_type is not None:
                self.variable_types[instruction.catch_name] = previous_type
        return terminated and catch_terminated

    def _emit_condition(self, condition: IRComparison, lines: list[str]) -> str:
        if isinstance(condition, IRLogicalCondition):
            left = self._emit_condition(condition.left, lines)
            right = self._emit_condition(condition.right, lines)
            temp_name = self._next_temp("logic")
            operation = "and" if condition.operator == "&&" else "or"
            lines.append(f"  {temp_name} = {operation} i1 {left}, {right}")
            return temp_name
        if self._is_boolean_ir_expression(condition.left) and self._is_boolean_ir_expression(condition.right):
            left = self._emit_boolean_expression(condition.left, lines)
            right = self._emit_boolean_expression(condition.right, lines)
            temp_name = self._next_temp("cmp")
            operation = {
                "==": "eq",
                "!=": "ne",
            }.get(condition.operator)
            if operation is None:
                raise TypeError(f"Unsupported boolean comparison operator: {condition.operator}")
            lines.append(f"  {temp_name} = icmp {operation} i1 {left}, {right}")
            return temp_name
        left = self._emit_integer_expression(condition.left, lines)
        right = self._emit_integer_expression(condition.right, lines)
        temp_name = self._next_temp("cmp")
        operation = {
            "==": "eq",
            "!=": "ne",
            "<": "slt",
            "<=": "sle",
            ">": "sgt",
            ">=": "sge",
        }.get(condition.operator)
        if operation is None:
            raise TypeError(f"Unsupported comparison operator: {condition.operator}")
        lines.append(f"  {temp_name} = icmp {operation} i64 {left}, {right}")
        return temp_name

    def _emit_function_definition(self, function: IRFunctionDefinition, string_lengths: dict[str, int]) -> list[str]:
        if function.cached:
            return self._emit_cached_function_definition(function, string_lengths)
        return self._emit_function_body(self._function_symbol(function.name), function.parameters, function.body, function.return_type, string_lengths)

    def _emit_function_body(
        self,
        symbol_name: str,
        parameters: list[IRFunctionParameter],
        body: list,
        return_type: str,
        string_lengths: dict[str, int],
    ) -> list[str]:
        lines: list[str] = []
        parameter_text = ", ".join(self._emit_function_parameter(parameter) for parameter in parameters)
        lines.append(f"define {self._llvm_type_for(return_type)} {symbol_name}({parameter_text}) {{")
        lines.append("entry:")
        self._reset_function_state()
        self.function_exception_label = self._next_label("exc.unwind")
        for parameter in parameters:
            self._bind_function_parameter(parameter, lines)
        terminated = False
        for instruction in body:
            terminated = self._emit_instruction(instruction, lines, string_lengths)
            if terminated:
                break
        lines[2:2] = self.alloca_lines
        if not terminated:
            self._emit_function_cleanup(lines)
            self._emit_default_return(return_type, lines)
        if self.exception_dispatch_used:
            lines.append(f"{self.function_exception_label}:")
            self._emit_function_cleanup(lines)
            self._emit_default_return(return_type, lines)
        lines.append("}")
        return lines

    def _emit_cached_function_definition(self, function: IRFunctionDefinition, string_lengths: dict[str, int]) -> list[str]:
        implementation_lines = self._emit_function_body(
            self._cached_impl_symbol(function.name),
            function.parameters,
            function.body,
            function.return_type,
            string_lengths,
        )
        parameter_text = ", ".join(self._emit_function_parameter(parameter) for parameter in function.parameters)
        cache_symbol = self._cached_cache_symbol(function.name)
        implementation_symbol = self._cached_impl_symbol(function.name)
        key_symbol = self._cached_key_symbol(function.name)

        lines = [*implementation_lines, "", *self._emit_cached_key_helper(function), ""]
        lines.append(f"define i64 {self._function_symbol(function.name)}({parameter_text}) {{")
        lines.append("entry:")
        self._reset_function_state()
        cache_ptr = self._next_temp("cache")
        cache_is_null = self._next_temp("cache")
        cache_new = self._next_temp("cache")
        cache_ready = self._next_temp("cache")
        key_name = self._next_temp("key")
        has_name = self._next_temp("has")
        cached_value = self._next_temp("cached")
        result_name = self._next_temp("result")
        init_label = self._next_label("cache.init")
        ready_label = self._next_label("cache.ready")
        hit_label = self._next_label("cache.hit")
        miss_label = self._next_label("cache.miss")
        exception_label = self._next_label("cache.exc")
        store_label = self._next_label("cache.store")

        lines.append(f"  {cache_ptr} = load ptr, ptr @{cache_symbol}")
        lines.append(f"  {cache_is_null} = icmp eq ptr {cache_ptr}, null")
        lines.append(f"  br i1 {cache_is_null}, label %{init_label}, label %{ready_label}")
        lines.append(f"{init_label}:")
        lines.append(
            f"  {cache_new} = call ptr @tb_map_new(i64 8, i32 {self._map_release_mode('string')}, i32 {self._map_release_mode('int')})"
        )
        lines.append(f"  store ptr {cache_new}, ptr @{cache_symbol}")
        lines.append(f"  br label %{ready_label}")
        lines.append(f"{ready_label}:")
        lines.append(f"  {cache_ready} = phi ptr [ {cache_ptr}, %entry ], [ {cache_new}, %{init_label} ]")
        call_args = ", ".join(self._emit_cached_argument(parameter) for parameter in function.parameters)
        lines.append(f"  {key_name} = call ptr {key_symbol}({call_args})")
        lines.append(f"  {has_name} = call i1 @tb_map_has_string_int(ptr {cache_ready}, ptr {key_name})")
        lines.append(f"  br i1 {has_name}, label %{hit_label}, label %{miss_label}")
        lines.append(f"{hit_label}:")
        lines.append(f"  {cached_value} = call i64 @tb_map_get_string_int(ptr {cache_ready}, ptr {key_name})")
        lines.append(f"  call void @tb_release(ptr {key_name})")
        lines.append(f"  ret i64 {cached_value}")
        lines.append(f"{miss_label}:")
        lines.append(
            f"  {result_name} = call i64 {implementation_symbol}({call_args})"
        )
        lines.append("  %cache.exc.pending = load i1, ptr @__tb_exception_pending")
        lines.append(f"  br i1 %cache.exc.pending, label %{exception_label}, label %{store_label}")
        lines.append(f"{store_label}:")
        lines.append(f"  call void @tb_map_put_string_int(ptr {cache_ready}, ptr {key_name}, i64 {result_name})")
        lines.append(f"  call void @tb_release(ptr {key_name})")
        lines.append(f"  ret i64 {result_name}")
        lines.append(f"{exception_label}:")
        lines.append(f"  call void @tb_release(ptr {key_name})")
        lines.append("  ret i64 0")
        lines.append("}")
        return lines

    def _emit_entry_wrapper(self) -> list[str]:
        body_lines: list[str] = []
        self._reset_function_state()
        self.function_exception_label = "__tb_entry_exc_unwind"
        self.global_init_mode = True
        try:
            for instruction in self.global_instructions:
                self._emit_instruction(instruction, body_lines, self.string_lengths)
        finally:
            self.global_init_mode = False
        body_lines.extend(
            [
            "  %argc64 = zext i32 %argc to i64",
            "  %args = call ptr @tb_args_from_argv(i64 %argc64, ptr %argv)",
            f"  %result = call i64 {self._function_symbol(self.entry_function_name)}(ptr %args)",
            "  %main.exc.pending = load i1, ptr @__tb_exception_pending",
            f"  br i1 %main.exc.pending, label %{self.function_exception_label}, label %__tb_entry_return",
            "__tb_entry_return:",
            "  %exit = trunc i64 %result to i32",
            "  call void @tb_arena_destroy()",
            "  ret i32 %exit",
            ]
        )
        body_lines.extend(
            [
                f"{self.function_exception_label}:",
                "  call void @tb_report_uncaught_exception()",
                "  call void @tb_clear_exception()",
                "  call void @tb_arena_destroy()",
                "  ret i32 1",
            ]
        )
        return [
            "define i32 @main(i32 %argc, ptr %argv) {",
            "entry:",
            *self.alloca_lines,
            *body_lines,
            "}",
        ]

    def _emit_function_parameter(self, parameter: IRFunctionParameter) -> str:
        return f"{self._llvm_type_for(parameter.type_name)} %{parameter.name}.param"

    def _function_symbol(self, name: str | None) -> str:
        if name is None:
            raise TypeError("Missing function name")
        return self.function_symbol_names.get(name, f"@{name}")

    def _sort_comparator_symbol(self, item_type: str, comparator_name: str) -> str:
        key = (item_type, comparator_name)
        symbol = self.sort_comparator_helpers.get(key)
        if symbol is None:
            symbol = f"@__tb_sort_cmp_{len(self.sort_comparator_helpers)}"
            self.sort_comparator_helpers[key] = symbol
        return symbol

    def _emit_sort_comparator_helpers(self) -> list[str]:
        lines: list[str] = []
        for (item_type, comparator_name), symbol in self.sort_comparator_helpers.items():
            llvm_type = self._llvm_type_for(item_type)
            comparator_symbol = self._function_symbol(comparator_name)
            lines.extend(
                [
                    f"define private i32 {symbol}(ptr %left.slot, ptr %right.slot) {{",
                    "entry:",
                    f"  %left = load {llvm_type}, ptr %left.slot",
                    f"  %right = load {llvm_type}, ptr %right.slot",
                    f"  %cmp64 = call i64 {comparator_symbol}({llvm_type} %left, {llvm_type} %right)",
                    "  %is.neg = icmp slt i64 %cmp64, 0",
                    "  %is.pos = icmp sgt i64 %cmp64, 0",
                    "  %signed = select i1 %is.neg, i32 -1, i32 0",
                    "  %result = select i1 %is.pos, i32 1, i32 %signed",
                    "  ret i32 %result",
                    "}",
                    "",
                ]
            )
        return lines

    @staticmethod
    def _cached_impl_symbol(name: str) -> str:
        return f"@__tb_cached_impl_{name}"

    @staticmethod
    def _cached_cache_symbol(name: str) -> str:
        return f"__tb_cached_cache_{name}"

    @staticmethod
    def _record_hash_symbol(name: str) -> str:
        return f"@__tb_record_hash_{name}"

    @staticmethod
    def _record_cache_key_symbol(name: str) -> str:
        return f"@__tb_record_cache_key_{name}"

    @staticmethod
    def _cached_key_symbol(name: str) -> str:
        return f"@__tb_cached_key_{name}"

    def _emit_cached_key_helper(self, function) -> list[str]:
        parameter_text = ", ".join(self._emit_function_parameter(parameter) for parameter in function.parameters)
        lines = [
            f"define private ptr {self._cached_key_symbol(function.name)}({parameter_text}) {{",
            "entry:",
        ]
        lengths: list[str] = []
        for index, parameter in enumerate(function.parameters):
            value_name = f"%{parameter.name}.param"
            text_name = self._emit_cache_stringify_value(parameter.type_name, value_name, lines, f"cache.measure.{index}")
            wrapped_name = f"%cache.measure.wrap.{index}"
            lines.append(f"  {wrapped_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
            if self._cache_stringify_needs_release(parameter.type_name):
                lines.append(f"  call void @tb_release(ptr {text_name})")
            length_name = f"%cache.measure.len.{index}"
            lines.append(f"  {length_name} = call i64 @strlen(ptr {wrapped_name})")
            lines.append(f"  call void @tb_release(ptr {wrapped_name})")
            lengths.append(length_name)

        total_length = lengths[0]
        for index, length_name in enumerate(lengths[1:], start=1):
            next_total = f"%cache.total.{index}"
            lines.append(f"  {next_total} = add i64 {total_length}, {length_name}")
            total_length = next_total
        buffer_name = "%cache.buffer"
        lines.append(f"  {buffer_name} = call ptr @tb_string_new(i64 {total_length})")

        current_offset = "0"
        for index, parameter in enumerate(function.parameters):
            value_name = f"%{parameter.name}.param"
            text_name = self._emit_cache_stringify_value(parameter.type_name, value_name, lines, f"cache.copy.{index}")
            wrapped_name = f"%cache.copy.wrap.{index}"
            lines.append(f"  {wrapped_name} = call ptr @tb_cache_wrap_string(ptr {text_name})")
            if self._cache_stringify_needs_release(parameter.type_name):
                lines.append(f"  call void @tb_release(ptr {text_name})")
            destination = f"%cache.dst.{index}"
            lines.append(f"  {destination} = getelementptr inbounds i8, ptr {buffer_name}, i64 {current_offset}")
            lines.append(f"  call ptr @memcpy(ptr {destination}, ptr {wrapped_name}, i64 {lengths[index]})")
            lines.append(f"  call void @tb_release(ptr {wrapped_name})")
            if index + 1 < len(lengths):
                next_offset = f"%cache.offset.{index}"
                lines.append(f"  {next_offset} = add i64 {current_offset}, {lengths[index]}")
                current_offset = next_offset

        terminator = "%cache.term"
        lines.append(f"  {terminator} = getelementptr inbounds i8, ptr {buffer_name}, i64 {total_length}")
        lines.append(f"  store i8 0, ptr {terminator}")
        lines.append(f"  ret ptr {buffer_name}")
        lines.append("}")
        return lines

    @staticmethod
    def _record_destroy_symbol(name: str) -> str:
        return f"@__tb_destroy_record_{name}"

    @staticmethod
    def _cache_array_string_symbol(type_name: str) -> str:
        sanitized = type_name.replace("[", "_").replace("]", "_").replace("<", "_").replace(">", "_").replace(",", "_")
        sanitized = sanitized.replace(" ", "").replace("-", "_")
        return f"@__tb_cache_array_string_{sanitized}"

    @staticmethod
    def _sanitize_type_name(type_name: str) -> str:
        sanitized = type_name.replace("[", "_").replace("]", "_").replace("<", "_").replace(">", "_").replace(",", "_")
        sanitized = sanitized.replace(" ", "").replace("-", "_")
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_")

    def _generic_set_contains_symbol(self, item_type: str) -> str:
        if item_type == "int":
            return "@tb_set_contains_int"
        self.generic_set_helper_types.add(item_type)
        return f"@__tb_set_contains_{self._sanitize_type_name(item_type)}"

    def _generic_set_add_symbol(self, item_type: str) -> str:
        if item_type == "int":
            return "@tb_set_add_int"
        self.generic_set_helper_types.add(item_type)
        return f"@__tb_set_add_{self._sanitize_type_name(item_type)}"

    def _generic_set_union_symbol(self, item_type: str) -> str:
        if item_type == "int":
            return "@tb_set_union_int"
        self.generic_set_helper_types.add(item_type)
        return f"@__tb_set_union_{self._sanitize_type_name(item_type)}"

    def _generic_map_put_symbol(self, key_type: str, value_type: str) -> str:
        if (key_type, value_type) == ("string", "int"):
            return "@tb_map_put_string_int"
        self.generic_map_helper_types.add((key_type, value_type))
        return f"@__tb_map_put_{self._sanitize_type_name(key_type)}_{self._sanitize_type_name(value_type)}"

    def _generic_map_get_symbol(self, key_type: str, value_type: str) -> str:
        if (key_type, value_type) == ("string", "int"):
            return "@tb_map_get_string_int"
        self.generic_map_helper_types.add((key_type, value_type))
        return f"@__tb_map_get_{self._sanitize_type_name(key_type)}_{self._sanitize_type_name(value_type)}"

    def _generic_map_has_symbol(self, key_type: str, value_type: str) -> str:
        if (key_type, value_type) == ("string", "int"):
            return "@tb_map_has_string_int"
        self.generic_map_helper_types.add((key_type, value_type))
        return f"@__tb_map_has_{self._sanitize_type_name(key_type)}_{self._sanitize_type_name(value_type)}"

    def _generic_map_keys_symbol(self, key_type: str, value_type: str) -> str:
        if (key_type, value_type) == ("string", "int"):
            return "@tb_map_keys_string_int"
        self.generic_map_helper_types.add((key_type, value_type))
        return f"@__tb_map_keys_{self._sanitize_type_name(key_type)}_{self._sanitize_type_name(value_type)}"

    def _generic_map_values_symbol(self, key_type: str, value_type: str) -> str:
        if (key_type, value_type) == ("string", "int"):
            return "@tb_map_values_string_int"
        self.generic_map_helper_types.add((key_type, value_type))
        return f"@__tb_map_values_{self._sanitize_type_name(key_type)}_{self._sanitize_type_name(value_type)}"

    def _cache_array_string_symbol_for_type(self, type_name: str) -> str:
        if type_name == "int[]":
            return "@tb_int_array_to_string"
        if type_name == "string[]":
            return "@tb_string_array_to_string"
        if type_name == "bool[]":
            return "@tb_bool_array_to_string"
        return self._cache_array_string_symbol(type_name)

    def _cache_stringify_needs_release(self, type_name: str) -> bool:
        return not (type_name == "string" or type_name in getattr(self, "enum_types", {}))

    def _emit_cache_stringify_value(self, type_name: str, value_name: str, lines: list[str], prefix: str) -> str:
        if type_name == "int":
            text_name = f"%{prefix}.text"
            lines.append(f"  {text_name} = call ptr @tb_int_to_string(i64 {value_name})")
            return text_name
        if type_name == "bool":
            bool_int = f"%{prefix}.bool"
            text_name = f"%{prefix}.text"
            lines.append(f"  {bool_int} = zext i1 {value_name} to i64")
            lines.append(f"  {text_name} = call ptr @tb_int_to_string(i64 {bool_int})")
            return text_name
        if type_name == "string" or type_name in getattr(self, "enum_types", {}):
            return value_name
        if self._is_array_type(type_name):
            text_name = f"%{prefix}.text"
            lines.append(f"  {text_name} = call ptr {self._cache_array_string_symbol_for_type(type_name)}(ptr {value_name})")
            return text_name
        if type_name in getattr(self, "record_types", {}):
            text_name = f"%{prefix}.text"
            lines.append(f"  {text_name} = call ptr {self._record_cache_key_symbol(type_name)}(ptr {value_name})")
            return text_name
        raise TypeError(f"Unsupported cached array item type: {type_name}")

    def _emit_cached_argument(self, parameter: IRFunctionParameter) -> str:
        return f"{self._llvm_type_for(parameter.type_name)} %{parameter.name}.param"

    def _bind_function_parameter(self, parameter: IRFunctionParameter, lines: list[str]) -> None:
        slot_name = f"%{parameter.name}"
        self.variable_slots[parameter.name] = slot_name
        self.variable_types[parameter.name] = parameter.type_name
        self.alloca_lines.append(f"  {slot_name} = alloca {self._llvm_type_for(parameter.type_name)}")
        if parameter.type_name == "string":
            self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
            self.owned_string_slots.append(slot_name)
            retained = self._next_temp("str.param")
            lines.append(f"  {retained} = call ptr @tb_retain(ptr %{parameter.name}.param)")
            lines.append(f"  store ptr {retained}, ptr {slot_name}")
            return
        if self._is_array_type(parameter.type_name) or self._is_set_type(parameter.type_name):
            self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
            self.owned_array_slots.append(slot_name)
            retained = self._next_temp("array.param")
            lines.append(f"  {retained} = call ptr @tb_retain(ptr %{parameter.name}.param)")
            lines.append(f"  store ptr {retained}, ptr {slot_name}")
            return
        if self._is_map_type(parameter.type_name):
            self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
            self.owned_map_slots.append(slot_name)
            retained = self._next_temp("map.param")
            lines.append(f"  {retained} = call ptr @tb_retain(ptr %{parameter.name}.param)")
            lines.append(f"  store ptr {retained}, ptr {slot_name}")
            return
        if self._is_priority_queue_type(parameter.type_name):
            self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
            self.owned_priority_queue_slots.append(slot_name)
            retained = self._next_temp("pq.param")
            lines.append(f"  {retained} = call ptr @tb_retain(ptr %{parameter.name}.param)")
            lines.append(f"  store ptr {retained}, ptr {slot_name}")
            return
        if parameter.type_name in self.record_types:
            self.alloca_lines.append(f"  store ptr null, ptr {slot_name}")
            self.owned_record_slots.append(slot_name)
            retained = self._next_temp("record.param")
            lines.append(f"  {retained} = call ptr @tb_retain(ptr %{parameter.name}.param)")
            lines.append(f"  store ptr {retained}, ptr {slot_name}")
            return
        lines.append(f"  store {self._llvm_type_for(parameter.type_name)} %{parameter.name}.param, ptr {slot_name}")

    def _llvm_type_for(self, type_name: str) -> str:
        if type_name == "int":
            return "i64"
        if type_name == "bool":
            return "i1"
        if self._is_map_type(type_name):
            return "ptr"
        if self._is_array_type(type_name) or self._is_set_type(type_name) or self._is_priority_queue_type(type_name) or type_name in getattr(self, "record_types", {}):
            return "ptr"
        if type_name in {"string", "file"} or type_name in getattr(self, "enum_types", {}):
            return "ptr"
        if type_name == "void":
            return "void"
        raise TypeError(f"Unsupported LLVM type: {type_name}")

    def _is_boolean_ir_expression(self, expression) -> bool:
        return (
            isinstance(expression, IRBoolean)
            or (isinstance(expression, IRVariable) and self.variable_types.get(expression.name) == "bool")
            or (isinstance(expression, IRArrayIndex) and expression.item_type == "bool")
            or (isinstance(expression, IRArrayPop) and expression.item_type == "bool")
            or (isinstance(expression, IRArrayRemove) and expression.item_type == "bool")
            or (isinstance(expression, IRRecordField) and expression.field_type == "bool")
            or (isinstance(expression, IRCallExpression) and expression.return_type == "bool")
            or (isinstance(expression, IRSelect) and expression.result_type == "bool")
        )

    def _next_temp(self, prefix: str) -> str:
        name = f"%{prefix}{self.temp_counter}"
        self.temp_counter += 1
        return name

    def _next_label(self, prefix: str) -> str:
        label = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def _reset_function_state(self) -> None:
        self.variable_slots = {}
        self.variable_types = {}
        self.owned_string_slots = []
        self.owned_array_slots = []
        self.owned_map_slots = []
        self.owned_priority_queue_slots = []
        self.owned_record_slots = []
        self.file_slots = {}
        self.open_file_slots = []
        self.continue_labels = []
        self.break_labels = []
        self.exception_handler_labels = []
        self.function_exception_label = None
        self.exception_dispatch_used = False
        self.alloca_lines = []
        self.temp_counter = 0
        self.label_counter = 0

    def _emit_function_cleanup(self, lines: list[str]) -> None:
        self._emit_release_owned_record_locals(lines)
        self._emit_release_owned_priority_queue_locals(lines)
        self._emit_release_owned_map_locals(lines)
        self._emit_release_owned_array_locals(lines)
        self._emit_release_owned_string_locals(lines)
        self._emit_close_open_files(lines)

    def _emit_default_return(self, return_type: str, lines: list[str]) -> None:
        if return_type == "void":
            lines.append("  ret void")
        elif return_type == "int":
            lines.append("  ret i64 0")
        elif return_type == "bool":
            lines.append("  ret i1 0")
        elif self._is_priority_queue_type(return_type) or self._is_map_type(return_type) or self._is_array_type(return_type) or return_type in self.record_types or return_type == "string":
            lines.append("  ret ptr null")
        else:
            raise TypeError(f"Unsupported function return type: {return_type}")

    def _emit_close_open_files(self, lines: list[str]) -> None:
        for slot_name in self.open_file_slots:
            file_handle = self._next_temp("file")
            lines.append(f"  {file_handle} = load ptr, ptr {slot_name}")
            lines.append(f"  call i32 @fclose(ptr {file_handle})")


def emit_llvm(module: IRModule) -> str:
    return LLVMEmitter().emit(module)
