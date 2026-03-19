import os
import sys

from object import Symbol, parse_objects

DEBUG = False
dprint = lambda *args, **kwargs: print(*args, **kwargs, file=sys.stderr) if DEBUG else None

class GlobalSymbol:
    def __init__(self, name, is_defined, is_common, obj):
        self.name = name
        self.is_defined = is_defined
        self.is_common = is_common
        self.obj = obj
        self.value = 0 # TODO: needs to be resolved later

    def to_symbol(self):
        SYM_ABSOLUTE = 0
        return Symbol(self.name, self.value, SYM_ABSOLUTE, 'D' if self.is_defined else 'U', 0)

    def __repr__(self):
        return f"GlobalSymbol(name={self.name}, is_defined={self.is_defined}, obj={self.obj.filename})"

def collect_symbols(library_dirs):
    symbols = {}
    for lib_dir in library_dirs:
        for filename in os.listdir(lib_dir):
            symbols[filename] = os.path.join(lib_dir, filename)
    return symbols

def resolve_names(objs, libsymtab):
    global_symbol_table = {}
    commons = {}

    to_visit = [o for o in objs]

    while len(to_visit) > 0:
        while len(to_visit) > 0:
            o = to_visit.pop(0)
            for sym in o.symbols.values():
                # Find common blocks and keep track of the largest common block for each symbol name
                is_common = sym.sym_type == 'U' and sym.value > 0
                if is_common:
                    if sym.name not in commons:
                        commons[sym.name] = sym
                    elif sym.value > commons[sym.name].value:
                        commons[sym.name] = sym
                # Find global symbols and check for multiply defined symbols and inconsistent definitions
                is_defined = sym.sym_type == 'D'
                if sym.name not in global_symbol_table:
                    global_symbol_table[sym.name] = GlobalSymbol(sym.name, is_defined, is_common, o)
                    continue
                if not is_defined:
                    continue
                existing_sym  = global_symbol_table[sym.name]
                if is_common ^ existing_sym.is_common:
                    print(f"Error: symbol '{sym.name}' has inconsistent definitions: one is common and the other is not", file=sys.stderr)
                    sys.exit(1)
                if existing_sym.is_defined:
                    print(f"Error: symbol '{sym.name}' is multiply defined in files '{existing_sym.obj.filename}' and '{o.filename}'", file=sys.stderr)
                    sys.exit(1)
                dprint(f"Symbol '{sym.name}' is resolved to file '{o.filename}'")
                existing_sym.is_defined = True
                existing_sym.obj = o
        dprint("Search for undefined symbols in global symbol table...")
        undefined_symbols = [sym for sym in global_symbol_table.values() if not sym.is_defined and not sym.is_common]
        for sym in undefined_symbols:
            if sym.name not in libsymtab:
                print(f"Error: symbol '{sym.name}' is undefined but referenced in file '{sym.obj.filename}'", file=sys.stderr)
                sys.exit(1)
            # load the library object file and add it to the list of objects to visit
            dprint(f"Resolving symbol '{sym.name}' from library file '{libsymtab[sym.name]}'")
            lib_filename = libsymtab[sym.name]
            lib_obj = parse_objects([lib_filename])[0]
            to_visit.append(lib_obj)
            objs.append(lib_obj)
            # we will resolve the symbol now, so that we don't have to load the same library file multiple times
            break
    return global_symbol_table, commons

def resolve_values(objs, symbol_table, out_segments, commons):
    for sym in symbol_table.values():
        if sym.is_common and sym.name in commons:
            common_sym = commons[sym.name]
            sym.value = common_sym.assigned_address
        elif sym.is_defined:
            local_sym = sym.obj.symbols[sym.name]
            seg = sym.obj.segments[local_sym.seg_number - 1]
            sym.value = seg.assigned_address + local_sym.value

