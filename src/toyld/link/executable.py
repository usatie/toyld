import os
import sys
from pathlib import Path

from toyld.objfile import Object, Symbol, parse_objects
import toyld.relocation as relocation
import toyld.storage as storage
import toyld.symbol as symbol

from toyld.link.options import ExecutableConfig

from .helper import (
    is_dynamic_shared_library_file,
    is_library_file,
    is_object_file,
    is_stub_library_directory,
    is_stub_library_file,
)


def link_executable(config: ExecutableConfig):
    # Input files may contain libraries, so we need to separately treat them
    library_dirs = []
    library_files = []
    stub_library_dirs = []
    stub_library_files = []
    dynamic_library_files = []
    object_files = []
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
        elif is_dynamic_shared_library_file(f):
            dynamic_library_files.append(f)
        elif is_object_file(f):
            object_files.append(f)
        else:
            print(f"Warning: {f} is not a valid object file or library, skipping", file=sys.stderr)
            sys.exit(1)
    objs = parse_objects(object_files)
    lib_symtab = symbol.collect_symbols(library_dirs, library_files)
    stublib_symtab = symbol.collect_symbols(stub_library_dirs, stub_library_files, is_stub_library=True)
    dynlib_symtab = symbol.collect_dynamic_symbols(dynamic_library_files)
    if lib_symtab.keys() & stublib_symtab.keys():
        print(f"Error: Symbol name conflict between libraries and stub libraries: {lib_symtab.keys() & stublib_symtab.keys()}", file=sys.stderr)
        sys.exit(1)
    lib_symtab.update(stublib_symtab)
    if lib_symtab.keys() & dynlib_symtab.keys():
        print(f"Error: Symbol name conflict between libraries and dynamic libraries: {lib_symtab.keys() & dynlib_symtab.keys()}", file=sys.stderr)
        sys.exit(1)
    lib_symtab.update(dynlib_symtab)

    # Resolve symbol names
    symbol.apply_wraps(objs, config.wrap)
    gsymtab = symbol.resolve_names(objs, lib_symtab, config.wrap)

    # Allocate Storage for .text, .data, .bss segments and assign addresses
    out_segments, gdata = storage.allocate(objs, gsymtab, config.base_addr, output_type='executable')

    # Resolve symbol values
    symbol.resolve_values(objs, gsymtab, out_segments)

    # Filter out symbols from stub libraries (they're already resolved and should not be exported in the executable)
    out_gsymtab = {name:gsym for name,gsym in gsymtab.items() if not gsym.obj.is_stub_library}

    # For dynamic shared library, we want to export non-absolute symbols
    out_symbols = {}
    for i, gsym in enumerate(out_gsymtab.values()):
        if gsym.obj.is_dynamic_shared_lib:
            out_symbols[gsym.name] = Symbol(name=gsym.name, value=0, seg_number=0, sym_type='U', number=i+1)
        else:
            # Executable is not relinkable, so absolute symbol
            out_symbols[gsym.name] = gsym.to_local()

    # Add _SHARED_LIBRARIES symbol pointing to the start of .lib segment if it exists
    lib_seg = next((seg for seg in out_segments if seg.name == '.lib'), None)
    if lib_seg:
        out_symbols['_SHARED_LIBRARIES'] = Symbol.absolute(name='_SHARED_LIBRARIES', value=lib_seg.start)

    # Relocate and generate output data
    out_relocations = relocation.relocate(objs, gsymtab, gdata, config.byteorder, out_segments, out_symbols)
    out_data = [v for v in gdata.values()]


    # Write to file
    obj = Object(
        filename=config.output,
        num_segments=len(out_segments),
        num_symbols=len(out_symbols),
        num_relocations=len(out_relocations),
        segments=out_segments,
        symbols=out_symbols,
        relocations=out_relocations,
        data=out_data,
        is_dynamic_shared_lib=False,
        deps = [os.path.basename(f).encode() for f in dynamic_library_files],
    )
    Path(config.output).write_bytes(obj.serialize(skip_symbols=config.skip_symbols, skip_relocations=config.skip_relocations, skip_data=config.skip_data))
