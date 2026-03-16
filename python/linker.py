#! /usr/bin/env python3

import sys
import os

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None


# All numbers in the input file are in hex, so we need to convert them from hex to int when parsing

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
            segments.append((name.decode(), start, size, code_letter.decode(), f.name))
            dprint(f"Segment {i}: name={name.decode()}, start={start}, size={size}, code_letter={code_letter.decode()}")
        except ValueError:
            print(f"Invalid segment format on line: {line}", file=sys.stderr)
            sys.exit(1)

def parse_symbols(f, num_symbols, symbols):
    for i in range(num_symbols):
        line = read_next_line(f)
        if line is None:
            print(f"Unexpected end of file while reading symbols", file=sys.stderr)
            sys.exit(1)
        try:
            name, value_str, seg_number_str, sym_type = line.split()
            value = int(value_str, 16)
            seg_number = int(seg_number_str, 16)
            symbols.append((name.decode(), value, seg_number, sym_type.decode(), f.name))
            dprint(f"Symbol {i}: name={name.decode()}, value={value}, seg_number={seg_number}, sym_type={sym_type.decode()}")
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
            relocations.append((loc, seg_number, ref, rel_type.decode(), extra_fields, f.name))
            dprint(f"Relocation {i}: loc={loc}, seg_number={seg_number}, ref={ref}, rel_type={rel_type.decode()}, extra_fields={extra_fields}")
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

    segments = []
    symbols = []
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
            if not SKIP_SYMBOLS:
                parse_symbols(infile, num_symbols, symbols)
                dprint(f"Symbols: {symbols}")

            # Read relocations
            if not SKIP_RELOCATIONS:
                parse_relocations(infile, num_relocations, relocations)

            # Read data
            if not SKIP_DATA:
                data_in_file = parse_data(infile)
                data.append((data_in_file, input_file))

    with open(output_file, 'wb') as outfile:
        # Write the output file
        outfile.write(b'LINK\n')
        outfile.write(f"{num_segments} {num_symbols} {num_relocations}\n".encode())
        for name, start, size, code_letter, filename in segments:
            # we need to convert int back to hex when writing to the output file
            outfile.write(f"{name} {start:x} {size:x} {code_letter}\n".encode())
        if not SKIP_SYMBOLS:
            for name, value, seg_number, sym_type, filename in symbols:
                outfile.write(f"{name} {value:x} {seg_number:x} {sym_type}\n".encode())
        if not SKIP_RELOCATIONS:
            for loc, seg_number, ref, rel_type, extra_fields, filename in relocations:
                extra_str = ' '.join(extra_fields)
                outfile.write(f"{loc:x} {seg_number:x} {ref:x} {rel_type} {extra_str}\n".encode())
        if not SKIP_DATA and data:
            combined_data = b''.join(d for d, filename in data)  # combine data from all input files
            outfile.write(combined_data.hex().encode())
            outfile.write(b'\n') # newline to indicate the end of the data section

if __name__ == '__main__':
    main()
