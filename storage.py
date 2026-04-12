from collections import defaultdict
import sys

from object import Segment

def roundup(size, alignment):
    return (size + alignment - 1) // alignment * alignment

def pad(data, alignment):
    return data + b'\x00' * (roundup(len(data), alignment) - len(data))

def allocate(objs, gsymtab, base_addr):
    # start text segment at 0x1000 to leave some space for the header
    TEXT_START = base_addr
    VALID_SEGMENT_TYPES = {'RP', 'RWP', 'RW'}
    WORD_ALIGNMENT = 0x0004
    PAGE_ALIGNMENT = 0x1000

    # 1st pass : Fix the order of output segments
    text_segments = {'.text': None}
    data_segments = {'.data': None}
    bss_segments = {'.bss': None}
    for o in objs:
        for lseg in o.segments:
            if lseg.code_letter not in VALID_SEGMENT_TYPES:
                print(f"Invalid code letter '{lseg.code_letter}' in segment '{lseg.name}' from file '{lseg.filename}'", file=sys.stderr)
                sys.exit(1)
            if lseg.code_letter == 'RP':
                text_segments[lseg.name] = None
            elif lseg.code_letter == 'RWP':
                data_segments[lseg.name] = None
            elif lseg.code_letter == 'RW':
                bss_segments[lseg.name] = None
    gsegments = {
        **{name: Segment(name, 0, 0, 'RP') for name in text_segments},
        '.got': Segment('.got', 0, 0, 'RWP'),
        **{name: Segment(name, 0, 0, 'RWP') for name in data_segments},
        **{name: Segment(name, 0, 0, 'RW') for name in bss_segments}}
    gdata = {
        **{name: bytearray() for name in text_segments},
        '.got': bytearray(),
        **{name: bytearray() for name in data_segments}
    }

    # Calculate the size of each segment group (textgroup, datagroup, bssgroup)
    for o in objs:
        data_index = 0
        for lseg in o.segments:
            gseg = gsegments[lseg.name]
            if gseg.code_letter != lseg.code_letter:
                print(f"Segment '{lseg.name}' has inconsistent code letters: '{gseg.code_letter}' and '{lseg.code_letter}'", file=sys.stderr)
                sys.exit(1)
            
            lseg.assigned_offset = gseg.size # For now, assign offset in the merged segment for now
            gseg.size += roundup(lseg.size, WORD_ALIGNMENT)
            if 'P' in lseg.code_letter:
                gdata[lseg.name] += pad(o.data[data_index], WORD_ALIGNMENT)
                data_index += 1

    # Calculate the start address of segments in textgroup
    text_group_start = TEXT_START
    text_group_size = 0
    text_group = []
    for gseg in (s for s in gsegments.values() if s.code_letter == 'RP'):
        gseg.start = text_group_start + text_group_size
        text_group_size += roundup(gseg.size, WORD_ALIGNMENT)
        text_group.append(gseg)

    # Calculate the GOT size and allocate it just before the .data and .bss segments
    got = {}
    for o in objs:
        for rel in o.relocations:
            if rel.rel_type == 'GP4':
                sym_name = list(o.symbols.keys())[rel.ref - 1]
                gsym = gsymtab[sym_name]
                if gsym.is_defined:
                    print(f"Warning: GOT entry for defined symbol '{gsym.name}' is not needed, but will be allocated anyway", file=sys.stderr)
                if gsym.name not in got:
                    gsym.got_offset = len(got) * WORD_ALIGNMENT
                    got[gsym.name] = gsym
                    print(f"Added GOT entry for symbol '{gsym.name}' at offset {gsym.got_offset}", file=sys.stderr)
    got_size = len(got) * WORD_ALIGNMENT
    gsegments['.got'].size = got_size
    if got_size == 0:
        gsegments.pop('.got')
        gdata.pop('.got')
    else:
        gdata['.got'] = bytearray(got_size) # Initialize GOT data with zeros, and it will be filled in later after symbol values are resolved

    # Calculate the start address of segments in datagroup
    data_group_start = roundup(text_group_start + text_group_size, PAGE_ALIGNMENT)
    data_group_size = 0
    data_group = []
    for gseg in (s for s in gsegments.values() if s.code_letter == 'RWP'):
        gseg.start = data_group_start + data_group_size
        data_group_size += roundup(gseg.size, WORD_ALIGNMENT)
        data_group.append(gseg)

    # Calculate the start address of segments in bssgroup
    bss_group_start = roundup(data_group_start + data_group_size, WORD_ALIGNMENT)
    bss_group_size = 0
    bss_group = []
    # Allocate space for common blocks at the end of the bss segment
    bss_start = bss_group_start
    bss_size = gsegments['.bss'].size
    common_start = roundup(bss_start + bss_size, WORD_ALIGNMENT)
    common_size = 0
    commons = {sym_name: sym for sym_name, sym in gsymtab.items() if sym.is_common}
    for sym in commons.values():
        address = roundup(common_start + common_size, WORD_ALIGNMENT)
        common_size = address + sym.value - common_start
        sym.value = address
    bss_size = common_start + common_size - bss_start
    gsegments['.bss'].size = bss_size
    for gseg in (s for s in gsegments.values() if s.code_letter == 'RW'):
        gseg.start = bss_group_start + bss_group_size
        bss_group_size += roundup(gseg.size, WORD_ALIGNMENT)
        bss_group.append(gseg)

    # Now assign addresses to all local segments based on the global segments they belong to
    for o in objs:
        for lseg in o.segments:
            lseg.assigned_address = lseg.assigned_offset + gsegments[lseg.name].start # Add the global segment start address to get the final assigned address
    out_segments = [Segment(gseg.name, gseg.start, gseg.size, gseg.code_letter) for gseg in (text_group + data_group + bss_group)]
    return out_segments, gdata

