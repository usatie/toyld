#! /usr/bin/env python3

import argparse
import os
import sys

from object import Object, parse_objects
import storage
import symbol


def parse_args():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file>", file=sys.stderr)
        sys.exit(1)

    # parse cli args to populate SKIP_SYMBOLS, SKIP_RELOCATIONS, SKIP_DATA
    parser = argparse.ArgumentParser(description='Simple linker that processes input files and produces an output file.')
    parser.add_argument('input_files', nargs='+', help='Input files to process')
    parser.add_argument('--skip-symbols', action='store_true', help='Skip processing symbols', default=False)
    parser.add_argument('--skip-relocations', action='store_true', help='Skip processing relocations', default=False)
    parser.add_argument('--skip-data', action='store_true', help='Skip processing data section', default=False)
    parser.add_argument('--common', action='store_true', help='Use common symbol resolution strategy (assign common symbols to the end of the bss segment)', default=False)
    parser.add_argument('--output', '-o', help='Specify output file name (default: a.out.lk)', default='a.out.lk')
    return parser.parse_args()

def is_object_file(filename):
    with open(filename, 'rb') as infile:
        magic = infile.read(5)
        return magic == b'LINK\n'

def is_library_file(filename):
    with open(filename, 'rb') as infile:
        magic = infile.read(8)
        return magic == b'LIBRARY '

def link_objects(input_files, use_common):
    # Input files may contain libraries (directory format), so we need to exclude them
    library_dirs = []
    library_files = []
    object_files = []
    for f in input_files:
        if os.path.isdir(f):
            library_dirs.append(f)
        elif is_object_file(f):
            object_files.append(f)
        elif is_library_file(f):
            library_files.append(f)
        else:
            print(f"Warning: {f} is not a valid object file or library, skipping", file=sys.stderr)
            sys.exit(1)
    objs = parse_objects(object_files)
    libsymtab = symbol.collect_symbols(library_dirs)

    # Resolve symbol names
    symbol_table, commons = symbol.resolve_names(objs, libsymtab)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    if len(objs) > 1:
        out_segments = storage.allocate(objs, commons if use_common else {})
        # Resolve symbol values
        symbol.resolve_values(objs, symbol_table, out_segments, commons if use_common else {})
        out_symbols = {name:gsym.to_symbol() for name,gsym in symbol_table.items()}
    else:
        out_segments = objs[0].segments
        out_symbols = objs[0].symbols

    out_relocations = [rel for o in objs for rel in o.relocations]
    # TODO: merge the data sections with the same name (e.g. .data) instead of just concatenating them
    out_data = [d for o in objs for d in o.data]  # combine data from all input files

    return out_segments, out_symbols, out_relocations, out_data

class WriteOptions:
    def __init__(self, skip_symbols, skip_relocations, skip_data):
        self.skip_symbols = skip_symbols
        self.skip_relocations = skip_relocations
        self.skip_data = skip_data

def write_output(filename, link_results, options):

    out_segments, out_symbols, out_relocations, out_data = link_results

    obj = Object(
        filename=filename,
        num_segments=len(out_segments),
        num_symbols=len(out_symbols),
        num_relocations=len(out_relocations),
        segments=out_segments,
        symbols=out_symbols,
        relocations=out_relocations,
        data=out_data,
    )

    contents = obj.serialize(
        skip_symbols=options.skip_symbols,
        skip_relocations=options.skip_relocations,
        skip_data=options.skip_data,
        )
        
    # Check if the output file already exists and remove it
    if os.path.exists(filename):
        os.remove(filename)

    with open(filename, 'wb') as outfile:
        outfile.write(contents)


def main():
    args = parse_args()
    results = link_objects(args.input_files, args.common)
    write_output(
        args.output,
        results,
        WriteOptions(
            skip_symbols=args.skip_symbols,
            skip_relocations=args.skip_relocations,
            skip_data=args.skip_data,
        ),
    )



if __name__ == '__main__':
    main()
