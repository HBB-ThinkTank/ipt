# ipt

 HBB Image Processing Tool

# IPT Tool – Image Processing Tool

**Version:** 1.0.0 *(in Entwicklung)*

## 📖 Projektziel
Das **IPT Tool** (Image Processing Tool) ist ein Python-basiertes Programm zur automatisierten Optimierung und Bearbeitung von Bilddateien (JPEG/PNG). Die Hauptfunktionen umfassen:

- Erstellung von Collagen und Einzelbildern im Format **800x1200 px**
- Optimierung der Bilder mit externen Tools
- Batch-Verarbeitung mehrerer Unterordner
- Automatisierte ZIP-Kompression mit 7-Zip
- Flexible Parametrierung über CLI

## ⚙️ Hauptfunktionen
### 1️⃣ **Bildoptimierung**
- **JPEG**: Verlustfrei oder verlustbehaftet
- **PNG**: Wird in JPEG konvertiert und optimiert

**Verwendete Tools & Reihenfolge:**
1. **pingo:** `-s4 -lossless -nostrip -notime` *(bzw. `-quality=85` für Cover/Collage)*
2. **jpegoptim:** `-p --keep-all --nofix` *(bzw. `-s --nofix` für Cover/Collage)*
3. **ECT:** `-9 -progressive -keep --mt-deflate --mt-file`

### 2️⃣ **Collage- und Einzelbild-Erstellung**
- Collage aus 4 Bildern im Format **800x1200 px**
- Einzelbild (Cover) aus dem ersten Bild
- Füllung mit unscharfem Hintergrund bei Seitenverhältnis-Abweichung

### 3️⃣ **ZIP-Kompression**
- Kompression mit 7-Zip in zwei Modi:
  - **BZip2:** `-mm=BZip2 -mx=9 -mpass=10`
  - **Deflate64:** `-mm=Deflate64 -mx=9 -mfb=257 -mpass=13`
- Das kleinere Archiv bleibt erhalten
- **Zeitstempel:** Jüngstes Datei-Erstellungsdatum als Archiv-Datum

### 4️⃣ **Batch-Modus**
- Verarbeitung mehrerer Unterordner mit einer Kommandozeile
- Struktur: `Hauptordner/UnterordnerX/…`

### 5️⃣ **Logging** *(Parameter `log`)*
- **`n`**: Kein Log *(Standard)*
- **`y`**: Normal (Kerninformationen)
- **`v`**: Verbose (detaillierte Debug-Infos)

## 🖥️ CLI-Aufrufe
**Einzelordner:**
```bash
python ipt.py <Eingabeordner> <Ausgabeordner>
```

**Batch-Verarbeitung:**
```bash
python ipt.py <Hauptordner> <Ausgabeordner> batch=true
```

## ⚠️ Parameter
- **`single_image (si)`**: Einzelbild erstellen *(true/false)*
- **`batch`**: Batch-Modus *(true/false)*
- **`log`**: Logging-Level *(n/y/v)*

## 🔍 Externe Abhängigkeiten
- **pingo:** [https://css-ig.net/pingo](https://css-ig.net/pingo)
- **jpegoptim:** [https://github.com/tjko/jpegoptim/releases](https://github.com/tjko/jpegoptim/releases)
- **ECT:** [https://github.com/fhanau/Efficient-Compression-Tool/releases](https://github.com/fhanau/Efficient-Compression-Tool/releases)
- **guetzli (CUDA/OpenCL):** [https://github.com/doterax/guetzli-cuda-opencl/releases](https://github.com/doterax/guetzli-cuda-opencl/releases)
- **7-Zip:** [https://7-zip.org](https://7-zip.org)

## 📑 Lizenz
Veröffentlicht unter der **GNU AGPLv3**.

---
**Nächster Schritt:** Projektstruktur & Basiskonfiguration. 🚀

