import os
import shutil
import subprocess
import sys

TMP_ROOT = ".merge_wizard_tmp"

# ---------------- UI ----------------

def banner():
    print("""
========================================
🧙 MERGE WIZARD v2
========================================
* Local / GitHub / Codeberg
* Seleção de branch ou tag
* Branch vs Branch
* Merge seguro em pasta de teste
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

def list_branches(repo):
    out = run(["git", "branch", "-a"], cwd=repo)
    branches = []
    for l in out.splitlines():
        l = l.strip().replace("* ", "")
        if "remotes/origin/" in l and "HEAD" not in l:
            branches.append(l.replace("remotes/origin/", ""))
    return sorted(set(branches))

def list_tags(repo):
    out = run(["git", "tag"], cwd=repo)
    return sorted(out.splitlines())

def checkout(repo, ref):
    print(f"🔀 Checkout: {ref}")
    subprocess.check_call(["git", "checkout", ref], cwd=repo)

# ---------------- Merge core ----------------

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

                merged += 1
                merged_txt = (
                    "-- >>>>>>>>>> BASE (antigo)\n"
                    + base_txt +
                    "\n-- ========= NOVO =========\n"
                    + src_txt +
                    "\n-- <<<<<<<<<< FIM MERGE\n"
                )
                write_file(dst, merged_txt)
                print(f"[MERGE] {dst}")

    print("\n📊 RELATÓRIO")
    print(f"Arquivos copiados : {copied}")
    print(f"Arquivos mesclados: {merged}")

# ---------------- Wizard ----------------

def select_ref(repo):
    branches = list_branches(repo)
    tags = list_tags(repo)

    options = []
    refs = []

    for b in branches:
        options.append("branch: " + b)
        refs.append(b)

    for t in tags:
        options.append("tag: " + t)
        refs.append(t)

    if not options:
        print("❌ Nenhuma branch/tag encontrada")
        sys.exit(1)

    c = menu("Selecionar branch ou tag", options)
    return refs[c - 1]

def get_source(label):
    print(f"\n📌 Selecionar {label}")
    opt = menu(
        f"Tipo de {label}",
        ["Caminho local", "URL Git (GitHub / Codeberg)"]
    )

    if opt == 1:
        p = ask("Digite o caminho local")
        if not os.path.exists(p):
            print("❌ Caminho inválido")
            sys.exit(1)
        return os.path.abspath(p)

    url = ask("Digite a URL do repositório git")
    if not is_git_url(url):
        print("❌ URL inválida")
        sys.exit(1)

    repo = clone_repo(url)
    ref = select_ref(repo)
    checkout(repo, ref)
    return repo

def main():
    banner()

    mode = menu(
        "Modo de operação",
        ["Merge normal", "Comparar branch vs branch (mesmo repo)"]
    )

    if mode == 2:
        url = ask("URL do repositório")
        repoA = clone_repo(url)
        repoB = repoA + "_cmp"

        shutil.copytree(repoA, repoB)

        print("\n🔹 Branch/TAG A")
        refA = select_ref(repoA)
        checkout(repoA, refA)

        print("\n🔹 Branch/TAG B")
        refB = select_ref(repoB)
        checkout(repoB, refB)

        base = repoA
        source = repoB
    else:
        base = get_source("BASE")
        source = get_source("ORIGEM")

    output = ask("\n📁 Pasta de SAÍDA (teste)")
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
    print("🧪 Teste em:", output)

    if os.path.exists(TMP_ROOT) and confirm("\nApagar temporários?"):
        shutil.rmtree(TMP_ROOT)
        print("✔ Temporários removidos")

if __name__ == "__main__":
    main()
