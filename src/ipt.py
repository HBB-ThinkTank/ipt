import json
import sys
import os
import shutil
from datetime import datetime
import math
import tempfile
from PIL import Image, ImageFilter
import hashlib
import subprocess
import zipfile

# Skript- und Konfigurationsversionen TEST VERION
SCRIPT_VERSION = "0.9.0"
MIN_CONFIG_VERSION = "0.9.0"

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
        log_file_name = f"ipt_{LOG_TIMESTAMP}.log"

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
    if config['parameters']['single_image'] == 0 and config['parameters']['collage'] == 0:
        pass
    else:
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
                    if len(image_files) == 4:
                        if config['parameters']['collage'] == 1:
                            log_message("Vier Collage-Bilder ausgewählt.")
                        else:
                            log_message(" Ein Bild für das Cover-Image wurde ausgewählt.")
                    elif len(image_files) >= 1:
                        if config['parameters']['collage'] == 1:
                            print("Es wird nur das Cover-Bild erstellt.")
                            log_message("Es wird nur das Cover-Bild erstellt.")
                            config['parameters']['collage'] = 0
                        else:
                            log_message(" Ein Bild für das Cover-Image wurde ausgewählt.")
                    else:  # Falls auto_select_images keine Bilder liefern konnte
                        print(f"[DEBUG] Keines der 4 Collage-Bilder (001-004) gefunden! Es wird nur der Bilderordner bearbeitet.")
                        log_message(f"[DEBUG] Automatische Auswahl fehlgeschlagen! Es wird nur der Bilderordner bearbeitet.")
                        config['parameters']['single_image'] = 0
                        config['parameters']['collage'] = 0
                elif num_subfolder_images >= 1:
                    image_files = auto_select_images(subfolder_images)  # Automatische Auswahl durchführen
                    if image_files:
                        print("Es wird nur das Cover-Bild erstellt.")
                        log_message("Es wird nur das Cover-Bild erstellt.")
                        config['parameters']['collage'] = 0
                    else:  # Falls auto_select_images keine Bilder liefern konnte
                        print(f"[DEBUG] Keines der 4 Collage-Bilder (001-004) gefunden! Es wird nur der Bilderordner bearbeitet.")
                        log_message(f"[DEBUG] Automatische Auswahl fehlgeschlagen! Es wird nur der Bilderordner bearbeitet.")
                        config['parameters']['single_image'] = 0
                        config['parameters']['collage'] = 0
                else:
                    print(f"[DEBUG] Keines der 4 Collage-Bilder (001-004) gefunden! Es wird nur der Bilderordner bearbeitet.")
                    log_message(f"Keines der 4 Collage-Bilder (001-004) gefunden! Es wird nur der Bilderordner bearbeitet.")
                    config['parameters']['single_image'] = 0
                    config['parameters']['collage'] = 0
            else:
                print(f"[DEBUG] Keines der 4 Collage-Bilder (001-004) gefunden! Es wird nur der Bilderordner bearbeitet.")
                log_message(f"Keines der 4 Collage-Bilder (001-004) gefunden! Es wird nur der Bilderordner bearbeitet.")
                config['parameters']['single_image'] = 0
                config['parameters']['collage'] = 0
        else:  # Falls nur 1-3 Bilder vorhanden sind
            if config['parameters']['abort_incomplete_001_004'] == 1:
                print(f"[ERROR] Nur {num_images} von 4 Collage-Bildern gefunden! Skript bricht ab.")
                log_message(f"[ERROR] Nur {num_images} von 4 Collage-Bildern gefunden! Skript bricht ab.")
                return
            else:
                debug_log(f"Nur {num_images} Collage-Bilder gefunden. Verwende erstes für Single Image.", 2)
                log_message(f"Nur {num_images} Collage-Bilder gefunden. Verwende erstes für Single Image.")
                image_files = [image_files[0]]  # Nur das erste Bild für Single Image nutzen
                config['parameters']['collage'] = 0
    
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

    image_subfolder_basename = os.path.basename(image_subfolder)

    # Kopieren der Dateien in die temporären Ordner
    copy_images(image_files, temp_folder)
    temp_subfolder = os.path.join(temp_folder, image_subfolder_basename)
    copy_images(subfolder_files, temp_subfolder)
    
    # Auflisten der Dateien zur Weiterverarbeitung
    collage_temp_images = find_image_files(temp_folder)
    temp_subfolder_images = [os.path.join(temp_subfolder, f) for f in os.listdir(temp_subfolder) if f.lower().endswith(('.jpg', '.jpeg'))]
    temp_subfolder_files = [os.path.join(temp_subfolder, f) for f in os.listdir(temp_subfolder) if os.path.isfile(os.path.join(temp_subfolder, f))]

    # Überprüfung der Datei-Integrität
    verify_file_integrity(subfolder_files, temp_subfolder_files)

    # Ermitteln des Seitenverhältnisses der Bilder Single Image und Collage (Breite-zu-Höhe)
    meta_images = []
    if config['parameters']['single_image'] == 0 and config['parameters']['collage'] == 0:
        pass
    else:
        # Standardwerte aus der Config
        target_width = config['parameters']['image_width']
        target_height = config['parameters']['image_height']
        aspect_ratio = target_width / target_height
        
        # Seitenverhältnis bestimmen
        if config['parameters']['aspect_ratio_mode'] == 0:
            pass
        elif config['parameters']['aspect_ratio_mode'] == 1:
            ref_width, ref_height = get_image_size(collage_temp_images[0])
            aspect_ratio = ref_width / ref_height
        elif config['parameters']['aspect_ratio_mode'] == 2:
            if temp_subfolder_images:
                ref_width, ref_height = get_image_size(temp_subfolder_images[0])
                aspect_ratio = ref_width / ref_height
        else:
            try:
                ref_width, ref_height = map(float, config['parameters']['manual_aspect_ratio'].split(":"))
                aspect_ratio = ref_width / ref_height
            except:
                print("[ERROR] Ungültiges manuelles Seitenverhältnis! Nutze Standard.")
                log_message("[ERROR] Ungültiges manuelles Seitenverhältnis! Nutze Standard.")
        
        # Größenanpassung je nach size_override
        if config['parameters']['size_override'] == 1:
            target_width = round(target_height * aspect_ratio)
        elif config['parameters']['size_override'] == 2:
            target_height = round(target_width / aspect_ratio)
        else:
            # Standard: Breite/Höhe unter max. Werten lassen
            if target_width / target_height > aspect_ratio:
                target_width = round(target_height * aspect_ratio)
            else:
                target_height = round(target_width / aspect_ratio)
        
        # Wenn Collage: dann müssen die Seiten durch 2 teilbar sein
        if config['parameters']['collage'] == 1:
            target_width = 2 * round(target_width / 2)
            target_height = 2 * round(target_height / 2)
            
        debug_log(f"Die Coverbilder werden mit {target_width}px weit und {target_height}px hoch erstellt.", 2)
        log_message(f"Die Coverbilder werden mit {target_width}px weit und {target_height}px hoch erstellt.", 2)
        
        # Single Image erstellen
        if config['parameters']['single_image'] == 1 and collage_temp_images:
            if config['parameters']['collage'] == 0:
                single_image_path = os.path.join(os.path.dirname(collage_temp_images[0]), image_subfolder_basename) + '.jpg'
            else:
                single_image_path = os.path.join(os.path.dirname(collage_temp_images[0]), image_subfolder_basename) + ' cover.jpg'
                
            resize_and_pad_image(collage_temp_images[0], target_width, target_height, single_image_path)
            debug_log("Das Cover-Image wurde erstellt.", 2)
            log_message("Das Cover-Image wurde erstellt.", 2)
            meta_images.append(single_image_path)
        
        # Collage erstellen
        if config['parameters']['collage'] == 1 and len(collage_temp_images) == 4:
            if config['parameters']['single_image'] == 0:
                collage_path = os.path.join(os.path.dirname(collage_temp_images[0]), image_subfolder_basename) + '.jpg'
            else:
                collage_path = os.path.join(os.path.dirname(collage_temp_images[0]), image_subfolder_basename) + ' cs.jpg'
                
            create_collage(collage_temp_images, target_width, target_height, collage_path)
            debug_log("Die Collage wurde erstellt.", 2)
            log_message("Die Collage wurde erstellt.", 2)
            meta_images.append(collage_path)
    
        optimize_images(meta_images, "single_collage_images")
        copy_images(meta_images, config['paths']['output_folder'])
        
    temp_subfolder_images = validate_jpeg_files(temp_subfolder_images)
    
    optimize_images(temp_subfolder_images, "folder_images")

    archive_objects = meta_images.copy()
    archive_objects.append(image_subfolder)

    create_best_archive(image_subfolder_basename, archive_objects)
    
    clear_temp_folder()
    
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

