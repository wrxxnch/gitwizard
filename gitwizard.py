#!/usr/bin/env python3

import os
import subprocess
import sys
from datetime import datetime
import urllib.request
import shutil

TMP_REMOTE = "__wizard_tmp__"
WIZARD_REPO = "https://raw.githubusercontent.com/wrxxnch/gitwizard/main/gitwizard.py"

# =========================================================
# helpers
# =========================================================

def run(cmd, cwd=None, check=True):
    result = subprocess.run(
        cmd,
        shell=True,
        text=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if check and result.returncode != 0:
        raise RuntimeError("Erro ao executar comando")
    return result.stdout.strip()

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def current_branch(repo):
    return run("git branch --show-current", repo)

def list_remotes(repo):
    out = run("git remote", repo)
    return out.splitlines() if out else []

def backup_branch(repo):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch = current_branch(repo) or "detached"
    name = f"backup/{branch}_{ts}"
    run(f"git branch {name}", repo)
    print(f"🛟 Backup criado: {name}")

# =========================================================
# repo comparado
# =========================================================

def setup_compare_remote(repo):
    remotes = list_remotes(repo)

    print("\nRepo comparado:")
    print("• URL (https://... ou git@...)")
    print("• nome de remote existente")
    print("• ENTER vazio → usar <origin>")

    src = input("URL / remote / ENTER: ").strip()

    if not src:
        if "origin" not in remotes:
            raise RuntimeError("remote <origin> não existe")
        src = "origin"

    # URL direta
    if "://" in src or src.startswith("git@"):
        run(f"git remote remove {TMP_REMOTE}", repo, check=False)
        run(f"git remote add {TMP_REMOTE} {src}", repo)
        remote = TMP_REMOTE
    else:
        if src not in remotes:
            raise RuntimeError(f"remote '{src}' não existe")
        remote = src

    run(f"git fetch {remote}", repo)
    return remote

def list_remote_branches(repo, remote):
    out = run("git branch -r", repo)
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(f"{remote}/") and "->" not in line:
            branches.append(line.replace(f"{remote}/", ""))
    if not branches:
        raise RuntimeError("nenhum branch remoto encontrado")
    return branches

def select_branch(branches):
    print("\n🌿 Branches disponíveis:")
    for i, b in enumerate(branches, 1):
        print(f"{i}) {b}")

    choice = input("Escolha (número ou nome): ").strip()

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(branches):
            return branches[idx]
        raise RuntimeError("número inválido")

    if choice in branches:
        return choice

    raise RuntimeError("branch inválido")

# =========================================================
# ações git
# =========================================================

def diff_flow(repo):
    remote = setup_compare_remote(repo)
    branches = list_remote_branches(repo, remote)
    branch = select_branch(branches)

    ref = input("Ref local (ENTER = HEAD): ").strip() or "HEAD"
    run(f"git diff {ref} {remote}/{branch}", repo)

def merge_flow(repo):
    remote = setup_compare_remote(repo)
    branches = list_remote_branches(repo, remote)
    branch = select_branch(branches)

    backup_branch(repo)
    run(f"git merge --no-ff {remote}/{branch}", repo, check=False)

    print("⚠️ Conflitos?")
    print("  git merge --abort")

def cherry_pick_flow(repo):
    commits = input("Commit(s) (ex: abc123 ou abc123..def456): ").strip()
    if not commits:
        raise RuntimeError("nenhum commit informado")

    backup_branch(repo)
    run(f"git cherry-pick {commits}", repo, check=False)

    print("⚠️ Conflitos?")
    print("  git cherry-pick --continue")
    print("  git cherry-pick --abort")

def revert_flow(repo):
    commit = input("Commit para voltar: ").strip()
    if not commit:
        raise RuntimeError("commit inválido")

    run(f"git reset --hard {commit}", repo)
    print("⏪ Revertido com sucesso")

def log_flow(repo):
    run("git --no-pager log --oneline --graph --decorate -20", repo)

# =========================================================
# auto-update
# =========================================================

def update_wizard():
    script_path = os.path.abspath(__file__)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{script_path}.bak_{ts}"

    print("🔄 Atualizando Git Wizard...")
    print("🌐 Fonte:", WIZARD_REPO)

    try:
        with urllib.request.urlopen(WIZARD_REPO) as r:
            new_code = r.read()

        shutil.copy2(script_path, backup)
        print(f"🛟 Backup criado: {backup}")

        with open(script_path, "wb") as f:
            f.write(new_code)

        print("✅ Atualização concluída!")
        print("♻️ Reinicie o script para usar a nova versão.")

    except Exception as e:
        print("❌ Falha na atualização:", e)
        print("👉 Script original preservado")

# =========================================================
# menu principal
# =========================================================

def menu():
    print("""
🧙 Git Wizard
==============================
1) Diff com repo comparado
2) Merge seguro de branch
3) Cherry-pick de commits
4) Reverter para commit
5) Log resumido
6) 🔄 Atualizar Git Wizard
0) Sair
""")

def main():
    repo = os.getcwd()

    if not is_git_repo(repo):
        sys.exit("❌ Execute dentro de um repositório git")

    print("📦 Repo ativo:", repo)
    print("🌿 Branch:", current_branch(repo))

    while True:
        menu()
        c = input("Escolha: ").strip()

        try:
            if c == "1":
                diff_flow(repo)
            elif c == "2":
                merge_flow(repo)
            elif c == "3":
                cherry_pick_flow(repo)
            elif c == "4":
                revert_flow(repo)
            elif c == "5":
                log_flow(repo)
            elif c == "6":
                update_wizard()
            elif c == "0":
                break
            else:
                print("❌ Opção inválida")
        except Exception as e:
            print("❌", e)

if __name__ == "__main__":
    main()
