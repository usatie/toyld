import os
import sys
from pathlib import Path

from toyld.objfile import Object, Segment, parse_object, parse_module
import toyld.relocation as relocation
import toyld.storage as storage
import toyld.symbol as symbol

from toyld.link.options import StaticSharedConfig

from .helper import (
    is_library_file,
    is_object_file,
    is_stub_library_directory,
    is_stub_library_file,
)


def link_static_shared_library(config: StaticSharedConfig):
    # Input files shall be only libraries
    library_dirs = []
    library_files = []
    stub_library_dirs = []
    stub_library_files = []
    for f in config.input_files:
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
    objs = collect_objects(library_dirs, library_files)

    # Link collected objects
    lib_symtab = symbol.collect_symbols(stub_library_dirs, stub_library_files, is_stub_library=True)

    # Resolve symbol names
    symbol.apply_wraps(objs, config.wrap)
    gsymtab = symbol.resolve_names(objs, lib_symtab, config.wrap)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    out_segments, gdata = storage.allocate(objs, gsymtab, config.base_addr, output_type='shared')
    # Resolve symbol values
    symbol.resolve_values(objs, gsymtab, out_segments)
    # Filter out symbols from stub libraries since they're already resolved and should not be exported in the shared library
    out_symbols = {name:gsym.to_local() for name,gsym in gsymtab.items() if not gsym.obj.is_stub_library}
    out_relocations = relocation.relocate(objs, gsymtab, gdata, config.byteorder, out_segments, out_symbols)
    out_data = [v for v in gdata.values()]

    write_stub_library(config.stub_output, (out_segments, out_symbols, out_relocations, out_data, stub_library_dirs + stub_library_files), config.stub_format)
    obj = Object(
        filename=config.output,
        num_segments=len(out_segments),
        num_symbols=len(out_symbols),
        num_relocations=len(out_relocations),
        segments=out_segments,
        symbols=out_symbols,
        relocations=out_relocations,
        data=out_data,
    )

    # For static shared library, we can't have relocations
    Path(config.output).write_bytes(obj.serialize(skip_relocations=True))

def collect_objects(library_dirs, library_files):
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

    obj = Object(
        filename=temp_file,
        num_segments=len(stub_out_segments),
        num_symbols=len(out_symbols),
        num_relocations=0,
        segments=stub_out_segments,
        symbols=out_symbols,
        relocations=[],
        data=[],
    )
    Path(temp_file).write_bytes(obj.serialize(skip_symbols=False, skip_relocations=True, skip_data=True))


    # Add hardlinks to each symbol in the output directory
    for name in out_symbols.keys():
        link_path = os.path.join(output_dir, name)
        os.link(temp_file, link_path)

    # Delete the output file (the hardlink will still exist in the output directory)
    os.remove(temp_file)
