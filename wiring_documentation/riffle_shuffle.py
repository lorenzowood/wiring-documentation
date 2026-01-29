#!/usr/bin/env python3

import argparse
import sys
import os
import glob
from pypdf import PdfReader, PdfWriter


def get_page_counts(input_files):
    page_counts = {}
    for filename in input_files:
        try:
            with open(filename, 'rb') as f:
                reader = PdfReader(f)
                page_counts[filename] = len(reader.pages)
        except Exception as e:
            print(f"Error reading {filename}: {e}", file=sys.stderr)
            return None
    return page_counts


def validate_page_counts(page_counts):
    if not page_counts:
        return False

    page_count_values = list(page_counts.values())
    first_count = page_count_values[0]

    if not all(count == first_count for count in page_count_values):
        print("Error: Input files have different numbers of pages:", file=sys.stderr)
        for filename, count in page_counts.items():
            print(f"  {filename}: {count} pages", file=sys.stderr)
        return False

    return True


def riffle_shuffle_pdfs(input_files, output_file):
    page_counts = get_page_counts(input_files)

    if page_counts is None:
        return False

    if not validate_page_counts(page_counts):
        return False

    num_pages = list(page_counts.values())[0]

    writer = PdfWriter()

    try:
        file_handles = []
        readers = []

        for filename in input_files:
            f = open(filename, 'rb')
            file_handles.append(f)
            readers.append(PdfReader(f))

        for page_num in range(num_pages):
            for reader in readers:
                writer.add_page(reader.pages[page_num])

        with open(output_file, 'wb') as output:
            writer.write(output)

        for f in file_handles:
            f.close()

        return True

    except Exception as e:
        print(f"Error processing files: {e}", file=sys.stderr)
        for f in file_handles:
            if not f.closed:
                f.close()
        return False


def expand_wildcards(patterns):
    expanded = []
    for pattern in patterns:
        if '*' in pattern or '?' in pattern:
            matches = glob.glob(pattern)
            if matches:
                expanded.extend(sorted(matches))
            else:
                print(f"Warning: No files match pattern '{pattern}'", file=sys.stderr)
        else:
            expanded.append(pattern)
    return expanded


def main():
    parser = argparse.ArgumentParser(
        description='Riffle shuffle multiple PDF files by interleaving pages'
    )

    parser.add_argument('input_files', nargs='+',
                       help='Input PDF files (wildcards supported)')

    parser.add_argument('-o', '--output', required=True,
                       help='Output PDF file')

    args = parser.parse_args()

    input_files = expand_wildcards(args.input_files)

    if not input_files:
        print("Error: No input files provided", file=sys.stderr)
        sys.exit(1)

    for filename in input_files:
        if not os.path.exists(filename):
            print(f"Error: File does not exist: {filename}", file=sys.stderr)
            sys.exit(1)

    success = riffle_shuffle_pdfs(input_files, args.output)

    if not success:
        sys.exit(1)

    print(f"Successfully created {args.output} with riffle-shuffled pages")


if __name__ == '__main__':
    main()