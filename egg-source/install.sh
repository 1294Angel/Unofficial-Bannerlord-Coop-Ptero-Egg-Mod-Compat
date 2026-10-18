#!/bin/bash
set -e
cd /mnt/server

echo "Installing SteamCMD..."
mkdir -p steamcmd
curl -fsSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar -xz -C steamcmd

echo "Installing the egg's start-up programs into coop-egg/..."
rm -rf coop-egg
mkdir -p coop-egg
base64 -d <<'PAYLOAD' | tar -xz -C coop-egg
@@PAYLOAD@@
PAYLOAD

mkdir -p logs addons
echo "Done. Start the server to download Coop (about 6 GB)."
