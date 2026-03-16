#! /usr/bin/env python3

import sys
import os

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None


# All numbers in the input file are in hex, so we need to convert them from hex to int when parsing

class Segment:
    def __init__(self, name, start, size, code_letter, filename=None):
        self.name = name
        self.start = start
        self.size = size
        self.code_letter = code_letter
        self.filename = filename
        self.assigned_address = None  # this will be used to store the assigned address for this segment when we allocate storage for it

    def __repr__(self):
        if self.assigned_address is None:
            return f"Segment(name={self.name}, start={self.start:x}, size={self.size:x}, code_letter={self.code_letter}, filename={self.filename})"
        else:
            return f"Segment(name={self.name}, start={self.start:x}, size={self.size:x}, code_letter={self.code_letter}, filename={self.filename}, assigned_address={self.assigned_address:x})"

class Symbol:
    def __init__(self, name, value, seg_number, sym_type, filename=None):
        self.name = name
        self.value = value
        self.seg_number = seg_number
        self.sym_type = sym_type
        self.filename = filename

    def __repr__(self):
        return f"Symbol(name={self.name}, value=0x{self.value:x}, seg_number=0x{self.seg_number:x}, sym_type={self.sym_type}, filename={self.filename})"

class Relocation:
    def __init__(self, loc, seg_number, ref, rel_type, extra_fields, filename=None):
        self.loc = loc
        self.seg_number = seg_number
        self.ref = ref
        self.rel_type = rel_type
        self.extra_fields = extra_fields
        self.filename = filename

def read_next_line(f):
    # ignore empty lines and comments to get the next meaningful line
    while True:
        line = f.readline()
        if not line:
            return None  # EOF
        line = line.strip() # remove leading/trailing whitespace
        if line and not line.startswith(b'#'):
            return line

def parse_segments(f, num_segments, segments):
    for i in range(num_segments):
        line = read_next_line(f)
        if line is None:
            print(f"Unexpected end of file while reading segments", file=sys.stderr)
            sys.exit(1)
        try:
            name, start_str, size_str, code_letter = line.split()
            start = int(start_str, 16)
            size = int(size_str, 16)
            seg = Segment(name.decode(), start, size, code_letter.decode(), f.name)
            segments.append(seg)
            dprint(f"Segment {i}: name={seg.name}, start={seg.start}, size={seg.size}, code_letter={seg.code_letter}")
        except ValueError:
            print(f"Invalid segment format on line: {line}", file=sys.stderr)
            sys.exit(1)

def parse_symbols(f, num_symbols, symbols, commons):
    for i in range(num_symbols):
        line = read_next_line(f)
        if line is None:
            print(f"Unexpected end of file while reading symbols", file=sys.stderr)
            sys.exit(1)
        try:
            name, value_str, seg_number_str, sym_type = line.split()
            value = int(value_str, 16)
            seg_number = int(seg_number_str, 16)
            sym = Symbol(name.decode(), value, seg_number, sym_type.decode(), f.name)
            symbols.append(sym)
            if sym.sym_type == 'U' and sym.value > 0:
                if sym.name not in commons:
                    commons[sym.name] = sym
                elif sym.value > commons[sym.name].value:
                    commons[sym.name] = sym
            dprint(f"Symbol {i}: name={sym.name}, value={sym.value}, seg_number={sym.seg_number}, sym_type={sym.sym_type}")
        except ValueError:
            print(f"Invalid symbol format on line: {line}", file=sys.stderr)
            sys.exit(1)

