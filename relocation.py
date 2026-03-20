import sys


def _relocate_a4(rel, obj, gsymtab, out_segments, gdata):
    tgt_lseg = obj.segments[rel.seg_number - 1]
    ref_lseg = obj.segments[rel.ref - 1]
    seg_data = gdata[tgt_lseg.name]
    offset = tgt_lseg.assigned_offset + rel.loc
    if offset + 4 > len(seg_data):
        print(f"Relocation out of bounds: segment '{tgt_lseg.name}', offset {offset}, seg_data length {len(seg_data)}", file=sys.stderr)
        sys.exit(1)
    # Big-endian 4-byte absolute address copy
    seg_data[offset:offset+4] = (ref_lseg.assigned_address).to_bytes(4, byteorder='big')

def _relocate_one(rel, obj, gsymtab, out_segments, gdata):
    if rel.rel_type == 'A4':
        return _relocate_a4(rel, obj, gsymtab, out_segments, gdata)
    else:
        print(f"Unsupported relocation type: {rel.rel_type}", file=sys.stderr)
        sys.exit(1)

def relocate(objs, gsymtab, out_segments, gdata):
    for o in objs:
        for rel in o.relocations:
            _relocate_one(rel, o, gsymtab, out_segments, gdata)
