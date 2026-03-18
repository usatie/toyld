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
    objs = parse_objects(input_files)

    # Resolve symbol names
    symbol_table, commons = symbol.resolve_names(objs)

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
    SKIP_SYMBOLS = options.skip_symbols
    SKIP_RELOCATIONS = options.skip_relocations
    SKIP_DATA = options.skip_data

    # Check if the output file already exists and remove it
    if os.path.exists(filename):
        os.remove(filename)

    with open(filename, 'wb') as outfile:
        # Write the output file
        outfile.write(b'LINK\n')
        num_segments = len(out_segments)
        num_symbols = 0 if SKIP_SYMBOLS else len(out_symbols)
        num_relocations = 0 if SKIP_RELOCATIONS else len(out_relocations)
        outfile.write(f"{num_segments:x} {num_symbols:x} {num_relocations:x}\n".encode())
        for s in out_segments:
            # we need to convert int back to hex when writing to the output file
            outfile.write(f"{s.name} {s.start:x} {s.size:x} {s.code_letter}\n".encode())
        if not SKIP_SYMBOLS:
            for sym in out_symbols:
                outfile.write(f"{sym.name} {sym.value:x} {sym.seg_number:x} {sym.sym_type}\n".encode())
        if not SKIP_RELOCATIONS:
            for rel in out_relocations:
                extra_str = ' '.join(rel.extra_fields)
                outfile.write(f"{rel.loc:x} {rel.seg_number:x} {rel.ref:x} {rel.rel_type}".encode())
                if extra_str:
                    outfile.write(f" {extra_str}".encode())
                outfile.write(b'\n')
        if not SKIP_DATA:
            outfile.write(out_data.encode())
            outfile.write(b'\n') # newline to indicate the end of the data section


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
