# raylib-tb

This folder contains the bundled `raylib` binding for tb and a small demo program.

Upstream library: [raylib](https://github.com/raysan5/raylib)

Contents:
- `raylib-tb-demo.tb` - demo program using `import raylib;`
- `raylib_tb.c` - thin C wrapper compiled as part of the build
- `assets/` - textures and sounds used by the demo

## Requirements

You need a local `raylib` installation.

On macOS with Homebrew:

```bash
brew install raylib
```

By default the binding probes these Homebrew-style roots:

```text
/opt/homebrew/opt/raylib
/usr/local/opt/raylib
```

You can override that with:

```bash
export TB_RAYLIB_ROOT=/path/to/raylib
```

## Build the demo

From the repository root:

```bash
./build_tb.sh
./tb.sh bindings/tb/raylib-tb/raylib-tb-demo.tb
```

This will:
- compile the demo with the self-hosted tb compiler
- emit LLVM under `.build/`
- compile `raylib_tb.c` automatically
- link the final binary with the required `raylib` flags

The output binary is written next to the source as:

```text
./bindings/tb/raylib-tb/raylib-tb-demo
```

Run it with:

```bash
./bindings/tb/raylib-tb/raylib-tb-demo
```

## Notes

The current bundled `raylib` support is intended for the shipped demo path and current supported API slice. It is not a general-purpose FFI layer.
