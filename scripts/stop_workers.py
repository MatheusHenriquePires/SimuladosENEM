from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parent.parent
STOP = ROOT / "backend" / "STOP_WORKERS"


def create_stop():
    STOP.write_text("stop", encoding='utf-8')
    print(f"Arquivo de parada criado: {STOP}")


def try_kill_local_python_procs():
    try:
        import psutil
    except Exception:
        print("psutil não disponível — só criei o arquivo de parada.")
        return

    # Tenta identificar processos Python que têm cwd dentro do projeto e terminá-los
    cwd = str(ROOT)
    for proc in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
        try:
            p_cwd = proc.info.get('cwd')
            if p_cwd and cwd in str(p_cwd):
                print(f"Terminando PID {proc.pid} - {proc.name()} (cwd: {p_cwd})")
                proc.terminate()
        except Exception as e:
            print(f"Falha ao avaliar/terminar processo: {e}")


if __name__ == '__main__':
    create_stop()
    # opcional: tentar matar processos Python locais
    try_kill_local_python_procs()
    print("Feito.")
