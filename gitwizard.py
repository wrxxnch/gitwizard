import os
import subprocess
import sys
from datetime import datetime

TMP_REMOTE = "__wizard_tmp__"

# =============================
# helpers
# =============================

def run(cmd, cwd=None, check=True):
    result = subprocess.run(
        cmd, shell=True, text=True,
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

def list_remotes(repo):
    out = run("git remote", repo)
    return out.splitlines() if out else []

def current_branch(repo):
    return run("git branch --show-current", repo)

def backup_branch(repo):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"backup/{current_branch(repo)}_{ts}"
    run(f"git branch {name}", repo)
    print(f"🛟 Backup criado: {name}")

# =============================
# repo comparado
# =============================

def setup_compare_remote(repo):
    remotes = list_remotes(repo)

    print("\nRepo comparado:")
    print("• URL")
    print("• nome de remote")
    print("• ENTER vazio → usar <origin>")

    src = input("URL / remote / ENTER: ").strip()

    if not src:
        if "origin" not in remotes:
            raise RuntimeError("origin não existe")
        src = "origin"

    # URL
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
    out = run(f"git branch -r", repo)
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(f"{remote}/") and "->" not in line:
            branches.append(line.replace(f"{remote}/", ""))
    return branches

def select_branch(branches):
    print("\nBranches disponíveis:")
    for i, b in enumerate(branches, 1):
        print(f"{i}) {b}")

    choice = input("Escolha (número ou nome): ").strip()

    if choice.isdigit():
        idx = int(choice) - 1
        if idx < 0 or idx >= len(branches):
            raise RuntimeError("Número inválido")
        return branches[idx]

    if choice in branches:
        return choice

    raise RuntimeError("Branch inválido")

# =============================
# actions
# =============================

def diff_flow(repo):
    remote = setup_compare_remote(repo)
    branches = list_remote_branches(repo, remote)
    branch = select_branch(branches)

    ref = input("Ref local (ENTER = HEAD): ").strip() or "HEAD"
    run(f"git diff {ref} {remote}/{branch}", repo)

def cherry_pick_flow(repo):
    commits = input("Commit(s) para cherry-pick: ")
    backup_branch(repo)
    run(f"git cherry-pick {commits}", repo, check=False)

    print("⚠️ Conflitos?")
    print("  git cherry-pick --continue")
    print("  git cherry-pick --abort")

def merge_flow(repo):
    remote = setup_compare_remote(repo)
    branches = list_remote_branches(repo, remote)
    branch = select_branch(branches)

    backup_branch(repo)
    run(f"git merge --no-ff {remote}/{branch}", repo, check=False)

    print("⚠️ Se der conflito:")
    print("  git merge --abort")

def revert_flow(repo):
    commit = input("Commit para voltar: ")
    run(f"git reset --hard {commit}", repo)
    print("⏪ Revertido.")

def log_flow(repo):
    run("git --no-pager log --oneline --graph --decorate -20", repo)

# =============================
# main wizard
# =============================

def menu():
    print("""
🧙 Git Wizard (URL + Remote + Branch Selector)
=============================================
1) Diff com repo comparado
2) Merge seguro de branch
3) Cherry-pick de commits
4) Reverter para commit
5) Log resumido
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
            elif c == "0":
                break
            else:
                print("❌ Opção inválida")
        except Exception as e:
            print("❌", e)

if __name__ == "__main__":
    main()
