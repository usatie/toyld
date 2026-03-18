#! /usr/bin/env python3

import sys
import os
from object import parse_objects, Segment, Symbol

# All numbers in the input file are in hex, so we need to convert them from hex to int when parsing


def roundup(size, alignment):
    return (size + alignment - 1) // alignment * alignment

def allocate_storage(objs, commons):
    # start text segment at 0x1000 to leave some space for the header
    TEXT_START = 0x1000
    VALID_SEGMENT_TYPES = {'RP', 'RWP', 'RW'}
    groups = {
        '.text': Segment('.text', 0, 0, 'RP'),
        '.data': Segment('.data', 0, 0, 'RWP'),
        '.bss': Segment('.bss', 0, 0, 'RW'),
    }
    WORD_ALIGNMENT = 0x0004
    PAGE_ALIGNMENT = 0x1000

    # Calculate the size of each segment group (textgroup, datagroup, bssgroup)
    for o in objs:
        for seg in o.segments:
            if seg.code_letter not in VALID_SEGMENT_TYPES:
                print(f"Invalid code letter '{seg.code_letter}' in segment '{seg.name}' from file '{seg.filename}'", file=sys.stderr)
                sys.exit(1)
            if seg.name not in groups:
                groups[seg.name] = Segment(seg.name, 0, 0, seg.code_letter)
            g = groups[seg.name]
            if g.code_letter != seg.code_letter:
                print(f"Segment '{seg.name}' has inconsistent code letters: '{g.code_letter}' and '{seg.code_letter}'", file=sys.stderr)
                sys.exit(1)
            
            seg.assigned_offset = g.size # For now, assign offset in the merged segment for now
            g.size += roundup(seg.size, WORD_ALIGNMENT)

    # Calculate the start address of segments in textgroup
    text_group_start = TEXT_START
    text_group_size = 0
    text_group = []
    for seg in groups.values():
        if seg.code_letter != 'RP': # Only allocate space for segments in the text group
            continue
        seg.start = text_group_start + text_group_size
        text_group_size += roundup(seg.size, WORD_ALIGNMENT)
        text_group.append(seg)

    # Calculate the start address of segments in datagroup
    data_group_start = roundup(text_group_start + text_group_size, PAGE_ALIGNMENT)
    data_group_size = 0 
    data_group = []
    for seg in groups.values():
        if seg.code_letter != 'RWP':
            continue
        seg.start = data_group_start + data_group_size
        data_group_size += roundup(seg.size, WORD_ALIGNMENT)
        data_group.append(seg)

    # Calculate the start address of segments in bssgroup
    bss_group_start = roundup(data_group_start + data_group_size, WORD_ALIGNMENT)
    bss_group_size = 0
    bss_group = []
    # Allocate space for common blocks at the end of the bss segment
    bss_start = bss_group_start
    bss_size = groups['.bss'].size
    common_start = roundup(bss_start + bss_size, WORD_ALIGNMENT)
    common_size = 0
    for sym_name, sym in commons.items():
        address = roundup(common_start + common_size, WORD_ALIGNMENT)
        common_size = address + sym.value - common_start
        sym.assigned_address = address
    bss_size = common_start + common_size - bss_start
    groups['.bss'].size = bss_size
    for seg in groups.values():
        if seg.code_letter != 'RW':
            continue
        seg.start = bss_group_start + bss_group_size
        bss_group_size += roundup(seg.size, WORD_ALIGNMENT)
        bss_group.append(seg)

    # Now assign addresses to all segments based on the group they belong to
    for o in objs:
        for seg in o.segments:
            seg.assigned_address = seg.assigned_offset + groups[seg.name].start # Add the group start address to get the final assigned address
    return [Segment(seg.name, seg.start, seg.size, seg.code_letter) for seg in (text_group + data_group + bss_group)]

class GlobalSymbol:
    def __init__(self, name, is_defined, is_common, obj):
        self.name = name
        self.is_defined = is_defined
        self.is_common = is_common
        self.obj = obj
        self.value = 0 # TODO: needs to be resolved later

    def to_symbol(self):
        SYM_ABSOLUTE = 0
        return Symbol(self.name, self.value, SYM_ABSOLUTE, 'D' if self.is_defined else 'U', 0)

    def __repr__(self):
        return f"GlobalSymbol(name={self.name}, is_defined={self.is_defined}, obj={self.obj.filename})"

