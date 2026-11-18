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
    case "$input_path" in
        /*) program_output="${input_dir}/${program_name}" ;;
        *) program_output="$repo_root/${input_dir}/${program_name}" ;;
    esac
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
raylib_static=${TB_RAYLIB_STATIC:-0}
case "$raylib_static" in
    0|1) ;;
    *) echo "TB_RAYLIB_STATIC must be 0 or 1" >&2; exit 1 ;;
esac

if [ ! -x "$compiler_bin" ]; then
    echo "Missing self-hosted tb compiler: $compiler_bin" >&2
    echo "Build it first with: ./build_tb.sh" >&2
    exit 1
fi

mkdir -p "$build_dir"
runtime_object_dir=$(mktemp -d "$build_dir/runtime.XXXXXX")
trap 'rm -f "$runtime_object_dir"/*.o; rmdir "$runtime_object_dir"' 0
trap 'exit 1' HUP INT TERM
if [ "$input_dir" != "." ]; then
    case "$input_path" in
        /*) ;;
        *) mkdir -p "$repo_root/$input_dir" ;;
    esac
fi

case "$input_path" in
    /*) source_path=$input_path ;;
    *) source_path="$repo_root/$input_path" ;;
esac

"$compiler_bin" "$source_path" "$llvm_output"

compile_c_source() {
    c_input=$1
    c_output=$2
    set --
    if [ -f "$cflags_file" ]; then
        while IFS= read -r flag || [ -n "$flag" ]; do
            [ -n "$flag" ] || continue
            set -- "$@" "$flag"
        done < "$cflags_file"
    fi
    clang -c "$@" "$c_input" -o "$c_output"
}

if [ -f "$csources_file" ]; then
    object_index=0
    while IFS= read -r c_source; do
        [ -n "$c_source" ] || continue
        case "$c_source" in
            /*) resolved_c_source=$c_source ;;
            *) resolved_c_source="$repo_root/$c_source" ;;
        esac
        if [ ! -f "$resolved_c_source" ] && [ -f "$repo_root/bindings/tb/$c_source" ]; then
            resolved_c_source="$repo_root/bindings/tb/$c_source"
        fi
        if [ ! -f "$resolved_c_source" ]; then
            echo "Missing foreign C source: $c_source" >&2
            exit 1
        fi
        object_output="$runtime_object_dir/${object_index}_$(basename "${resolved_c_source%.*}")_${platform_suffix}.o"
        compile_c_source "$resolved_c_source" "$object_output"
        set -- "$@" "$object_output"
        object_index=$((object_index + 1))
    done < "$csources_file"
fi

if [ -f "$linkflags_file" ]; then
    library_dir=""
    while IFS= read -r flag || [ -n "$flag" ]; do
        [ -n "$flag" ] || continue
        case "$flag" in
            -L*) library_dir=${flag#-L} ;;
        esac
        if [ "$raylib_static" = 1 ]; then
            case "$flag" in
                "-Wl,-rpath,$library_dir")
                    continue ;;
                -lraylib)
                    if [ "$platform_os" != macos ]; then
                        echo "Static raylib linking is currently supported on macOS" >&2
                        exit 1
                    fi
                    if [ -z "$library_dir" ] || [ ! -f "$library_dir/libraylib.a" ]; then
                        echo "Static raylib archive missing. Check TB_RAYLIB_ROOT or install raylib with libraylib.a." >&2
                        exit 1
                    fi
                    set -- "$@" "$library_dir/libraylib.a" \
                        -framework Cocoa -framework IOKit -framework OpenGL \
                        -framework CoreVideo -framework CoreAudio -framework AudioToolbox
                    continue ;;
            esac
        fi
        set -- "$@" "$flag"
    done < "$linkflags_file"
fi

clang "$llvm_output" "$@" -o "$program_output"

echo "Built tb program: $program_output"
echo "LLVM output: $llvm_output"
