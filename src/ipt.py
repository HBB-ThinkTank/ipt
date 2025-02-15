import json
import sys
import os
import shutil
from datetime import datetime
import math
import tempfile

# Skript- und Konfigurationsversionen
SCRIPT_VERSION = "0.1.0"
MIN_CONFIG_VERSION = "0.0.3"

######################################################################## 
####                KONFIGURATION & EINSTELLUNGEN                   ####
######################################################################## 

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
print(f"{config['program']['name']} - Version {SCRIPT_VERSION}\nCopyright 2025 HBB under AGPLv3")


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

process_cli_args()

######################################################################## 
####                    LOGGING & DEBUGGING                         ####
######################################################################## 

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

def debug_log(message, level=1):
    if config['parameters'].get('debug', 0) >= level:
        print(f"[DEBUG] {message}")

######################################################################## 
####                         HAUPTPROGRAMM                          ####
######################################################################## 

def process_images(base_folder, input_folder=None):
    """Hauptverarbeitung für einen Basisordner."""
    
    # Einzelmodus - der Bilderordner ist bereits definiert
    if input_folder != None:
        subfolder_images = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(('.jpg', '.jpeg'))]
        subfolder_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]
        subfolder_subfolders = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, f))]
        num_subfolder_images = len(subfolder_images)  # Anzahl der gefundenen JPEG-Bilder im Unterordner
        image_subfolder = input_folder
        print(f"[INFO] Bildverarbeitung des Ordners {image_subfolder}\n")
        log_message(f"Bildverarbeitung des Ordners {image_subfolder}\n")
    else:
    # Batchmodus - die Anzahl der Bilderordner ist nicht bekannt
    # Prüfung der Anzahl der Bilderordner
        image_folders = []
        for subfolder in os.listdir(base_folder):
            image_folder_path = os.path.join(base_folder, subfolder)
            if os.path.isdir(image_folder_path):  # Stellt sicher, dass nur Ordner verarbeitet werden
                image_folders.append(image_folder_path)
        
        num_image_folders = len(image_folders)  # Anzahl der gefundenen Ordner
        
        if num_image_folders == 0:
            print(f"[ERROR] Kein Bilderordner gefunden! Skript bricht ab.")
            log_message(f"[ERROR] Kein Bilderordner gefunden! Skript bricht ab.")
            return
        elif num_image_folders > 1:
            print(f"[ERROR] Zu viele Unterordner gefunden! Es kann nur einen geben! Skript bricht ab.")
            log_message(f"[ERROR] Es wurden {num_image_folders} Unterordner in {base_folder} gefunden! Es kann nur einen geben! Skript bricht ab.")
            return
        else:
            image_subfolder = image_folders[0]
            subfolder_images = [os.path.join(image_subfolder, f) for f in os.listdir(image_subfolder) if f.lower().endswith(('.jpg', '.jpeg'))]
            subfolder_files = [os.path.join(image_subfolder, f) for f in os.listdir(image_subfolder) if os.path.isfile(os.path.join(image_subfolder, f))]
            subfolder_subfolders = [os.path.join(image_subfolder, f) for f in os.listdir(image_subfolder) if os.path.isdir(os.path.join(image_subfolder, f))]
            num_subfolder_images = len(subfolder_images)  # Anzahl der gefundenen JPEG-Bilder im Unterordner
            print(f"[INFO] Bildverarbeitung des Ordners {image_subfolder}\n")
            log_message(f"Bildverarbeitung des Ordners {image_subfolder}\n")
    
    # Debug/Log-Ausgabe der Bildanzahl im Bilderordner
    debug_log(f"[INFO] Gefundene Bilder im Bilderordner: {num_subfolder_images}", 2)
    log_message(f"Gefundene Bilder im Bilderordner: {num_subfolder_images}", 2)

    # Prüfung der Anzahl der JPEG-Bilder im Bilderordner
    if num_subfolder_images == 0:
        if config['parameters']['abort_no_jpeg'] == 1:
            print(f"[ERROR] Es wurden keine optimierbaren Bilder gefunden! Skript bricht ab.")
            log_message(f"[ERROR] Es wurden keine optimierbaren Bilder gefunden! Skript bricht ab.")
            return
        else:
            print(f"[INFO] Es wurden keine optimierbaren Bilder gefunden! Der Ordner wird weiterverarbeitet.")
            log_message(f"Es wurden keine optimierbaren Bilder gefunden! Der Ordner wird weiterverarbeitet.")
    
    # Prüfen der Bilder zum Erstellen der Collage und des Single Images

    image_files = find_image_files(base_folder)
    num_images = len(image_files)  # Anzahl der gefundenen Collage-Bilder

    # Debug/Log-Ausgabe der Bildanzahl
    debug_log(f"[INFO] Gefundene Collage-Bilder: {num_images}", 2)
    log_message(f"Gefundene Collage-Bilder: {num_images}", 2)

    # Prüfung der Anzahl der Bilder
    if num_images == 4:
        debug_log("Alle vier Collage-Bilder vorhanden.", 2)
        log_message("Alle vier Collage-Bilder vorhanden.")
    elif num_images == 0:
        if config['parameters']['abort_missing_001_004'] == 1:
            print(f"[ERROR] Keines der 4 Collage-Bilder (001-004) gefunden! Skript bricht ab.")
            log_message(f"[ERROR] Keines der 4 Collage-Bilder (001-004) gefunden! Skript bricht ab.")
            return
        elif config['parameters']['abort_missing_001_004'] == 2:
            debug_log("Keine Collage-Bilder vorhanden, versuche automatische Auswahl...", 2)
            log_message("Keine Collage-Bilder vorhanden, versuche automatische Auswahl...", 2)
            if num_subfolder_images >= 4:
                image_files = auto_select_images(subfolder_images)  # Automatische Auswahl durchführen
                if image_files:
                    pass
                else:  # Falls auto_select_images keine Bilder liefern konnte
                    print(f"[ERROR] Automatische Auswahl fehlgeschlagen! Skript bricht ab.")
                    log_message(f"[ERROR] Automatische Auswahl fehlgeschlagen! Skript bricht ab.")
                    return
            else:
                print(f"[ERROR] Keines der 4 Collage-Bilder (001-004) gefunden! Skript bricht ab.")
                log_message(f"[ERROR] Keines der 4 Collage-Bilder (001-004) gefunden! Skript bricht ab.")
                return
    else:  # Falls nur 1-3 Bilder vorhanden sind
        if config['parameters']['abort_incomplete_001_004'] == 1:
            print(f"[ERROR] Nur {num_images} von 4 Collage-Bildern gefunden! Skript bricht ab.")
            log_message(f"[ERROR] Nur {num_images} von 4 Collage-Bildern gefunden! Skript bricht ab.")
            return
        else:
            debug_log(f"Nur {num_images} Collage-Bilder gefunden. Verwende erstes für Single Image.", 2)
            log_message(f"Nur {num_images} Collage-Bilder gefunden. Verwende erstes für Single Image.")
            image_files = [image_files[0]]  # Nur das erste Bild für Single Image nutzen
    
    temp_abs_path = os.path.abspath(config['paths']['temp_folder'])
    output_abs_path = os.path.abspath(config['paths']['output_folder'])
    base_abs_path = os.path.abspath(base_folder)
    
    if any(os.path.commonpath([p1]) == os.path.commonpath([p1, p2])
       for p1, p2 in [
           (base_abs_path, temp_abs_path),
           (base_abs_path, output_abs_path),
           (output_abs_path, temp_abs_path)
       ]):
           temp_folder = get_safe_temp_folder(base_folder, config['paths']['output_folder'])
    else:
        temp_folder = config['paths']['temp_folder']

    if subfolder_subfolders:
        print(f"[WARN] Es wurden {len(subfolder_subfolders)} Unterordner gefunden, diese werden ignoriert!")
        log_message(f"[WARN] Es wurden {len(subfolder_subfolders)} Unterordner gefunden, diese werden ignoriert!")

    copy_images(image_files, temp_folder)
    copy_images(subfolder_files, os.path.join(temp_folder, os.path.basename(image_subfolder)))
    
