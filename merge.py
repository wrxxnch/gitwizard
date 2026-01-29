#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
import urllib.request
from hashlib import sha256

# ================= CONFIG =================

SCRIPT_REMOTE_RAW = "https://raw.githubusercontent.com/wrxxnch/gitwizard/main/merge.py"
CONFIG_FILE = ".gitwizard.json"
TMP_DIR = ".merge_wizard_tmp"
LOG_FILE = "merge_report.txt"

# ================= UTILS =================

def normalize(p):
    return os.path.abspath(os.path.expanduser(p))

def menu(title, options):
    print("\n" + title)
    for i, o in enumerate(options, 1):
        print(f"{i}) {o}")
    print("0) ❌ Sair")
    while True:
        try:
            c = int(input("> "))
            if 0 <= c <= len(options):
                return c
        except:
            pass
        print("❌ Opção inválida")

def ask(msg, default=None):
    if default is not None:
        v = input(f"{msg} [{default}]: ").strip()
        return v if v else default
    return input(f"{msg}: ").strip()

def sha(data):
    return sha256(data).hexdigest()

def progress(cur, total, text):
    pct = int((cur / total) * 100)
    bar = "█" * (pct // 4) + "-" * (25 - pct // 4)
    print(f"\r[{bar}] {pct:3d}% | {text[:60]:60}", end="", flush=True)

# ================= UPDATE =================

def check_update():
    try:
        with urllib.request.urlopen(SCRIPT_REMOTE_RAW, timeout=8) as r:
            remote = r.read()
        with open(sys.argv[0], "rb") as f:
            local = f.read()
        if sha(remote) != sha(local):
            return remote
    except:
        pass
    return None

def apply_update(data):
    with open(sys.argv[0], "wb") as f:
        f.write(data)
    print("\n✅ Script atualizado. Reiniciando...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# ================= GIT =================

def git(cmd, cwd=None):
    subprocess.check_call(["git"] + cmd, cwd=cwd)

def clone_repo(url, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    git(["clone", url, dest])

def checkout(repo, ref):
    if ref:
        git(["checkout", ref], cwd=repo)

# ================= SOURCE =================

def get_source(label, cfg):
    print(f"\n📌 Selecionar {label}")

    t = menu(f"Tipo de {label}", ["Caminho local", "URL Git"])

    if t == 0:
        sys.exit(0)

    if t == 1:
        p = normalize(ask("Digite o caminho local", cfg.get(f"{label}_path")))
        if not os.path.isdir(p):
            print("❌ Caminho inválido:", p)
            sys.exit(1)
        return {"type": "local", "path": p}

    url = ask("URL do repositório", cfg.get(f"{label}_url"))
    ref = ask("Branch/tag/commit (opcional)", cfg.get(f"{label}_ref", ""))

    os.makedirs(TMP_DIR, exist_ok=True)
    dest = os.path.join(TMP_DIR, label.lower())

    print("🌐 Clonando:", url)
    clone_repo(url, dest)

    try:
        checkout(dest, ref)
    except:
        print("❌ Referência inválida:", ref)
        sys.exit(1)

    return {"type": "git", "url": url, "ref": ref, "path": dest}

# ================= MERGE =================

def read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except:
        return b""

def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

def collect_files(root):
    files = {}
    for r, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(r, f)
            files[os.path.relpath(p, root)] = p
    return files

def merge(base, src):
    base_files = collect_files(base)
    src_files = collect_files(src)

    added = []
    modified = []
    removed = []
    conflicts = []

    all_keys = sorted(set(base_files) | set(src_files))
    total = len(all_keys)

    for i, rel in enumerate(all_keys, 1):
        progress(i, total, rel)

        b = base_files.get(rel)
        s = src_files.get(rel)
        dst = os.path.join(base, rel)

        if s and not b:
            write(dst, read(s))
            added.append(rel)

        elif b and not s:
            removed.append(rel)

        elif b and s:
            bd = read(b)
            sd = read(s)
            if bd == sd:
                continue

            if b.endswith(".lua") or b.endswith(".txt"):
                merged = (
                    b"-- >>>>>>>>>> BASE\n" + bd +
                    b"\n-- ========= ORIGEM =========\n" + sd +
                    b"\n-- <<<<<<<<<< FIM\n"
                )
                write(dst, merged)
                conflicts.append(rel)
            else:
                write(dst, sd)
                modified.append(rel)

    print("\n")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== MERGE REPORT ===\n\n")

        def section(title, data):
            f.write(f"{title} ({len(data)}):\n")
            for x in data:
                f.write(f"  - {x}\n")
            f.write("\n")

        section("ADICIONADOS", added)
        section("MODIFICADOS", modified)
        section("REMOVIDOS", removed)
        section("CONFLITOS", conflicts)

    print("📄 Relatório salvo em", LOG_FILE)

# ================= WIZARD =================

def wizard(cfg):
    base = get_source("BASE", cfg)
    src = get_source("ORIGEM", cfg)

    print("\n🔀 Iniciando merge...")
    merge(base["path"], src["path"])
    print("✅ Merge concluído")

    cfg.update({
        "BASE_path": base["path"],
        "ORIGEM_path": src["path"],
        "ORIGEM_url": src.get("url"),
        "ORIGEM_ref": src.get("ref"),
    })

    return cfg

# ================= MAIN =================

def main():
    up = check_update()
    if up:
        c = menu(
            "Atualização disponível",
            ["Continuar", "Atualizar agora"]
        )
        if c == 2:
            apply_update(up)

    cfg = {}
    if os.path.exists(CONFIG_FILE):
        cfg = json.load(open(CONFIG_FILE))
        c = menu(
            "Configuração encontrada",
            ["Usar anterior (editar)", "Novo merge"]
        )
        cfg = wizard(cfg if c == 1 else {})
    else:
        cfg = wizard({})

    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

if __name__ == "__main__":
    main()