def file_hash(file_path):
    """Berechnet den SHA256-Hash einer Datei mit dynamischer Chunk-Größe."""
    hasher = hashlib.sha256()
    extensions = ['.jpg', '.jpeg', '.png']
    
    # Bestimme die optimale Chunk-Größe
    file_size = os.path.getsize(file_path)
    
    if file_path.lower().endswith(tuple(extensions)):
        chunk_size = 4096  # 4 KB für Bilder
    elif file_size > 4 * 1024 * 1024 * 1024:  # > 4 GB
        chunk_size = 1048576  # 1 MB
    elif file_size > 1024 * 1024 * 1024:  # > 1 GB
        chunk_size = 262144  # 256 KB
    else:
        chunk_size = 65536  # 64 KB Standard
    
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        log_message(f"[ERROR] Fehler beim Lesen der Datei {file_path}: {e}")
        return None  # Falls Datei nicht lesbar ist

def verify_file_integrity(source_files, target_files):
    """Vergleicht Original- und Kopien inhaltlich und meldet fehlende oder defekte Dateien."""
    
    # Set-Vergleich für schnelle Überprüfung
    original_files = {os.path.basename(f): f for f in source_files}
    copied_files = {os.path.basename(f): f for f in target_files}

    missing_files = set(original_files) - set(copied_files)  # Dateien, die fehlen
    extra_files = set(copied_files) - set(original_files)  # Dateien, die zu viel sind

    if missing_files:
        print(f"[ERROR] {len(missing_files)} Datei(en) fehlen nach dem Kopieren: {missing_files}")
        log_message(f"[ERROR] {len(missing_files)} Datei(en) fehlen nach dem Kopieren: {missing_files}")

    if extra_files:
        print(f"[WARN] {len(extra_files)} Datei(en) im Temp-Ordner, die nicht im Original waren: {extra_files}")
        log_message(f"[WARN] {len(extra_files)} Datei(en) im Temp-Ordner, die nicht im Original waren: {extra_files}")

    # Falls alle Dateien existieren, weiter mit Hash-Vergleich
    corrupt_files = []
    for filename in original_files:
        if filename in copied_files:
            orig_file = original_files[filename]
            temp_file = copied_files[filename]

            orig_hash = file_hash(orig_file)
            temp_hash = file_hash(temp_file)
            
            corrupt_log_message = ''
            
            if orig_hash and temp_hash and orig_hash != temp_hash:
                corrupt_files.append(filename)
                corrupt_log_message = f"\n{temp_file} (Kopie) ist beschädigt." 
                
            log_message(f"\n{os.path.basename(orig_file)} - Hash: {orig_hash} (Original)\n{os.path.basename(temp_file)} - Hash: {temp_hash} (Kopie){corrupt_log_message}", 2)


    if corrupt_files:
        print(f"[ERROR] {len(corrupt_files)} Datei(en) sind beschädigt: {corrupt_files}")
        log_message(f"[ERROR] {len(corrupt_files)} Datei(en) sind beschädigt: {corrupt_files}")

    # Endstatus
    if not missing_files and not corrupt_files:
        print(f"[INFO] Alle Dateien wurden korrekt kopiert.")
        log_message(f"[INFO] Alle Dateien wurden korrekt kopiert.")

