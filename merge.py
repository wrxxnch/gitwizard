#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
import re
import urllib.request

# ================= CONFIG =================

TMP_ROOT = ".merge_wizard_tmp"
CFG_FILE = ".merge_wizard.json"

SCRIPT_REPO_RAW = "https://raw.githubusercontent.com/wrxxnch/gitwizard/main/merge.py"
SCRIPT_VERSION = "2.3"

# ================= UI =================

def banner():
    print(f"""
========================================
🧙 MERGE WIZARD v{SCRIPT_VERSION}
========================================
* Local / GitHub / Codeberg
* Branch / Tag / Branch vs Branch
* Config persistente
* Auto-update
""")

def menu(title, options, allow_exit=True):
    print("\n" + title)

    if allow_exit:
        print("0) ❌ Sair")

    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")

    lookup = {opt.lower(): i for i, opt in enumerate(options, 1)}

    while True:
        c = input("> ").strip().lower()

        if allow_exit and c in ("0", "sair", "exit", "q", "quit"):
            sys.exit(0)

        if c.isdigit():
            n = int(c)
            if 1 <= n <= len(options):
                return n
        else:
            for k, v in lookup.items():
                if c in k:
                    return v

        print("❌ Opção inválida")

def ask(msg, default=None):
    if default:
        v = input(f"{msg} [{default}]: ").strip()
        return v if v else default
    return input(msg + ": ").strip()

def confirm(msg, default=False):
    d = "S/n" if default else "s/N"
    r = input(f"{msg} [{d}]: ").lower().strip()
    if not r:
        return default
    return r.startswith("s")

# ================= CONFIG FILE =================

def load_cfg():
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_cfg(cfg):
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

# ================= AUTO UPDATE =================

def auto_update():
    print("🔎 Verificando atualização...")
    try:
        with urllib.request.urlopen(SCRIPT_REPO_RAW, timeout=5) as r:
            remote = r.read().decode("utf-8")

        if f"SCRIPT_VERSION = \"{SCRIPT_VERSION}\"" in remote:
            return

        if confirm("🚀 Nova versão disponível. Atualizar agora?"):
            with open(sys.argv[0], "w", encoding="utf-8") as f:
                f.write(remote)
            print("✅ Atualizado! Reiniciando...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except:
        print("⚠ Não foi possível verificar atualizações")

# ================= GIT =================

def run(cmd, cwd=None):
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL)

def parse_git_url(url):
    m = re.match(r"(https?://[^/]+/[^/]+/[^/]+)/src/branch/([^/]+)", url)
    if m:
        return m.group(1) + ".git", m.group(2)

    m = re.match(r"(https?://github\.com/[^/]+/[^/]+)/tree/([^/]+)", url)
    if m:
        return m.group(1) + ".git", m.group(2)

    return url, None

def clone_repo(url):
    os.makedirs(TMP_ROOT, exist_ok=True)
    name = os.path.basename(url.rstrip("/")).replace(".git", "")
    path = os.path.join(TMP_ROOT, name)

    if os.path.exists(path):
        shutil.rmtree(path)

    try:
        subprocess.check_call(["git", "clone", url, path])
    except:
        print("❌ Falha ao clonar repositório")
        return None

    return os.path.abspath(path)

def checkout(repo, ref):
    try:
        subprocess.check_call(["git", "checkout", ref], cwd=repo)
        return True
    except:
        try:
            subprocess.check_call(
                ["git", "checkout", "-B", ref, f"origin/{ref}"],
                cwd=repo
            )
            return True
        except:
            print(f"❌ Branch/Tag '{ref}' não encontrada")
            return False

def list_refs(repo):
    branches = []
    for l in run(["git", "branch", "-a"], cwd=repo).splitlines():
        l = l.strip().replace("* ", "")
        if "remotes/origin/" in l and "HEAD" not in l:
            branches.append(l.replace("remotes/origin/", ""))

    tags = run(["git", "tag"], cwd=repo).splitlines()
    return sorted(set(branches)), sorted(tags)

# ================= MERGE =================

def read_file(p):
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def write_file(p, c):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)

def merge(base, source, output):
    shutil.copytree(base, output)
    copied = merged = 0

    for root, _, files in os.walk(source):
        rel = os.path.relpath(root, source)
        dst_dir = output if rel == "." else os.path.join(output, rel)

        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(dst_dir, f)

            st = read_file(s)
            if not os.path.exists(d):
                write_file(d, st)
                copied += 1
            else:
                bt = read_file(d)
                if bt != st:
                    write_file(d,
                        "-- >>> BASE\n" + bt +
                        "\n-- === NOVO ===\n" + st +
                        "\n-- <<< FIM\n"
                    )
                    merged += 1

    print(f"\n📊 Copiados: {copied}")
    print(f"📊 Mesclados: {merged}")

# ================= WIZARD =================

def wizard(cfg=None):
    cfg = cfg or {}

    cfg["mode"] = ask(
        "Modo (1=normal, 2=branch vs branch)",
        cfg.get("mode", "1")
    )

    cfg["base"] = ask("BASE (caminho ou URL)", cfg.get("base"))
    cfg["base_ref"] = ask("BASE branch/tag (vazio = atual)", cfg.get("base_ref", ""))

    cfg["source"] = ask("ORIGEM (caminho ou URL)", cfg.get("source"))
    cfg["source_ref"] = ask("ORIGEM branch/tag", cfg.get("source_ref"))

    cfg["output"] = ask("Pasta de saída", cfg.get("output", "merge_test"))

    return cfg

# ================= MAIN =================

def main():
    banner()
    auto_update()

    cfg = load_cfg()

    if cfg:
        c = menu(
            "Configuração encontrada",
            [
                "Usar opções anteriores",
                "Editar opções (wizard)",
                "Novo merge do zero"
            ]
        )

        if c == 1:
            pass
        elif c == 2:
            cfg = wizard(cfg)
        else:
            cfg = wizard({})
    else:
        cfg = wizard({})

    save_cfg(cfg)

    base_url, base_ref = parse_git_url(cfg["base"])
    src_url, src_ref = parse_git_url(cfg["source"])

    base = clone_repo(base_url) if base_url.startswith("http") else cfg["base"]
    source = clone_repo(src_url) if src_url.startswith("http") else cfg["source"]

    if base_ref:
        checkout(base, base_ref)
    if src_ref:
        checkout(source, src_ref)

    if os.path.exists(cfg["output"]):
        if confirm("Pasta existe. Apagar?"):
            shutil.rmtree(cfg["output"])
        else:
            return

    if confirm("Confirmar merge?"):
        merge(base, source, cfg["output"])

    if os.path.exists(TMP_ROOT) and confirm("Apagar temporários?"):
        shutil.rmtree(TMP_ROOT)

if __name__ == "__main__":
    main()
