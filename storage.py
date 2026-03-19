import sys

from object import Segment

def roundup(size, alignment):
    return (size + alignment - 1) // alignment * alignment

def allocate(objs, gsymtab):
    # start text segment at 0x1000 to leave some space for the header
    TEXT_START = 0x1000
    VALID_SEGMENT_TYPES = {'RP', 'RWP', 'RW'}
    groups = {
        '.text': Segment('.text', 0, 0, 'RP'),
        '.data': Segment('.data', 0, 0, 'RWP'),
        '.bss': Segment('.bss', 0, 0, 'RW'),
    }
    WORD_ALIGNMENT = 0x0004
    PAGE_ALIGNMENT = 0x1000

    # Calculate the size of each segment group (textgroup, datagroup, bssgroup)
    for o in objs:
        for seg in o.segments:
            if seg.code_letter not in VALID_SEGMENT_TYPES:
                print(f"Invalid code letter '{seg.code_letter}' in segment '{seg.name}' from file '{seg.filename}'", file=sys.stderr)
                sys.exit(1)
            if seg.name not in groups:
                groups[seg.name] = Segment(seg.name, 0, 0, seg.code_letter)
            g = groups[seg.name]
            if g.code_letter != seg.code_letter:
                print(f"Segment '{seg.name}' has inconsistent code letters: '{g.code_letter}' and '{seg.code_letter}'", file=sys.stderr)
                sys.exit(1)
            
            seg.assigned_offset = g.size # For now, assign offset in the merged segment for now
            g.size += roundup(seg.size, WORD_ALIGNMENT)

    # Calculate the start address of segments in textgroup
    text_group_start = TEXT_START
    text_group_size = 0
    text_group = []
    for seg in groups.values():
        if seg.code_letter != 'RP': # Only allocate space for segments in the text group
            continue
        seg.start = text_group_start + text_group_size
        text_group_size += roundup(seg.size, WORD_ALIGNMENT)
        text_group.append(seg)

    # Calculate the start address of segments in datagroup
    data_group_start = roundup(text_group_start + text_group_size, PAGE_ALIGNMENT)
    data_group_size = 0 
    data_group = []
    for seg in groups.values():
        if seg.code_letter != 'RWP':
            continue
        seg.start = data_group_start + data_group_size
        data_group_size += roundup(seg.size, WORD_ALIGNMENT)
        data_group.append(seg)

    # Calculate the start address of segments in bssgroup
    bss_group_start = roundup(data_group_start + data_group_size, WORD_ALIGNMENT)
    bss_group_size = 0
    bss_group = []
    # Allocate space for common blocks at the end of the bss segment
    bss_start = bss_group_start
    bss_size = groups['.bss'].size
    common_start = roundup(bss_start + bss_size, WORD_ALIGNMENT)
    common_size = 0
    commons = {sym_name: sym for sym_name, sym in gsymtab.items() if sym.is_common}
    for sym in commons.values():
        address = roundup(common_start + common_size, WORD_ALIGNMENT)
        common_size = address + sym.value - common_start
        sym.value = address
    bss_size = common_start + common_size - bss_start
    groups['.bss'].size = bss_size
    for seg in groups.values():
        if seg.code_letter != 'RW':
            continue
        seg.start = bss_group_start + bss_group_size
        bss_group_size += roundup(seg.size, WORD_ALIGNMENT)
        bss_group.append(seg)

    # Now assign addresses to all segments based on the group they belong to
    for o in objs:
        for seg in o.segments:
            seg.assigned_address = seg.assigned_offset + groups[seg.name].start # Add the group start address to get the final assigned address
    return [Segment(seg.name, seg.start, seg.size, seg.code_letter) for seg in (text_group + data_group + bss_group)]

