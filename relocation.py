import sys
from dataclasses import dataclass

@dataclass
class RelocationContext:
    rel: object
    obj: object
    gsymtab: dict
    gdata: dict
    got_gseg: object
    byteorder: str
    tgt_lseg: object
    seg_data: object
    offset: int

def _resolve_symbol_addr(ctx):
    sym_name = list(ctx.obj.symbols.keys())[ctx.rel.ref - 1]
    ref_sym = ctx.gsymtab[sym_name]
    return ref_sym.value

def _relocate_a4(ctx):
    ref_lseg = ctx.obj.segments[ctx.rel.ref - 1]
    ctx.seg_data[ctx.offset:ctx.offset+4] = ref_lseg.assigned_address.to_bytes(4, byteorder=ctx.byteorder)

def _relocate_r4(ctx):
    ref_lseg = ctx.obj.segments[ctx.rel.ref - 1]
    pc_relative_addr = ref_lseg.assigned_address - (ctx.tgt_lseg.assigned_address + ctx.rel.loc + 4)
    ctx.seg_data[ctx.offset:ctx.offset+4] = pc_relative_addr.to_bytes(4, byteorder=ctx.byteorder)

def _relocate_as4(ctx):
    abs_addr = _resolve_symbol_addr(ctx)
    # NOTE: Probably it's safer to read the addend from the original segment data, not from the already modified data
    # because seg_data may have been modified by previous relocations.
    addend = int.from_bytes(ctx.seg_data[ctx.offset:ctx.offset+4], byteorder=ctx.byteorder, signed=True)
    abs_addr += addend
    ctx.seg_data[ctx.offset:ctx.offset+4] = abs_addr.to_bytes(4, byteorder=ctx.byteorder)

def _relocate_rs4(ctx):
    abs_addr = _resolve_symbol_addr(ctx)
    # NOTE: Probably it's safer to read the addend from the original segment data, not from the already modified data
    # because seg_data may have been modified by previous relocations.
    addend = int.from_bytes(ctx.seg_data[ctx.offset:ctx.offset+4], byteorder=ctx.byteorder, signed=True)
    abs_addr += addend
    pc_relative_addr = abs_addr - (ctx.tgt_lseg.assigned_address + ctx.rel.loc + 4)
    ctx.seg_data[ctx.offset:ctx.offset+4] = pc_relative_addr.to_bytes(4, byteorder=ctx.byteorder, signed=True)

def _relocate_u2(ctx):
    abs_addr = _resolve_symbol_addr(ctx)
    ctx.seg_data[ctx.offset:ctx.offset+2] = ((abs_addr >> 16) & 0xffff).to_bytes(2, byteorder=ctx.byteorder)

def _relocate_l2(ctx):
    abs_addr = _resolve_symbol_addr(ctx)
    ctx.seg_data[ctx.offset:ctx.offset+2] = (abs_addr & 0xffff).to_bytes(2, byteorder=ctx.byteorder)

def _relocate_gp4(ctx):
    sym_name = list(ctx.obj.symbols.keys())[ctx.rel.ref - 1]
    ref_sym = ctx.gsymtab[sym_name]

    # Write the GOT offset of the symbol into the instruction
    got_offset = ref_sym.got_offset
    ctx.seg_data[ctx.offset:ctx.offset+4] = got_offset.to_bytes(4, byteorder=ctx.byteorder)

    # Write the address relative to the beginning of the executable (0x1000) into the GOT entry
    executable_rel_addr = ref_sym.value - 0x1000
    ctx.gdata['.got'][got_offset:got_offset+4] = executable_rel_addr.to_bytes(4, byteorder=ctx.byteorder)

def _relocate_ga4(ctx):
    distance_to_got = ctx.got_gseg.start - (ctx.tgt_lseg.assigned_address + ctx.rel.loc)
    ctx.seg_data[ctx.offset:ctx.offset+4] = distance_to_got.to_bytes(4, byteorder=ctx.byteorder)

_HANDLERS = {
    'A4':  _relocate_a4,
    'R4':  _relocate_r4,
    'AS4': _relocate_as4,
    'RS4': _relocate_rs4,
    'U2':  _relocate_u2,
    'L2':  _relocate_l2,
    'GP4': _relocate_gp4,
    'GA4': _relocate_ga4,
}

def relocate(objs, gsymtab, gdata, byteorder, got_gseg):
    for o in objs:
        for rel in o.relocations:
            tgt_lseg = o.segments[rel.seg_number - 1]
            seg_data = gdata[tgt_lseg.name]
            offset = tgt_lseg.assigned_offset + rel.loc
            if offset + 4 > len(seg_data):
                print(f"Relocation out of bounds: segment '{tgt_lseg.name}', offset {offset}, seg_data length {len(seg_data)}", file=sys.stderr)
                sys.exit(1)
            handler = _HANDLERS.get(rel.rel_type)
            if handler is None:
                print(f"Unsupported relocation type: {rel.rel_type}", file=sys.stderr)
                sys.exit(1)
            ctx = RelocationContext(
                rel=rel, obj=o, gsymtab=gsymtab, gdata=gdata, got_gseg=got_gseg,
                byteorder=byteorder, tgt_lseg=tgt_lseg, seg_data=seg_data, offset=offset,
            )
            handler(ctx)
