import sys

from object import Symbol

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

def resolve_names(objs):
    global_symbol_table = {}
    commons = {}

    for o in objs:
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
            existing_sym.is_defined = True
            existing_sym.obj = o
    for sym in global_symbol_table.values():
        if not sym.is_defined and not sym.is_common:
            print(f"Error: symbol '{sym.name}' is undefined but referenced in file '{sym.obj.filename}'", file=sys.stderr)
            sys.exit(1)
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

