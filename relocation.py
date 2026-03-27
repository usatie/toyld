import sys

def _resolve_symbol_addr(rel, obj, gsymtab):
    sym_name = list(obj.symbols.keys())[rel.ref - 1]
    ref_sym = gsymtab[sym_name]
    return ref_sym.value

def _relocate_a4(rel, obj, seg_data, offset, byteorder):
    ref_lseg = obj.segments[rel.ref - 1]
    seg_data[offset:offset+4] = (ref_lseg.assigned_address).to_bytes(4, byteorder=byteorder)

def _relocate_r4(rel, obj, seg_data, offset, tgt_lseg, byteorder):
    ref_lseg = obj.segments[rel.ref - 1]
    pc_relative_addr = ref_lseg.assigned_address - (tgt_lseg.assigned_address + rel.loc + 4)
    seg_data[offset:offset+4] = pc_relative_addr.to_bytes(4, byteorder=byteorder)

def _relocate_as4(rel, obj, gsymtab, seg_data, offset, byteorder):
    abs_addr = _resolve_symbol_addr(rel, obj, gsymtab)
    # NOTE: Probably it's safer to read the addend from the original segment data, not from the already modified data
    # because seg_data may have been modified by previous relocations.
    addend = int.from_bytes(seg_data[offset:offset+4], byteorder=byteorder, signed=True)
    abs_addr += addend
    seg_data[offset:offset+4] = abs_addr.to_bytes(4, byteorder=byteorder)

def _relocate_rs4(rel, obj, gsymtab, seg_data, offset, tgt_lseg, byteorder):
    abs_addr = _resolve_symbol_addr(rel, obj, gsymtab)
    # NOTE: Probably it's safer to read the addend from the original segment data, not from the already modified data
    # because seg_data may have been modified by previous relocations.
    addend = int.from_bytes(seg_data[offset:offset+4], byteorder=byteorder, signed=True)
    abs_addr += addend
    pc_relative_addr = abs_addr - (tgt_lseg.assigned_address + rel.loc + 4)
    seg_data[offset:offset+4] = pc_relative_addr.to_bytes(4, byteorder=byteorder, signed=True)

def _relocate_u2(rel, obj, gsymtab, seg_data, offset, byteorder):
    abs_addr = _resolve_symbol_addr(rel, obj, gsymtab)
    seg_data[offset:offset+2] = ((abs_addr >> 16) & 0xffff).to_bytes(2, byteorder=byteorder)

def _relocate_l2(rel, obj, gsymtab, seg_data, offset, byteorder):
    abs_addr = _resolve_symbol_addr(rel, obj, gsymtab)
    seg_data[offset:offset+2] = (abs_addr & 0xffff).to_bytes(2, byteorder=byteorder)

def _relocate_gp4(rel, obj, gsymtab, seg_data, offset, gdata, byteorder):
    sym_name = list(obj.symbols.keys())[rel.ref - 1]
    ref_sym = gsymtab[sym_name]
    executable_rel_addr = ref_sym.value - 0x1000
    got_offset = ref_sym.got_offset
    seg_data[offset:offset+4] = got_offset.to_bytes(4, byteorder=byteorder)
    gdata['.got'][got_offset:got_offset+4] = executable_rel_addr.to_bytes(4, byteorder=byteorder)

def _relocate_ga4(rel, seg_data, offset, tgt_lseg, got_gseg, byteorder):
    seg_data[offset:offset+4] = (got_gseg.start - (tgt_lseg.assigned_address + rel.loc)).to_bytes(4, byteorder=byteorder)
    print(f"GOT start address {got_gseg.start} written to offset {offset}", file=sys.stderr)

def _relocate_one(rel, obj, gsymtab, gdata, byteorder, got_seg):
    tgt_lseg = obj.segments[rel.seg_number - 1]
    seg_data = gdata[tgt_lseg.name]
    offset = tgt_lseg.assigned_offset + rel.loc
    if offset + 4 > len(seg_data):
        print(f"Relocation out of bounds: segment '{tgt_lseg.name}', offset {offset}, seg_data length {len(seg_data)}", file=sys.stderr)
        sys.exit(1)
    if rel.rel_type == 'A4':
        return _relocate_a4(rel, obj, seg_data, offset, byteorder)
    elif rel.rel_type == 'R4':
        return _relocate_r4(rel, obj, seg_data, offset, tgt_lseg, byteorder)
    elif rel.rel_type == 'AS4':
        return _relocate_as4(rel, obj, gsymtab, seg_data, offset, byteorder)
    elif rel.rel_type == 'RS4':
        return _relocate_rs4(rel, obj, gsymtab, seg_data, offset, tgt_lseg, byteorder)
    elif rel.rel_type == 'U2':
        return _relocate_u2(rel, obj, gsymtab, seg_data, offset, byteorder)
    elif rel.rel_type == 'L2':
        return _relocate_l2(rel, obj, gsymtab, seg_data, offset, byteorder)
    elif rel.rel_type == 'GP4':
        return _relocate_gp4(rel, obj, gsymtab, seg_data, offset, gdata, byteorder)
    elif rel.rel_type == 'GA4':
        return _relocate_ga4(rel, seg_data, offset, tgt_lseg, got_seg, byteorder)
    else:
        print(f"Unsupported relocation type: {rel.rel_type}", file=sys.stderr)
        sys.exit(1)

def relocate(objs, gsymtab, gdata, byteorder, got_seg):
    for o in objs:
        for rel in o.relocations:
            _relocate_one(rel, o, gsymtab, gdata, byteorder, got_seg)
