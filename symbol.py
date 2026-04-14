import os
import sys

from object import Symbol, parse_object, parse_module

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None

class GlobalSymbol:
    def __init__(self, name, obj, lsym, value):
        self.name = name
        self.obj = obj
        self.lsym = lsym
        self.value = value
        self.got_offset = None

    @classmethod
    def from_local(cls, lsym, obj):
        return cls(
            name=lsym.name,
            obj=obj,
            lsym=lsym,
            value=lsym.value
            )

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
        return Symbol.absolute(self.name, self.value)

    def __repr__(self):
        return f"GlobalSymbol(name={self.name}, is_defined={self.is_defined}, is_common={self.is_common}, obj={self.obj.filename}, value={self.value})"

class Module:
    @staticmethod
    def file_format(filename, offset, size, is_stub_library, deps):
        mod = Module()
        mod.filename = filename
        mod.offset = offset
        mod.size = size
        mod.is_stub_library = is_stub_library
        mod.format = 'file'
        mod.deps = deps
        return mod
    
    @staticmethod
    def dir_format(filename, is_stub_library, deps):
        mod = Module()
        mod.filename = filename
        mod.is_stub_library = is_stub_library
        mod.format = 'dir'
        mod.deps = deps
        return mod

    def library_name(self):
        if self.format == 'file':
            return os.path.basename(self.filename)
        elif self.format == 'dir':
            return os.path.basename(os.path.dirname(self.filename))

    def __repr__(self):
        if self.format == 'file':
            return f"Module(file='{self.filename}', offset={self.offset:x}, size={self.size:x}, is_stub_library={self.is_stub_library})"
        elif self.format == 'dir':
            return f"Module(dir='{self.filename}', is_stub_library={self.is_stub_library})"

def collect_symbols(library_dirs, library_files, is_stub_library=False):
    symtab = {}
    for lib_dir in library_dirs:
        entries = os.listdir(lib_dir)
        deps = []
        if is_stub_library:
            with open(os.path.join(lib_dir, 'LIBRARY NAME'), 'r') as f:
                deps = [line.strip() for line in f if line.strip()]
        for filename in sorted(entries):
            # 'LIBRARY NAME' is the special file in stub libraries
            if filename == 'LIBRARY NAME':
                continue
            symbol_name = filename
            symtab[symbol_name] = Module.dir_format(os.path.join(lib_dir, symbol_name), is_stub_library, deps=deps)

    for file in library_files:
        with open(file, 'r') as f:
            line = f.readline()
            magic, nmods, dir_offset, *deps = line.strip().split()
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
                    symtab[sym] = Module.file_format(file, mod_offset, mod_size, is_stub_library, deps=deps)
    dprint(f"Collected {len(symtab)} symbols from libraries")
    dprint(f"Library symbol table: {symtab}")
    return symtab

def _merge_symbol(lsym, o, gsymtab):
    if lsym.name not in gsymtab:
        gsymtab[lsym.name] = GlobalSymbol.from_local(lsym, o)
        return

    gsym = gsymtab[lsym.name]

    # Consistency check
    if lsym.is_common ^ gsym.is_common:
        print(f"Error: symbol '{lsym.name}' has inconsistent definitions: "
              f"one is common and the other is not", file=sys.stderr)
        sys.exit(1)
    if lsym.is_defined and gsym.is_defined:
        print(f"Error: symbol '{lsym.name}' is multiply defined in files "
              f"'{gsym.obj.filename}' and '{o.filename}'", file=sys.stderr)
        sys.exit(1)

    # common blocks: larger common block wins
    if lsym.is_common:
        if lsym.value > gsym.value:
            gsym.value = lsym.value
            gsym.lsym = lsym
    # undefined symbols: skip
    elif lsym.is_undefined:
        pass
    # defined symbols: resolve name to the file it is defined in
    elif lsym.is_defined:
        dprint(f"Symbol '{lsym.name}' is resolved to file '{o.filename}'")
        gsym.lsym = lsym
        gsym.obj = o

def search_module(symbol_name, libsymtab):
    if symbol_name not in libsymtab:
        print(f"Error: symbol '{symbol_name}' is undefined but referenced in library files", file=sys.stderr)
        sys.exit(1)
    return libsymtab[symbol_name]

def resolve_names(objs, lib_symtab, wrap_symbols):
    gsymtab = {}
    to_visit = [o for o in objs]

    while to_visit:
        current_batch = to_visit[:]
        to_visit.clear()
        for o in current_batch:
            for lsym in o.symbols.values():
                _merge_symbol(lsym, o, gsymtab)

        dprint("Search for undefined symbols in global symbol table...")
        undefined_symbols = [gsym for gsym in gsymtab.values() if gsym.is_undefined]
        if undefined_symbols:
            # we will resolve undefined symbols one at a time to avoid loading the same library module multiple times if it defines multiple symbols
            gsym = undefined_symbols[0]
            is_wrapped_symbol = False
            search_key = gsym.name
            if gsym.name.startswith('real_') or gsym.name.startswith('wrap_'):
                unwrapped_name = gsym.name[5:]
                is_wrapped_symbol = unwrapped_name in wrap_symbols
                search_key = unwrapped_name

            # load the library module and add it to the list of objects to visit
            mod = search_module(search_key, lib_symtab)
            dprint(f"Resolving symbol '{search_key}' from library file '{lib_symtab[search_key]}'")
            if mod.format == 'dir':
                lib_obj = parse_object(mod.filename, mod.is_stub_library)
            elif mod.format == 'file':
                lib_obj = parse_module(mod.filename, offset=mod.offset, size=mod.size, is_stub_library=mod.is_stub_library)
            lib_obj.mod = mod
            if is_wrapped_symbol:
                apply_wraps([lib_obj], wrap_symbols)
            to_visit.append(lib_obj)
            objs.append(lib_obj)
    return gsymtab

def resolve_values(objs, gsymtab, out_segments):
    for gsym in (s for s in gsymtab.values() if s.is_defined):
        local_sym = gsym.obj.symbols[gsym.name]
        seg = gsym.obj.segments[local_sym.seg_number - 1]
        gsym.value = seg.assigned_address + local_sym.value


def apply_wraps(objs, wrap_symbols):
    for w in wrap_symbols:
        for o in objs:
            if w not in o.symbols:
                continue
            sym = o.symbols[w]
            if sym.sym_type == 'D':
                # Add real_name as a new symbol (to be not referenced internally)
                real_sym = Symbol(f'real_{sym.name}', sym.value, sym.seg_number, 'D', len(o.symbols) + 1)
                o.symbols[real_sym.name] = real_sym
                # Change the original symbol to be a wrapper (to be referenced internally)
                sym.name = f'wrap_{sym.name}'
                sym.sym_type = 'U'
                o.symbols = {(sym.name if s == w else s): v for s, v in o.symbols.items()}
            elif sym.sym_type == 'U':
                sym.name = f'wrap_{sym.name}'
                o.symbols = {(sym.name if s == w else s): v for s, v in o.symbols.items()}
        
