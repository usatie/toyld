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

        # TODO: Read segments
        # TODO: Read symbols
        # TODO: Read relocations
        # TODO: Read data

    with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
        outfile.write(infile.read())

if __name__ == '__main__':
    main()