def get_image_size(image_path):
    """Liest die Breite und Höhe eines Bildes aus."""
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception as e:
        print(f"[ERROR] Konnte Bildgröße nicht auslesen: {e}")
        log_message(f"[ERROR] Konnte Bildgröße nicht auslesen: {e}")
        return None, None

def resize_and_pad_image(image_path, target_width, target_height, output_path):
    """Skaliert das Bild auf die Zielgröße und füllt den Hintergrund mit einem unscharfen Bild."""
    try:
        with Image.open(image_path) as img:
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height

            # Berechnung der neuen Größe, um Seitenverhältnis zu bewahren
            if img_width / img_height > target_width / target_height:
                new_width = target_width
                new_height = round(target_width / aspect_ratio)
            else:
                new_height = target_height
                new_width = round(target_height * aspect_ratio)

            img_resized = img.resize((new_width, new_height), Image.LANCZOS)

            # Erstelle einen vergrößerten Hintergrund aus dem Bild
            background = img.resize((target_width, target_height), Image.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(30))  # Starke Unschärfe
            
            # Berechnung der Position für das Bild (zentriert)
            paste_x = (target_width - new_width) // 2
            paste_y = (target_height - new_height) // 2

            # Setzt das eigentliche Bild auf den verschwommenen Hintergrund
            background.paste(img_resized, (paste_x, paste_y))

            background.save(output_path, quality=100)
            
            print(f"[INFO] Das Cover-Bild transformiert und gespeichert: {output_path}")
            log_message(f"[INFO] Das Cover-Bild transformiert und gespeichert: {output_path}")

    except Exception as e:
        print(f"[ERROR] Konnte Bild nicht transformieren: {e}")
        log_message(f"[ERROR] Konnte Bild nicht transformieren: {e}")

