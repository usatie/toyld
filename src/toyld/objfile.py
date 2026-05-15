import io
import sys
from enum import Enum

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None

class ObjectType(Enum):
    OBJECT = 0
    STUB_LIBRARY = 1
    DYNAMIC_SHARED_LIB = 2

class Object:
    def __init__(self, filename, num_segments, num_symbols, num_relocations, segments=None, symbols=None, relocations=None, data=None, is_stub_library=False, is_dynamic_shared_lib=False, deps=None):
        self.filename = filename
        self.num_segments = num_segments
        self.num_symbols = num_symbols
        self.num_relocations = num_relocations
        self.segments = segments
        self.symbols = symbols
        self.relocations = relocations
        self.data = data
        self.mod = None  # this will be used to store the Module object that this Object belongs to when we parse the input files into Modules and Objects
        self.deps = deps if deps else [] # This will be used to store the dependencies of this object if it's a dynamic shared library (LINKLIB) or an executable (LINK) with dynamic shared library dependencies.
        if is_stub_library and is_dynamic_shared_lib:
            print(f"Object '{filename}' cannot be both a stub library and a dynamic shared library", file=sys.stderr)
            sys.exit(1)
        self.type = ObjectType.OBJECT
        if is_stub_library:
            self.type = ObjectType.STUB_LIBRARY
        if is_dynamic_shared_lib:
            self.type = ObjectType.DYNAMIC_SHARED_LIB

    @property
    def is_stub_library(self):
        return self.type == ObjectType.STUB_LIBRARY

    @property
    def is_dynamic_shared_lib(self):
        return self.type == ObjectType.DYNAMIC_SHARED_LIB

    def serialize(self, skip_symbols=False, skip_relocations=False, skip_data=False):
        contents = b''
        # Magic number
        if self.is_dynamic_shared_lib:
            contents = b' '.join([b'LINKLIB'] + self.deps) + b'\n'
        else:
            contents = b' '.join([b'LINK'] + self.deps) + b'\n'
        # Header
        num_segments = len(self.segments)
        num_symbols = 0 if skip_symbols else len(self.symbols)
        num_relocations = 0 if skip_relocations else len(self.relocations)
        contents += f"{num_segments:x} {num_symbols:x} {num_relocations:x}\n".encode()
        # Segments
        for s in self.segments:
            contents += f"{s.name} {s.start:x} {s.size:x} {s.code_letter}\n".encode()
        # Symbols
        if not skip_symbols:
            for sym in self.symbols.values():
                contents += f"{sym.name} {sym.value:x} {sym.seg_number:x} {sym.sym_type}\n".encode()
        # Relocations
        if not skip_relocations:
            for rel in self.relocations:
                extra_str = ' '.join(rel.extra_fields)
                contents += f"{rel.loc:x} {rel.seg_number:x} {rel.ref:x} {rel.rel_type}".encode()
                if extra_str:
                    contents += f" {extra_str}".encode()
                contents += b'\n'
        # Data
        if not skip_data:
            if self.data:
                for d in self.data:
                    contents += d.hex().encode()
                    contents += b'\n'
        return contents

    def __repr__(self):
        return f"Object(filename={self.filename}, segments={self.segments}, symbols={self.symbols}, relocations={self.relocations}, data_length={len(self.data) if self.data else 0}, is_stub_library={self.is_stub_library})"

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

"""
The name is the symbol name. The value is the hexadecimal value of the sym-bol. seg is the segment number relative to which the segment is defined (0 for absolute or undefined symbols). The type is a string of letters that includes D for defined or U for undefined. Symbols are also numbered in the order they're listed, starting at 1.
"""
class Symbol:
    def __init__(self, name, value, seg_number, sym_type, number=None):
        self.name = name
        self.value = value
        self.seg_number = seg_number
        self.sym_type = sym_type
        self.number = number

    @classmethod
    def absolute(cls, name, value):
        # Absolute symbols are defined symbols, their value is an absolute address
        return cls(name=name, value=value, seg_number=0, sym_type='D')

    @property
    def is_defined(self):
        return self.sym_type == 'D'

    @property
    def is_common(self):
        return self.sym_type == 'U' and self.value > 0

    @property
    def is_undefined(self):
        return self.sym_type == 'U' and self.value == 0

    def __repr__(self):
        return f"Symbol(name={self.name}, value=0x{self.value:x}, seg_number=0x{self.seg_number:x}, sym_type={self.sym_type}, number={self.number})"

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
            extra_fields = list(map(lambda x: x.decode(), fields[4:]))  # decode any extra fields as well
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

