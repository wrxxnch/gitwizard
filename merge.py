import os
import shutil
import subprocess
import sys
import time
import stat
import difflib

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
🧙 MERGE WIZARD v4.5 (Filtered Diff)
========================================
* Local / GitHub / Codeberg
* Várias branches / tags / commits
* Vários Pull Requests (não mergeados)
* Saída: APENAS arquivos novos ou modificados
* Diferença de linhas (diff) para código
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

def is_code_file(filename):
    code_extensions = {
        '.py', '.js', '.ts', '.html', '.css', '.c', '.cpp', '.h', 
        '.java', '.go', '.rs', '.php', '.rb', '.sh', '.sql', '.md', '.json', '.xml', '.lua'
    }
    return os.path.splitext(filename)[1].lower() in code_extensions

def get_line_diff(old_txt, new_txt):
    diff = difflib.unified_diff(
        old_txt.splitlines(keepends=True),
        new_txt.splitlines(keepends=True),
        fromfile='BASE',
        tofile='NOVO',
        n=3
    )
    return "".join(diff)

def apply_source(output, base_dir, source):
    copied = merged = 0

    for root, _, files in os.walk(source):
        if '.git' in root:
            continue
            
        rel = os.path.relpath(root, source)
        
        for f in files:
            if f.startswith('.git'): continue
            
            src_path = os.path.join(root, f)
            base_path = os.path.join(base_dir, rel, f)
            dst_path = os.path.join(output, rel, f)

            src_txt_raw = None # Cache para leitura se necessário

            # 1. NOVO: Arquivo não existe na base
            if not os.path.exists(base_path):
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                copied += 1
                print(f"[NOVO] {rel}/{f}")
                continue

            # 2. EXISTE: Comparar
            if is_binary_file(f):
                # Comparação binária simples por hash ou apenas copia se quiser sempre o novo
                # Aqui vamos copiar se forem diferentes (usando stat para rapidez ou apenas copiar)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                merged += 1
                print(f"[BINÁRIO ATUALIZADO] {rel}/{f}")
                continue

            base_txt = read_file(base_path)
            src_txt = read_file(src_path)

            if base_txt == src_txt:
                continue

            # 3. DIFERENTES: Processar mesclagem na pasta de saída
            merged += 1
            if is_code_file(f):
                diff_txt = get_line_diff(base_txt, src_txt)
                if diff_txt:
                    write_file(dst_path, diff_txt)
                    print(f"[DIFF] {rel}/{f}")
                else:
                    write_file(dst_path, src_txt)
                    print(f"[ATUALIZADO] {rel}/{f}")
            else:
                # Fallback para outros tipos de texto (bloco de merge)
                merged_txt = (
                    "-- >>>>>>>>>> BASE (antigo)\n"
                    + base_txt +
                    "\n-- ========= NOVO =========\n"
                    + src_txt +
                    "\n-- <<<<<<<<<< FIM MERGE\n"
                )
                write_file(dst_path, merged_txt)
                print(f"[MERGE] {rel}/{f}")

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

    output = ask("\n📁 Pasta de SAÍDA (apenas alterados)")
    if not output:
        sys.exit(1)

    if os.path.exists(output):
        if not confirm(f"Pasta '{output}' existe. Apagar?"):
            sys.exit(0)
        safe_rmtree(output)
    
    os.makedirs(output, exist_ok=True)

    origin_sources = get_sources("ORIGEM")

    total_copied = total_merged = 0
    for _, src in origin_sources:
        c, m = apply_source(output, base_path, src)
        total_copied += c
        total_merged += m

    print("\n📊 RELATÓRIO FINAL (Apenas alterações)")
    print(f"Arquivos novos: {total_copied}")
    print(f"Arquivos modificados: {total_merged}")

    if total_copied == 0 and total_merged == 0:
        print("⚠ Nenhuma diferença encontrada.")

    print("\n✅ Processo finalizado")
    print("🧪 Arquivos em:", output)

    if os.path.exists(TMP_ROOT) and confirm("\nApagar temporários?"):
        safe_rmtree(TMP_ROOT)

if __name__ == "__main__":
    main()