def create_collage(image_files, target_width, target_height, output_path):
    """Erstellt eine Collage aus vier Bildern in einer 2x2-Anordnung."""
    
    try:
        # Collage-Hintergrund erstellen
        collage = Image.new("RGB", (target_width, target_height), (0, 0, 0))

        # Berechnung der Einzelbild-Größe
        single_width = target_width // 2
        single_height = target_height // 2

        positions = [(0, 0), (single_width, 0), (0, single_height), (single_width, single_height)]

        for i, img_path in enumerate(image_files):
            with Image.open(img_path) as img:
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height

                # Skalierung berechnen
                if aspect_ratio > (single_width / single_height):
                    new_width = single_width
                    new_height = round(single_width / aspect_ratio)
                else:
                    new_height = single_height
                    new_width = round(single_height * aspect_ratio)

                img_resized = img.resize((new_width, new_height), Image.LANCZOS)

                # Hintergrundbild (unscharf) erstellen
                background = img_resized.filter(ImageFilter.GaussianBlur(30))
                paste_x = (single_width - new_width) // 2
                paste_y = (single_height - new_height) // 2

                # Hintergrund in Zielgröße setzen
                background = background.resize((single_width, single_height), Image.LANCZOS)
                background.paste(img_resized, (paste_x, paste_y))

                # Bild in Collage einfügen
                collage.paste(background, positions[i])

        # Speichern der Collage
        collage.save(output_path, quality=100)
        debug_log("Die Collage wurde erstellt.", 2)
        log_message("Die Collage wurde erstellt.", 2)

    except Exception as e:
        print(f"[ERROR] Konnte Collage nicht erstellen: {e}")
        log_message(f"[ERROR] Konnte Collage nicht erstellen: {e}")