def parse_relocations(f, num_relocations, relocations):
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
            relocation = Relocation(loc, seg_number, ref, rel_type.decode(), extra_fields, f.name)
            relocations.append(relocation)
            dprint(f"Relocation {i}: loc={relocation.loc}, seg_number={relocation.seg_number}, ref={relocation.ref}, rel_type={relocation.rel_type}, extra_fields={relocation.extra_fields}")
        except ValueError:
            print(f"Invalid relocation format on line: {line}", file=sys.stderr)
            sys.exit(1)

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
    COMMON = args.common
    global DEBUG
    DEBUG = args.debug
    input_files = args.input_files

    output_file = 'a.out.lk'

    # Check if the output file already exists and remove it
    if os.path.exists(output_file):
        os.remove(output_file)

    segments = []
    symbols = []
    commons = {}
    relocations = []
    data = []
    for input_file in input_files:
        # Simply copy the input file to the output file
        num_segments = 0
        num_symbols = 0
        num_relocations = 0

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
            except ValueError:
                print("Invalid header format: expected three integers", file=sys.stderr)
                sys.exit(1)

            # Read segments
            parse_segments(infile, num_segments, segments)
            dprint(f"Segments: {segments}")

            # Read symbols
            parse_symbols(infile, num_symbols, symbols, commons)
            dprint(f"Symbols: {symbols}")

            # Read relocations
            if not SKIP_RELOCATIONS:
                parse_relocations(infile, num_relocations, relocations)

            # Read data
            if not SKIP_DATA:
                data_in_file = parse_data(infile)
                data.append((data_in_file, input_file))

    dprint(f"Common symbols: {commons}")

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    if len(input_files) > 1:
        text_start = 0x1000 # start text segment at 0x1000 to leave some space for the header
        text_size = 0
        data_size = 0
        bss_size = 0
        WORD_ALIGNMENT = 0x0004
        PAGE_ALIGNMENT = 0x1000

        def roundup(size, alignment):
            return (size + alignment - 1) // alignment * alignment

        for seg in segments:
            if seg.name == '.text':
                seg.assigned_address = text_size
                text_size += roundup(seg.size, WORD_ALIGNMENT)
            elif seg.name == '.data': 
                seg.assigned_address = data_size
                data_size += roundup(seg.size, WORD_ALIGNMENT)
            elif seg.name == '.bss':
                seg.assigned_address = bss_size
                bss_size += roundup(seg.size, WORD_ALIGNMENT)

        data_start = roundup(text_start + text_size, PAGE_ALIGNMENT)
        bss_start = roundup(data_start + data_size, WORD_ALIGNMENT)
        for seg in segments:
            if seg.name == '.text':
                seg.assigned_address = text_start + seg.assigned_address
            elif seg.name == '.data':
                seg.assigned_address = data_start + seg.assigned_address
            elif seg.name == '.bss':
                seg.assigned_address = bss_start + seg.assigned_address
        if COMMON:
            common_start = roundup(bss_start + bss_size, WORD_ALIGNMENT)
            common_size = 0
            for sym_name, sym in commons.items():
                address = roundup(common_start + common_size, WORD_ALIGNMENT)
                common_size = address + sym.value - common_start
            bss_size = common_start + common_size - bss_start
        non_standard_segments = [s for s in segments if s.name not in ['.text', '.data', '.bss']]

        out_segments = [Segment('.text', text_start, text_size, 'RP'),
                        Segment('.data', data_start, data_size, 'RWP'),
                        Segment('.bss', bss_start, bss_size, 'RW')] + non_standard_segments
    else:
        out_segments = segments

    with open(output_file, 'wb') as outfile:
        # Write the output file
        outfile.write(b'LINK\n')
        if SKIP_SYMBOLS:
            num_symbols = 0
        if SKIP_RELOCATIONS:
            num_relocations = 0
        outfile.write(f"{num_segments} {num_symbols} {num_relocations}\n".encode())
        for s in out_segments:
            # we need to convert int back to hex when writing to the output file
            outfile.write(f"{s.name} {s.start:x} {s.size:x} {s.code_letter}\n".encode())
        if not SKIP_SYMBOLS:
            for sym in symbols:
                outfile.write(f"{sym.name} {sym.value:x} {sym.seg_number:x} {sym.sym_type}\n".encode())
        if not SKIP_RELOCATIONS:
            for rel in relocations:
                extra_str = ' '.join(rel.extra_fields)
                outfile.write(f"{rel.loc:x} {rel.seg_number:x} {rel.ref:x} {rel.rel_type} {extra_str}\n".encode())
        if not SKIP_DATA and data:
            combined_data = b''.join(d for d, filename in data)  # combine data from all input files
            outfile.write(combined_data.hex().encode())
            outfile.write(b'\n') # newline to indicate the end of the data section

if __name__ == '__main__':
    main()
