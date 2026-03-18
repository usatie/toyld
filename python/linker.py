#! /usr/bin/env python3

import sys
import os

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None


# All numbers in the input file are in hex, so we need to convert them from hex to int when parsing

class ObjectFileData:
    def __init__(self, filename, num_segments, num_symbols, num_relocations):
        self.filename = filename
        self.num_segments = num_segments
        self.num_symbols = num_symbols
        self.num_relocations = num_relocations
        self.segments = None
        self.symbols = None
        self.relocations = []
        self.data = None

    def __repr__(self):
        return f"ObjectFileData(filename={self.filename}, segments={self.segments}, symbols={self.symbols}, relocations={self.relocations}, data_length={len(self.data) if self.data else 0})"

class Segment:
    def __init__(self, name, start, size, code_letter):
        self.name = name
        self.start = start
        self.size = size
        self.code_letter = code_letter
        self.assigned_address = None  # this will be used to store the assigned address for this segment when we allocate storage for it

    def __repr__(self):
        if self.assigned_address is None:
            return f"Segment(name={self.name}, start={self.start:x}, size={self.size:x}, code_letter={self.code_letter})"
        else:
            return f"Segment(name={self.name}, start={self.start:x}, size={self.size:x}, code_letter={self.code_letter}, assigned_address={self.assigned_address:x})"

class Symbol:
    def __init__(self, name, value, seg_number, sym_type, number):
        self.name = name
        self.value = value
        self.seg_number = seg_number
        self.sym_type = sym_type
        self.number = number

    def __repr__(self):
        return f"Symbol(name={self.name}, value=0x{self.value:x}, seg_number=0x{self.seg_number:x}, sym_type={self.sym_type})"

class Relocation:
    def __init__(self, loc, seg_number, ref, rel_type, extra_fields):
        self.loc = loc
        self.seg_number = seg_number
        self.ref = ref
        self.rel_type = rel_type
        self.extra_fields = extra_fields

    def __repr__(self):
        return f"Relocation(loc=0x{self.loc:x}, seg_number=0x{self.seg_number:x}, ref=0x{self.ref:x}, rel_type={self.rel_type}, extra_fields={self.extra_fields})"

def read_next_line(f):
    # ignore empty lines and comments to get the next meaningful line
    while True:
        line = f.readline()
        if not line:
            return None  # EOF
        line = line.strip() # remove leading/trailing whitespace
        if line and not line.startswith(b'#'):
            return line

def parse_segments(f, num_segments):
    segments = []
    for i in range(num_segments):
        line = read_next_line(f)
        if line is None:
            print(f"Unexpected end of file while reading segments", file=sys.stderr)
            sys.exit(1)
        try:
            name, start_str, size_str, code_letter = line.split()
            start = int(start_str, 16)
            size = int(size_str, 16)
            seg = Segment(name.decode(), start, size, code_letter.decode())
            segments.append(seg)
            dprint(f"Segment {i}: name={seg.name}, start={seg.start}, size={seg.size}, code_letter={seg.code_letter}")
        except ValueError:
            print(f"Invalid segment format on line: {line}", file=sys.stderr)
            sys.exit(1)
    return segments

def parse_symbols(f, num_symbols):
    symbols = {}
    for i in range(num_symbols):
        line = read_next_line(f)
        if line is None:
            print(f"Unexpected end of file while reading symbols", file=sys.stderr)
            sys.exit(1)
        try:
            name, value_str, seg_number_str, sym_type = line.split()
            value = int(value_str, 16)
            seg_number = int(seg_number_str, 16)
            sym = Symbol(name.decode(), value, seg_number, sym_type.decode(), i + 1) # symbols are numbered starting from 1
            symbols[sym.name] = sym
            dprint(f"Symbol {i}: name={sym.name}, value={sym.value}, seg_number={sym.seg_number}, sym_type={sym.sym_type}")
        except ValueError:
            print(f"Invalid symbol format on line: {line}", file=sys.stderr)
            sys.exit(1)
    return symbols

def parse_relocations(f, num_relocations):
    relocations = []
    for i in range(num_relocations):
        line = read_next_line(f)
        if line is None:
            print(f"Unexpected end of file while reading relocations", file=sys.stderr)
            sys.exit(1)
        try:
            # Relocation entry may contain extra fields other than loc,seg,ref,type
            fields = line.split()
            loc_str, seg_number_str, ref_str, rel_type = fields[0:4]
            extra_fields = map(lambda x: x.decode(), fields[4:])  # decode any extra fields as well
            loc = int(loc_str, 16)
            seg_number = int(seg_number_str, 16)
            ref = int(ref_str, 16)
            relocation = Relocation(loc, seg_number, ref, rel_type.decode(), extra_fields)
            relocations.append(relocation)
            dprint(f"Relocation {i}: loc={relocation.loc}, seg_number={relocation.seg_number}, ref={relocation.ref}, rel_type={relocation.rel_type}, extra_fields={relocation.extra_fields}")
        except ValueError:
            print(f"Invalid relocation format on line: {line}", file=sys.stderr)
            sys.exit(1)
    return relocations

