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

# ================= UTILS =================

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def pause():
    input("\nENTER para continuar...")

def sha(data):
    return sha256(data).hexdigest()

def menu(title, options):
    print("\n" + title)
    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")
    print("0) ❌ Sair")

    while True:
        try:
            c = int(input("> "))
            if 0 <= c <= len(options):
                return c
        except:
            pass

def ask(msg, default=None):
    if default:
        v = input(f"{msg} [{default}]: ").strip()
        return v if v else default
    return input(f"{msg}: ").strip()

# ================= UPDATE =================

def check_update(force=False):
    try:
        with urllib.request.urlopen(SCRIPT_REMOTE_RAW, timeout=8) as r:
            remote = r.read()
        with open(sys.argv[0], "rb") as f:
            local = f.read()

        if sha(remote) == sha(local):
            if force:
                print("✔ Script já está atualizado")
            return False, None

        return True, remote
    except:
        if force:
            print("⚠ Não foi possível verificar atualização")
        return False, None

def apply_update(remote):
    with open(sys.argv[0], "wb") as f:
        f.write(remote)
    print("✅ Script atualizado. Reiniciando...")
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

# ================= SOURCES =================

def get_source(label, cfg=None):
    print(f"\n📌 Selecionar {label}")

    t = menu(
        f"Tipo de {label}",
        ["Caminho local", "URL Git (GitHub / Codeberg)"]
    )

    if t == 0:
        sys.exit(0)

    if t == 1:
        path = ask("Digite o caminho local", cfg.get(f"{label}_path") if cfg else None)
        return {"type": "local", "path": path}

    url = ask("Digite a URL do repositório git", cfg.get(f"{label}_url") if cfg else None)
    ref = ask("Branch / tag / commit (opcional)", cfg.get(f"{label}_ref") if cfg else "")

    dest = os.path.join(TMP_DIR, label.lower())
    print(f"🌐 Clonando {url}")
    clone_repo(url, dest)
    checkout(dest, ref)

    return {"type": "git", "url": url, "ref": ref, "path": dest}

# ================= MERGE =================

def merge_dirs(base, src):
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = os.path.join(base, rel)
        os.makedirs(target, exist_ok=True)

        for f in files:
            sp = os.path.join(root, f)
            tp = os.path.join(target, f)

            if not os.path.exists(tp):
                shutil.copy2(sp, tp)

# ================= WIZARD =================

def wizard(cfg):
    base = get_source("BASE", cfg)
    src  = get_source("ORIGEM", cfg)

    cfg.update({
        "BASE_type": base["type"],
        "BASE_path": base["path"],
        "ORIGEM_type": src["type"],
        "ORIGEM_path": src["path"],
        "ORIGEM_url": src.get("url"),
        "ORIGEM_ref": src.get("ref"),
    })

    print("\n🔀 Mesclando arquivos...")
    merge_dirs(base["path"], src["path"])
    print("✅ Merge concluído")

    return cfg

# ================= MAIN =================

def main():
    clear()

    has_update, remote = check_update(False)
    if has_update:
        print("🔔 Atualização disponível (use a opção no menu)")

    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)

        c = menu(
            "Configuração anterior encontrada",
            [
                "Usar opções anteriores (editar uma a uma)",
                "Novo merge do zero",
                "🔄 Atualizar script agora"
            ]
        )

        if c == 0:
            return

        if c == 3:
            u, r = check_update(True)
            if u:
                apply_update(r)
            pause()
            return

        if c == 1:
            cfg = wizard(cfg)
        else:
            cfg = wizard({})

    else:
        cfg = wizard({})

    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

    pause()

# ================= START =================

if __name__ == "__main__":
    main()
