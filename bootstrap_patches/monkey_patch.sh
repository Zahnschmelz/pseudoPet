#!/usr/bin/env bash
# ============================================================
# PseudoPet Bootstrap-Patch (Notification-Receiver)
# Spielt Java-Datei + Receiver-Zeile in die von buildozer
# benutzte p4a-Kopie (Clone) ein - plus venv (zur Sicherheit).
#
# Aufruf:
#   ./bootstrap_patches/apply_patches.sh           # nur patchen (idempotent)
#   ./bootstrap_patches/apply_patches.sh --clean   # patchen + Build-Caches loeschen
#
# Neu ausfuehren nach: p4a-Update (git pull im Clone),
# geloeschtem .buildozer, venv-Neuaufbau - oder wenn
# Notifications nach einem Build "verschwunden" sind.
#
# Hinweis: Der Clone ist ein Git-Repo. Falls buildozer wegen
# der lokalen Aenderung git-Fehler wirft:
#   git -C .buildozer/android/platform/python-for-android \
#       checkout -- pythonforandroid/bootstraps
# ...und danach das Script erneut laufen lassen (mit --clean).
# ============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RECEIVER_XML='<receiver android:name="org.beezi.pseudopet.PetAlarmReceiver" android:exported="false"/>'

P4A_CLONE="$PROJECT_DIR/.buildozer/android/platform/python-for-android/pythonforandroid"
VENV_P4A="$PROJECT_DIR/venv/lib/python3.10/site-packages/pythonforandroid"
JAVA_SRC="$PROJECT_DIR/src/org/beezi/pseudopet/PetAlarmReceiver.java"

DO_CLEAN=0
if [ "${1:-}" = "--clean" ]; then DO_CLEAN=1; fi

info() { echo "[patch] $*"; }
fail() { echo "[patch] FEHLER: $*" >&2; exit 1; }

[ -f "$JAVA_SRC" ] || fail "Quelle fehlt: $JAVA_SRC"

# --- Java-Datei in einen p4a-Bootstrap kopieren -----------------
patch_java() {
    local p4a_dir="$1" label="$2"
    local target="$p4a_dir/bootstraps/sdl2/build/src/main/java/org/beezi/pseudopet"
    if [ ! -d "$p4a_dir/bootstraps/sdl2" ]; then
        info "$label: Bootstrap nicht vorhanden - uebersprungen"
        return 0
    fi
    mkdir -p "$target"
    cp "$JAVA_SRC" "$target/PetAlarmReceiver.java"
    info "$label: PetAlarmReceiver.java kopiert"
}

# --- Receiver ins Manifest-Template einfuegen (idempotent) ------
# benoetigt GNU sed (Arch: ok)
patch_manifest() {
    local tmpl="$1" label="$2"
    if [ ! -f "$tmpl" ]; then
        info "$label: Template fehlt - uebersprungen"
        return 0
    fi
    if grep -q "PetAlarmReceiver" "$tmpl"; then
        info "$label: Receiver bereits drin (ok)"
        return 0
    fi
    sed -i "s|</application>|    $RECEIVER_XML\n    </application>|" "$tmpl"
    grep -q "PetAlarmReceiver" "$tmpl" || fail "$label: Einfuegen fehlgeschlagen"
    info "$label: Receiver vor </application> eingefuegt"
}

info "Projekt: $PROJECT_DIR"

# 1) Clone - DIE relevante Kopie:
[ -d "$P4A_CLONE" ] || fail "p4a-Clone fehlt: $P4A_CLONE (erst buildozer einmal laufen lassen)"
patch_java     "$P4A_CLONE" "clone"
patch_manifest "$P4A_CLONE/bootstraps/_sdl_common/build/templates/AndroidManifest.tmpl.xml" "clone"

# 2) venv - wird normalerweise ueberdeckt, schadet aber nicht:
if [ -d "$VENV_P4A" ]; then
    patch_java     "$VENV_P4A" "venv"
    patch_manifest "$VENV_P4A/bootstraps/_sdl_common/build/templates/AndroidManifest.tmpl.xml" "venv"
fi

# 3) Optional: Caches entsorgen, damit der naechste Build uebernimmt:
if [ "$DO_CLEAN" = "1" ]; then
    for bd in "$PROJECT_DIR"/.buildozer/android/platform/build-*; do
        [ -d "$bd" ] || continue
        rm -rf "$bd/build/bootstrap_builds" "$bd/dists"
        info "Caches geloescht: $(basename "$bd")"
    done
fi

# --- Verification ---
echo
info "Ergebnis:"
grep -n "PetAlarmReceiver" \
    "$P4A_CLONE/bootstraps/_sdl_common/build/templates/AndroidManifest.tmpl.xml" | sed 's/^/    /'
ls -1 "$P4A_CLONE/bootstraps/sdl2/build/src/main/java/org/beezi/pseudopet/" | sed 's/^/    /'

if [ "$DO_CLEAN" != "1" ]; then
    echo
    info "Damit der naechste Build die Patches uebernimmt:"
    echo "    $0 --clean"
    echo "    buildozer -v android debug"
fi
