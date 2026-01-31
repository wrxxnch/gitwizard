#!/usr/bin/env bash

CONFIG_FILE=".merge_wizard.conf"

ask() {
  local prompt="$1"
  local default="$2"

  if [ -n "$default" ]; then
    read -rp "$prompt [$default]: " value
    echo "${value:-$default}"
  else
    read -rp "$prompt: " value
    echo "$value"
  fi
}

load_config() {
  [ -f "$CONFIG_FILE" ] && source "$CONFIG_FILE"
}

save_config() {
  cat > "$CONFIG_FILE" <<EOF
BASE_SRC="$BASE_SRC"
INCOMING_SRC="$INCOMING_SRC"
OUT_DIR="$OUT_DIR"
EOF
}

clone_if_needed() {
  local src="$1"
  local dir="$2"

  if [[ "$src" =~ ^https?:// ]]; then
    git clone "$src" "$dir"
  else
    cp -r "$src" "$dir"
  fi
}

echo "🧙 MERGE CHERRYPICK WIZARD v1.0"
echo "==================="

load_config

KEEP=$(ask "Manter configurações anteriores? (s/n)" "s")

if [[ "$KEEP" != "s" ]]; then
  BASE_SRC=""
  INCOMING_SRC=""
  OUT_DIR=""
fi

BASE_SRC=$(ask "BASE (path local ou URL git)" "$BASE_SRC")
INCOMING_SRC=$(ask "INCOMING (path local ou URL git)" "$INCOMING_SRC")
OUT_DIR=$(ask "Diretório de saída" "${OUT_DIR:-merge_output}")

save_config

WORKDIR=$(mktemp -d)
BASE_DIR="$WORKDIR/base"
INCOMING_DIR="$WORKDIR/incoming"

echo "📥 Preparando BASE..."
clone_if_needed "$BASE_SRC" "$BASE_DIR"

echo "📥 Preparando INCOMING..."
clone_if_needed "$INCOMING_SRC" "$INCOMING_DIR"

mkdir -p "$OUT_DIR"
mkdir -p "$OUT_DIR/patches_aplicados"
mkdir -p "$OUT_DIR/arquivos_novos"
mkdir -p "$OUT_DIR/rejeitados"

cd "$INCOMING_DIR" || exit 1

echo "🔍 Gerando diff..."
git diff --binary "$BASE_DIR" > "$WORKDIR/merge.diff"

echo "🧩 Aplicando diff (sem sobrescrever)..."
git apply \
  --directory="$OUT_DIR" \
  --reject \
  "$WORKDIR/merge.diff" \
  2>>"$OUT_DIR/merge.log"

echo "📂 Copiando arquivos novos..."
git diff --name-status "$BASE_DIR" | awk '$1=="A"{print $2}' | while read -r file; do
  mkdir -p "$OUT_DIR/arquivos_novos/$(dirname "$file")"
  cp "$file" "$OUT_DIR/arquivos_novos/$file"
done

echo "⚠️ Rejeições (.rej):"
find "$OUT_DIR" -name "*.rej" -exec mv {} "$OUT_DIR/rejeitados/" \;

echo "✅ MERGE FINALIZADO"
echo "📁 Resultado em: $OUT_DIR"
