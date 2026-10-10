#!/bin/sh

set -eu

usage() {
    echo "Usage: ./bundle_release.sh VERSION [OUTPUT_DIR]" >&2
    exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
version=$1
output_dir=${2:-.build/releases}

case "$version" in
    *[!0-9A-Za-z.-]*|.*|-*|*.)
        echo "Invalid version: $version" >&2
        exit 2
        ;;
esac
printf '%s\n' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?$' || {
    echo "Invalid version: $version" >&2
    exit 2
}

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd "$script_dir" && pwd)
os=$(uname -s)
arch=$(uname -m)
if [ "$os" != "Darwin" ]; then
    echo "Release bundles currently require macOS (Darwin)" >&2
    exit 1
fi
case "$arch" in
    arm64|x86_64) ;;
    *)
        echo "Unsupported host architecture: $arch" >&2
        exit 1
        ;;
esac

compiler="$repo_root/bin/tb"
if [ ! -x "$compiler" ]; then
    echo "Missing executable self-hosted compiler: $compiler" >&2
    echo "Build it first with: ./build_tb.sh" >&2
    exit 1
fi
if ! lipo -verify_arch "$arch" "$compiler" >/dev/null 2>&1; then
    echo "Compiler does not contain host architecture $arch: $compiler" >&2
    exit 1
fi

case "$output_dir" in
    /*) ;;
    *) output_dir="$PWD/$output_dir" ;;
esac
mkdir -p "$output_dir"
archive_name="tb-$version-macos-$arch.zip"
checksum_name="$archive_name.sha256"
archive_path="$output_dir/$archive_name"
checksum_path="$output_dir/$checksum_name"
if [ -e "$archive_path" ] || [ -e "$checksum_path" ]; then
    echo "Refusing to overwrite release artifact: $archive_path or $checksum_path" >&2
    exit 1
fi

resources_file="$repo_root/release/resources.txt"
if [ ! -f "$resources_file" ]; then
    echo "Missing release resource list: $resources_file" >&2
    exit 1
fi
while IFS= read -r resource || [ -n "$resource" ]; do
    [ -n "$resource" ] || continue
    case "$resource" in
        /*|../*|*/../*|*/..) echo "Invalid release resource path: $resource" >&2; exit 1 ;;
    esac
    if [ ! -f "$repo_root/compiler/tb/$resource" ]; then
        echo "Missing release asset: compiler/tb/$resource" >&2
        exit 1
    fi
done < "$resources_file"

stage_dir=$(mktemp -d "$output_dir/.tb-release.XXXXXX")
published_archive=0
cleanup() {
    if [ "$published_archive" -eq 1 ]; then
        rm -f "$archive_path"
    fi
    rm -rf "$stage_dir"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

bundle_dir="$stage_dir/tb-$version-macos-$arch"
mkdir -p "$bundle_dir/compiler/tb" "$bundle_dir/libexec" "$bundle_dir/docs"
cp "$compiler" "$bundle_dir/libexec/tb"
cp "$resources_file" "$bundle_dir/compiler/tb/resources.txt"
while IFS= read -r resource || [ -n "$resource" ]; do
    [ -n "$resource" ] || continue
    target_dir="$bundle_dir/compiler/tb/$(dirname "$resource")"
    mkdir -p "$target_dir"
    cp "$repo_root/compiler/tb/$resource" "$target_dir/$(basename "$resource")"
done < "$resources_file"
cp "$repo_root/release/tb" "$bundle_dir/tb"
cp "$repo_root/release/tb-build" "$bundle_dir/tb-build"
cp "$repo_root/release/README.md" "$bundle_dir/README.md"
cp "$repo_root/docs/tb.md" "$bundle_dir/docs/tb.md"
cp "$repo_root/CHANGELOG.md" "$bundle_dir/CHANGELOG.md"
cp "$repo_root/LICENSE" "$bundle_dir/LICENSE"
printf '%s\n' "$version" > "$bundle_dir/VERSION"
chmod +x "$bundle_dir/tb" "$bundle_dir/tb-build" "$bundle_dir/libexec/tb"

(cd "$stage_dir" && ditto -c -k --keepParent --norsrc --noextattr "tb-$version-macos-$arch" "$archive_name")
(cd "$stage_dir" && shasum -a 256 "$archive_name" > "$checksum_name")
mv "$stage_dir/$archive_name" "$archive_path"
published_archive=1
mv "$stage_dir/$checksum_name" "$checksum_path"
published_archive=0
echo "Created $archive_path"
echo "Created $checksum_path"
