#!/usr/bin/env bash

set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir" && pwd)
source_file="$repo_root/compiler/tb/tb.tb"
build_root="$repo_root/.build/stage2"
stage1_ll="$build_root/tb_stage1.ll"
stage1_bin="$build_root/tb_stage1"
stage2_ll="$build_root/tb_stage2.ll"
output_dir="$repo_root/bin"
output_bin="$output_dir/tb"

mkdir -p "$build_root" "$output_dir"

echo "[1/4] build stage1 llvm"
(
  cd "$repo_root"
  python3 compiler/python/tb.py "$source_file" "$stage1_ll"
)

echo "[2/4] link stage1 compiler"
clang -O2 "$stage1_ll" -o "$stage1_bin"

echo "[3/4] build stage2 llvm"
"$stage1_bin" "$source_file" "$stage2_ll"

echo "[4/4] link self-hosted compiler"
clang -O2 "$stage2_ll" -o "$output_bin"

echo "Built self-hosted tb compiler: $output_bin"
echo "Temporary build files: $build_root"
