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
🧙 MERGE WIZARD v4.5
========================================
* Local / GitHub / Codeberg
* Várias branches / tags / commits
* Vários Pull Requests (não mergeados)
* Separados por vírgula
* BASE soberana
* Código + imagens + assets
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
    print(f"🔀 Checkout PR #{pr_id}")
    run(
        ["git", "fetch", "origin", f"pull/{pr_id}/head:pr-{pr_id}"],
        cwd=repo
    )
    run(["git", "checkout", f"pr-{pr_id}"], cwd=repo)

# ==========================================================
# PR / refs parser
# ==========================================================

def parse_list(text):
    return [t.strip() for t in text.split(",") if t.strip()]

def parse_pr_input(text):
    if text.isdigit():
        return None, text

    parts = text.rstrip("/").split("/")
    if "pulls" in parts:
        idx = parts.index("pulls")
    elif "pull" in parts:
        idx = parts.index("pull")
    else:
        return text, None

    pr = parts[idx + 1]
    repo = "/".join(parts[:idx])
    return repo + ".git", pr

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

def is_binary_file(filename):
    return os.path.splitext(filename)[1].lower() in {
        ".png", ".jpg", ".jpeg", ".ogg", ".wav",
        ".mp3", ".obj", ".mtl", ".blend",
        ".dds", ".tga"
    }

def comment_prefix(filename):
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
    }.get(os.path.splitext(filename)[1].lower(), "#")

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

    return (
        base_txt.rstrip()
        + f"\n\n{prefix} ===== MERGE-WIZARD: linhas adicionadas =====\n"
        + "\n".join(added)
        + "\n"
    ), True

def apply_source(output, source):
    copied = merged = 0

    for root, _, files in os.walk(source):
        rel = os.path.relpath(root, source)
        dest_dir = os.path.join(output, rel) if rel != "." else output

        for f in files:
            src = os.path.join(root, f)
            dst = os.path.join(dest_dir, f)

            os.makedirs(os.path.dirname(dst), exist_ok=True)

            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                copied += 1
                print(f"[COPIADO] {dst}")
                continue

            if is_binary_file(f):
                shutil.copy2(src, dst)
                merged += 1
                print(f"[BINÁRIO ATUALIZADO] {dst}")
                continue

            base_txt = read_file(dst)
            src_txt = read_file(src)

            if base_txt == src_txt:
                continue

            merged_txt, changed = smart_merge(base_txt, src_txt, f)
            if changed:
                write_file(dst, merged_txt)
                merged += 1
                print(f"[MERGED+] {dst}")

    return copied, merged

# ==========================================================
# Wizard
# ==========================================================

def get_sources(label):
    print(f"\n📌 Selecionar {label}")
    opt = menu(
        f"Tipo de {label}",
        [
            "Caminho local",
            "Git (branches / tags / commits)",
            "Pull Requests (não mergeados)",
        ]
    )

    if opt == 1:
        p = ask("Digite o caminho local")
        if not os.path.exists(p):
            sys.exit("❌ Caminho inválido")
        return [("local", p)]

    repo_url = ask("URL do repositório git")
    repo = clone_repo(repo_url)

    sources = []

    if opt == 2:
        refs = parse_list(ask("Branches / tags / commits (separados por vírgula)"))
        for ref in refs:
            checkout(repo, ref)
            sources.append(("git", repo))
    else:
        prs = parse_list(ask("IDs ou links de PR (separados por vírgula)"))
        for raw in prs:
            _, pr = parse_pr_input(raw)
            if not pr:
                sys.exit(f"❌ PR inválido: {raw}")
            checkout_pr(repo, pr)
            sources.append(("git", repo))

    return sources

# ==========================================================
# Main
# ==========================================================

def main():
    banner()

    base_list = get_sources("BASE")
    base_type, base_path = base_list[0]

    output = ask("\n📁 Pasta de SAÍDA (teste)")
    if not output:
        sys.exit(1)

    if os.path.exists(output):
        if not confirm("Pasta existe. Apagar?"):
            sys.exit(0)
        safe_rmtree(output)

    print("\n📂 Copiando BASE → pasta de teste")
    shutil.copytree(base_path, output)

    origin_sources = get_sources("ORIGEM")

    total_copied = total_merged = 0
    for _, src in origin_sources:
        c, m = apply_source(output, src)
        total_copied += c
        total_merged += m

    print("\n📊 RELATÓRIO FINAL")
    print(f"Arquivos copiados : {total_copied}")
    print(f"Arquivos mesclados: {total_merged}")

    print("\n✅ Merge finalizado")
    print("🧪 Teste em:", output)

    if os.path.exists(TMP_ROOT) and confirm("\nApagar temporários?"):
        safe_rmtree(TMP_ROOT)

if __name__ == "__main__":
    main()
