#!/bin/sh
# Discover WSL interop socket path (dynamic per WSL session) and export it.
# This is required because the gateway must launch cmd.exe (Windows) via WSL interop.

for sock in /run/WSL/*_interop; do
  if [ -S "$sock" ]; then
    export WSL_INTEROP="$sock"
    break
  fi
done

# Add Windows System32 to PATH so cmd.exe is findable by subprocess.Popen
export PATH="/mnt/c/Windows/System32:$PATH"

exec python3 /gateway.py "$@"
