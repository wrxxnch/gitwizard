import os
import subprocess
import sys
from datetime import datetime

# =============================
# helpers
# =============================

def run(cmd, cwd=None, check=True):
    print(f"\n[{cwd or os.getcwd()}]$ {cmd}")
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
        sys.exit("❌ Erro ao executar comando.")
    return result.stdout.strip()

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def pick_repo(prompt):
    path = input(prompt).strip()
    if not path:
        return None
    if not os.path.isdir(path):
        print("❌ Diretório não existe")
        return None
    if not is_git_repo(path):
        print("❌ Não é um repositório git")
        return None
    return os.path.abspath(path)

def current_branch(repo):
    return run("git branch --show-current", repo)

def current_commit(repo):
    return run("git rev-parse HEAD", repo)

def backup_branch(repo):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch = current_branch(repo)
    name = f"backup/{branch}_{ts}"
    run(f"git branch {name}", repo)
    print(f"🛟 Backup criado: {name}")
    return name

# =============================
# flows
# =============================

def diff_repos(repo_a, repo_b):
    ref_a = input("Ref do repo ATIVO (ex: HEAD): ")
    ref_b = input("Ref do repo COMPARADO (ex: main): ")

    tmp = "__wizard_tmp__"

    run(f"git remote remove {tmp}", repo_a, check=False)
    run(f"git remote add {tmp} {repo_b}", repo_a)
    run(f"git fetch {tmp}")

    run(f"git diff {ref_a} {tmp}/{ref_b}", repo_a)

def cherry_pick(repo_a):
    commits = input("Commit(s) para cherry-pick: ")
    backup_branch(repo_a)
    run(f"git cherry-pick {commits}", repo_a, check=False)

    print("⚠️ Conflito?")
    print("  git cherry-pick --continue")
    print("  git cherry-pick --abort")

def merge(repo_a):
    branch = input("Branch para merge: ")
    backup_branch(repo_a)
    run(f"git merge --no-ff {branch}", repo_a, check=False)

    print("⚠️ Se der ruim:")
    print("  git merge --abort")

def revert(repo_a):
    commit = input("Commit para voltar: ")
    run(f"git reset --hard {commit}", repo_a)
    print("⏪ Revertido.")

def log(repo):
    run("git --no-pager log --oneline --graph --decorate -20", repo)

# =============================
# main wizard
# =============================

def menu():
    print("""
🧙 Git Wizard (Multi-Repo)
=========================
1) Trocar repo ATIVO (meu)
2) Trocar repo COMPARADO
3) Diff entre repos
4) Cherry-pick (repo ativo)
5) Merge (repo ativo)
6) Reverter commit (repo ativo)
7) Log resumido
0) Sair
""")

def main():
    repo_active = pick_repo("Caminho do repo ATIVO (meu): ")
    repo_compare = pick_repo("Caminho do repo COMPARADO: ")

    if not repo_active:
        sys.exit("❌ Repo ativo obrigatório.")

    print("\n📦 Repo ativo:", repo_active)
    print("🌿 Branch:", current_branch(repo_active))
    print("📌 Commit:", current_commit(repo_active))

    if repo_compare:
        print("\n📦 Repo comparado:", repo_compare)
        print("🌿 Branch:", current_branch(repo_compare))
        print("📌 Commit:", current_commit(repo_compare))

    while True:
        menu()
        c = input("Escolha: ").strip()

        if c == "1":
            repo_active = pick_repo("Novo repo ATIVO: ")
        elif c == "2":
            repo_compare = pick_repo("Novo repo COMPARADO: ")
        elif c == "3":
            if not repo_compare:
                print("❌ Defina o repo comparado primeiro.")
            else:
                diff_repos(repo_active, repo_compare)
        elif c == "4":
            cherry_pick(repo_active)
        elif c == "5":
            merge(repo_active)
        elif c == "6":
            revert(repo_active)
        elif c == "7":
            log(repo_active)
        elif c == "0":
            break
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
