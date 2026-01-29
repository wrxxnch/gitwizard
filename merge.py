import os
import shutil
import subprocess
import sys
import time

LOG_FILE = "merge_report.txt"

# ---------------- UI ----------------

def banner():
    print("""
========================================
🧙 MERGE WIZARD v4
========================================
1) Merge novo (cria pasta base)
2) Update (incremental)
* Barra de progresso
* (A)(M)(D) no topo
* Log --name-status
""")

def ask(msg):
    return input(msg + ": ").strip().strip('"')

def confirm(msg):
    return input(f"{msg} [s/N]: ").lower().startswith("s")

# ---------------- Helpers ----------------

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

def all_files(root):
    files = []
    for r, _, fs in os.walk(root):
        for f in fs:
            files.append(os.path.join(r, f))
    return files

# ---------------- Progress ----------------

def progress(i, total, name):
    size = 30
    fill = int(size * i / total)
    bar = "█" * fill + "-" * (size - fill)
    print(f"\r[{bar}] {i}/{total} {name[:70]}", end="", flush=True)

# ---------------- Core ----------------

def compute_maps(base, src):
    b = {os.path.relpath(f, base): f for f in all_files(base)}
    s = {os.path.relpath(f, src): f for f in all_files(src)}
    return b, s, sorted(set(b) | set(s))

def merge_new(base, src, out):
    print("\n📂 Criando nova pasta base...")
    shutil.copytree(base, out)
    update(out, src)

def update(base_out, src):
    print("\n🔄 UPDATE incremental iniciado")

    base_files, src_files, keys = compute_maps(base_out, src)
    total = len(keys)

    log = open(os.path.join(base_out, LOG_FILE), "w", encoding="utf-8")

    A = M = D = 0

    for i, rel in enumerate(keys, 1):
        progress(i, total, rel)
        time.sleep(0.01)

        b = base_files.get(rel)
        s = src_files.get(rel)
        out = os.path.join(base_out, rel)

        # ADD
        if not b and s:
            write_file(out, "(A)\n" + read_file(s))
            log.write(f"A {rel}\n")
            A += 1

        # DELETE
        elif b and not s:
            log.write(f"D {rel}\n")
            D += 1

        # MODIFY
        elif b and s:
            btxt = read_file(b)
            stxt = read_file(s)

            if btxt != stxt:
                merged = (
                    "(M)\n"
                    "-- >>>>>>>>>> BASE\n"
                    + btxt +
                    "\n-- ========= NOVO =========\n"
                    + stxt +
                    "\n-- <<<<<<<<<< FIM MERGE\n"
                )
                write_file(out, merged)
                log.write(f"M {rel}\n")
                M += 1

    log.close()

    print("\n\n📊 UPDATE FINALIZADO")
    print(f"A {A} | M {M} | D {D}")
    print(f"📄 Log: {LOG_FILE}")

# ---------------- Main ----------------

def main():
    banner()

    mode = ask("Modo (1=merge novo / 2=update)")

    base = os.path.abspath(ask("📌 Caminho BASE / DESTINO"))
    src  = os.path.abspath(ask("📌 Caminho ORIGEM (novos arquivos)"))

    if mode == "1":
        out = os.path.abspath(ask("📁 Pasta de SAÍDA (nova)"))
        if os.path.exists(out):
            print("❌ Pasta já existe")
            sys.exit(1)
        if confirm("Confirmar MERGE NOVO?"):
            merge_new(base, src, out)

    elif mode == "2":
        if not os.path.exists(base):
            print("❌ Pasta base não existe")
            sys.exit(1)
        if confirm("Confirmar UPDATE incremental?"):
            update(base, src)

    else:
        print("❌ Modo inválido")

    print("\n✅ Operação concluída")

if __name__ == "__main__":
    main()
