#!/bin/sh

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

set -eu

if [ "$#" -lt 1 ]; then
    echo "Usage: ./tb.sh <file.tb> [clang args...]" >&2
    exit 1
fi

input_path=$1
shift

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir" && pwd)
compiler_bin="$repo_root/bin/tb"
input_name=$(basename "$input_path")
program_name=${input_name%.tb}
input_dir=$(dirname "$input_path")
build_dir="$repo_root/.build"
llvm_output="$build_dir/${program_name}.ll"
if [ "$input_dir" = "." ]; then
    program_output="$repo_root/${program_name}"
else
    program_output="$repo_root/${input_dir}/${program_name}"
fi
linkflags_file="${llvm_output}.linkflags"
cflags_file="${llvm_output}.cflags"
csources_file="${llvm_output}.csources"
platform_os=$(uname -s | tr '[:upper:]' '[:lower:]')
platform_arch=$(uname -m)
if [ "$platform_os" = "darwin" ]; then
    platform_os="macos"
fi
platform_suffix="${platform_os}_${platform_arch}"
objects=""
linkflags=""
cflags=""

if [ ! -x "$compiler_bin" ]; then
    echo "Missing self-hosted tb compiler: $compiler_bin" >&2
    echo "Build it first with: ./build_tb.sh" >&2
    exit 1
fi

mkdir -p "$build_dir"
if [ "$input_dir" != "." ]; then
    mkdir -p "$repo_root/$input_dir"
fi

"$compiler_bin" "$repo_root/$input_path" "$llvm_output"

if [ -f "$linkflags_file" ]; then
    linkflags=$(tr '\n' ' ' < "$linkflags_file")
fi

if [ -f "$cflags_file" ]; then
    cflags=$(tr '\n' ' ' < "$cflags_file")
fi

if [ -f "$csources_file" ]; then
    while IFS= read -r c_source; do
        [ -n "$c_source" ] || continue
        resolved_c_source="$repo_root/$c_source"
        if [ ! -f "$resolved_c_source" ] && [ -f "$repo_root/bindings/tb/$c_source" ]; then
            resolved_c_source="$repo_root/bindings/tb/$c_source"
        fi
        if [ ! -f "$resolved_c_source" ]; then
            echo "Missing foreign C source: $c_source" >&2
            exit 1
        fi
        object_dir="$(dirname "$resolved_c_source")/lib"
        mkdir -p "$object_dir"
        object_output="$object_dir/$(basename "${resolved_c_source%.*}")_${platform_suffix}.o"
        if [ ! -f "$object_output" ]; then
            clang -c $cflags "$resolved_c_source" -o "$object_output"
        fi
        objects="$objects $object_output"
    done < "$csources_file"
fi

clang "$llvm_output" $objects -o "$program_output" $linkflags "$@"

echo "Built tb program: $program_output"
echo "LLVM output: $llvm_output"
