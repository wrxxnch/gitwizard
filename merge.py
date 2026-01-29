import os
import shutil
import subprocess
import sys
import re

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
            print("\n👋 Saindo do Merge Wizard")
            sys.exit(0)

        if c.isdigit():
            n = int(c)
            if 1 <= n <= len(options):
                return n
        else:
            for key, idx in lookup.items():
                if c in key:
                    return idx

        print("❌ Opção inválida (número ou nome)")

def ask(msg):
    return input(msg + ": ").strip().strip('"')

def confirm(msg):
    return input(f"{msg} [s/N]: ").lower().startswith("s")

# ---------------- Git helpers ----------------

def run(cmd, cwd=None):
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL)

def is_git_url(url):
    return url.startswith(("http://", "https://", "git@"))

def parse_git_url(url):
    """
    Aceita URLs de página do GitHub / Codeberg
    Retorna (repo_url, ref_ou_None)
    """

    # Codeberg: /src/branch/<branch>
    m = re.match(r"(https?://[^/]+/[^/]+/[^/]+)/src/branch/([^/]+)", url)
    if m:
        return m.group(1) + ".git", m.group(2)

    # GitHub: /tree/<branch>
    m = re.match(r"(https?://github\.com/[^/]+/[^/]+)/tree/([^/]+)", url)
    if m:
        return m.group(1) + ".git", m.group(2)

    # URL git normal
    return url, None

def clone_repo(url):
    os.makedirs(TMP_ROOT, exist_ok=True)

    name = os.path.basename(url.rstrip("/")).replace(".git", "")
    if not name:
        name = "repo"

    path = os.path.join(TMP_ROOT, name)

    if os.path.exists(path):
        shutil.rmtree(path)

    print(f"🌐 Clonando {url}")
    try:
        subprocess.check_call(
            ["git", "clone", url, path],
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError:
        print("❌ Falha ao clonar repositório")
        print("👉 Verifique se a URL está correta ou se o repo é público")
        return None

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

    # tentativa direta
    try:
        subprocess.check_call(["git", "checkout", ref], cwd=repo)
        return
    except subprocess.CalledProcessError:
        pass

    # tentativa via origin/<branch>
    try:
        subprocess.check_call(
            ["git", "checkout", "-B", ref, f"origin/{ref}"],
            cwd=repo
        )
        return
    except subprocess.CalledProcessError:
        pass

    print(f"❌ Branch ou tag '{ref}' não encontrada")
    print("👉 Dica: verifique se o nome está correto ou se é remoto")
    return


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
            return None
        return os.path.abspath(p)

    url_raw = ask("Digite a URL do repositório git")
    repo_url, auto_ref = parse_git_url(url_raw)

    if not is_git_url(repo_url):
        print("❌ URL inválida")
        return None

    repo = clone_repo(repo_url)
    if not repo:
        return None

    if auto_ref:
        checkout(repo, auto_ref)
    else:
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
        url_raw = ask("URL do repositório")
        repo_url, _ = parse_git_url(url_raw)

        repoA = clone_repo(repo_url)
        if not repoA:
            return

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
        if not base:
            return
        source = get_source("ORIGEM")
        if not source:
            return

    output = ask("\n📁 Pasta de SAÍDA (teste)")
    if not output:
        print("❌ Pasta inválida")
        return

    if os.path.exists(output):
        if not confirm("Pasta existe. Apagar?"):
            return
        shutil.rmtree(output)

    if not confirm("\nConfirmar merge seguro?"):
        return

    merge(base, source, output)

    print("\n✅ Merge finalizado")
    print("🧪 Teste em:", output)

    if os.path.exists(TMP_ROOT) and confirm("\nApagar temporários?"):
        shutil.rmtree(TMP_ROOT)
        print("✔ Temporários removidos")

if __name__ == "__main__":
    main()