def find_image_files(base_folder):
    """Sucht nach vier Bildern mit erlaubten Endungen."""
    candidates = ["001", "002", "003", "004"]
    extensions = ['.jpg', '.jpeg', '.png']
    image_paths = []

    for base in candidates:
        found = False
        for ext in extensions:
            path = os.path.join(base_folder, base + ext)
            if os.path.exists(path):
                image_paths.append(path)
                found = True
                break
        if not found:
            debug_log(f"Bild {base} nicht gefunden in {base_folder}", 2)
            log_message(f"Bild {base} nicht gefunden in {base_folder}", 2)
    return image_paths

def auto_select_images(subfolder_images):
    """Wählt automatisch 4 Bilder aus einer Liste von JPEGs für die Collage."""
    
    num_images = len(subfolder_images)
    
    if num_images < 4:
        print("[ERROR] Zu wenige Bilder für automatische Auswahl!")
        log_message("[ERROR] Zu wenige Bilder für automatische Auswahl!")
        return None  # Falls weniger als 4 Bilder vorhanden sind, bricht es ab.

    max_index = num_images - 1  # Der höchste Index der Liste
    
    # Berechnung der Indizes mit Rundung
    index_001 = 0
    index_002 = max(1, round(max_index * 0.3))
    index_003 = max(index_002 + 1, round(max_index * 0.6))
    index_004 = max(index_003 + 1, round(max_index * 0.9))
    
    # Sicherstellen, dass die Indizes gültig bleiben
    index_002 = min(index_002, max_index)
    index_003 = min(index_003, max_index)
    index_004 = min(index_004, max_index)
    
    selected_images = [
        subfolder_images[index_001],
        subfolder_images[index_002],
        subfolder_images[index_003],
        subfolder_images[index_004]
    ]

    # Nur Dateinamen extrahieren
    filenames = [os.path.basename(img) for img in selected_images]
    
    # Übergeordneten Ordner extrahieren (alle Bilder sollten aus demselben Ordner sein)
    parent_folder = os.path.basename(os.path.dirname(selected_images[0]))

    # Benutzerfreundliche Ausgabe
    formatted_files = f"{filenames[0]}, {filenames[1]}, {filenames[2]} und {filenames[3]}"
    print(f"[INFO] Automatisch gewählte Bilder: {formatted_files} aus dem Ordner {parent_folder}")
    log_message(f"Automatisch gewählte Bilder: {formatted_files} aus dem Ordner {parent_folder}")

    return selected_images

