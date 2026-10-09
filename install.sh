#!/bin/sh
# job-search-os installer for macOS and Linux. Paste this into Terminal:
#   curl -fsSL https://raw.githubusercontent.com/JacksonBopp/job-search-os/main/install.sh | sh
#
# It puts job-search-os in its own folder (~/job-search-os), adds a "Job Search" icon to
# your Desktop on a Mac, and starts it. Run it again any time to update. No sudo needed.
set -e
DIR="${JOBOS_INSTALL_DIR:-$HOME/job-search-os}"
SRC="${JOBOS_SOURCE:-https://github.com/JacksonBopp/job-search-os/archive/refs/heads/main.zip}"

echo "Installing job-search-os..."
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 or newer is needed. Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

mkdir -p "$DIR"
[ -x "$DIR/.venv/bin/python" ] || "$PY" -m venv "$DIR/.venv"
"$DIR/.venv/bin/python" -m pip install --upgrade --quiet --disable-pip-version-check "$SRC"

if [ "$(uname)" = "Darwin" ] && [ -d "$HOME/Desktop" ] && [ -z "$JOBOS_NO_SHORTCUT" ]; then
  cat > "$HOME/Desktop/Job Search.command" <<EOF
#!/bin/sh
cd "$DIR" && exec "$DIR/.venv/bin/python" -m jobos
EOF
  chmod +x "$HOME/Desktop/Job Search.command"
  echo "Added a 'Job Search' icon to your Desktop (double-click it)."
fi

echo "Done! Your job list lives in $DIR"
if [ -z "$JOBOS_NO_LAUNCH" ]; then
  cd "$DIR"
  exec "$DIR/.venv/bin/python" -m jobos </dev/tty    # stdin is the download pipe; talk to the keyboard
fi
