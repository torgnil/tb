#!/usr/bin/env bash

set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
program_dir="$script_dir/programs"
python_dir="$script_dir/python"
c_dir="$script_dir/c"
build_dir="$repo_root/.build/benchmarks"
compiler="$repo_root/bin/tb"
python3_bin=$(command -v python3 || true)
runs=5
filter=""
date_supports_nanoseconds=0
result_best=""
result_avg=""
result_status=""

usage() {
    cat <<EOF
Usage: ./benchmarks/run.sh [options]

Options:
  --compiler PATH  tb compiler to use (default: bin/tb)
  --filter TEXT    run only benchmarks whose file name contains TEXT
  --runs N         executable runs per benchmark (default: 5)
  --skip-python    run only tb benchmarks
  -h, --help       show this help
EOF
}

include_python=1
while [ "$#" -gt 0 ]; do
    case "$1" in
        --compiler)
            compiler="$2"
            shift 2
            ;;
        --filter)
            filter="$2"
            shift 2
            ;;
        --runs)
            runs="$2"
            shift 2
            ;;
        --skip-python)
            include_python=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

case "$compiler" in
    /*) ;;
    *) compiler="$repo_root/$compiler" ;;
esac

if [ ! -x "$compiler" ]; then
    echo "Missing executable compiler: $compiler" >&2
    exit 1
fi

if ! command -v clang >/dev/null 2>&1; then
    echo "Missing clang" >&2
    exit 1
fi

case "$runs" in
    ''|*[!0-9]*)
        echo "--runs must be a positive integer" >&2
        exit 1
        ;;
esac

if [ "$runs" -lt 1 ]; then
    echo "--runs must be at least 1" >&2
    exit 1
fi

date_probe=$(date +%s%N 2>/dev/null || true)
case "$date_probe" in
    *N) date_supports_nanoseconds=0 ;;
    *) date_supports_nanoseconds=1 ;;
esac

if [ "$date_supports_nanoseconds" -eq 0 ] && ! command -v perl >/dev/null 2>&1; then
    echo "Missing high-resolution timer: need date +%s%N support or perl" >&2
    exit 1
fi

now_us() {
    if [ "$date_supports_nanoseconds" -eq 1 ]; then
        value=$(date +%s%N)
        printf "%s" "${value%???}"
    else
        perl -MTime::HiRes=time -e 'printf "%.0f", time() * 1000000'
    fi
}

run_target() {
    local output_file="$1"
    local error_file="$2"
    local expected_file="$3"
    shift 3

    local best=""
    local total="0"
    local run_index
    local start_us
    local end_us
    local run_status
    local elapsed_ms

    : > "$error_file"

    if ! "$@" > "$output_file" 2> "$error_file"; then
        result_status="fail"
        result_best="-"
        result_avg="-"
        return 1
    fi

    if [ -f "$expected_file" ] && ! diff -u "$expected_file" "$output_file" >/dev/null; then
        result_status="fail"
        result_best="-"
        result_avg="-"
        return 1
    fi

    run_index=1
    while [ "$run_index" -le "$runs" ]; do
        start_us=$(now_us)
        if "$@" > "$output_file" 2> "$error_file"; then
            run_status=0
        else
            run_status=$?
        fi
        end_us=$(now_us)

        if [ "$run_status" -ne 0 ]; then
            result_status="fail"
            result_best="-"
            result_avg="-"
            return 1
        fi

        if [ -f "$expected_file" ] && ! diff -u "$expected_file" "$output_file" >/dev/null; then
            result_status="fail"
            result_best="-"
            result_avg="-"
            return 1
        fi

        elapsed_ms=$(awk -v start="$start_us" -v end="$end_us" 'BEGIN { printf "%.3f", (end - start) / 1000 }')
        total=$(awk -v left="$total" -v right="$elapsed_ms" 'BEGIN { printf "%.3f", left + right }')
        if [ -z "$best" ]; then
            best="$elapsed_ms"
        else
            best=$(awk -v left="$best" -v right="$elapsed_ms" 'BEGIN { if (right < left) print right; else print left }')
        fi
        run_index=$((run_index + 1))
    done

    result_status="ok"
    result_best="$best"
    result_avg=$(awk -v total="$total" -v runs="$runs" 'BEGIN { printf "%.3f", total / runs }')
}

mkdir -p "$build_dir"

benchmarks=()
for source in "$program_dir"/*.tb; do
    name=$(basename "$source" .tb)
    if [ -n "$filter" ] && [[ "$name" != *"$filter"* ]]; then
        continue
    fi
    benchmarks+=("$source")
done

if [ "${#benchmarks[@]}" -eq 0 ]; then
    echo "No benchmarks matched filter: $filter" >&2
    exit 1
fi

if [ "$include_python" -eq 1 ]; then
    if [ -z "$python3_bin" ]; then
        echo "Missing python3" >&2
        exit 1
    fi
fi

printf "%-20s %5s %10s %10s %10s %10s %10s %10s %10s %10s %8s\n" \
    "benchmark" "runs" "tb_best" "tb_avg" "c_best" "c_avg" "tb/c" "py3_best" "py3_avg" "tb/py3" "status"
echo "Warmup: 1 unreported run before timing" >&2

index=1
total_benchmarks=${#benchmarks[@]}
for source in "${benchmarks[@]}"; do
    name=$(basename "$source" .tb)
    echo "[$index/$total_benchmarks] building and running $name" >&2

    llvm_output="$build_dir/$name.ll"
    executable="$build_dir/$name"
    expected_file="$program_dir/$name.out"
    tb_output_file="$build_dir/$name.tb.out"
    tb_error_file="$build_dir/$name.tb.err"
    c_output_file="$build_dir/$name.c.out"
    c_error_file="$build_dir/$name.c.err"
    py_output_file="$build_dir/$name.py.out"
    py_error_file="$build_dir/$name.py.err"
    c_source="$c_dir/$name.c"
    c_executable="$build_dir/$name.c.bin"
    python_source="$python_dir/$name.py"

    if [ "$include_python" -eq 1 ] && [ ! -f "$python_source" ]; then
        echo "Missing python benchmark: $python_source" >&2
        exit 1
    fi

    if ! (
        cd "$repo_root"
        "$compiler" "$source" "$llvm_output" >/dev/null
    ); then
        echo "Compile failed for $name" >&2
        exit 1
    fi

    if ! clang -Wno-override-module "$llvm_output" -o "$executable"; then
        echo "Link failed for $name" >&2
        exit 1
    fi

    if ! run_target "$tb_output_file" "$tb_error_file" "$expected_file" "$executable"; then
        echo "tb run failed for $name" >&2
        exit 1
    fi
    tb_best="$result_best"
    tb_avg="$result_avg"
    status="ok"

    if [ -f "$c_source" ]; then
        if ! clang -O3 -DNDEBUG "$c_source" -o "$c_executable"; then
            echo "C compile failed for $name" >&2
            exit 1
        fi
        if ! run_target "$c_output_file" "$c_error_file" "$expected_file" "$c_executable"; then
            echo "C run failed for $name" >&2
            exit 1
        fi
        c_best="$result_best"
        c_avg="$result_avg"
        tb_vs_c=$(awk -v tb="$tb_avg" -v c="$c_avg" 'BEGIN { printf "%.2fx", tb / c }')
    else
        c_best="-"
        c_avg="-"
        tb_vs_c="-"
    fi

    if [ "$include_python" -eq 1 ]; then
        if ! run_target "$py_output_file" "$py_error_file" "$expected_file" "$python3_bin" "$python_source"; then
            echo "python3 run failed for $name" >&2
            exit 1
        fi
        py3_best="$result_best"
        py3_avg="$result_avg"
        tb_vs_py3=$(awk -v tb="$tb_avg" -v py="$py3_avg" 'BEGIN { printf "%.2fx", tb / py }')
    else
        py3_best="-"
        py3_avg="-"
        tb_vs_py3="-"
    fi

    printf "%-20s %5s %10s %10s %10s %10s %10s %10s %10s %10s %8s\n" \
        "$name" "$runs" "$tb_best" "$tb_avg" "$c_best" "$c_avg" "$tb_vs_c" "$py3_best" "$py3_avg" "$tb_vs_py3" "$status"
    index=$((index + 1))
done
