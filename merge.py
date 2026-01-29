#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

TMP_ROOT = ".merge_wizard_tmp"
LOG_FILE = "merge_report.txt"

# ---------------- UI ----------------

def banner():
    print("""
========================================
🧙 MERGE WIZARD
========================================
* Base copiada para nova pasta
* Merge seguro (não altera a base)
* Local / GitHub / Codeberg
""")

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
        print("❌ Opção inválida")

def ask(msg):
    return input(msg + ": ").strip().strip('"')

def confirm(msg):
    return input(f"{msg} [s/N]: ").lower().startswith("s")

def norm(p):
    return os.path.abspath(os.path.expanduser(p))

# ---------------- Git helpers ----------------

def run(cmd, cwd=None):
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL)

def is_git_url(url):
    return url.startswith(("http://", "https://", "git@"))

def clone_repo(url):
    os.makedirs(TMP_ROOT, exist_ok=True)
    name = os.path.basename(url).replace(".git", "")
    path = os.path.join(TMP_ROOT, name)

    if os.path.exists(path):
        shutil.rmtree(path)

    print(f"🌐 Clonando {url}")
    subprocess.check_call(["git", "clone", url, path])
    return os.path.abspath(path)

def list_refs(repo):
    refs = []
    out = run(["git", "branch", "-a"], cwd=repo)
    for l in out.splitlines():
        l = l.strip().replace("* ", "")
        if "remotes/origin/" in l and "HEAD" not in l:
            refs.append(l.replace("remotes/origin/", ""))
    out = run(["git", "tag"], cwd=repo)
    refs.extend(out.splitlines())
    return sorted(set(refs))

def checkout(repo, ref):
    print(f"🔀 Checkout: {ref}")
    subprocess.check_call(["git", "checkout", ref], cwd=repo)

# ---------------- Merge core ----------------

def read_file(p):
    try:
        with open(p, "rb") as f:
            return f.read()
    except:
        return b""

def write_file(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)

def collect(root):
    files = {}
    for r, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(r, f)
            files[os.path.relpath(p, root)] = p
    return files

def merge(base, source, output):
    print("\n📂 Copiando BASE → pasta de saída")
    shutil.copytree(base, output)

    base_files = collect(base)
    src_files = collect(source)

    report = []

    for rel in sorted(set(base_files) | set(src_files)):
        b = base_files.get(rel)
        s = src_files.get(rel)
        dst = os.path.join(output, rel)

        if s and not b:
            write_file(dst, b"(A) ADDED FILE\n" + read_file(s))
            report.append(f"A  {rel}")

        elif b and not s:
            write_file(dst, b"(D) DELETED FILE\n")
            report.append(f"D  {rel}")

        elif b and s:
            bd = read_file(b)
            sd = read_file(s)
            if bd == sd:
                continue

            merged = (
                b"(C) CONFLICT FILE\n"
                b"-- >>>>>>>>>> BASE\n" + bd +
                b"\n-- ========= ORIGEM =========\n" + sd +
                b"\n-- <<<<<<<<<< FIM MERGE\n"
            )
            write_file(dst, merged)
            report.append(f"C  {rel}")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        for r in report:
            f.write(r + "\n")

    print("\n📄 Relatório salvo em:", LOG_FILE)

# ---------------- Wizard ----------------

def get_source(label):
    print(f"\n📌 Selecionar {label}")
    opt = menu(f"Tipo de {label}", ["Caminho local", "URL Git"])

    if opt == 0:
        sys.exit(0)

    if opt == 1:
        p = norm(ask("Digite o caminho local"))
        if not os.path.isdir(p):
            print("❌ Caminho inválido")
            sys.exit(1)
        return p

    url = ask("Digite a URL do repositório git")
    if not is_git_url(url):
        print("❌ URL inválida")
        sys.exit(1)

    repo = clone_repo(url)
    refs = list_refs(repo)

    c = menu("Selecionar branch/tag", refs)
    checkout(repo, refs[c - 1])
    return repo

def main():
    banner()

    base = get_source("BASE")
    source = get_source("ORIGEM")

    output = norm(ask("\n📁 Pasta de SAÍDA"))
    if not output:
        print("❌ Pasta inválida")
        sys.exit(1)

    if os.path.exists(output):
        if not confirm("Pasta existe. Apagar?"):
            sys.exit(0)
        shutil.rmtree(output)

    if not confirm("\nConfirmar merge seguro?"):
        sys.exit(0)

    merge(base, source, output)

    print("\n✅ Merge finalizado")
    print("🧪 Resultado em:", output)

    if os.path.exists(TMP_ROOT) and confirm("\nApagar temporários?"):
        shutil.rmtree(TMP_ROOT)

if __name__ == "__main__":
    main()
