#! /usr/bin/env python3

import argparse
import os
import sys

from object import parse_objects
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

def link_objects(input_files, use_common):
    # Input files may contain libraries (directory format), so we need to exclude them
    library_dirs = [f for f in input_files if os.path.isdir(f)]
    object_files = [f for f in input_files if os.path.isfile(f)]
    objs = parse_objects(object_files)
    libsymtab = symbol.collect_symbols(library_dirs)

    # Resolve symbol names
    symbol_table, commons = symbol.resolve_names(objs, libsymtab)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    if len(objs) > 1:
        out_segments = storage.allocate(objs, commons if use_common else {})
        # Resolve symbol values
        symbol.resolve_values(objs, symbol_table, out_segments, commons if use_common else {})
        out_symbols = [sym.to_symbol() for sym in symbol_table.values()]
    else:
        out_segments = objs[0].segments
        out_symbols = [sym for o in objs for sym in o.symbols.values()]

    out_relocations = [rel for o in objs for rel in o.relocations]
    out_data = '\n'.join(d.hex() for o in objs for d in o.data)  # combine data from all input files

    return out_segments, out_symbols, out_relocations, out_data

class WriteOptions:
    def __init__(self, skip_symbols, skip_relocations, skip_data):
        self.skip_symbols = skip_symbols
        self.skip_relocations = skip_relocations
        self.skip_data = skip_data

def write_output(filename, link_results, options):

    out_segments, out_symbols, out_relocations, out_data = link_results

    contents = b''
    # Magic number
    contents += b'LINK\n'
    # Header
    num_segments = len(out_segments)
    num_symbols = 0 if options.skip_symbols else len(out_symbols)
    num_relocations = 0 if options.skip_relocations else len(out_relocations)
    contents += f"{num_segments:x} {num_symbols:x} {num_relocations:x}\n".encode()
    # Segments
    for s in out_segments:
        contents += f"{s.name} {s.start:x} {s.size:x} {s.code_letter}\n".encode()
    # Symbols
    if not options.skip_symbols:
        for sym in out_symbols:
            contents += f"{sym.name} {sym.value:x} {sym.seg_number:x} {sym.sym_type}\n".encode()
    # Relocations
    if not options.skip_relocations:
        for rel in out_relocations:
            extra_str = ' '.join(rel.extra_fields)
            contents += f"{rel.loc:x} {rel.seg_number:x} {rel.ref:x} {rel.rel_type}".encode()
            if extra_str:
                contents += f" {extra_str}".encode()
            contents += b'\n'
    # Data
    if not options.skip_data:
        if out_data:
            contents += out_data.encode()
            contents += b'\n'

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