def validate_jpeg_files(image_list):
    """Überprüft, ob die JPEG-Dateien gültig sind und entfernt defekte."""
    valid_images = []

    for img_path in image_list:
        try:
            with Image.open(img_path) as img:
                img.verify()  # Erste Prüfung
            with Image.open(img_path) as img:
                img.load()  # Zweite Prüfung: Dekodiert das gesamte Bild
            valid_images.append(img_path)
        except (OSError, UnidentifiedImageError):
            print(f"[ERROR] Defekte JPEG-Datei gefunden: {os.path.basename(img_path)} - wird übersprungen.")
            log_message(f"[ERROR] Defekte JPEG-Datei gefunden: {os.path.basename(img_path)} - wird übersprungen.")

    return valid_images

def optimize_images_old(image_list, optim_profile):
    """Optimiert eine Liste von Bildern mit den Tools und Einstellungen aus config.json."""

    if not image_list:
        print("[INFO] Keine Bilder zur Optimierung vorhanden.")
        log_message("[INFO] Keine Bilder zur Optimierung vorhanden.")
        return

    # Richtige Parameter-Sektion aus der Config laden
    profile_key = f"tool_parameters_{config['profile_selection'][optim_profile]}"
    log_message(f"Lädt das Bilder-Profil {config['profile_selection'][optim_profile]} mit dem Tool-Profil {profile_key}.", 2)
    tool_params = config.get(profile_key, {})
    # Logge die Parameter der Tools
    for tool, params in tool_params.items():
        log_message(f"Parameter von {tool}: {params}", 2)

    # Tool-Reihenfolge aus der Config ermitteln oder Defaults verwenden
    tools = config['tool_order'].get(config['profile_selection'][optim_profile], list(tool_params.keys()))

    log_message(f"[DEBUG] Reihenfolge der Tools: {tools}", 2)

    for img_path in image_list:
        for tool in tools:
            tool_config = config['tools'].get(tool)
            if tool_config and tool_config['path']:
                tool_path = tool_config['path']
                tool_args = tool_params.get(tool, "")

                if tool_args:
                    cmd = f'"{tool_path}" {tool_args} "{img_path}"'
                    try:
                        # Korrektur: Resultat wird gespeichert
                        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        
                        # Tool-Output loggen
                        if result.stdout.strip():
                            log_message(f"[DEBUG] {tool} output:\n{result.stdout}", 2)
                        if result.stderr.strip():
                            log_message(f"[ERROR] {tool} Fehler:\n{result.stderr}")

                    except subprocess.CalledProcessError as e:
                        print(f"[ERROR] Fehler bei {tool}: {e}")
                        log_message(f"[ERROR] Fehler bei {tool}: {e}")

    print(f"[INFO] {len(image_list)} Bilder optimiert mit Profil '{optim_profile}'.")
    log_message(f"[INFO] {len(image_list)} Bilder optimiert mit Profil '{optim_profile}'.")

