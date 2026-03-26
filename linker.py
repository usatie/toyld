#! /usr/bin/env python3

import argparse
import os
import sys

from object import Object, Relocation, parse_objects, parse_object
import storage
import symbol
import relocation


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
    parser.add_argument('--output', '-o', help='Specify output file name (default: a.out.lk)', default='a.out.lk')
    parser.add_argument('--byteorder', choices=['big', 'little'], default='little', help='Specify byte order for output file (default: little)')
    parser.add_argument('--wrap', '-w', action='append', help='Use a wrapper function for SYMBOL.', metavar='SYMBOL', default=[])
    return parser.parse_args()

def is_object_file(filename):
    with open(filename, 'rb') as infile:
        magic = infile.read(5)
        return magic == b'LINK\n'

def is_library_file(filename):
    with open(filename, 'rb') as infile:
        magic = infile.read(8)
        return magic == b'LIBRARY '

def link_objects(input_files, byteorder, wrap_symbols):
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
    lib_symtab = symbol.collect_symbols(library_dirs, library_files)

    # Resolve symbol names
    symbol.apply_wraps(objs, wrap_symbols)
    gsymtab = symbol.resolve_names(objs, lib_symtab, wrap_symbols)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    out_segments, gdata = storage.allocate(objs, gsymtab)
    # Resolve symbol values
    symbol.resolve_values(objs, gsymtab, out_segments)
    out_symbols = {name:gsym.to_local() for name,gsym in gsymtab.items()}
    relocation.relocate(objs, gsymtab, gdata, byteorder)
    out_data = [v for v in gdata.values()]
    got_segment_index = next((i + 1 for i, s in enumerate(out_segments) if s.name == '.got'), None)
    out_relocations = [Relocation(s.got_offset, got_segment_index, 0, 'ER4', [])  for s in gsymtab.values() if s.got_offset is not None]

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
    if len(args.input_files) == 1:
        # If only one input file, just copy it to the output (with optional skipping)
        obj = parse_object(args.input_files[0])
        write_output(
            args.output,
            (obj.segments, obj.symbols, obj.relocations, obj.data),
            WriteOptions(
                skip_symbols=args.skip_symbols,
                skip_relocations=args.skip_relocations,
                skip_data=args.skip_data,
            ),
        )
    else:
        # Multiple input files, need to link them together
        results = link_objects(args.input_files, args.byteorder, args.wrap)
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
