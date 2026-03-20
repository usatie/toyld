import sys


def _relocate_a4(rel, obj, gsymtab, out_segments, gdata):
    lseg = obj.segments[rel.seg_number - 1]
    ref_lseg = obj.segments[rel.ref - 1]
    data = gdata[lseg.name]
    # Big-endian 4-byte absolute address copy
    data[rel.loc:rel.loc+4] = (ref_lseg.assigned_address).to_bytes(4, byteorder='big')

def _relocate(rel, obj, gsymtab, out_segments, gdata):
    if rel.rel_type == 'A4':
        return _relocate_a4(rel, obj, gsymtab, out_segments, gdata)
    else:
        print(f"Unsupported relocation type: {rel.rel_type}", file=sys.stderr)
        sys.exit(1)

def resolve(objs, gsymtab, out_segments, gdata):
    for o in objs:
        for rel in o.relocations:
            _relocate(rel, o, gsymtab, out_segments, gdata)
