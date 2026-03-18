#! /usr/bin/env python3

import sys
import os
from object import parse_objects

def main():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file> [--output <output_file>]", file=sys.stderr)
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description='Simple librarian that creates a library from input object files.')
    parser.add_argument('input_files', nargs='+', help='Input object files to process')
    parser.add_argument('--output', '-o', help='Output file name (default: lib.lk)', default='lib.lk')
    args = parser.parse_args()

if __name__ == '__main__':
    main()
