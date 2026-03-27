import sys
from dataclasses import dataclass

from object import Relocation

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
    out_segments: list

def _resolve_symbol_addr(ctx):
    sym_name = list(ctx.obj.symbols.keys())[ctx.rel.ref - 1]
    ref_sym = ctx.gsymtab[sym_name]
    return ref_sym.value

def _relocate_a4(ctx):
    ref_lseg = ctx.obj.segments[ctx.rel.ref - 1]
    ctx.seg_data[ctx.offset:ctx.offset+4] = ref_lseg.assigned_address.to_bytes(4, byteorder=ctx.byteorder)
    # Create ER4 relocation entries for the output
    offset = ctx.tgt_lseg.assigned_offset + ctx.rel.loc
    segment_number = next((i + 1 for i, s in enumerate(ctx.out_segments) if s.name == ctx.tgt_lseg.name), None)
    return Relocation(offset, segment_number, 0, 'ER4', [])

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
    # Create ER4 relocation entries for the output
    offset = ctx.tgt_lseg.assigned_offset + ctx.rel.loc
    segment_number = next((i + 1 for i, s in enumerate(ctx.out_segments) if s.name == ctx.tgt_lseg.name), None)
    return Relocation(offset, segment_number, 0, 'ER4', [])

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

    # Write the address relative to the beginning of the executable into the GOT entry
    executable_rel_addr = ref_sym.value
    ctx.gdata['.got'][got_offset:got_offset+4] = executable_rel_addr.to_bytes(4, byteorder=ctx.byteorder)

def _relocate_ga4(ctx):
    distance_to_got = ctx.got_gseg.start - (ctx.tgt_lseg.assigned_address + ctx.rel.loc)
    ctx.seg_data[ctx.offset:ctx.offset+4] = distance_to_got.to_bytes(4, byteorder=ctx.byteorder)

def _relocate_gr4(ctx):
    ref_lseg = ctx.obj.segments[ctx.rel.ref - 1]
    ref_lseg_offset = int.from_bytes(ctx.seg_data[ctx.offset:ctx.offset+4], byteorder=ctx.byteorder, signed=True)
    got_relative_addr = ref_lseg.assigned_address + ref_lseg_offset - ctx.got_gseg.start
    ctx.seg_data[ctx.offset:ctx.offset+4] = got_relative_addr.to_bytes(4, byteorder=ctx.byteorder, signed=True)

_HANDLERS = {
    'A4':  _relocate_a4,
    'R4':  _relocate_r4,
    'AS4': _relocate_as4,
    'RS4': _relocate_rs4,
    'U2':  _relocate_u2,
    'L2':  _relocate_l2,
    'GP4': _relocate_gp4,
    'GA4': _relocate_ga4,
    'GR4': _relocate_gr4,
}

def relocate(objs, gsymtab, gdata, byteorder, out_segments):
    got_segment_index = next((i + 1 for i, s in enumerate(out_segments) if s.name == '.got'), None)
    got_gseg = out_segments[got_segment_index - 1] if got_segment_index is not None else None
    # We need to create ER4 relocations for the output for all symbols that are stored in the GOT
    out_relocations = [Relocation(s.got_offset, got_segment_index, 0, 'ER4', [])  for s in gsymtab.values() if s.got_offset is not None]
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
                byteorder=byteorder, tgt_lseg=tgt_lseg, seg_data=seg_data, offset=offset, out_segments=out_segments
            )
            ret = handler(ctx)
            if isinstance(ret, Relocation):
                out_relocations.append(ret)
    return out_relocations