def get_safe_temp_folder(base_folder, output_folder):
    """Ermittelt einen sicheren Temp-Ordner, wechselt falls nötig zu einem alternativen Speicherort."""
    
    try:
        temp_folder = os.path.join(tempfile.gettempdir(), "ipt_temp")
        os.makedirs(temp_folder, exist_ok=True)  # Falls nicht vorhanden, erstellen
        return temp_folder
    
    except PermissionError:
        debug_log("[WARN] Kein Schreibzugriff auf systemweiten Temp-Ordner! Nutze Alternativen...", 2)
        log_message("[WARN] Kein Schreibzugriff auf systemweiten Temp-Ordner! Nutze Alternativen...", 2)

        # Alternative 1: User-spezifischer Temp-Ordner
        user_temp = os.path.expanduser("~")
        if user_temp:
            fallback_folder = os.path.join(user_temp, ".ipt_temp")
            try:
                os.makedirs(fallback_folder, exist_ok=True)
                return fallback_folder
            except PermissionError:
                debug_log("[ERROR] Kein Zugriff auf Benutzer-Temp! Wechsle zu letztem Fallback...", 2)
                log_message("[ERROR] Kein Zugriff auf Benutzer-Temp! Wechsle zu letztem Fallback...", 2)

        # Alternative 2: Output-Ordner als letzten Fallback nehmen
        if not os.path.commonpath([base_folder]) == os.path.commonpath([base_folder, output_folder]):
            return os.path.join(output_folder, "ipt_temp")

        print("[ERROR] Kein sicherer Temp-Ordner gefunden! Skript bricht ab.")
        log_message("[ERROR] Kein sicherer Temp-Ordner gefunden! Skript bricht ab.")
        sys.exit(1)

def copy_images(file_list, target_folder):
    """Kopiert eine Liste von Dateien in einen Ziel-Ordner."""
    
    os.makedirs(target_folder, exist_ok=True)  # Sicherstellen, dass der Temp-Ordner existiert

    for file in file_list:
        if os.path.exists(file):  # Sicherheitscheck, ob die Datei existiert
            dst = os.path.join(target_folder, os.path.basename(file))
            shutil.copy2(file, dst)  # Metadaten erhalten
            log_message(f"Kopiert: {file} → {dst}", 2)
        else:
            log_message(f"[WARN] Datei nicht gefunden und wurde nicht kopiert: {file}")

    print(f"[INFO] {len(file_list)} Dateien nach {target_folder} kopiert.")
    log_message(f"{len(file_list)} Dateien nach {target_folder} kopiert.")

######################################################################## 
####                    NACHBEREITUNG & SÄUBERN                     ####
######################################################################## 

def clear_temp_folder():
    temp_folder = config['paths']['temp_folder']
    if config['parameters'].get('empty', 0) == 1:
        if os.path.exists(temp_folder):
            try:
                shutil.rmtree(temp_folder)
                print(f"[INFO] Temp-Ordner '{temp_folder}' wurde gelöscht.")
            except Exception as e:
                print(f"[ERROR] Konnte Temp-Ordner nicht löschen: {e}")

clear_temp_folder()

######################################################################## 
####                           MAIN CORE                            ####
######################################################################## 

def main(config):
    """Hauptfunktion zur Steuerung der Bildverarbeitung."""
    debug_log("Programmstart")
    log_message("Programmstart")
    debug_log("Programm erfolgreich gestartet", 2)

    # Einzelmodus
    if config['parameters']['batch_mode'] == 0:
        base_folder = os.path.dirname(config['paths']['base_folder_single'])
        subfolder = config['paths']['base_folder_single']
        log_message(f"Einzelmodus beginnt", 2)
        process_images(base_folder, subfolder)
    # Batchmodus
    else:
        input_folder = config['paths']['base_folder_batch']
        for subfolder in os.listdir(input_folder):
            base_folder = os.path.join(input_folder, subfolder)
            if os.path.isdir(base_folder):  # Stellt sicher, dass nur Ordner verarbeitet werden
                log_message(f"Batchmodus beginnt", 2)
                process_images(base_folder)

if __name__ == "__main__":
    main(config)