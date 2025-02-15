import json
import sys
import os
import shutil
from datetime import datetime

# Skript- und Konfigurationsversionen
SCRIPT_VERSION = "0.0.3"
MIN_CONFIG_VERSION = "0.0.3"

def load_config(file_path="config.json"):

# AB HIER AUS DER TEST VERSION KOPIEREN

    with open(file_path, "r") as f:
        config = json.load(f)

    # Versionsprüfung
    config_version = config['program']['version']
    if config_version < MIN_CONFIG_VERSION:
        print(f"[ERROR] Inkompatible Config-Version: {config_version}. Benötigt wird mindestens {MIN_CONFIG_VERSION}.")
        sys.exit(1)

    return config

config = load_config()

# Prüfung ob die Tool-Executables erreichbar sind
def verify_tool_paths():
    missing_tools = []
    
    for tool, data in config["tools"].items():
        tool_path = data["path"]
        if not os.path.exists(tool_path):
            missing_tools.append(tool)
            print(f"[ERROR] Tool '{tool}' nicht gefunden: {tool_path}")

    if missing_tools:
        print("[ERROR] Die folgenden Tools fehlen oder die Pfade sind falsch:")
        print(", ".join(missing_tools))
        sys.exit(1)  # Beenden, falls wichtige Tools fehlen
    else:
        print("[INFO] Alle benötigten Tools sind vorhanden.")

# Diese Funktion sollte nach dem Laden der Config, aber vor der Verarbeitung der CLI-Parameter aufgerufen werden:
verify_tool_paths()

# CLI-Parameter verarbeiten
def process_cli_args():
    for arg in sys.argv[1:]:
        # Debug-Level
        if arg.startswith("debug=") or arg.startswith("d="):
            try:
                debug_level = int(arg.split("=")[1])
                if debug_level in (0, 1, 2):
                    config['parameters']['debug'] = debug_level
                    print(f"[INFO] Debug-Level auf {debug_level} gesetzt (override)")
                else:
                    print("[WARN] Ungültiger Debug-Level. Erlaubt: 0, 1, 2")
            except ValueError:
                print("[ERROR] Debug-Level muss eine Zahl sein (0 oder 1)")

        # Log-Level
        if arg.startswith("log=") or arg.startswith("l="):
            try:
                log_level = int(arg.split("=")[1])
                if log_level in (0, 1, 2):
                    config['parameters']['loglevel'] = log_level
                    print(f"[INFO] Log-Level auf {log_level} gesetzt (override)")
                else:
                    print("[WARN] Ungültiger Log-Level. Erlaubt: 0, 1, 2")
            except ValueError:
                print("[ERROR] Log-Level muss eine Zahl sein (0 oder 1)")

        # Batch-Modus
        if arg.startswith("batch_mode=") or arg.startswith("b="):
            try:
                batch_mode = int(arg.split("=")[1])
                if batch_mode in (0, 1):
                    config['parameters']['batch_mode'] = batch_mode
                    print(f"[INFO] Batch-Modus auf {batch_mode} gesetzt (override)")
                else:
                    print("[WARN] Ungültiger Batch-Modus. Erlaubt: 0, 1")
            except ValueError:
                print("[ERROR] Batch-Modus muss eine Zahl sein (0 oder 1)")

        # Single-Image
        if arg.startswith("single_image=") or arg.startswith("si="):
            try:
                single_image = int(arg.split("=")[1])
                if single_image in (0, 1):
                    config['parameters']['single_image'] = single_image
                    print(f"[INFO] Single-Image auf {single_image} gesetzt (override)")
                else:
                    print("[WARN] Ungültiges Single-Image. Erlaubt: 0, 1")
            except ValueError:
                print("[ERROR] Single-Image muss eine Zahl sein (0 oder 1)")

        # Collage
        if arg.startswith("collage=") or arg.startswith("c="):
            try:
                collage = int(arg.split("=")[1])
                if collage in (0, 1):
                    config['parameters']['collage'] = collage
                    print(f"[INFO] Collage auf {collage} gesetzt (override)")
                else:
                    print("[WARN] Ungültige Collage-Einstellung. Erlaubt: 0, 1")
            except ValueError:
                print("[ERROR] Collage muss eine Zahl sein (0 oder 1)")

        # Input-Ordner
        if arg.startswith("i="):
            input_folder = os.path.abspath(arg.split("=")[1])
            if not os.path.exists(input_folder):
                print(f"[ERROR] Der angegebene Input-Ordner '{input_folder}' existiert nicht!")
                sys.exit(1)
            elif config['parameters']['batch_mode'] == 0:
                config['paths']['base_folder_single'] = input_folder
                print(f"[INFO] Input-Ordner für Einzelmodus auf '{input_folder}' gesetzt (override)")
            else:
                config['paths']['base_folder_batch'] = input_folder
                print(f"[INFO] Input-Ordner für Batchmodus auf '{input_folder}' gesetzt (override)")

        # Output-Ordner
        if arg.startswith("o="):
            output_folder = os.path.abspath(arg.split("=")[1])
            if not os.path.exists(output_folder):
                try:
                    os.makedirs(output_folder)
                    print(f"[INFO] Output-Ordner '{output_folder}' wurde erstellt.")
                except Exception as e:
                    print(f"[ERROR] Der Output-Ordner konnte nicht erstellt werden: {e}")
                    sys.exit(1)
            config['paths']['output_folder'] = output_folder
            print(f"[INFO] Output-Ordner auf '{output_folder}' gesetzt (override)")

        # CLI-Parameter für das Logging verarbeiten
        if arg.startswith("log="):
            log_override_mapping = {
                "t": "temp",
                "i": "input",
                "o": "output",
                "d": "default"
            }
            log_value = arg.split("=")[1].lower()
            
            if log_value in log_override_mapping:
                config["logging"]["log_override"] = log_override_mapping[log_value]
                print(f"[INFO] Log-Override auf '{log_override_mapping[log_value]}' gesetzt (override)")
            else:
                print("[WARN] Ungültiger Log-Override. Erlaubte Werte: t (temp), i (input), o (output), d (default)")

