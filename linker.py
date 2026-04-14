#! /usr/bin/env python3

import argparse
import os
import sys

from object import Object, Segment, Symbol, Relocation, parse_objects, parse_object, parse_module
import storage
import symbol
import relocation


def parse_args():
    if len(sys.argv) < 2:
        file_name = sys.argv[0]
        print(f"Usage: {file_name} <input_file>", file=sys.stderr)
        sys.exit(1)

    # parse cli args to populate SKIP_SYMBOLS, SKIP_RELOCATIONS, SKIP_DATA
    parser = argparse.ArgumentParser(description='Simple linker that processes input files and produces an output file.')
    parser.add_argument('input_files', nargs='+', help='Input files to process')
    parser.add_argument('--skip-symbols', action='store_true', help='Skip processing symbols', default=False)
    parser.add_argument('--skip-relocations', action='store_true', help='Skip processing relocations', default=False)
    parser.add_argument('--skip-data', action='store_true', help='Skip processing data section', default=False)
    parser.add_argument('--output', '-o', help='Specify output file name (default: a.out.lk)', default='a.out.lk')
    parser.add_argument('--byteorder', choices=['big', 'little'], default='little', help='Specify byte order for output file (default: little)')
    parser.add_argument('--wrap', '-w', action='append', help='Use a wrapper function for SYMBOL.', metavar='SYMBOL', default=[])
    parser.add_argument('--shared', action='store_true', help='Produce a shared library instead of an executable (default: false)', default=False)
    parser.add_argument('--base-addr', type=lambda x: int(x, 16), help='Specify base address for output segments (default: 0x1000)', default=0x1000)
    parser.add_argument('--stub-format', choices=['directory', 'file'], default='directory', help='Specify format for stub libraries (default: directory)')
    parser.add_argument('--stub-output', help='Specify output file name for stub library')
    args = parser.parse_args()
    if args.shared and not args.stub_output:
        parser.error("--shared requires --stub-output to be specified")
    if args.shared and os.path.basename(args.stub_output) != os.path.basename(args.output):
        parser.error(f"--stub-output file name must be the same as output file name when --shared is specified. Expected '{os.path.basename(args.output)}', got '{os.path.basename(args.stub_output)}'")
    return args

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

def link_objects(input_files, byteorder, wrap_symbols, base_addr):
    # Input files may contain libraries, so we need to separately treat them
    library_dirs = []
    library_files = []
    stub_library_dirs = []
    stub_library_files = []
    object_files = []
    for f in input_files:
        if os.path.isdir(f):
            if is_stub_library_directory(f):
                stub_library_dirs.append(f)
            else:
                library_dirs.append(f)
        elif is_library_file(f):
            library_files.append(f)
        elif is_stub_library_file(f):
            stub_library_files.append(f)
        elif is_object_file(f):
            object_files.append(f)
        else:
            print(f"Warning: {f} is not a valid object file or library, skipping", file=sys.stderr)
            sys.exit(1)
    objs = parse_objects(object_files)
    lib_symtab = symbol.collect_symbols(library_dirs, library_files)
    stublib_symtab = symbol.collect_symbols(stub_library_dirs, stub_library_files, is_stub_library=True)
    if lib_symtab.keys() & stublib_symtab.keys():
        print(f"Error: Symbol name conflict between libraries and stub libraries: {lib_symtab.keys() & stublib_symtab.keys()}", file=sys.stderr)
        sys.exit(1)
    lib_symtab.update(stublib_symtab)

    # Resolve symbol names
    symbol.apply_wraps(objs, wrap_symbols)
    gsymtab = symbol.resolve_names(objs, lib_symtab, wrap_symbols)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    out_segments, gdata = storage.allocate(objs, gsymtab, base_addr, output_type='executable')
    # Resolve symbol values
    symbol.resolve_values(objs, gsymtab, out_segments)

    # Filter out symbols from stub libraries (they're already resolved and should not be exported in the executable)
    out_symbols = {name:gsym.to_local() for name,gsym in gsymtab.items() if not gsym.obj.is_stub_library}

    # Add _SHARED_LIBRARIES symbol pointing to the start of .lib segment if it exists
    lib_seg = next((seg for seg in out_segments if seg.name == '.lib'), None)
    if lib_seg:
        out_symbols['_SHARED_LIBRARIES'] = Symbol.absolute(name='_SHARED_LIBRARIES', value=lib_seg.start)

    # Relocate and generate output data
    out_relocations = relocation.relocate(objs, gsymtab, gdata, byteorder, out_segments)
    out_data = [v for v in gdata.values()]

    return out_segments, out_symbols, out_relocations, out_data

