import sys
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

# NOTA: Non importare interface qui per evitare crash se mancano le dipendenze (yt_dlp)
# import interface  <-- RIMOSSO DA QUI

# Controllo Avvio
# Se il flag "--verified" non è presente, assume che sia il primo avvio e delega a checker.py
if "--verified" not in sys.argv:
    checker_path = "checker.py"
    if os.path.exists(checker_path):
        try:
            # Avvia checker.py che gestirà il controllo dipendenze e l'eventuale apertura di updater.py
            # Se tutto ok, checker.py dovrà rilanciare questo script con: subprocess.Popen([sys.executable, "main.py", "--verified"])
            subprocess.Popen([sys.executable, checker_path])
            sys.exit()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore critico avvio checker: {e}")
            sys.exit()
    else:
        # Se checker.py non esiste, prova ad avviarsi comunque (o gestisci l'errore come preferisci)
        pass 

if __name__ == "__main__":
    try:
        # Importa l'interfaccia SOLO ORA, quando siamo sicuri (grazie a --verified) che le lib ci sono.
        import interface
    except ImportError as e:
        messagebox.showerror("Errore Fatale", f"Impossibile avviare l'interfaccia.\n\nErrore: {e}\n\nAssicurati che tutte le dipendenze siano installate.")
        sys.exit()

    root = tk.Tk()
    app = interface.DownloaderApp(root)
    root.mainloop()
