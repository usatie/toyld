#! /usr/bin/env python3

import sys
import os

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
            start = int(start_str)
            size = int(size_str)
            segments.append((name.decode(), start, size, code_letter.decode()))
            print(f"Segment {i}: name={name.decode()}, start={start}, size={size}, code_letter={code_letter.decode()}")
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
            value = int(value_str)
            seg_number = int(seg_number_str)
            symbols.append((name.decode(), value, seg_number, sym_type.decode()))
            print(f"Symbol {i}: name={name.decode()}, value={value}, seg_number={seg_number}, sym_type={sym_type.decode()}")
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
            loc = int(loc_str)
            seg_number = int(seg_number_str)
            ref = int(ref_str)
            relocations.append((loc, seg_number, ref, rel_type.decode(), extra_fields))
            print(f"Relocation {i}: loc={loc}, seg_number={seg_number}, ref={ref}, rel_type={rel_type.decode()}, extra_fields={extra_fields}")
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
        print(f"Data section length: {len(data)} bytes")
        print(f"Data section (hex): {data.hex()}")
        return data
    except ValueError:
        print(f"Invalid data format: expected hex string, got: {line}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file>", file=sys.stderr)
        sys.exit(1)

    output_file = 'newobj'
    input_file = sys.argv[1]

    # Check if the output file already exists and remove it
    if os.path.exists(output_file):
        os.remove(output_file)

    # Simply copy the input file to the output file
    num_segments = 0
    num_symbols = 0
    num_relocations = 0
    segments = []
    symbols = []
    relocations = []
    data = None

    with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
        # Check magic number: 'LINK'
        line = read_next_line(infile)
        if line != b'LINK':
            print("Invalid file format: missing magic number 'LINK'", file=sys.stderr)
            print(f"Got: {line}", file=sys.stderr)
            sys.exit(1)

        # Read header: 'nsegs nsyms nrels'
        line = read_next_line(infile)
        try:
            num_segments, num_symbols, num_relocations = map(int, line.split())
            print(f"Header: num_segments={num_segments}, num_symbols={num_symbols}, num_relocations={num_relocations}")
        except ValueError:
            print("Invalid header format: expected three integers", file=sys.stderr)
            sys.exit(1)

        # Read segments
        parse_segments(infile, num_segments, segments)
        print(f"Segments: {segments}")

        # Read symbols
        parse_symbols(infile, num_symbols, symbols)
        print(f"Symbols: {symbols}")

        # Read relocations
        parse_relocations(infile, num_relocations, relocations)

        # Read data
        data = parse_data(infile)

        # Write the output file
        outfile.write(b'LINK\n')
        outfile.write(f"{num_segments} {num_symbols} {num_relocations}\n".encode())
        for name, start, size, code_letter in segments:
            outfile.write(f"{name} {start} {size} {code_letter}\n".encode())
        for name, value, seg_number, sym_type in symbols:
            outfile.write(f"{name} {value} {seg_number} {sym_type}\n".encode())
        for loc, seg_number, ref, rel_type, extra_fields in relocations:
            extra_str = ' '.join(extra_fields)
            outfile.write(f"{loc} {seg_number} {ref} {rel_type} {extra_str}\n".encode())
        outfile.write(data.hex().encode())
        outfile.write(b'\n') # newline to indicate the end of the data section

if __name__ == '__main__':
    main()