def collect_objecs(library_dirs, library_files):
    objs = []
    for lib_dir in library_dirs:
        distinct_object_files = set()
        entries = os.listdir(lib_dir)
        for filename in sorted(entries):
            # Check if the file is already included (same inode)
            file_path = os.path.join(lib_dir, filename)
            file_inode = os.stat(file_path).st_ino
            if file_inode in distinct_object_files:
                continue
            objs.append(parse_object(file_path))
            distinct_object_files.add(file_inode)
    for file in library_files:
        with open(file, 'r') as f:
            line = f.readline()
            magic, nmods, dir_offset = line.strip().split()
            nmods = int(nmods, 16)
            dir_offset = int(dir_offset, 16)
            f.seek(dir_offset)
            for i in range(nmods):
                line = f.readline()
                mod_offset, mod_size, *symbol_strs = line.strip().split()
                mod_offset = int(mod_offset, 16)
                mod_size = int(mod_size, 16)
                lib_obj = parse_module(file, offset=mod_offset, size=mod_size)
                objs.append(lib_obj)
    return objs

def link_shared_library(input_files, byteorder, wrap_symbols, base_addr):
    # Input files shall be only libraries
    library_dirs = []
    library_files = []
    stub_library_dirs = []
    stub_library_files = []
    for f in input_files:
        if os.path.isdir(f):
            if is_stub_library_directory(f):
                stub_library_dirs.append(f)
            else:
                library_dirs.append(f)
        elif is_library_file(f):
            library_files.append(f)
        elif is_stub_library_file(f):
            stub_library_files.append(f)
        elif is_object_file(f):
            print(f"Warning: {f} is an object file, but --shared option is specified. Input files for shared library should be libraries, skipping", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Warning: {f} is not a valid object file or library, skipping", file=sys.stderr)
            sys.exit(1)
    objs = collect_objecs(library_dirs, library_files)

    # Link collected objects
    lib_symtab = symbol.collect_symbols(stub_library_dirs, stub_library_files, is_stub_library=True)

    # Resolve symbol names
    symbol.apply_wraps(objs, wrap_symbols)
    gsymtab = symbol.resolve_names(objs, lib_symtab, wrap_symbols)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    out_segments, gdata = storage.allocate(objs, gsymtab, base_addr, output_type='shared')
    # Resolve symbol values
    symbol.resolve_values(objs, gsymtab, out_segments)
    # Filter out symbols from stub libraries since they're already resolved and should not be exported in the shared library
    out_symbols = {name:gsym.to_local() for name,gsym in gsymtab.items() if not gsym.obj.is_stub_library}
    out_relocations = relocation.relocate(objs, gsymtab, gdata, byteorder, out_segments)
    out_data = [v for v in gdata.values()]

    return out_segments, out_symbols, out_relocations, out_data, stub_library_dirs + stub_library_files

class WriteOptions:
    def __init__(self, skip_symbols, skip_relocations, skip_data):
        self.skip_symbols = skip_symbols
        self.skip_relocations = skip_relocations
        self.skip_data = skip_data

def write_output(filename, link_results, options):

    out_segments, out_symbols, out_relocations, out_data = link_results

    obj = Object(
        filename=filename,
        num_segments=len(out_segments),
        num_symbols=len(out_symbols),
        num_relocations=len(out_relocations),
        segments=out_segments,
        symbols=out_symbols,
        relocations=out_relocations,
        data=out_data,
    )

    contents = obj.serialize(
        skip_symbols=options.skip_symbols,
        skip_relocations=options.skip_relocations,
        skip_data=options.skip_data,
        )
        
    # Check if the output file already exists and remove it
    if os.path.exists(filename):
        os.remove(filename)

    with open(filename, 'wb') as outfile:
        outfile.write(contents)

def write_stub_library(filename, link_results, stub_format):
    if stub_format == 'directory':
        write_stub_library_directory(filename, link_results)
    elif stub_format == 'file':
        write_stub_library_file(filename, link_results)
    else:
        print(f"Error: Invalid stub format '{stub_format}' specified", file=sys.stderr)
        sys.exit(1)

def write_stub_library_file(output_file, link_results):
    out_segments, out_symbols, out_relocations, out_data, dependencies = link_results
    stub_out_segments = [Segment(seg.name, seg.start, seg.size, seg.code_letter.replace('P', '')) for seg in out_segments]

    # Module content (only one)
    mod = Object(
        filename='',
        num_segments=len(stub_out_segments),
        num_symbols=len(out_symbols),
        num_relocations=0,
        segments=stub_out_segments,
        symbols=out_symbols,
        relocations=[],
        data=[]
    )
    contents = mod.serialize(
        skip_symbols=False,
        skip_relocations=True,
        skip_data=True
        )
    mod_size = len(contents)

    # Header (only one module, so it's deterministic)
    tmp_dir_offset = 0x10 + mod_size
    num_files = 1
    dep_str = ' '.join([os.path.basename(f) for f in [output_file] + dependencies])
    header = f"LIBRARY {num_files:x} {tmp_dir_offset:x} {dep_str}\n".encode()
    dir_offset = len(header) + len(contents)
    while dir_offset != tmp_dir_offset:
        tmp_dir_offset = dir_offset
        header = f"LIBRARY {num_files:x} {tmp_dir_offset:x} {dep_str}\n".encode()
        dir_offset = len(header) + len(contents)

    # Directory entries (one per symbol)
    dir_entries = b''
    mod_offset = len(header)
    symbols_str = ' '.join(name for name, sym in mod.symbols.items() if sym.sym_type == 'D' or (sym.sym_type == 'U' and sym.value > 0))
    dir_entries += f"{mod_offset:x} {mod_size:x} {symbols_str}\n".encode()

    # Write
    with open(output_file, 'wb') as outfile:
        outfile.write(header)
        outfile.write(contents)
        outfile.write(dir_entries)

def write_stub_library_directory(output_dir, link_results):
    out_segments, out_symbols, out_relocations, out_data, dependencies = link_results

    # Create output directory
    if os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' already exists. Please remove it or choose a different name.", file=sys.stderr)
        sys.exit(1)
    os.mkdir(output_dir)
    
    # Add "LIBRARY NAME" file
    library_name_file = os.path.join(output_dir, 'LIBRARY NAME')
    with open(library_name_file, 'w') as f:
        # Library name itself
        lib_name = os.path.basename(output_dir)
        f.write(f"{lib_name}\n")
        # List dependencies (one per line)
        for dep in dependencies:
            dep_name = os.path.basename(dep)
            f.write(f"{dep_name}\n")

    # Create a temporary output file to link from (the contents don't matter since we will skip symbols and relocations when writing the output)
    temp_file = os.path.join(output_dir, 'TEMP_STUB_FILE')

    # Remove 'P' from segment name if it exists, since it's not valid for object files
    stub_out_segments = [Segment(seg.name, seg.start, seg.size, seg.code_letter.replace('P', '')) for seg in out_segments]
    write_output(
        temp_file,
        (stub_out_segments, out_symbols, [], []),
        WriteOptions(
            skip_symbols=False,
            skip_relocations=True,
            skip_data=True,
        ),
    )

    # Add hardlinks to each symbol in the output directory
    for name in out_symbols.keys():
        link_path = os.path.join(output_dir, name)
        os.link(temp_file, link_path)

    # Delete the output file (the hardlink will still exist in the output directory)
    os.remove(temp_file)

def main():
    args = parse_args()
    if args.shared:
        results = link_shared_library(args.input_files, args.byteorder, args.wrap, args.base_addr)
        write_stub_library(args.stub_output, results, args.stub_format)
        results = results[:4]
        args.skip_relocations = True # For shared library, we can't have relocations
    elif len(args.input_files) == 1:
        # If only one input file, just copy it to the output (with optional skipping)
        obj = parse_object(args.input_files[0])
        results = (obj.segments, obj.symbols, obj.relocations, obj.data)
    else:
        # Multiple input files, need to link them together
        results = link_objects(args.input_files, args.byteorder, args.wrap, args.base_addr)
    write_output(
        args.output,
        results,
        WriteOptions(
            skip_symbols=args.skip_symbols,
            skip_relocations=args.skip_relocations,
            skip_data=args.skip_data,
        ),
    )

if __name__ == '__main__':
    main()