def resolve_symbol_names(objs):
    global_symbol_table = {}
    commons = {}

    for o in objs:
        for sym in o.symbols.values():
            # Find common blocks and keep track of the largest common block for each symbol name
            is_common = sym.sym_type == 'U' and sym.value > 0
            if is_common:
                if sym.name not in commons:
                    commons[sym.name] = sym
                elif sym.value > commons[sym.name].value:
                    commons[sym.name] = sym
            # Find global symbols and check for multiply defined symbols and inconsistent definitions
            is_defined = sym.sym_type == 'D'
            if sym.name not in global_symbol_table:
                global_symbol_table[sym.name] = GlobalSymbol(sym.name, is_defined, is_common, o)
                continue
            if not is_defined:
                continue
            existing_sym  = global_symbol_table[sym.name]
            if is_common ^ existing_sym.is_common:
                print(f"Error: symbol '{sym.name}' has inconsistent definitions: one is common and the other is not", file=sys.stderr)
                sys.exit(1)
            if existing_sym.is_defined:
                print(f"Error: symbol '{sym.name}' is multiply defined in files '{existing_sym.obj.filename}' and '{o.filename}'", file=sys.stderr)
                sys.exit(1)
            existing_sym.is_defined = True
            existing_sym.obj = o
    for sym in global_symbol_table.values():
        if not sym.is_defined and not sym.is_common:
            print(f"Error: symbol '{sym.name}' is undefined but referenced in file '{sym.obj.filename}'", file=sys.stderr)
            sys.exit(1)
    return global_symbol_table, commons

def resolve_symbol_values(objs, symbol_table, out_segments, commons):
    for sym in symbol_table.values():
        if sym.is_common and sym.name in commons:
            common_sym = commons[sym.name]
            sym.value = common_sym.assigned_address
        elif sym.is_defined:
            local_sym = sym.obj.symbols[sym.name]
            seg = sym.obj.segments[local_sym.seg_number - 1]
            sym.value = seg.assigned_address + local_sym.value

def main():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file>", file=sys.stderr)
        sys.exit(1)

    # parse cli args to populate SKIP_SYMBOLS, SKIP_RELOCATIONS, SKIP_DATA
    import argparse
    parser = argparse.ArgumentParser(description='Simple linker that processes input files and produces an output file.')
    parser.add_argument('input_files', nargs='+', help='Input files to process')
    parser.add_argument('--skip-symbols', action='store_true', help='Skip processing symbols', default=False)
    parser.add_argument('--skip-relocations', action='store_true', help='Skip processing relocations', default=False)
    parser.add_argument('--skip-data', action='store_true', help='Skip processing data section', default=False)
    parser.add_argument('--common', action='store_true', help='Use common symbol resolution strategy (assign common symbols to the end of the bss segment)', default=False)
    args = parser.parse_args()

    SKIP_SYMBOLS = args.skip_symbols
    SKIP_RELOCATIONS = args.skip_relocations
    SKIP_DATA = args.skip_data
    input_files = args.input_files

    output_file = 'a.out.lk'

    # Check if the output file already exists and remove it
    if os.path.exists(output_file):
        os.remove(output_file)

    objs = parse_objects(input_files)

    # Resolve symbol names
    symbol_table, commons = resolve_symbol_names(objs)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    if len(objs) > 1:
        out_segments = allocate_storage(objs, commons if args.common else {})
        # Resolve symbol values
        resolve_symbol_values(objs, symbol_table, out_segments, commons if args.common else {})
        out_symbols = [sym.to_symbol() for sym in symbol_table.values()]
    else:
        out_segments = objs[0].segments
        out_symbols = [sym for o in objs for sym in o.symbols.values()]

    out_relocations = [rel for o in objs for rel in o.relocations]
    out_data = '\n'.join(d.hex() for o in objs for d in o.data)  # combine data from all input files

    with open(output_file, 'wb') as outfile:
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

if __name__ == '__main__':
    main()
