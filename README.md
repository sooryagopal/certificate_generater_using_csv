# AURELIA — Bulk Certificate Generator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-black.svg)](https://customtkinter.tomschimansky.com/)
[![Tests: 44 Passed](https://img.shields.io/badge/tests-44%20passed-brightgreen.svg)]()

**AURELIA** is a bulk certificate generation studio designed for academic institutions, corporate events, and conferences. Built with Python, CustomTkinter, Pillow, and PyMuPDF, AURELIA transforms raw CSV recipient rosters and graphic templates (PDF/PNG/JPG) into high-fidelity, print-ready certificates in individual and multi-page formats.

All certificate generation and recipient data processing run strictly on your local machine. No participant names, roll numbers, or documents are ever uploaded to cloud servers.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Dynamic CSV Placeholders System](#dynamic-csv-placeholders-system)
3. [Technology Stack](#technology-stack)
4. [Architecture and Directory Structure](#architecture-and-directory-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
   - [macOS Setup](#macos-setup)
   - [Windows Setup](#windows-setup)
   - [Linux Setup](#linux-setup)
7. [Launching the Application](#launching-the-application)
8. [Step-by-Step Usage Guide](#step-by-step-usage-guide)
9. [Sample CSV Format](#sample-csv-format)
10. [Visual Certificate Canvas & Positioning](#visual-certificate-canvas--positioning)
11. [Typography, Fonts, and International Scripts](#typography-fonts-and-international-scripts)
12. [Layout Presets Management (Version 2.0)](#layout-presets-management-version-20)
13. [Export Options & File Structure](#export-options--file-structure)
14. [Auditing & Generation Reports](#auditing--generation-reports)
15. [Automated Testing Suite (44 Tests)](#automated-testing-suite-44-tests)
16. [PyInstaller Standalone Packaging](#pyinstaller-standalone-packaging)
17. [Changelog](#changelog)
18. [Troubleshooting & Common Questions](#troubleshooting--common-questions)

---

## Key Features

- **Luxury Studio Aesthetic**: Visual layout with a pitch black (`#0B0B0D`) background, dark charcoal (`#151518`) panels, and restrained regal gold (`#D4AF37`) accents.
- **Dynamic CSV Column Detection**: Automatically detects *every* column header in any uploaded CSV file (5, 20, 50, or 100+ columns) without hardcoding or arbitrary limits.
- **Canonical `{{ColumnName}}` Syntax**: Fully preserves spaces, special characters, and Unicode scripts (e.g. `{{Student Name}}`, `{{பெயர்}}`).
- **Dedicated CSV PLACEHOLDERS Panel**:
  - Live search box with instantaneous case-insensitive filtering across column names and placeholder syntax.
  - Live sample values from the currently active preview record that switch in real-time.
  - **Method A (Click to Insert)**: Adds a dynamic text field near the canvas center with smart typography defaults.
  - **Method B (Drag and Drop)**: Drag a placeholder tag directly onto the canvas to position it precisely.
  - **Method C (Copy to Clipboard)**: Copies placeholder syntax with interactive feedback toasts.
  - **Method D (Template Text Interpolation)**: Combine static text with multiple dynamic tags (e.g. `Awarded to {{Name}} for {{EventName}}`).
  - **⚡ Insert All Columns**: One-click structured vertical layout generation with safety confirmation.
- **CSV Reload & Synchronization**: Detects missing columns, prompts the user to keep or remove unmapped fields, and never silently corrupts layouts.
- **Universal CSV Engine**: Automatic delimiter detection (`,`, `;`, `\t`, `|`), fallback text encodings (UTF-8, UTF-8 BOM, CP1252, Latin-1), and preserved leading zeros for roll numbers and student IDs (e.g. `00142`).
- **High-DPI Template Ingestion**: Accepts PNG, JPG, JPEG, WEBP, and multi-page PDF files rendered natively at 300 DPI print quality without altering the original template.
- **Visual Drag-and-Drop Canvas**: Position text fields by dragging on the template. Coordinates are normalized (`0.0` to `1.0`), ensuring layout consistency across preview and print resolutions.
- **Live Participant Preview**: Switch between participant records using previous/next navigation buttons to preview how short names, long names, and international scripts fit onto the certificate.
- **Rich Typography Engine**: Font size presets, TTF/OTF custom font loading, character tracking/letter spacing, word wrapping with max-width boundaries, text rotation, outlines, and case transformations (`UPPERCASE`, `Title Case`, etc.).
- **Multi-Format Export**:
  - Individual print-ready PDFs (300 DPI)
  - Lossless PNG images
  - High-quality JPG images
  - Dual exports (PDF + PNG, PDF + JPG)
  - Consolidated multi-page PDF (`combined_certificates.pdf`) containing the entire batch.
- **Atomic File Writing**: Temporary staging prevents corrupt or incomplete files in the event of unexpected cancellations or power interruptions.
- **Pre-Flight Diagnostic Audit**: Catches missing mappings, unresolved placeholders, unreadable fonts, low-resolution templates, and blank values before batch generation begins.
- **Threaded Worker Processing**: Non-blocking background generation keeps the user interface responsive, featuring live progress bars, speed metrics, and clean cancellation.
- **Comprehensive Audit Report**: Automatically exports `generation_report.csv` detailing the outcome, generated filenames, and timestamps for every single row.

---

## Dynamic CSV Placeholders System

AURELIA provides an automated pipeline for transforming raw CSV columns into certificate placeholders:

```mermaid
graph TD
    A[Upload CSV File] --> B[CSVReader Sanitization & Header Detection]
    B --> C[Extract Canonical Columns]
    C --> D[Generate Dynamic Placeholders: {{ColumnName}}]
    D --> E[Populate CSV PLACEHOLDERS Panel]
    E --> F1[Method A: Click to Insert Field]
    E --> F2[Method B: Drag & Drop to Canvas Coordinate]
    E --> F3[Method C: Copy {{Tag}} to Clipboard]
    E --> F4[Method D: Embed in Custom Template String]
    E --> F5[⚡ Insert All Columns Action]
    F1 & F2 & F3 & F4 & F5 --> G[Interactive Canvas Live Preview]
    G --> H[Record Switcher: Updates Sample Values Live]
    H --> I[Pre-Flight Verification of Placeholders]
    I --> J[Bulk Export: 100% Resolved Values, Zero Raw Tags]
```

### Supported Placeholder Methods

1. **Direct Single-Column Field**:
   - Creates a dynamic text field bound to `column_name` (e.g. `{{Name}}`).
2. **Multi-Tag Template String**:
   - `Awarded to {{Name}} (Roll No: {{RollNumber}}) of {{Department}} for winning {{Prize}} in {{EventName}}.`
   - Substitutes every tag safely using regex matching without using `eval` or `exec`.
3. **Repeated Placeholders**:
   - Supports identical column tags placed multiple times in one text field or across independent text fields with distinct styling (e.g. Large Name in center + small Name in signature block).
4. **Leading Zeros & Unicode**:
   - Preserves strings such as `001048` and international scripts like Tamil `சூர்யா ஜி` without truncation or alteration.

---

## Technology Stack

| Component | Library / Tool | Purpose |
| :--- | :--- | :--- |
| **GUI Framework** | `customtkinter` (6.0+) | Dark theme, responsive controls, and visual panels |
| **Core UI Base** | `tkinter` (Native Python) | Embedded canvas, native file dialogs, color choosers |
| **Data Engine** | `pandas` (2.0+) | CSV ingestion, type preservation, and validation |
| **Placeholder Engine** | `core/placeholder_engine.py` | Safe regex tokenization, extraction, and substitution |
| **Image & Text** | `Pillow` (10.0+) | Raster processing, FreeType typography, and previews |
| **PDF Processing** | `PyMuPDF` (`fitz` 1.23+) | PDF template rasterization and multi-page PDF stitching |
| **Packaging** | `PyInstaller` (6.0+) | Standalone executable compilation for macOS & Windows |
| **Test Suite** | `pytest` (7.0+) | Automated testing (44 test cases covering 15 scenarios) |

---

## Architecture and Directory Structure

The project follows a modular, decoupled architecture separating UI, graphic rendering, data parsing, and background services:

```
Certificate_Generator/
│
├── app.py                      # Application entry point with global exception handler
├── requirements.txt            # Python production dependencies
├── aurelia.spec                # PyInstaller packaging configuration
├── conftest.py                 # PyTest test runner configuration
├── sample.csv                  # 12-column sample recipient dataset
│
├── assets/                     # Graphical assets and default templates
│   ├── sample_template.png     # 2400x1600 print-ready certificate template
│   └── icons/                  # Application icons
│
├── models/                     # Strongly-typed data models
│   ├── __init__.py
│   ├── text_field.py           # TextField dataclass with {{placeholder}} & template_text
│   ├── layout_preset.py        # LayoutPreset schema v2.0 with v1.0 migration
│   └── generation_result.py    # Per-row generation outcome container
│
├── core/                       # Core graphic and data processing engines
│   ├── __init__.py             # Core package initialization
│   ├── placeholder_engine.py   # Safe regex placeholder parser & resolver
│   ├── csv_reader.py           # Robust CSV parser with delimiter sniffing & BOM support
│   ├── template_loader.py      # Image & PDF loader with 300 DPI rasterization
│   ├── font_manager.py         # OS font scanner, TTF resolver, and caching
│   ├── renderer.py             # Single source of truth for preview and export rendering
│   ├── layout_manager.py       # Active field state, placeholder fields, layers, undo/redo
│   ├── filename_utils.py       # Template pattern expansion & collision handling
│   └── validators.py           # Diagnostic pre-flight check engine with placeholder checks
│
├── services/                   # Application background services
│   ├── __init__.py
│   ├── pdf_service.py          # PDF generation, image export, and PDF combining
│   ├── generation_service.py   # Multi-threaded batch rendering worker
│   ├── preset_service.py       # JSON preset filesystem CRUD & validation
│   ├── settings_service.py     # Cross-session user preferences persistence
│   └── report_service.py       # CSV audit report generator
│
├── ui/                         # User Interface components (CustomTkinter)
│   ├── __init__.py
│   ├── theme.py                # Black and Gold theme tokens and palette
│   ├── main_window.py          # Master window coordinating all panels
│   ├── canvas_editor.py        # Interactive drag-and-drop certificate canvas
│   ├── sidebar_panel.py        # Left sidebar (CSV, Template, Export settings)
│   ├── placeholder_panel.py    # Dedicated collapsible CSV PLACEHOLDERS panel
│   ├── field_panel.py          # Right sidebar (Field Inspector, Typography, Color, Tags)
│   └── dialogs.py              # CSV Table Viewer, Validation Report, and Progress Modals
│
├── presets/                    # Pre-packaged layout configurations
│   └── default_award.json      # Pre-configured award layout for NEWELLS 3.0
│
└── tests/                      # Automated pytest suite (44 tests)
    ├── test_placeholder_engine.py # 15 scenarios for dynamic CSV placeholders
    ├── test_csv_reader.py      # CSV encodings, leading zeroes, edge cases
    ├── test_renderer.py        # Normalized positioning and text rendering
    ├── test_filename_utils.py  # Pattern substitution and collision policies
    ├── test_presets.py         # Preset serialization and JSON validation
    ├── test_export.py          # PDF, PNG, JPG, and multi-page combining
    ├── test_validators.py      # Pre-flight diagnostic rules
    └── test_generation_service.py # Batch execution and thread cancellation
```

---

## Prerequisites

- **Python**: Version 3.11 or newer (Python 3.9+ supported).
- **Operating System**: macOS 11+, Windows 10/11, or Linux (Ubuntu 20.04+, Debian, Fedora, Arch).
- **Disk Space**: At least 500 MB free for high-resolution batch rendering.

---

## Installation & Setup

### macOS Setup

1. Open Terminal and navigate to the project directory:
   ```bash
   cd /Users/macbookpro/Projects/Certificate_Generator
   ```

2. Create a virtual environment using Python 3.11+:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Upgrade `pip` and install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Windows Setup

1. Open PowerShell or Command Prompt in the project folder:
   ```powershell
   cd C:\path\to\Certificate_Generator
   ```

2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Linux Setup

1. Install system prerequisites for Python Tkinter:
   ```bash
   sudo apt update
   sudo apt install -y python3-tk python3-venv
   ```

2. Create virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

---

## Launching the Application

Ensure your virtual environment is active, then launch:

```bash
python3 app.py
```
*(On Windows, run `python app.py`)*

---

## Step-by-Step Usage Guide

### Step 1: Upload Recipient CSV
1. In the Left Sidebar under **1. RECIPIENT DATA (CSV)**, click **Upload CSV File...**.
2. Select your CSV file (you can use `sample.csv` included in the root folder).
3. The application immediately reads every column header and populates the **CSV PLACEHOLDERS** panel.

### Step 2: Explore & Insert Dynamic Placeholders
1. In the **CSV PLACEHOLDERS** panel:
   - Use the **Search box** to filter columns (e.g. typing `Roll`, `Event`, or `Name`).
   - Observe live sample values from the currently selected record.
   - Click **+ Insert** on any card to create a dynamic text field on the canvas.
   - Or **Drag and Drop** the card directly onto the canvas to place it at exact coordinates.
   - Click **📋 Copy** to copy `{{ColumnName}}` to your clipboard.
   - Click **⚡ Insert All Columns** to auto-generate a structured layout containing every column.

### Step 3: Upload Certificate Template
1. In the Left Sidebar under **2. CERTIFICATE TEMPLATE**, click **Upload Template (PNG, JPG, PDF)...**.
2. Select your graphic template (supports `.png`, `.jpg`, `.jpeg`, `.webp`, or `.pdf`). You can use `assets/sample_template.png`.
3. If using a multi-page PDF, select which page to use via the **PDF Page** dropdown.

### Step 4: Fine-Tune Typography & Embed Multi-Tags
1. Select any field on the canvas or in the **TEXT FIELDS** inspector on the right.
2. In the inspector:
   - Use **Template / Multi-Tag Text** to write strings with multiple placeholders:
     `Awarded to {{Name}} for {{EventName}}`
   - Click **+ Tag ▾** to insert any detected column placeholder at your cursor.
   - Adjust Font Size, Font Family, Bold, Italic, Tracking, Max Width, and Color.

### Step 5: Preview Different Participants
1. In the toolbar directly above the canvas, use the **◀ Prev** and **Next ▶** buttons to browse through different participant rows.
2. Both the certificate canvas and the placeholder cards update their displayed values in real time.

### Step 6: Configure Output & Export
1. Under **4. OUTPUT DESTINATION & NAMING**:
   - Select an **Output Directory** where certificates will be saved.
   - Set the **Filename Pattern** (e.g. `{Name}_{RollNumber}` or `{CertificateID}_{Name}`).
   - Choose your **Export Format** (`Individual PDF Certificates`, `PNG`, `JPG`, `PDF + PNG`, `PDF + JPG`, or `Combined Multi-Page PDF Only`).
   - Check **Also compile combined multi-page PDF** to compile the batch into a single document.
2. Click **⚡ GENERATE CERTIFICATES** to launch the threaded background batch processor.

---

## Sample CSV Format

The included `sample.csv` features 12 diverse recipient fields covering academic events, leading zeros, Tamil script, accented European names, and long names:

```csv
Name,RollNumber,Department,Class,EventName,EventDate,College,Email,Phone,CertificateID,Prize,Duration
Soorya G,23ADR154,AIDS,IV Year,NEWELLS 3.0,24-10-2026,KEC,soorya@example.com,9876543210,CERT001,First Prize,24 Hours
Prathisha S,23ADR132,AIDS,IV Year,NEWELLS 3.0,24-10-2026,KEC,prathisha@example.com,9876543211,CERT002,Second Prize,24 Hours
Ruban S,23ADR144,AIDS,IV Year,NEWELLS 3.0,24-10-2026,KEC,ruban@example.com,9876543212,CERT003,Third Prize,24 Hours
Karthik Raja M,009ADR042,CSE,III Year,HACK-A-THON 2026,15-11-2026,MIT,karthik@example.com,0987654321,CERT004,Special Jury Award,36 Hours
Aurelia Vance,001048,ECE,II Year,INNOVISION 2026,05-12-2026,Stanford,aurelia@example.com,9876543214,CERT005,First Prize,12 Hours
சூர்யா ஜி,23ADR155,AIDS,IV Year,NEWELLS 3.0,24-10-2026,KEC,soorya_tamil@example.com,9876543215,CERT006,Participation,24 Hours
René François,007890,MECH,I Year,ROBO-CHALLENGE,18-09-2026,Polytechnique,rene@example.com,0033145678,CERT007,Best Innovation,48 Hours
Ananya Subramanian,23ADR199,AIDS,IV Year,NEWELLS 3.0,24-10-2026,KEC,ananya@example.com,9876543217,CERT008,First Prize,24 Hours
Alexander Montgomery-Cunningham,22CSE890,CSE,IV Year,INTERNATIONAL TECH EXPO,30-10-2026,Oxford,alex@example.com,9876543218,CERT009,Excellence Award,72 Hours
Divya Bharathi K,24IT005,IT,I Year,CODE CRAFT 2026,12-11-2026,KEC,divya@example.com,9876543219,CERT010,Consolation Prize,8 Hours
```

---

## Visual Certificate Canvas & Positioning

- **Normalized Coordinates**: Text coordinates are tracked from `0.0` to `1.0`. `(0.5, 0.5)` represents exact horizontal and vertical center.
- **Snapping Guidelines**: Magenta guidelines appear when dragging fields across center axes.
- **Keyboard Nudging**: Select any field on canvas and use `Arrow Keys` for micro-adjustments or `Shift + Arrow Keys` for 1% shifts.
- **Canvas Zoom & Pan**: Dedicated zoom buttons (`+`, `−`, `Fit View`, `100%`) and mouse wheel support.

---

## Typography, Fonts, and International Scripts

- **System Fonts**: Automatically discovers all TrueType/OpenType fonts installed in Windows, macOS, and Linux font directories.
- **Custom Font Loader**: Load any downloaded `.ttf` or `.otf` file via **Browse TTF...**.
- **Unicode & Non-Latin Scripts**: Supports Tamil, Hindi, Japanese, Cyrillic, Arabic, and extended European accents without box glyph errors when using Unicode fonts (e.g. Nirmala UI, Noto Sans).
- **Text Wrapping**: Set maximum width thresholds (`0.10` to `1.00`) to automatically wrap long attendee names or designations.

---

## Layout Presets Management (Version 2.0)

Presets are stored as JSON documents in `presets/`. Version 2.0 includes full support for dynamic placeholders and template strings while retaining full backward compatibility for Version 1.0 presets:

```json
{
  "name": "Academic Excellence Award",
  "version": "2.0",
  "description": "Pre-configured layout with dynamic placeholders",
  "template_width": 2400,
  "template_height": 1600,
  "template_name": "sample_template.png",
  "fields": [
    {
      "id": "fld_001",
      "name": "Recipient Name",
      "type": "dynamic",
      "column": "Name",
      "placeholder": "{{Name}}",
      "x": 0.50,
      "y": 0.44,
      "font_family": "Arial",
      "font_size": 52,
      "color": "#D4AF37",
      "bold": true,
      "align_h": "center"
    },
    {
      "id": "fld_002",
      "name": "Award Description",
      "type": "dynamic",
      "template_text": "for securing {{Prize}} in {{EventName}}",
      "x": 0.50,
      "y": 0.58,
      "font_family": "Arial",
      "font_size": 28,
      "color": "#F5F1E5",
      "bold": false,
      "align_h": "center"
    }
  ]
}
```

---

## Automated Testing Suite (44 Tests)

Run the comprehensive pytest suite:

```bash
./.venv/bin/pytest tests/ -v
```

### Test Coverage Summary:
- **Scenario 1**: Detecting all CSV headers (`test_detecting_all_csv_headers`)
- **Scenario 2**: Handling 5, 20, 50, and 100 columns (`test_handling_various_column_counts`)
- **Scenario 3**: Generating placeholders dynamically (`test_generating_placeholders_dynamically`)
- **Scenario 4**: Preserving Unicode header names (`test_preserving_unicode_header_names`)
- **Scenario 5**: Resolving multiple placeholders (`test_resolving_multiple_placeholders`)
- **Scenario 6**: Resolving repeated placeholders (`test_resolving_repeated_placeholders`)
- **Scenario 7**: Preserving leading zeros (`test_preserving_leading_zeros`)
- **Scenario 8**: Handling empty cells (`test_handling_empty_cells`)
- **Scenario 9**: Detecting unknown placeholders (`test_detecting_unknown_placeholders`)
- **Scenario 10**: Supporting duplicate use of a column in multiple fields (`test_supporting_duplicate_use_of_column_in_multiple_fields`)
- **Scenario 11**: Reloading a CSV with the same headers (`test_reloading_csv_with_same_headers`)
- **Scenario 12**: Reloading a CSV with changed headers (`test_reloading_csv_with_changed_headers`)
- **Scenario 13**: Saving and loading placeholder-based presets (`test_saving_and_loading_placeholder_based_presets`)
- **Scenario 14**: Exporting different participant values correctly (`test_exporting_different_participant_values_correctly`)
- **Scenario 15**: Ensuring no unresolved placeholders remain in generated output (`test_ensuring_no_unresolved_placeholders_remain_in_generated_output`)
- **Core Engine Tests**: CSV parsing, delimiter sniffing, PDF generation, combined multi-page PDF compilation, collision policies, filename sanitization, thread cancellation, and pre-flight validation.

---

## PyInstaller Standalone Packaging

Compile AURELIA into a standalone executable using `aurelia.spec`:

### On macOS:
```bash
source .venv/bin/activate
pyinstaller --clean aurelia.spec
```
Outputs standalone application bundle at `dist/Aurelia.app`.

### On Windows:
```powershell
.venv\Scripts\activate
pyinstaller --clean aurelia.spec
```
Outputs standalone executable at `dist\Aurelia\Aurelia.exe`.

---

## Changelog

### Version 2.0.0 — Dynamic CSV Placeholders Update
- **Added `core/placeholder_engine.py`**: Safe regex placeholder parsing engine with dynamic placeholder generation, tag extraction, unknown placeholder auditing, and zero `eval`/`exec`.
- **Added `ui/placeholder_panel.py`**: Dedicated collapsible CSV PLACEHOLDERS panel with real-time case-insensitive search, live sample previews, click-to-insert, drag-and-drop onto the certificate canvas, clipboard copy with feedback toasts, and `⚡ Insert All Columns`.
- **Updated `models/text_field.py`**: Added `placeholder`, `template_text` attributes, safe resolution with empty string fallbacks, and schema v2.0 serialization.
- **Updated `models/layout_preset.py`**: Upgraded layout preset schema to Version 2.0 with backward compatibility for Version 1.0 presets and `LayoutPreset.from_file` support.
- **Updated `core/validators.py`**: Integrated placeholder auditing to catch unmapped or misspelled `{{...}}` tags during pre-flight checks.
- **Updated `core/layout_manager.py`**: Added `add_placeholder_field`, `insert_all_columns`, and `synchronize_with_csv` with missing column detection.
- **Updated `sample.csv`**: Enhanced with all 12 participant columns (`Name`, `RollNumber`, `Department`, `Class`, `EventName`, `EventDate`, `College`, `Email`, `Phone`, `CertificateID`, `Prize`, `Duration`).
- **Added Automated Tests**: 18 new automated tests in `tests/test_placeholder_engine.py` covering all 15 scenarios from the project specification (total suite: 44 tests, 100% passing).

---

## Troubleshooting & Common Questions

**Q: Can I upload a CSV with 50 or 100 columns?**
> Yes. Every column header detected in the CSV is displayed in the scrollable CSV PLACEHOLDERS panel. You can search, insert, copy, or drag any column tag at any time.

**Q: What happens if a participant's roll number has leading zeros (e.g. `001048`)?**
> AURELIA ingests roll numbers and IDs as raw text strings. Leading zeros are strictly preserved on the canvas and in all exported PDFs and images.

**Q: Can I use the same CSV column more than once?**
> Yes. You can insert `Name` multiple times on the certificate (for instance, a large decorative name in the center and a small name in the signature footer) with independent positions, fonts, and colors.
