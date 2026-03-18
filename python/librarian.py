#! /usr/bin/env python3

import sys
import os
from object import parse_objects

def create_directory_library(objs, output_dir):
    # Create output directory
    if os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' already exists. Please remove it or choose a different name.", file=sys.stderr)
        sys.exit(1)
    os.mkdir(output_dir)

def main():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file> [--output <output_file>] [--format <output_format>]", file=sys.stderr)
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description='Simple librarian that creates a library from input object files.')
    parser.add_argument('input_files', nargs='+', help='Input object files to process')
    parser.add_argument('--output', '-o', help='Output file name (default: lib.lk)', default='lib.lk')
    parser.add_argument('--format', '-f', help='Output format (default: directory)', choices=['directory', 'file'], default='directory')
    args = parser.parse_args()

    objs = parse_objects(args.input_files)

    if args.format == 'directory':
        create_directory_library(objs, args.output)
    else:
        print(f"Unsupported output format: {args.format}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
