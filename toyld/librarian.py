#! /usr/bin/env python3

import argparse
import os
import sys


from toyld.object import parse_objects

def create_directory_library(objs, output_dir):
    # Create output directory
    if os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' already exists. Please remove it or choose a different name.", file=sys.stderr)
        sys.exit(1)
    os.mkdir(output_dir)
    # Global symbol table to track all symbols across input modules, mapping symbol name to the input file it came from (for error reporting)
    gsymtab = {}
    for o in objs:
        # Copy input file in the output directory as a temp file to create hardlinks to each symbol in the output directory
        input_file = o.filename
        temp_file = os.path.join(output_dir, os.path.basename(input_file))
        with open(input_file, 'rb') as infile, open(temp_file, 'wb') as outfile:
            outfile.write(infile.read())
        # Add hardlinks to each symbol in the output directory
        for name, sym in o.symbols.items():
            # Skip undefined symbols
            if sym.sym_type != 'D':
                continue
            # Check for duplicate symbol names across input files
            if name in gsymtab:
                print(f"Error: Duplicate symbol '{name}' found in multiple input files: {o.filename} and {gsymtab[name]}. Cannot create library.", file=sys.stderr)
                sys.exit(1)
            gsymtab[name] = o.filename
            link_path = os.path.join(output_dir, name)
            os.link(temp_file, link_path)

        # Delete the output file (the hardlink will still exist in the output directory)
        os.remove(temp_file)

def create_file_library(objs, output_file):
    # Library Header `LIBRARY <nmods> <diroff>`
    num_files = len(objs)
    tmp_dir_offset = 0x10 + sum(os.path.getsize(o.filename) for o in objs) # this is temporary
    header = f"LIBRARY {num_files:x} {tmp_dir_offset:x}\n".encode()

    # object file contents (concatenated to skip comments and whitespace in the input files)
    contents = b''
    mod_sizes = {}
    for o in objs:
        serialized = o.serialize()
        contents += serialized
        mod_sizes[o.filename] = len(serialized)
    # recalculate the directory offset based on the actual header and contents size
    dir_offset = len(header) + len(contents)
    while dir_offset != tmp_dir_offset:
        tmp_dir_offset = dir_offset
        header = f"LIBRARY {num_files:x} {tmp_dir_offset:x}\n".encode()
        dir_offset = len(header) + len(contents)

    # Directory entries (one per symbol)
    dir_entries = b''
    mod_offset = len(header)
    for o in objs:
        mod_size = mod_sizes[o.filename]
        symbols_str = ' '.join(name for name, sym in o.symbols.items() if sym.sym_type == 'D' or (sym.sym_type == 'U' and sym.value > 0))
        dir_entries += f"{mod_offset:x} {mod_size:x} {symbols_str}\n".encode()
        mod_offset += mod_size

    with open(output_file, 'wb') as outfile:
        outfile.write(header)
        outfile.write(contents)
        outfile.write(dir_entries)

def main():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file> [--output <output_file>] [--format <output_format>]", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Simple librarian that creates a library from input object files.')
    parser.add_argument('input_files', nargs='+', help='Input object files to process')
    parser.add_argument('--output', '-o', help='Output file name (default: lib.lk)', default='lib.lk')
    parser.add_argument('--format', '-f', help='Output format (default: directory)', choices=['directory', 'file'], default='directory')
    args = parser.parse_args()

    objs = parse_objects(args.input_files)

    if args.format == 'directory':
        create_directory_library(objs, args.output)
    elif args.format == 'file':
        create_file_library(objs, args.output)
    else:
        print(f"Unsupported output format: {args.format}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
