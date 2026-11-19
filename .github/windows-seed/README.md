# tb for Windows x64

Extract the ZIP and run `tb.exe --version` from PowerShell. The compiler
emits LLVM IR and build metadata. This bundle also includes `tb.ps1` to
compile, adapt, and link a native Windows program.

Install Clang and Python from MSYS2 CLANG64 and add its `bin` directory
to your PowerShell PATH. Run the launcher from the directory you want
to use for relative paths.

```powershell
& 'C:\path\to\tb\tb.ps1' .\hello.tb -OutputPath .\hello.exe
.\hello.exe
```

With no output path, the launcher writes an `.exe` next to the source.
The language reference is in `tb.md`.
