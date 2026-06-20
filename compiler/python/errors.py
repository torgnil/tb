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


@dataclass(slots=True)
class CompilationError(Exception):
    message: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"Error: {self.message}\nat line {self.line}, column {self.column}"


class LexerError(CompilationError):
    pass


class ParserError(CompilationError):
    pass
