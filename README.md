# Wiring Documentation Generator

A tool for building construction wiring documentation packs from plan PDFs and CSV data files.

## Installation

Clone this repository and create a symlink to the executable:

```bash
git clone https://github.com/lorenzowood/wiring-documentation.git
cd wiring-documentation
ln -s "$(pwd)/wiring-documentation" ~/.local/bin/wiring-documentation
```

Make sure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

Install dependencies:

```bash
pip3 install -r requirements.txt
```

## Usage

### Check Configuration

Validate a configuration file without building:

```bash
wiring-documentation check config.yml
```

### Build Documentation Pack

Build a documentation pack from a configuration file:

```bash
wiring-documentation build config.yml
```

This will create a PDF with the same name as the config file (e.g., `config.pdf`).

You can specify a custom output filename:

```bash
wiring-documentation build config.yml output.pdf
```

### Options

- `-y, --auto-yes`: Automatically answer yes to prompts
- `--debug-retain-working-directory`: Keep temporary files for debugging
- `--set-timestamp "DATE"`: Use custom timestamp instead of current time

## Configuration File

Create a YAML configuration file with the following structure:

```yaml
# Input files and directories
crops_file: "crops.csv"
tabs_file: "tabs.csv"
csv_data_directory: "/path/to/csv/data"
plan_pdfs_directory: "./plans"

# Plan PDF filename pattern
pdf_filename_pattern: "{tab}.pdf"

# Rooms configuration
rooms:
  - name: "Room Name"
    zones: ["Zone 1", "Zone 2"]

# Output configuration (optional)
output:
  working_directory: "./temp_build"
  cleanup_temp_files: true
```

## Project Structure

```
wiring-documentation/
├── wiring_documentation/
│   ├── __init__.py
│   ├── __main__.py
│   ├── builder.py        # Main documentation builder
│   ├── cli.py            # Command-line interface
│   ├── cropper.py        # PDF cropping utility
│   ├── extract_zone_data.py  # Data extraction from CSV
│   ├── make_pdf.py       # HTML to PDF conversion
│   └── riffle_shuffle.py # PDF page interleaving
├── wiring-documentation  # Executable wrapper
├── requirements.txt
└── README.md
```

## How It Works

1. **Find Plan PDFs**: Locates plan PDFs for each tab based on the filename pattern
2. **Crop Plans**: Extracts room-specific views from plan PDFs using crop coordinates
3. **Riffle Shuffle**: Interleaves pages from different plan types
4. **Extract Data**: Generates data tables from CSV files for each room's zones
5. **Combine**: Merges data pages and plan pages into final documentation pack

## License

MIT