def log_message(message, log_level=1):
    """Schreibt eine Lognachricht je nach gewähltem Log-Level."""
    
    # Log-Level-Filterung
    if config['parameters']['loglevel'] == 0:
        return
    if config['parameters']['loglevel'] < log_level:
        return

    # Speicherort bestimmen
    if config['logging']['log_override'] == 't':
        folder = config['paths']['temp_folder']
    elif config['logging']['log_override'] == 'i':
        if config['parameters']['batch_mode'] == 0:
            folder = config['paths']['base_folder_single']
        else:
            folder = config['paths']['base_folder_batch']
    elif config['logging']['log_override'] == 'o':
        folder = config['paths']['output_folder']
    else:
        folder = config['logging']['log_folder']
    
    # Log-Dateinamen bestimmen
    if config['logging']['log_mode'] == 'append':
        log_file_name = "ipt.log"
    else:
        log_file_name = f"ipt_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"

    # Log-Dateipfad erstellen
    os.makedirs(folder, exist_ok=True)
    log_file = os.path.join(folder, log_file_name)
    
    # Zeitstempel generieren
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log-Dateigröße überprüfen
    MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
    if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_LOG_SIZE:
        archive_name = f"{os.path.splitext(log_file)[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
        os.rename(log_file, archive_name)
        print(f"[INFO] Log-Datei zu '{archive_name}' umbenannt, da sie zu groß wurde.")
        
    # Log-Level Tag setzen
    log_levels = {0: "NONE", 1: "INFO", 2: "DEBUG"}
    level_tag = log_levels.get(log_level, "INFO")  # Standard ist INFO

    # Log-Nachricht schreiben
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level_tag}] {message}\n")

def process_images(base_folder):
        return

def clear_temp_folder():
    temp_folder = config['paths']['temp_folder']
    if config['parameters'].get('empty', 0) == 1:
        if os.path.exists(temp_folder):
            try:
                shutil.rmtree(temp_folder)
                print(f"[INFO] Temp-Ordner '{temp_folder}' wurde gelöscht.")
            except Exception as e:
                print(f"[ERROR] Konnte Temp-Ordner nicht löschen: {e}")

process_cli_args()
clear_temp_folder()

def debug_log(message, level=1):
    if config['parameters'].get('debug', 0) >= level:
        print(f"[DEBUG] {message}")

def main(config):
    """Hauptfunktion zur Steuerung der Bildverarbeitung."""
    debug_log("Programmstart")
    log_message("Programmstart")
    print(f"{config['program']['name']} - Version {SCRIPT_VERSION}")
    debug_log("Programm erfolgreich gestartet", 2)

    if config['parameters']['batch_mode'] == 0:
        base_folder = os.path.dirname(config['paths']['base_folder_single'])
        process_images(base_folder)
    else:
        input_folder = config['paths']['base_folder_batch']
        for subfolder in os.listdir(input_folder):
            base_folder = os.path.join(input_folder, subfolder)
            if os.path.isdir(base_folder):  # Stellt sicher, dass nur Ordner verarbeitet werden
                process_images(base_folder)

if __name__ == "__main__":
    main(config)
