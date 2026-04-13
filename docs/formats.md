# Format Reference

## Object File Format (`.lk`)

All numbers are hexadecimal. Lines starting with `#` are comments and are ignored.

```
LINK
<nsegs> <nsyms> <nrels>
# Segment entries (one per line):
<name> <start> <size> <flags>
# Symbol entries:
<name> <value> <seg_number> <type>
# Relocation entries:
<loc> <seg_number> <ref> <type> [extra fields...]
# Data section (hex string):
# The data for each segment is a single long hexadecimal string followed by a newline.
# The same order as the segment entries, and there must be segment data for each segment that is identified as being present
<data>
...
```

Example:

```
LINK
2 2 1

# segments
.text 1000 100 RP
.data 2000 80 RWP

# symbols
foo 10 1 D
bar 20 2 U

# relocations
0 1 1 R_32

# data
0123456789abcdef...
0123456789abcdef...
```

**Segment flags:** `RP` (read/execute, present in file), `RWP` (read-write, present), `RW` (read-write, not in file — e.g., `.bss`)

**Symbol types:** `D` (defined), `U` (undefined/external). An undefined symbol with a nonzero value is a common block of that size.

**Segment numbers** in symbol and relocation entries are 1-based.

**Relocation types:** `A4` (Absolute [Segment] reference), `R4` (Relative [Segment] reference), `AS4` (Absolute Symbol reference), `RS4` (Relative Symbol reference), `U2` (Upper half reference), `L2` (Lower half reference), `GA4` (distance to GOT base), `GP4` (GOT pointer for external symbol), `GR4` (GOT-relative local address), `ER4` (executable-relative, output-only). See `relocation.md` and `got.md` for details.

---

## Library Formats

Libraries use a distinct extension from plain object files (`.lk`):

| Format | Extension | Heritage |
|--------|-----------|---------|
| Directory | `.pds` | IBM OS/360 Partitioned Data Set |
| File | `.a` | Unix `ar` archive |

### Directory Format (`.pds`)

The output is a directory. Each defined symbol in the input object files becomes a hard link inside the output directory pointing to the object file that defines it. This allows a linker to load only the modules needed to resolve undefined symbols by looking up a symbol name directly as a filename in the directory.

Example for a library containing `foo.lk` (defines `foo` and `helper`) and `bar.lk` (defines `bar`):

```
libfoo.pds/
├── foo     ← hard link to foo.lk content  (inode A)
├── helper  ← hard link to foo.lk content  (inode A, same file)
└── bar     ← hard link to bar.lk content  (inode B)
```

To resolve a symbol, the linker opens `libfoo.pds/<symbol>`. Because `foo` and `helper` share an inode, loading either one loads the same object module, which defines both symbols.

### File Format (`.a`)

The output is a single file with three sections:

1. **Header line:** `LIBRARY <nmods> <diroff>` — number of modules (hex) and the byte offset (hex) of the directory at the end of the file.
2. **Module contents:** the raw bytes of each input object file, concatenated in order.
3. **Directory:** one line per module, at the end of the file:
   ```
   <offset> <size> <sym1> <sym2> ...
   ```
   All numbers are hexadecimal. `offset` and `size` are the byte position and length of the module within the file. Only defined symbols are listed.

Example for a library containing `foo.lk` (56 bytes, defines `foo` and `helper`) and `bar.lk` (53 bytes, defines `bar`):

```
LIBRARY 2 7a
<foo.lk bytes — 0x38 bytes starting at offset 0xd>
<bar.lk bytes — 0x35 bytes starting at offset 0x45>
d 38 foo helper
45 35 bar
```

---

## Storage Allocation Strategy

1. **Text group** (`RP` segments): placed starting at `0x1000`, each segment word-aligned (4-byte).
2. **Data group** (`RWP` segments): placed at the next 4KB page boundary after the text group.
3. **BSS group** (`RW` segments): placed at the next word boundary after the data group. Common blocks are appended word-aligned at the end of `.bss`.

---

## Symbol Resolution

- **Defined symbols** (`D`): value = segment's assigned address + symbol's offset within the segment.
- **Common blocks** (`U` with nonzero value): the largest declaration across all input files is kept; the symbol is assigned an address at the end of `.bss`.
- **Undefined symbols** (`U` with zero value): must be satisfied by a definition in another input file; an error is raised if unresolved.
- Multiply-defined symbols are an error.