def optimize_images(image_list, optim_profile):
    """Optimiert eine Liste von Bildern mit den Tools und Einstellungen aus config.json."""

    if not image_list:
        print("[INFO] Keine Bilder zur Optimierung vorhanden.")
        log_message("[INFO] Keine Bilder zur Optimierung vorhanden.")
        return

    # Richtige Parameter-Sektion aus der Config laden
    profile_key = f"tool_parameters_{config['profile_selection'][optim_profile]}"
    log_message(f"Lädt das Bilder-Profil {config['profile_selection'][optim_profile]} mit dem Tool-Profil {profile_key}.", 2)
    tool_params = config.get(profile_key, {})

    # Logge die Parameter der Tools
    for tool, params in tool_params.items():
        log_message(f"Parameter von {tool}: {params}", 2)

    # Tool-Reihenfolge aus der Config ermitteln oder Defaults verwenden
    tools = config['tool_order'].get(config['profile_selection'][optim_profile], list(tool_params.keys()))
    log_message(f"[DEBUG] Reihenfolge der Tools: {tools}", 2)

    for img_path in image_list:
        for tool in tools:
            tool_config = config['tools'].get(tool)
            if tool_config and tool_config['path']:
                tool_path = tool_config['path']
                tool_args = tool_params.get(tool, "")

                # Falls das Tool 'guetzli' ist, wird ein temporärer Output-Pfad benötigt
                if tool == "guetzli":
                    output_path = img_path + "_optimized.jpg"  # Temporärer Pfad

                    cmd = f'"{tool_path}" {tool_args} "{img_path}" "{output_path}"'
                else:
                    cmd = f'"{tool_path}" {tool_args} "{img_path}"'  # Standard-Pfad

                try:
                    # Korrektur: Resultat wird gespeichert
                    result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    # Falls guetzli, dann das optimierte Bild zurückkopieren
                    if tool == "guetzli":
                        if os.path.exists(output_path):  # Prüfe, ob das optimierte Bild existiert
                            shutil.move(output_path, img_path)  # Ersetze Originalbild

                    # Tool-Output loggen
                    if result.stdout.strip():
                        log_message(f"[DEBUG] {tool} output:\n{result.stdout}", 2)
                    if result.stderr.strip():
                        log_message(f"[ERROR] {tool} Fehler:\n{result.stderr}")

                except subprocess.CalledProcessError as e:
                    print(f"[ERROR] Fehler bei {tool}: {e}")
                    log_message(f"[ERROR] Fehler bei {tool}: {e}")

    print(f"[INFO] {len(image_list)} Bilder optimiert mit Profil '{optim_profile}'.")
    log_message(f"[INFO] {len(image_list)} Bilder optimiert mit Profil '{optim_profile}'.")

def create_archive(compression_profile, image_archive_name, meta_images, archive_path):
    """Erstellt ein Archiv mit dem gewählten Kompressionsprofil."""

    if compression_profile not in config["compression_profiles"]:
        print(f"[ERROR] Kompressionsprofil '{compression_profile}' nicht gefunden!")
        log_message(f"[ERROR] Kompressionsprofil '{compression_profile}' nicht gefunden!")
        return

    profile = config["compression_profiles"][compression_profile]
    tool_path = profile["path"]
    parameters = profile["parameters"]
    file_extension = profile.get("filext", "zip")  # Standard auf ZIP setzen, falls nicht definiert

    if not os.path.exists(tool_path):
        print(f"[ERROR] Kompressionstool '{tool_path}' nicht gefunden!")
        log_message(f"[ERROR] Kompressionstool '{tool_path}' nicht gefunden!")
        return

    # Output-Dateipfad setzen
    output_path = os.path.join(archive_path, f"{image_archive_name}.{file_extension}")

    # Alle Input-Dateien aus meta_images zusammenfügen
    input_files = " ".join(f'"{file}"' for file in meta_images)

    # Parameter nach `order` sortieren und Werte extrahieren
    sorted_params = sorted(parameters.values(), key=lambda x: x["order"])
    cmd_parts = [f'"{tool_path}"']
    
    for param in sorted_params:
        value = param["value"]
        value = value.replace("ipt:output", f'"{output_path}"')
        if "ipt:input" in value:
            value = value.replace("ipt:input", input_files)  # Alle Dateien ersetzen
        cmd_parts.append(value)

    cmd = " ".join(cmd_parts)

    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        log_message(f"[INFO] Archiv erstellt mit Profil '{compression_profile}': {output_path}")
        if result.stdout.strip():
            log_message(f"[DEBUG] {tool_path} output:\n{result.stdout}", 2)
        if result.stderr.strip():
            log_message(f"[ERROR] {tool_path} Fehler:\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Fehler bei der Archivierung mit {compression_profile}: {e}")
        log_message(f"[ERROR] Fehler bei der Archivierung mit {compression_profile}: {e}")

    return output_path  # Rückgabe des Archivpfads für spätere Verarbeitung

