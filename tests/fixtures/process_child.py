"""Portable child commands used by the numbered process fixtures."""

import os
import subprocess
import sys
import time


mode, *args = sys.argv[1:]
if mode == "print":
    sys.stdout.buffer.write(args[0].encode("ascii"))
elif mode == "copy":
    sys.stdout.buffer.write(sys.stdin.buffer.read())
elif mode == "first-byte":
    sys.stdout.buffer.write(sys.stdin.buffer.read(1))
elif mode == "streams":
    sys.stdout.buffer.write(sys.stdin.buffer.read())
    sys.stderr.buffer.write(b"err")
    sys.exit(7)
elif mode == "environment":
    # Python startup can coerce the locale, and Apple's python3 launcher
    # adds SDK search paths even when the supplied environment is empty.
    startup_variables = {"LC_CTYPE"}
    if sys.platform == "darwin":
        startup_variables.update(
            {"CPATH", "LIBRARY_PATH", "MANPATH", "SDKROOT", "__CF_USER_TEXT_ENCODING"}
        )
    for key, value in sorted(os.environ.items()):
        if key not in startup_variables:
            sys.stdout.buffer.write(f"{key}={value}\n".encode("utf-8"))
elif mode == "sleep":
    time.sleep(5)
elif mode == "timeout-code":
    sys.stdout.buffer.write(b"1" if os.name == "nt" else b"-9")
elif mode == "partial":
    sys.stdout.buffer.write(b"partial")
    sys.stdout.buffer.flush()
    time.sleep(5)
elif mode == "input-timeout":
    sys.stdin.buffer.read()
    sys.stdout.buffer.write(b"started")
    sys.stdout.buffer.flush()
    time.sleep(5)
elif mode == "held-pipes":
    subprocess.Popen([sys.executable, "-I", "-S", __file__, "sleep"],
                     stdout=sys.stdout, stderr=sys.stderr)
elif mode == "closed-pipes":
    # Replacing both descriptors closes the inherited capture handles.
    with open(os.devnull, "wb") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    time.sleep(5)
elif mode == "symlink":
    target, link, kind = args
    os.symlink(target, link, target_is_directory=kind == "directory")
elif mode == "null-device":
    sys.stdout.buffer.write(os.devnull.encode("ascii"))
elif mode == "redirect-stderr":
    with open("stderr-capture.txt", "wb") as destination:
        destination.write(b"prefix:")
        destination.flush()
        sys.exit(subprocess.call(args, stderr=destination))
elif mode == "closed-stderr":
    if os.name != "nt":
        os.close(2)
        os.execv(args[0], args)
    # Pass a read-only stderr handle so a write fails on Windows as well.
    with open("stderr-capture.txt", "rb") as unreadable_stderr:
        sys.exit(subprocess.call(args, stderr=unreadable_stderr))
else:
    raise SystemExit(f"unknown process fixture mode: {mode}")