def parse_data(f, num_data):
    data = []
    for i in range(num_data):
        line = read_next_line(f)
        # The line is a hex string representing the data section, so we need to convert it to bytes
        if line is None:
            data.append(b'') # It is possible that the data section is empty, so we can treat EOF as an empty data section
            if i < num_data - 1:
                print(f"Unexpected end of file while reading data sections: expected {num_data} sections, but got {i + 1}", file=sys.stderr)
                sys.exit(1)
            continue

        try:
            datum = bytes.fromhex(line.decode())
            dprint(f"Data section length: {len(datum)} bytes")
            dprint(f"Data section (hex): {datum.hex()}")
            data.append(datum)
        except ValueError:
            print(f"Invalid data format: expected hex string, got: {line}", file=sys.stderr)
            sys.exit(1)
    return data

class LimitedReader(io.RawIOBase):
    """Wraps a file object to limit reads to a specified number of bytes."""
    def __init__(self, f, limit):
        self._f = f
        self._remaining = limit

    def readinto(self, b):
        if self._remaining <= 0:
            return 0
        max_read = min(len(b), self._remaining)
        data = self._f.read(max_read)
        n = len(data)
        b[:n] = data
        self._remaining -= n
        return n

    def readable(self):
        return True

def parse_object(filename, is_stub_library=False):
    dprint(f"Processing input file: {filename}")
    with open(filename, 'rb') as infile:
        return _parse_object(filename, infile, is_stub_library)

def parse_module(filename, offset, size, is_stub_library=False):
    dprint(f"Processing input file: {filename} with offset={offset} and size={size}")
    with open(filename, 'rb') as infile:
        infile.seek(offset)
        reader = io.BufferedReader(LimitedReader(infile.raw, size))
        return _parse_object(filename, reader, is_stub_library)

def _parse_object(filename, reader, is_stub_library):
    # Check magic number: 'LINK' or 'LINKLIB'
    line = read_next_line(reader)
    magic, *deps = line.split()
    if magic not in (b'LINK', b'LINKLIB'):
        print("Invalid file format: missing magic 'LINK' or 'LINKLIB'", file=sys.stderr)
        print(f"Got: {line}", file=sys.stderr)
        sys.exit(1)

    # Read header: 'nsegs nsyms nrels'
    line = read_next_line(reader)
    try:
        # num are written in hex, so we need to convert them from hex to int
        num_segments, num_symbols, num_relocations = map(lambda x: int(x, 16), line.split())
        dprint(f"Header: num_segments={num_segments}, num_symbols={num_symbols}, num_relocations={num_relocations}")
        obj = Object(filename, num_segments, num_symbols, num_relocations, is_stub_library=is_stub_library, is_dynamic_shared_lib=(magic == b'LINKLIB'), deps=deps)
    except ValueError:
        print("Invalid header format: expected three integers", file=sys.stderr)
        sys.exit(1)

    #Read segments
    obj.segments = parse_segments(reader, obj.num_segments)
    if is_stub_library:
        for seg in obj.segments:
            seg.assigned_address = 0  # For stub libraries, we can assign 0 since they are fixed absolute addresses
    dprint(f"Segments: {obj.segments}")

    # Read symbols
    obj.symbols = parse_symbols(reader, num_symbols)
    dprint(f"Symbols: {obj.symbols}")

    # Read relocations
    obj.relocations = parse_relocations(reader, num_relocations)

    # Read data
    # count all segments that have 'P': present in their code letter
    num_data = sum(1 for seg in obj.segments if 'P' in seg.code_letter)
    obj.data = parse_data(reader, num_data)
    for i, seg in enumerate(s for s in obj.segments if 'P' in s.code_letter):
        if seg.size != len(obj.data[i]):
            print(f"Data length mismatch for segment '{seg.name}': expected {seg.size} bytes, got {len(obj.data[i])} bytes", file=sys.stderr)
            sys.exit(1)
    return obj

def parse_objects(input_files):
    return [parse_object(f) for f in input_files]
