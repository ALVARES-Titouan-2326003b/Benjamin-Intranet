import subprocess
import sys
import time
import os
import signal

def main():
    print(f"🚀 Démarrage de l'environnement de développement sur {sys.platform}...")
    python_exe = sys.executable

    # Définition des commandes
    worker_cmd = [python_exe, "-m", "celery", "-A", "config", "worker", "--loglevel=info"]
    
    if sys.platform == "win32":
        worker_cmd.append("--pool=solo")

    cmds = [
        # (Nom, Commande)
        ("Celery Worker", worker_cmd),
        ("Celery Beat",   [python_exe, "-m", "celery", "-A", "config", "beat", "--loglevel=info"]),
        ("Django Server", [python_exe, "manage.py", "runserver"])
    ]

    procs = []

    try:
        for name, cmd in cmds:
            print(f"✅ Lancement de {name}...")
            if sys.platform == "win32":
                p = subprocess.Popen(cmd, shell=False)
            else:
                p = subprocess.Popen(cmd, shell=False, preexec_fn=os.setsid)
            
            procs.append(p)
            time.sleep(1)

        print("\n Tous les services sont lancés ! Appuyez sur CTRL+C pour arrêter.")
        
        while True:
            time.sleep(1)
            for i, p in enumerate(procs):
                if p.poll() is not None:
                    print(f" Le processus {cmds[i][0]} s'est arrêté inopinément.")
                    raise KeyboardInterrupt

    except KeyboardInterrupt:
        print("\n Arrêt demandé, nettoyage des processus...")
    finally:
        for p in procs:
            if p.poll() is None:
                print(f"Killing PID {p.pid}...")
                if sys.platform == "win32":
                    p.terminate() 
                else:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        print("Terminé.")

if __name__ == "__main__":
    main()
