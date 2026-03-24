#! /usr/bin/env python3

import argparse
import os
import sys


from object import parse_objects

def main():
    parser = argparse.ArgumentParser(description='Simple object symbol wrapper that redirects all references to wrapped symbols, and renames the original symbols with a prefix.')
    parser.add_argument('input_files', nargs='+', help='Input object file')
    parser.add_argument('--wrap', '-w', action='append', default=[], help='Symbol to wrap (can be specified multiple times)')
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

if __name__ == '__main__':
    main()
