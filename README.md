# toyld — Toy Linker & Librarian

A toy linker and librarian built in Python, implementing projects from *Linkers and Loaders* by John R. Levine.

## Overview

This project implements a linker and librarian that process a simple text-based object file format (`.lk`) defined in Chapter 3 of the book. Both tools are built incrementally across chapters:

| Project | Chapter | Tool | Feature |
|---------|---------|------|---------|
| 3.1 | Ch. 3 | linker | Parse and re-emit a single object file |
| 4.1 | Ch. 4 | linker | UNIX-style storage allocation (`.text`, `.data`, `.bss`) |
| 4.2 | Ch. 4 | linker | Common block resolution |
| 4.3 | Ch. 4 | linker | Arbitrary segment support |
| 5.1 | Ch. 5 | linker | Symbol name and value resolution |
| 6.1 | Ch. 6 | librarian | Directory-format library creation |
| 6.2 | Ch. 6 | linker | Linking against directory-format libraries |
| 6.3 | Ch. 6 | librarian | File-format library creation |

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

e.g.
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

**Relocation types:** `A4` (Absolute [Segment] reference), `R4` (Relative [Segment] reference), `AS4` (Absolute Symbol reference), `RS4` (Relative Symbol reference), `U2` (Upper half reference), `L2` (Lower half reference). See `docs/relocation.md` for details.

## Usage

### Linker

```sh
./linker.py <input_files...> [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--skip-symbols` | Omit symbol table from output |
| `--skip-relocations` | Omit relocation entries from output |
| `--skip-data` | Omit data section from output |
| `--common` | Allocate common blocks at the end of `.bss` |
| `--debug` | Print debug info to stderr |

Output is always written to `a.out.lk`.

### Librarian

```sh
./librarian.py <input_files...> [--output <output_dir>] [--format <format>]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Output library name (default: `lib.lk`) |
| `--format`, `-f` | Library format: `directory` (default) or `file` |

### Directory format

The output is a directory. Each defined symbol in the input object files becomes a hard link inside the output directory pointing to the object file that defines it. This allows a linker to load only the modules needed to resolve undefined symbols by looking up a symbol name directly as a filename in the directory.

Example for a library containing `foo.lk` (defines `foo` and `helper`) and `bar.lk` (defines `bar`):

```
lib.lk/
├── foo     ← hard link to foo.lk content  (inode A)
├── helper  ← hard link to foo.lk content  (inode A, same file)
└── bar     ← hard link to bar.lk content  (inode B)
```

To resolve a symbol, the linker opens `lib.lk/<symbol>`. Because `foo` and `helper` share an inode, loading either one loads the same object module, which defines both symbols.

### File format

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

## Running Tests

```sh
make          # Run all tests
make test1    # Run individual test
make test2
make test3
make test4
make test5
make test6
make test7
make test8
```

## Test Cases

### Test 1 — Single object file pass-through (Project 3.1)
Parses `tests/testcase1/main.lk` and re-emits it. Verifies that the parser and writer round-trip a single object file correctly.

```sh
./linker.py tests/testcase1/main.lk
```

### Test 2 — Storage allocation (Project 4.1)
Links four object files. Merges `.text`, `.data`, and `.bss` segments from all inputs and assigns load addresses. Text starts at `0x1000`; data starts on the next 4KB-aligned page; BSS follows data.

```sh
./linker.py tests/testcase2/{main,california,massachusetts,newyork}.lk \
    --skip-symbols --skip-relocations --skip-data
```

### Test 3 — Common blocks (Project 4.2)
Same as Test 2, but with `--common` to allocate UNIX-style common blocks at the end of `.bss`. The largest common block definition wins.

```sh
./linker.py tests/testcase3/{main,california,massachusetts,newyork}.lk \
    --skip-symbols --skip-relocations --skip-data --common
```

### Test 4 — Arbitrary segments (Project 4.3)
Links files that contain segments beyond `.text`/`.data`/`.bss`. Segments are grouped by permission flags (`RP`, `RWP`, `RW`) to form the text, data, and BSS groups.

```sh
./linker.py tests/testcase4/{main,california,massachusetts,newyork}.lk \
    --skip-symbols --skip-relocations --skip-data --common
```

### Test 5 — Symbol resolution (Project 5.1)
Links two object files and resolves both symbol names and values. Each global symbol is assigned its final virtual address based on which segment it belongs to and where that segment was placed.

```sh
./linker.py tests/testcase5/{main,calif}.lk \
    --skip-relocations --skip-data --common
```

### Test 6 — Directory-format library (Project 6.1)
Creates a directory-format library from two object files. Each defined symbol becomes a hard link inside the output directory pointing to the object file that defines it.

```sh
./librarian.py --output lib.lk tests/testcase6/foo.lk tests/testcase6/bar.lk
```

### Test 7 — Linking against directory-format libraries (Project 6.2)
Links `main.lk` against five directory-format libraries. The linker searches each library and loads only the modules needed to resolve undefined symbols, repeating until all symbols are satisfied.

```sh
./librarian.py --output libprintf.lk tests/testcase7/{printf,sprintf}.lk
./linker.py tests/testcase7/main.lk libprintf.lk ...
```

### Test 8 — File-format library (Project 6.3)
Creates a file-format library from two object files. The library is a single file: a header line, the concatenated module contents, and a directory at the end mapping each symbol to its module's offset and size.

```sh
./librarian.py --format file --output lib.lk tests/testcase8/foo.lk tests/testcase8/bar.lk
```

## Storage Allocation Strategy

1. **Text group** (`RP` segments): placed starting at `0x1000`, each segment word-aligned (4-byte).
2. **Data group** (`RWP` segments): placed at the next 4KB page boundary after the text group.
3. **BSS group** (`RW` segments): placed at the next word boundary after the data group. Common blocks are appended word-aligned at the end of `.bss`.

## Symbol Resolution

- **Defined symbols** (`D`): value = segment's assigned address + symbol's offset within the segment.
- **Common blocks** (`U` with nonzero value): the largest declaration across all input files is kept; the symbol is assigned an address at the end of `.bss`.
- **Undefined symbols** (`U` with zero value): must be satisfied by a definition in another input file; an error is raised if unresolved.
- Multiply-defined symbols are an error.
