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

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$script_dir
build_dir="$repo_root/.build"
verifier_source="$repo_root/compiler/tb/verify_fixtures_cli.tb"
cached_source="$build_dir/verify_fixtures_cli.tb"
verifier_binary="$build_dir/verify_fixtures_cli"

mkdir -p "$build_dir"
needs_build=0
if [ ! -x "$verifier_binary" ] || [ ! -f "$cached_source" ]; then
    needs_build=1
elif ! cmp -s "$verifier_source" "$cached_source"; then
    needs_build=1
elif [ "$repo_root/tb.sh" -nt "$verifier_binary" ] || [ "$repo_root/bin/tb" -nt "$verifier_binary" ]; then
    needs_build=1
elif find "$repo_root/compiler/tb" -type f -newer "$verifier_binary" -print | grep -q .; then
    needs_build=1
fi

if [ "$needs_build" -eq 1 ]; then
    cp "$verifier_source" "$cached_source"
    "$repo_root/tb.sh" "$cached_source"
fi

exec "$verifier_binary" "$@"
