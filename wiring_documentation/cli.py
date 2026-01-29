#!/usr/bin/env python3

import argparse
import sys
import os
from pathlib import Path

from .builder import DocumentationPackBuilder


def build_command(args):
    """Handle the build command."""
    config_file = args.config_file

    # Determine output filename
    if args.output_file:
        output_file = args.output_file
    else:
        # Default: same name as config but with .pdf extension
        config_path = Path(config_file)
        output_file = config_path.stem + '.pdf'

    # Build the documentation pack
    try:
        builder = DocumentationPackBuilder(config_file)
        builder.build(
            output_file,
            auto_yes=args.auto_yes,
            retain_working_dir=args.debug_retain_working_directory,
            custom_timestamp=args.set_timestamp
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def check_command(args):
    """Handle the check command."""
    config_file = args.config_file

    try:
        builder = DocumentationPackBuilder(config_file)
        if builder.check():
            return 0
        else:
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Wiring Documentation Generator - Build construction wiring documentation packs',
        prog='wiring-documentation'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    subparsers.required = True

    # Build command
    build_parser = subparsers.add_parser('build', help='Build documentation pack from configuration')
    build_parser.add_argument('config_file', help='YAML configuration file')
    build_parser.add_argument('output_file', nargs='?', help='Output PDF file (default: <config_name>.pdf)')
    build_parser.add_argument('-y', '--auto-yes', action='store_true',
                             help='Automatically answer yes to prompts')
    build_parser.add_argument('--debug-retain-working-directory', action='store_true',
                             help='Retain working directory for debugging')
    build_parser.add_argument('--set-timestamp', type=str,
                             help='Use specified timestamp string instead of current time')
    build_parser.set_defaults(func=build_command)

    # Check command
    check_parser = subparsers.add_parser('check', help='Check configuration validity without building')
    check_parser.add_argument('config_file', help='YAML configuration file')
    check_parser.set_defaults(func=check_command)

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
