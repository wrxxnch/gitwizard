import os
import shutil
import sys
import time

LOG_FILE = "merge_report.txt"

# ---------------- UI ----------------

def banner():
    print("""
========================================
🧙 MERGE WIZARD v4.1
========================================
1) Merge novo (cria pasta base)
2) Update (incremental)
* Barra de carregamento detalhada
* (A)(M)(D) no topo dos arquivos
* Log estilo git --name-status
""")

def ask(msg):
    return input(msg + ": ").strip().strip('"')

def confirm(msg):
    return input(f"{msg} [s/N]: ").lower().startswith("s")

# ---------------- File helpers ----------------

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
    out = []
    for r, _, fs in os.walk(root):
        for f in fs:
            out.append(os.path.join(r, f))
    return out

# ---------------- Progress bar ----------------

def progress(i, total, action, name):
    width = 32
    filled = int(width * i / total)
    bar = "█" * filled + "-" * (width - filled)
    print(
        f"\r[{bar}] {i}/{total} {action} {name[:70]}",
        end="",
        flush=True
    )

# ---------------- Core logic ----------------

def compute_maps(base, src):
    b = {os.path.relpath(f, base): f for f in all_files(base)}
    s = {os.path.relpath(f, src): f for f in all_files(src)}
    return b, s, sorted(set(b) | set(s))

def merge_new(base, src, out):
    print("\n📂 Copiando BASE para nova pasta...")
    shutil.copytree(base, out)
    update(out, src)

def update(base_out, src):
    print("\n🔄 UPDATE incremental iniciado")

    base_files, src_files, keys = compute_maps(base_out, src)
    total = len(keys)

    log_path = os.path.join(base_out, LOG_FILE)
    log = open(log_path, "w", encoding="utf-8")

    A = M = D = 0

    for i, rel in enumerate(keys, 1):
        b = base_files.get(rel)
        s = src_files.get(rel)
        out = os.path.join(base_out, rel)

        # ADD
        if not b and s:
            write_file(out, "(A)\n" + read_file(s))
            log.write(f"A {rel}\n")
            A += 1
            action = "A"

        # DELETE (log only)
        elif b and not s:
            log.write(f"D {rel}\n")
            D += 1
            action = "D"

        # MODIFY
        elif b and s:
            btxt = read_file(b)
            stxt = read_file(s)

            if btxt == stxt:
                continue

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
            action = "M"
        else:
            continue

        progress(i, total, action, rel)
        time.sleep(0.005)

    log.close()

    print("\n\n📊 UPDATE FINALIZADO")
    print(f"(A) {A}  (M) {M}  (D) {D}")
    print(f"📄 Log salvo em: {log_path}")

# ---------------- Main ----------------

def main():
    banner()

    mode = ask("Modo (1=merge novo / 2=update)")

    base = os.path.abspath(ask("📌 Caminho BASE / DESTINO"))
    src  = os.path.abspath(ask("📌 Caminho ORIGEM"))

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
        sys.exit(1)

    print("\n✅ Operação concluída")

if __name__ == "__main__":
    main()