def parse_data(f):
    line = read_next_line(f)
    # The line is a hex string representing the data section, so we need to convert it to bytes
    if line is None:
        print(f"Unexpected end of file while reading data section", file=sys.stderr)
        sys.exit(1)
    try:
        data = bytes.fromhex(line.decode())
        dprint(f"Data section length: {len(data)} bytes")
        dprint(f"Data section (hex): {data.hex()}")
        return data
    except ValueError:
        print(f"Invalid data format: expected hex string, got: {line}", file=sys.stderr)
        sys.exit(1)

def parse_objects(input_files, SKIP_SYMBOLS=False, SKIP_RELOCATIONS=False, SKIP_DATA=False):
    objs = []
    for input_file in input_files:
        # Simply copy the input file to the output file

        with open(input_file, 'rb') as infile:
            dprint(f"Processing input file: {input_file}")
            # Check magic number: 'LINK'
            line = read_next_line(infile)
            if line != b'LINK':
                print("Invalid file format: missing magic number 'LINK'", file=sys.stderr)
                print(f"Got: {line}", file=sys.stderr)
                sys.exit(1)

            # Read header: 'nsegs nsyms nrels'
            line = read_next_line(infile)
            try:
                # num are written in hex, so we need to convert them from hex to int
                num_segments, num_symbols, num_relocations = map(lambda x: int(x, 16), line.split())
                dprint(f"Header: num_segments={num_segments}, num_symbols={num_symbols}, num_relocations={num_relocations}")
                obj = ObjectFileData(input_file, num_segments, num_symbols, num_relocations)
            except ValueError:
                print("Invalid header format: expected three integers", file=sys.stderr)
                sys.exit(1)

            # Read segments
            obj.segments = parse_segments(infile, obj.num_segments)
            dprint(f"Segments: {obj.segments}")

            # Read symbols
            obj.symbols = parse_symbols(infile, num_symbols)
            dprint(f"Symbols: {obj.symbols}")

            # Read relocations
            if not SKIP_RELOCATIONS:
                obj.relocations = parse_relocations(infile, num_relocations)

            # Read data
            if not SKIP_DATA:
                obj.data = parse_data(infile)
        objs.append(obj)
    return objs

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
    # Find all common blocks
    commons = {}

    for o in objs:
        for sym in o.symbols.values():
            is_common = sym.sym_type == 'U' and sym.value > 0
            if is_common:
                if sym.name not in commons:
                    commons[sym.name] = sym
                elif sym.value > commons[sym.name].value:
                    commons[sym.name] = sym
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

def resolve_symbol_values(objs, symbol_table, out_segments):
    for sym in symbol_table.values():
        if sym.is_common:
            # TODO
            pass
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
    parser.add_argument('--debug', action='store_true', help='Enable debug output', default=False)
    args = parser.parse_args()

    SKIP_SYMBOLS = args.skip_symbols
    SKIP_RELOCATIONS = args.skip_relocations
    SKIP_DATA = args.skip_data
    global DEBUG
    DEBUG = args.debug
    input_files = args.input_files

    output_file = 'a.out.lk'

    # Check if the output file already exists and remove it
    if os.path.exists(output_file):
        os.remove(output_file)

    objs = parse_objects(input_files, SKIP_SYMBOLS, SKIP_RELOCATIONS, SKIP_DATA)

    # Resolve symbol names
    symbol_table, commons = resolve_symbol_names(objs)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    if len(objs) > 1:
        out_segments = allocate_storage(objs, commons if args.common else {})
        # Resolve symbol values
        resolve_symbol_values(objs, symbol_table, out_segments)
        out_symbols = [sym.to_symbol() for sym in symbol_table.values()]
    else:
        out_segments = objs[0].segments
        out_symbols = [sym for o in objs for sym in o.symbols.values()]

    out_relocations = [rel for o in objs for rel in o.relocations]
    out_data = b''.join(o.data for o in objs if o.data is not None)  # combine data from all input files

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
                outfile.write(f"{rel.loc:x} {rel.seg_number:x} {rel.ref:x} {rel.rel_type} {extra_str}\n".encode())
        if not SKIP_DATA:
            outfile.write(out_data.hex().encode())
            outfile.write(b'\n') # newline to indicate the end of the data section

if __name__ == '__main__':
    main()
