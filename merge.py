import os
import shutil
import subprocess
import sys
import time
import stat

TMP_ROOT = ".merge_wizard_tmp"

# ==========================================================
# Utils
# ==========================================================

def safe_rmtree(path, retries=5, delay=0.5):
    def onerror(func, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except:
            pass

    for _ in range(retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=onerror)
            return
        except PermissionError:
            time.sleep(delay)

    try:
        if os.path.exists(path):
            os.rename(path, path + "_old_" + str(int(time.time())))
    except:
        print(f"⚠ Não foi possível remover {path}. Remova manualmente.")
        sys.exit(1)

# ==========================================================
# UI
# ==========================================================

def banner():
    print("""
========================================
🧙 MERGE WIZARD v4.4
========================================
* Local / GitHub / Codeberg
* Branch / Tag / Commit
* Pull Request (não mergeado)
* BASE soberana
* Merge seguro para mods Lua
* Windows-safe filesystem
""")

def menu(title, options):
    print("\n" + title)
    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")
    while True:
        try:
            c = int(input("> "))
            if 1 <= c <= len(options):
                return c
        except:
            pass
        print("❌ Opção inválida")

def ask(msg):
    return input(msg + ": ").strip().strip('"')

def confirm(msg):
    return input(f"{msg} [s/N]: ").lower().startswith("s")

# ==========================================================
# Git helpers
# ==========================================================

def run(cmd, cwd=None):
    subprocess.check_call(cmd, cwd=cwd)

def clone_repo(url):
    os.makedirs(TMP_ROOT, exist_ok=True)
    name = os.path.basename(url).replace(".git", "")
    path = os.path.join(TMP_ROOT, name)

    if os.path.exists(path):
        print("🧹 Limpando clone anterior...")
        safe_rmtree(path)

    print(f"🌐 Clonando {url}")
    run(["git", "clone", url, path])
    return os.path.abspath(path)

def checkout(repo, ref):
    print(f"🔀 Checkout: {ref}")
    run(["git", "checkout", ref], cwd=repo)

def checkout_pr(repo, pr_id):
    print(f"🔀 Checkout Pull Request #{pr_id}")
    run(
        ["git", "fetch", "origin", f"pull/{pr_id}/head:pr-{pr_id}"],
        cwd=repo
    )
    run(["git", "checkout", f"pr-{pr_id}"], cwd=repo)

# ==========================================================
# PR URL parser (AQUI está a correção chave)
# ==========================================================

def parse_pr_input(text):
    """
    Aceita:
    - https://codeberg.org/user/repo/pulls/4090/files
    - https://github.com/user/repo/pull/4090
    - apenas '4090'
    Retorna (repo_url, pr_id)
    """
    text = text.strip()

    if text.isdigit():
        return None, text

    parts = text.rstrip("/").split("/")

    if "pulls" in parts:
        idx = parts.index("pulls")
    elif "pull" in parts:
        idx = parts.index("pull")
    else:
        return text, None

    pr_id = parts[idx + 1]
    repo = "/".join(parts[:idx])
    return repo + ".git", pr_id

# ==========================================================
# File helpers
# ==========================================================

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ==========================================================
# Merge logic
# ==========================================================

def comment_prefix(filename):
    ext = os.path.splitext(filename)[1].lower()
    return {
        ".lua": "--",
        ".py": "#",
        ".sh": "#",
        ".js": "//",
        ".ts": "//",
        ".c": "//",
        ".cpp": "//",
        ".h": "//",
        ".java": "//",
    }.get(ext, "#")

def smart_merge(base_txt, src_txt, filename):
    base_lines = base_txt.splitlines()
    src_lines = src_txt.splitlines()

    base_set = set(l.strip() for l in base_lines if l.strip())
    prefix = comment_prefix(filename)

    added = []
    for line in src_lines:
        if line.strip() and line.strip() not in base_set:
            added.append(f"{prefix} [MERGE-WIZARD ADD]\n{line}")

    if not added:
        return base_txt, False

    merged = (
        base_txt.rstrip()
        + f"\n\n{prefix} ===== MERGE-WIZARD: linhas adicionadas =====\n"
        + "\n".join(added)
        + "\n"
    )
    return merged, True

def merge(base, source, output):
    print("\n📂 Copiando BASE → pasta de teste")
    shutil.copytree(base, output)

    copied = merged = 0

    for root, _, files in os.walk(source):
        rel = os.path.relpath(root, source)
        dest_dir = os.path.join(output, rel) if rel != "." else output

        for f in files:
            src = os.path.join(root, f)
            dst = os.path.join(dest_dir, f)

            src_txt = read_file(src)

            if not os.path.exists(dst):
                write_file(dst, src_txt)
                copied += 1
                print(f"[COPIADO] {dst}")
            else:
                base_txt = read_file(dst)
                if base_txt == src_txt:
                    continue

                merged_txt, changed = smart_merge(base_txt, src_txt, f)
                if changed:
                    write_file(dst, merged_txt)
                    merged += 1
                    print(f"[MERGED+] {dst}")

    print("\n📊 RELATÓRIO")
    print(f"Arquivos copiados : {copied}")
    print(f"Arquivos mesclados: {merged}")

# ==========================================================
# Wizard
# ==========================================================

def get_source(label):
    print(f"\n📌 Selecionar {label}")
    opt = menu(
        f"Tipo de {label}",
        [
            "Caminho local",
            "Git (branch / tag / commit)",
            "Pull Request (não mergeado)",
        ]
    )

    if opt == 1:
        p = ask("Digite o caminho local")
        if not os.path.exists(p):
            sys.exit("❌ Caminho inválido")
        return os.path.abspath(p)

    if opt == 2:
        repo_url = ask("URL do repositório git")
        repo = clone_repo(repo_url)
        ref = ask("Branch / tag / commit")
        checkout(repo, ref)
        return repo

    # ---- Pull Request ----
    raw = ask("Cole o LINK do PR ou apenas o ID")
    repo_url, pr = parse_pr_input(raw)

    if not pr:
        sys.exit("❌ Pull Request inválido")

    if not repo_url:
        repo_url = ask("URL do repositório git")

    repo = clone_repo(repo_url)
    checkout_pr(repo, pr)
    return repo

# ==========================================================
# Main
# ==========================================================

def main():
    banner()

    base = get_source("BASE")
    source = get_source("ORIGEM")

    output = ask("\n📁 Pasta de SAÍDA (teste)")
    if not output:
        sys.exit(1)

    if os.path.exists(output):
        if not confirm("Pasta existe. Apagar?"):
            sys.exit(0)
        safe_rmtree(output)

    if not confirm("\nConfirmar merge seguro?"):
        sys.exit(0)

    merge(base, source, output)

    print("\n✅ Merge finalizado")
    print("🧪 Teste em:", output)

    if os.path.exists(TMP_ROOT) and confirm("\nApagar temporários?"):
        safe_rmtree(TMP_ROOT)

if __name__ == "__main__":
    main()
