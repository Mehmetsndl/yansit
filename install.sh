#!/usr/bin/env bash
# Yansıt — Linux kurulum betiği (Fedora, Ubuntu/Debian, Arch)
#
#   ./install.sh            kur / güncelle
#   ./install.sh --kaldir   kaldır
#
# Hazır derlenmiş paketten (Yansit dosyası yanındaysa) veya kaynak koddan kurar.
# Hiçbir şeyi sistem geneline yazmaz; her şey kullanıcının ev klasörüne gider.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
ROOT="$DATA/yansit"
INST="$ROOT/app"
VENV="$ROOT/venv"
BIN="$HOME/.local/bin"
DESK="$DATA/applications"
ICONS="$DATA/icons/hicolor/256x256/apps"
PY="${PYTHON:-python3}"

renk() { printf '\033[1;35m==>\033[0m %s\n' "$*"; }
uyari() { printf '\033[1;33m!!\033[0m  %s\n' "$*"; }

if [[ "${1:-}" == "--kaldir" || "${1:-}" == "--uninstall" ]]; then
    rm -rf "$INST" "$VENV" "$BIN/yansit" "$DESK/yansit.desktop" "$ICONS/yansit.png"
    command -v update-desktop-database >/dev/null && update-desktop-database "$DESK" 2>/dev/null || true
    renk "Yansıt kaldırıldı."
    echo "    Ayarlar (~/.config/yansit) ve indirilen scrcpy ($ROOT/scrcpy) duruyor; istersen elle sil."
    exit 0
fi

paket_kur() {  # $1 = fedora paketi, $2 = debian paketi, $3 = arch paketi
    if command -v dnf >/dev/null; then sudo dnf install -y "$1"
    elif command -v apt-get >/dev/null; then sudo apt-get install -y "$2"
    elif command -v pacman >/dev/null; then sudo pacman -S --needed --noconfirm "$3"
    else uyari "Paket yöneticisi bulunamadı, '$1' paketini elle kurun."; return 1; fi
}

mkdir -p "$INST" "$BIN" "$DESK" "$ICONS"

if [[ -f "$SRC/Yansit" ]]; then
    renk "Hazır derlenmiş Yansıt kuruluyor..."
    install -m755 "$SRC/Yansit" "$INST/Yansit"
    EXEC="\"$INST/Yansit\""
else
    renk "Kaynak koddan kuruluyor..."
    command -v "$PY" >/dev/null || { uyari "python3 bulunamadı."; paket_kur python3 python3 python; }
    if ! "$PY" -c "import tkinter" 2>/dev/null; then
        renk "Tkinter eksik, kuruluyor (sudo şifresi istenebilir)..."
        paket_kur python3-tkinter python3-tk tk
    fi
    if ! "$PY" -c "import venv, ensurepip" 2>/dev/null; then
        paket_kur python3 python3-venv python
    fi
    install -m644 "$SRC/yansit.py" "$INST/yansit.py"
    mkdir -p "$INST/assets"
    install -m644 "$SRC/assets/yansit.png" "$INST/assets/yansit.png"
    renk "Python ortamı hazırlanıyor ($VENV)..."
    "$PY" -m venv "$VENV"
    "$VENV/bin/python" -m pip install --quiet --upgrade pip
    "$VENV/bin/python" -m pip install --quiet -r "$SRC/requirements.txt"
    EXEC="\"$VENV/bin/python\" \"$INST/yansit.py\""
fi

# Komut satırı başlatıcısı: yansit
cat > "$BIN/yansit" <<EOF
#!/bin/sh
exec $EXEC "\$@"
EOF
chmod +x "$BIN/yansit"

# Uygulama menüsü kaydı
install -m644 "$SRC/assets/yansit.png" "$ICONS/yansit.png"
cat > "$DESK/yansit.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Yansıt
GenericName=Telefon Ekran Yansıtma
Comment=Android telefon ekranını ve sesini bilgisayara yansıt
Exec=$BIN/yansit
Icon=yansit
Terminal=false
Categories=Utility;AudioVideo;
Keywords=android;scrcpy;ekran;yansıtma;mirror;obs;telefon;
StartupWMClass=Yansit
EOF
command -v update-desktop-database >/dev/null && update-desktop-database "$DESK" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "$DATA/icons/hicolor" 2>/dev/null || true

# USB için öneri (udev kuralları android-tools paketiyle gelir)
if ! command -v adb >/dev/null; then
    echo
    uyari "USB ile bağlanacaksan önerilir:"
    if command -v dnf >/dev/null; then echo "    sudo dnf install android-tools"
    elif command -v apt-get >/dev/null; then echo "    sudo apt install android-sdk-platform-tools-common"
    else echo "    android-tools / android-udev paketini kurun"; fi
fi

echo
renk "Kurulum tamam! Uygulama menüsünden 'Yansıt'ı aç ya da terminalde: yansit"
case ":$PATH:" in *":$BIN:"*) ;; *) uyari "$BIN PATH'te değil; menüden açabilir ya da tam yolu kullanabilirsin.";; esac
