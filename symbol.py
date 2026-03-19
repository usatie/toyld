import os
import sys

from object import Symbol, parse_objects

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None

class GlobalSymbol:
    def __init__(self, lsym, obj):
        self.name = lsym.name
        self.obj = obj
        self.lsym = lsym
        self.value = lsym.value

    @property
    def is_defined(self):
        return self.lsym.is_defined

    @property
    def is_common(self):
        return self.lsym.is_common

    @property
    def is_undefined(self):
        return self.lsym.is_undefined

    def to_local(self):
        SYM_ABSOLUTE = 0
        return Symbol(self.name, self.value, SYM_ABSOLUTE, 'D', 0)

    def __repr__(self):
        return f"GlobalSymbol(name={self.name}, is_defined={self.is_defined}, is_common={self.is_common}, obj={self.obj.filename}, value={self.value})"

class Module:
    @staticmethod
    def file_format(filename, offset, size):
        mod = Module()
        mod.filename = filename
        mod.offset = offset
        mod.size = size
        mod.format = 'file'
        return mod
    
    @staticmethod
    def dir_format(filename):
        mod = Module()
        mod.filename = filename
        mod.format = 'dir'
        return mod

def collect_symbols(library_dirs, library_files):
    symtab = {}
    for lib_dir in library_dirs:
        for filename in os.listdir(lib_dir):
            symbol_name = filename
            symtab[symbol_name] = Module.dir_format(os.path.join(lib_dir, symbol_name))

    for file in library_files:
        with open(file, 'r') as f:
            line = f.readline()
            magic, nmods, dir_offset = line.strip().split()
            nmods = int(nmods, 16)
            dir_offset = int(dir_offset, 16)
            dprint(f"Reading library file '{file}' with {nmods} modules and directory offset {dir_offset}")
            f.seek(dir_offset)
            for i in range(nmods):
                line = f.readline()
                mod_offset, mod_size, *symbol_strs = line.strip().split()
                mod_offset = int(mod_offset, 16)
                mod_size = int(mod_size, 16)
                dprint(f"Module {i}: offset={mod_offset} size={mod_size} symbols={symbol_strs}")
                for sym in symbol_strs:
                    if sym in symtab:
                        print(f"Error: symbol '{sym}' is multiply defined in library files '{symtab[sym].filename}' and '{file}'", file=sys.stderr)
                        sys.exit(1)
                    symtab[sym] = Module.file_format(file, mod_offset, mod_size)
    dprint(f"Collected {len(symtab)} symbols from libraries")
    dprint(f"Library symbol table: {symtab}")

    return symtab

def resolve_names(objs, libsymtab):
    gsymtab = {}

    to_visit = [o for o in objs]

    while len(to_visit) > 0:
        while len(to_visit) > 0:
            o = to_visit.pop(0)
            for lsym in o.symbols.values():
                if lsym.name not in gsymtab:
                    gsymtab[lsym.name] = GlobalSymbol(lsym, o)
                    continue
                # Consistency check for symbol definitions
                gsym = gsymtab[lsym.name]
                if lsym.is_common ^ gsym.is_common:
                    print(f"Error: symbol '{lsym.name}' has inconsistent definitions: one is common and the other is not", file=sys.stderr)
                    sys.exit(1)
                if lsym.is_defined and gsym.is_defined:
                    print(f"Error: symbol '{lsym.name}' is multiply defined in files '{gsym.obj.filename}' and '{o.filename}'", file=sys.stderr)
                    sys.exit(1)
                # common blocks
                if lsym.is_common:
                    # larger common block wins
                    if lsym.value > gsym.value:
                        gsym.value = lsym.value
                        gsym.lsym = lsym
                # Skip undefined symbols
                elif lsym.is_undefined:
                    continue
                # Defined symbols
                elif lsym.is_defined:
                    dprint(f"Symbol '{lsym.name}' is resolved to file '{o.filename}'")
                    gsym.lsym = lsym
                    gsym.obj = o
        dprint("Search for undefined symbols in global symbol table...")
        undefined_symbols = [gsym for gsym in gsymtab.values() if gsym.is_undefined]
        for gsym in undefined_symbols:
            if gsym.name not in libsymtab:
                print(f"Error: symbol '{gsym.name}' is undefined but referenced in file '{gsym.obj.filename}'", file=sys.stderr)
                sys.exit(1)
            # load the library object file and add it to the list of objects to visit
            dprint(f"Resolving symbol '{gsym.name}' from library file '{libsymtab[gsym.name]}'")
            lib_filename = libsymtab[gsym.name].filename
            lib_obj = parse_objects([lib_filename])[0]
            to_visit.append(lib_obj)
            objs.append(lib_obj)
            # we will resolve the symbol now, so that we don't have to load the same library file multiple times
            break
    return gsymtab

def resolve_values(objs, gsymtab, out_segments):
    for sym in gsymtab.values():
        if sym.is_defined:
            local_sym = sym.obj.symbols[sym.name]
            seg = sym.obj.segments[local_sym.seg_number - 1]
            sym.value = seg.assigned_address + local_sym.value

