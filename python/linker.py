import sys
import os

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
        # Iterate through the lines in the input file and print them to the output file
        # TODO: Check magic number
        line = infile.readline()
        if line != b'LINK\n':
            print("Invalid file format: missing magic number 'LINK'", file=sys.stderr)
            sys.exit(1)
        # TODO: Read header and populate num_segments, num_symbols, num_relocations
        # TODO: Read segments
        # TODO: Read symbols
        # TODO: Read relocations
        # TODO: Read data

    with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
        outfile.write(infile.read())

if __name__ == '__main__':
    main()
