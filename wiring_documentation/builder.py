#!/usr/bin/env python3

import yaml
import os
import sys
import tempfile
import shutil
import glob
import csv
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from .cropper import crop_pdf
from .extract_zone_data import extract_zone_data
from .make_pdf import html_to_pdf
from .riffle_shuffle import riffle_shuffle_pdfs


class DocumentationPackBuilder:
    def __init__(self, config_path):
        """Initialise the documentation pack builder with configuration."""
        self.config_path = config_path
        self.config_dir = os.path.dirname(os.path.abspath(config_path))
        self.config = self._load_config()
        self.working_dir = None
        self.plan_pdfs = {}

    def _resolve_path(self, path):
        """Resolve a path relative to current working directory if not absolute."""
        if os.path.isabs(path):
            return path
        return os.path.abspath(path)

    def _load_config(self):
        """Load and validate the YAML configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")

        # Validate required fields
        required_fields = ['crops_file', 'tabs_file', 'csv_data_directory',
                          'plan_pdfs_directory', 'rooms']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Required configuration field missing: {field}")

        return config

    def _setup_working_directory(self):
        """Create working directory for temporary files."""
        if 'output' in self.config and 'working_directory' in self.config['output']:
            working_dir = self._resolve_path(self.config['output']['working_directory'])
            os.makedirs(working_dir, exist_ok=True)
            self.working_dir = working_dir
        else:
            self.working_dir = tempfile.mkdtemp(prefix='doc_pack_')

        print(f"Working directory: {self.working_dir}")

    def _cleanup_working_directory(self, retain_working_dir=False):
        """Clean up temporary files if configured to do so."""
        if retain_working_dir:
            print(f"Working directory retained for debugging: {self.working_dir}")
            return

        should_cleanup = (
            'output' in self.config and
            self.config['output'].get('cleanup_temp_files', True)
        )

        if should_cleanup and self.working_dir and os.path.exists(self.working_dir):
            if self.working_dir.startswith('/tmp') or 'temp' in self.working_dir.lower():
                shutil.rmtree(self.working_dir)
                print(f"Cleaned up working directory: {self.working_dir}")

    def _find_plan_pdfs(self):
        """Find and match plan PDFs for each tab."""
        plan_dir = self._resolve_path(self.config['plan_pdfs_directory'])
        tabs_file = self._resolve_path(self.config['tabs_file'])

        # Read tabs list
        try:
            with open(tabs_file, 'r') as f:
                tabs = [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"Tabs file not found: {tabs_file}")

        # Find matching PDFs for each tab
        pdf_pattern = self.config.get('pdf_filename_pattern', '*{tab}*.pdf')

        for tab in tabs:
            # Replace {tab} placeholder with actual tab name
            search_pattern = pdf_pattern.replace('{tab}', tab)
            search_path = os.path.join(plan_dir, search_pattern)

            matching_files = glob.glob(search_path)

            if len(matching_files) == 0:
                raise FileNotFoundError(f"No PDF files found for tab '{tab}' using pattern: {search_pattern}")
            elif len(matching_files) > 1:
                raise ValueError(f"Multiple PDF files found for tab '{tab}': {matching_files}")
            else:
                self.plan_pdfs[tab] = matching_files[0]
                print(f"Found PDF for '{tab}': {os.path.basename(matching_files[0])}")

    def _create_cropped_plans(self):
        """Create cropped plan pages for each tab using cropper utility."""
        crops_file = self._resolve_path(self.config['crops_file'])
        cropped_files = {}

        for tab, pdf_path in self.plan_pdfs.items():
            output_path = os.path.join(self.working_dir, f"cropped_{tab.replace(' ', '_')}.pdf")

            try:
                crop_pdf(pdf_path, output_path, crops_file)
                cropped_files[tab] = output_path
                print(f"Created cropped plans for '{tab}': {os.path.basename(output_path)}")
            except Exception as e:
                raise RuntimeError(f"Error cropping PDF for '{tab}': {e}")

        return cropped_files

    def _riffle_shuffle_plans(self, cropped_files):
        """Combine all cropped plan files using riffle shuffle."""
        tabs_file = self._resolve_path(self.config['tabs_file'])

        # Read tabs to maintain order
        with open(tabs_file, 'r') as f:
            tabs = [line.strip() for line in f.readlines() if line.strip()]

        # Collect PDF files in tab order
        pdf_files = [cropped_files[tab] for tab in tabs if tab in cropped_files]

        shuffled_output = os.path.join(self.working_dir, "shuffled_plans.pdf")

        try:
            success = riffle_shuffle_pdfs(pdf_files, shuffled_output)
            if not success:
                raise RuntimeError("Riffle shuffle failed")
            print(f"Created shuffled plans: {os.path.basename(shuffled_output)}")
            return shuffled_output
        except Exception as e:
            raise RuntimeError(f"Error shuffling plans: {e}")

    def _create_room_data_pages(self, custom_timestamp=None):
        """Create data pages for each room."""
        csv_data_dir = self._resolve_path(self.config['csv_data_directory'])
        tabs_file = self._resolve_path(self.config['tabs_file'])
        room_data_files = {}

        for room in self.config['rooms']:
            room_name = room['name']
            zones = room['zones']

            # Create temporary zones file for this room
            zones_file = os.path.join(self.working_dir, f"zones_{room_name.replace(' ', '_')}.csv")
            with open(zones_file, 'w') as f:
                for zone in zones:
                    f.write(f"{zone}\n")

            # Create HTML output file
            html_file = os.path.join(self.working_dir, f"data_{room_name.replace(' ', '_')}.html")

            try:
                extract_zone_data(csv_data_dir, room_name, tabs_file, zones_file, html_file, custom_timestamp)

                # Convert HTML to PDF
                pdf_file = html_file.replace('.html', '.pdf')
                html_to_pdf(html_file, pdf_file)

                room_data_files[room_name] = pdf_file
                print(f"Created data page for '{room_name}': {os.path.basename(pdf_file)}")

            except Exception as e:
                raise RuntimeError(f"Error creating data page for '{room_name}': {e}")

        return room_data_files

    def _check_missing_zones(self, auto_yes=False):
        """Check for zones that don't have any data in the CSV files."""
        csv_data_dir = self._resolve_path(self.config['csv_data_directory'])
        tabs_file = self._resolve_path(self.config['tabs_file'])

        # Get all zones mentioned in config
        all_zones = set()
        for room in self.config['rooms']:
            for zone in room['zones']:
                # Normalise zone names to match CSV normalization
                zone_name = ' '.join(zone.split()).strip()
                zone_name = zone_name.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
                all_zones.add(zone_name)

        # Get all zones that have data in CSV files
        zones_with_data = set()

        # Read tabs
        with open(tabs_file, 'r') as f:
            tabs = [line.strip() for line in f.readlines() if line.strip()]

        # Check each CSV file for zones with data
        for tab in tabs:
            matching_files = [
                f for f in os.listdir(csv_data_dir) if f.startswith(tab) and f.endswith(".csv")
            ]

            if len(matching_files) == 1:
                csv_path = os.path.join(csv_data_dir, matching_files[0])
                try:
                    with open(csv_path, 'r') as csvfile:
                        reader = csv.reader(csvfile)
                        for i, row in enumerate(reader):
                            if i == 0:  # Skip header
                                continue
                            if row and len(row) > 1 and row[1].strip():  # Check Location column
                                # Normalise zone names from CSV
                                zone_name = ' '.join(row[1].split()).strip()
                                zone_name = zone_name.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
                                zones_with_data.add(zone_name)
                except Exception as e:
                    print(f"Warning: Could not read {csv_path}: {e}")

        # Find missing zones
        missing_zones = all_zones - zones_with_data

        if missing_zones:
            print("\nWarnings:")
            for zone in sorted(missing_zones):
                print(f'No data for zone "{zone}"')

            if auto_yes:
                print("Proceeding automatically (--auto-yes specified)")
                return True
            else:
                while True:
                    response = input("Proceed with output? (Y/N): ").strip().upper()
                    if response in ['Y', 'YES']:
                        return True
                    elif response in ['N', 'NO']:
                        return False
                    else:
                        print("Please answer Y or N")

        return True

    def _check_missing_plan_pages(self, auto_yes=False):
        """Check for rooms that don't have plan pages (not in crops file)."""
        crops_file = self._resolve_path(self.config['crops_file'])

        # Get all room names from config
        config_rooms = set()
        for room in self.config['rooms']:
            # Normalise config room names to match crops normalization
            room_name = ' '.join(room['name'].split()).strip()
            room_name = room_name.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
            config_rooms.add(room_name)

        # Get all room names from crops file
        crops_rooms = set()
        with open(crops_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and len(row) > 0:
                    # Normalise room name like we do elsewhere
                    crop_name = ' '.join(row[0].split()).strip()
                    crop_name = crop_name.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
                    crops_rooms.add(crop_name)

        # Find rooms with missing plan pages
        missing_plan_rooms = config_rooms - crops_rooms

        if missing_plan_rooms:
            print("\nWarnings:")
            for room in sorted(missing_plan_rooms):
                print(f'No plan pages for room "{room}" (not found in crops file)')

            if auto_yes:
                print("Proceeding automatically (--auto-yes specified)")
                return True
            else:
                while True:
                    response = input("Proceed with output? (Y/N): ").strip().upper()
                    if response in ['Y', 'YES']:
                        return True
                    elif response in ['N', 'NO']:
                        return False
                    else:
                        print("Please answer Y or N")

        return True

    def _get_crop_position(self, room_name):
        """Find the position of a room in the crops file."""
        crops_file = self._resolve_path(self.config['crops_file'])

        with open(crops_file, 'r') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if row and len(row) > 0:
                    # Handle multi-line entries by normalising whitespace and Unicode quotes
                    crop_name = ' '.join(row[0].split()).strip()
                    crop_name = crop_name.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')

                    normalised_room_name = ' '.join(room_name.split()).strip()
                    normalised_room_name = normalised_room_name.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')

                    if crop_name == normalised_room_name:
                        return idx

        raise ValueError(f"Room '{room_name}' not found in crops file: {crops_file}")

    def _combine_final_output(self, room_data_files, shuffled_plans_file, output_path):
        """Combine data pages and plan pages into final output."""
        # Read the number of tabs to calculate pages per room
        tabs_file = self._resolve_path(self.config['tabs_file'])
        with open(tabs_file, 'r') as f:
            num_tabs = len([line.strip() for line in f.readlines() if line.strip()])

        final_writer = PdfWriter()

        # Read shuffled plans PDF
        with open(shuffled_plans_file, 'rb') as f:
            shuffled_reader = PdfReader(f)

            for room in self.config['rooms']:
                room_name = room['name']

                # Add data pages for this room
                if room_name in room_data_files:
                    with open(room_data_files[room_name], 'rb') as data_f:
                        data_reader = PdfReader(data_f)
                        for page in data_reader.pages:
                            final_writer.add_page(page)
                        print(f"Added {len(data_reader.pages)} data page(s) for '{room_name}'")

                # Add plan pages for this room
                try:
                    crop_position = self._get_crop_position(room_name)
                    start_page = crop_position * num_tabs

                    for page_offset in range(num_tabs):
                        page_idx = start_page + page_offset
                        if page_idx < len(shuffled_reader.pages):
                            final_writer.add_page(shuffled_reader.pages[page_idx])

                    print(f"Added {num_tabs} plan page(s) for '{room_name}' (crop position {crop_position})")

                except ValueError:
                    # Room not found in crops - this should have been caught earlier, but skip silently
                    print(f"Skipped plan pages for '{room_name}' (not in crops file)")
                    continue

        # Write final output
        with open(output_path, 'wb') as output_file:
            final_writer.write(output_file)

        print(f"Final documentation pack created: {output_path}")

    def build(self, output_path, auto_yes=False, retain_working_dir=False, custom_timestamp=None):
        """Build the complete documentation pack."""
        try:
            print("Starting documentation pack build...")

            # Setup working directory
            self._setup_working_directory()

            # Find plan PDFs
            print("\n1. Finding plan PDFs...")
            self._find_plan_pdfs()

            # Create cropped plans
            print("\n2. Creating cropped plan pages...")
            cropped_files = self._create_cropped_plans()

            # Riffle shuffle plans
            print("\n3. Combining plan pages...")
            shuffled_plans = self._riffle_shuffle_plans(cropped_files)

            # Create room data pages
            print("\n4. Creating room data pages...")
            room_data_files = self._create_room_data_pages(custom_timestamp)

            # Check for missing zones
            print("\n5. Checking for missing zone data...")
            if not self._check_missing_zones(auto_yes):
                print("Build cancelled by user.")
                sys.exit(1)

            # Check for missing plan pages
            print("\n6. Checking for missing plan pages...")
            if not self._check_missing_plan_pages(auto_yes):
                print("Build cancelled by user.")
                sys.exit(1)

            # Combine everything
            print("\n7. Combining final output...")
            self._combine_final_output(room_data_files, shuffled_plans, output_path)

            print(f"\n✓ Documentation pack successfully created: {output_path}")

        except Exception as e:
            print(f"\n✗ Error building documentation pack: {e}")
            raise
        finally:
            # Clean up
            self._cleanup_working_directory(retain_working_dir)

    def check(self):
        """Check configuration validity without building."""
        try:
            print("Checking configuration...")

            # Check that all files exist
            print("\nChecking file paths...")
            crops_file = self._resolve_path(self.config['crops_file'])
            tabs_file = self._resolve_path(self.config['tabs_file'])
            csv_data_dir = self._resolve_path(self.config['csv_data_directory'])
            plan_dir = self._resolve_path(self.config['plan_pdfs_directory'])

            for name, path in [
                ('Crops file', crops_file),
                ('Tabs file', tabs_file),
                ('CSV data directory', csv_data_dir),
                ('Plan PDFs directory', plan_dir)
            ]:
                if os.path.exists(path):
                    print(f"  ✓ {name}: {path}")
                else:
                    print(f"  ✗ {name} not found: {path}")
                    raise FileNotFoundError(f"{name} not found: {path}")

            # Check rooms configuration
            print("\nChecking rooms configuration...")
            if not self.config.get('rooms'):
                raise ValueError("No rooms configured")

            for room in self.config['rooms']:
                if 'name' not in room:
                    raise ValueError("Room missing 'name' field")
                if 'zones' not in room:
                    raise ValueError(f"Room '{room.get('name', 'unknown')}' missing 'zones' field")
                print(f"  ✓ Room: {room['name']} ({len(room['zones'])} zones)")

            print("\n✓ Configuration is valid")
            return True

        except Exception as e:
            print(f"\n✗ Configuration error: {e}")
            return False
