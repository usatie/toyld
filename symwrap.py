#! /usr/bin/env python3

import argparse
import os
import sys


from object import parse_objects
from symbol import apply_wraps

def parse_args():
    parser = argparse.ArgumentParser(description='Simple object symbol wrapper that redirects all references to wrapped symbols, and renames the original symbols with a prefix.')
    parser.add_argument('input_files', nargs='+', help='Input object file')
    parser.add_argument('--wrap', '-w', action='append', default=[], help='Symbol to wrap (can be specified multiple times)')
    parser.add_argument('--output-dir', '-o', default='.', help='Output directory for wrapped object files (default: current directory)')
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    input_files = args.input_files

    objs = parse_objects(input_files)

    # Apply the wraps to the objects, which will modify the symbol tables and references accordingly
    apply_wraps(objs, args.wrap)

    # Write the modified objects back to disk with a "wrapped_" prefix in the filename
    for o in objs:
        contents = o.serialize()
        basefilename = os.path.basename(o.filename)
        filename = f"wrapped_{basefilename}"
        path = os.path.join(args.output_dir, filename)
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        if os.path.exists(path):
            print(f"Warning: Output file {path} already exists and will be overwritten.")
        with open(path, 'wb') as outfile:
            outfile.write(contents)

if __name__ == '__main__':
    main()
