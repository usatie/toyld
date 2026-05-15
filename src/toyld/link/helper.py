import os
import sys
from pathlib import Path


def is_object_file(filename):
    with open(filename, 'rb') as infile:
        magic = infile.read(5)
        return magic == b'LINK\n'


def is_library_file(filename):
    with open(filename, 'rb') as infile:
        line = infile.readline()
        fields = line.strip().split()
        magic = fields[0] if len(fields) > 0 else b''
        return magic == b'LIBRARY' and len(fields) == 3


def is_stub_library_file(filename):
    with open(filename, 'rb') as infile:
        line = infile.readline()
        fields = line.strip().split()
        magic = fields[0] if len(fields) > 0 else b''
        return magic == b'LIBRARY' and len(fields) > 3


def is_stub_library_directory(dirname):
    # If "LIBRARY NAME" file exists, it's a stub library
    return os.path.isfile(os.path.join(dirname, 'LIBRARY NAME'))


def is_dynamic_shared_library_file(filename):
    with open(filename, 'rb') as infile:
        magic = infile.read(7)
        return magic == b'LINKLIB' and infile.read(1) in (b' ', b'\n')