def create_best_archive(image_archive_name, meta_images):
    """Erstellt Archive mit allen Profilen und wählt das kleinste für den Output."""

    best_archive = None
    best_size = float('inf')
    archive_candidates = []
    temp_folder = config["paths"]["temp_folder"]
    output_folder = config["paths"]["output_folder"]

    for compression_profile in config["compression_profiles"]:
        temp_archive_name = f"{image_archive_name}_{compression_profile}"
        
        log_message(f"[INFO] Erstelle Test-Archiv mit Profil '{compression_profile}'...", 2)
        temp_archive = create_archive(compression_profile, temp_archive_name, meta_images, temp_folder)
        
        if os.path.exists(temp_archive):
            size = os.path.getsize(temp_archive)
            log_message(f"[INFO] Archiv '{temp_archive}' erstellt ({size} Bytes)", 2)

            archive_candidates.append((temp_archive, size))

            if size < best_size:
                best_size = size
                best_archive = temp_archive

    if not best_archive:
        log_message("[ERROR] Kein gültiges Archiv konnte erstellt werden!", 2)
        return None

    # Hole die Datei-Endung des kleinsten Archivs
    file_extension = os.path.splitext(best_archive)[1].lstrip('.')

    # Prüfe, ob eine alternative Endung für die gewählte existiert
    override_ext = config.get("parameters", {}).get("override_ext", {}).get(file_extension, file_extension)

    # Setze den finalen Archivpfad mit der ggf. überschriebenen Endung
    final_archive = os.path.join(output_folder, f"{image_archive_name}.{override_ext}")
    log_message(f"[INFO] Bestes Archiv bestimmt: {best_archive} → {final_archive}", 2)

    # Prüfen, ob die Datei korrekt kopiert/verschoben wird
    if verify_and_move_file(best_archive, final_archive):
        log_message(f"[INFO] Bestes Archiv '{best_archive}' wurde nach '{final_archive}' verschoben.")

        # Unnötige Archive löschen
        for archive, _ in archive_candidates:
            if archive != best_archive:
                os.remove(archive)
                log_message(f"[INFO] Ungenutztes Archiv '{archive}' wurde gelöscht.", 2)

    return final_archive

def verify_and_move_file(source, destination):
    """Überprüft die Integrität der Datei nach dem Kopieren/Verschieben."""
    
    shutil.copy2(source, destination)

    # Hashes vergleichen
    source_hash = file_hash(source)  # Hash der Originaldatei
    destination_hash = file_hash(destination)  # Hash der Zieldatei

    if source_hash == destination_hash:
        log_message(f"[INFO] Hash-Verifikation erfolgreich für '{destination}'", 2)
        os.remove(source)  # Erst jetzt Originaldatei löschen!
        log_message(f"[INFO] Datei '{source}' wurde nach '{destination}' verschoben.", 2)
        return True
    else:
        log_message(f"[ERROR] Hash-Verifikation fehlgeschlagen für '{destination}'", 2)
        return False  # Originaldatei bleibt erhalten, um Datenverlust zu vermeiden

######################################################################## 
####                    NACHBEREITUNG & SÄUBERN                     ####
######################################################################## 

def clear_temp_folder():
    temp_folder = config['paths']['temp_folder']
    
    if config['parameters'].get('empty', 0) == 1:
        if os.path.exists(temp_folder):
            try:
                shutil.rmtree(temp_folder)
                log_message(f"[INFO] Temp-Ordner '{temp_folder}' wurde gelöscht.", 2)
            except Exception as e:
                log_message(f"[ERROR] Konnte Temp-Ordner nicht löschen: {e}", 2)

######################################################################## 
####                           MAIN CORE                            ####
######################################################################## 

def main(config):
    """Hauptfunktion zur Steuerung der Bildverarbeitung."""
    global LOG_TIMESTAMP
    LOG_TIMESTAMP = datetime.now().strftime('%Y%m%d%H%M%S')

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