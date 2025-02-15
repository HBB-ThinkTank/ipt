import json
import sys
import os
import shutil

# Skript- und Konfigurationsversionen
SCRIPT_VERSION = "0.0.2"
MIN_CONFIG_VERSION = "0.0.1"

def load_config(file_path="config.json"):
    with open(file_path, "r") as f:
        config = json.load(f)

    # Versionsprüfung
    config_version = config['program']['version']
    if config_version < MIN_CONFIG_VERSION:
        print(f"[ERROR] Inkompatible Config-Version: {config_version}. Benötigt wird mindestens {MIN_CONFIG_VERSION}.")
        sys.exit(1)

    return config

config = load_config()

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
    debug_log("Programmstart")
    print(f"{config['program']['name']} - Version {SCRIPT_VERSION}")
    debug_log("Programm erfolgreich gestartet", 2)

if __name__ == "__main__":
    main(config)

