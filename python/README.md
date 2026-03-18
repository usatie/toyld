# Linkers and Loaders — Project Implementation

A Python implementation of the linker projects from *Linkers and Loaders* by John R. Levine.

## Overview

This project implements a linker that processes a simple text-based object file format (`.lk`) defined in Chapter 3 of the book. The linker is built incrementally across chapters:

| Project | Chapter | Feature |
|---------|---------|---------|
| 3.1 | Ch. 3 | Parse and re-emit a single object file |
| 4.1 | Ch. 4 | UNIX-style storage allocation (`.text`, `.data`, `.bss`) |
| 4.2 | Ch. 4 | Common block resolution |
| 4.3 | Ch. 4 | Arbitrary segment support |
| 5.1 | Ch. 5 | Symbol name and value resolution |

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
<hex bytes>
```

**Segment flags:** `RP` (read/execute, present in file), `RWP` (read-write, present), `RW` (read-write, not in file — e.g., `.bss`)

**Symbol types:** `D` (defined), `U` (undefined/external). An undefined symbol with a nonzero value is a common block of that size.

**Segment numbers** in symbol and relocation entries are 1-based.

## Usage

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

## Running Tests

```sh
make          # Run all tests
make test1    # Run individual test
make test2
make test3
make test4
make test5
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

## Storage Allocation Strategy

1. **Text group** (`RP` segments): placed starting at `0x1000`, each segment word-aligned (4-byte).
2. **Data group** (`RWP` segments): placed at the next 4KB page boundary after the text group.
3. **BSS group** (`RW` segments): placed at the next word boundary after the data group. Common blocks are appended word-aligned at the end of `.bss`.

## Symbol Resolution

- **Defined symbols** (`D`): value = segment's assigned address + symbol's offset within the segment.
- **Common blocks** (`U` with nonzero value): the largest declaration across all input files is kept; the symbol is assigned an address at the end of `.bss`.
- **Undefined symbols** (`U` with zero value): must be satisfied by a definition in another input file; an error is raised if unresolved.
- Multiply-defined symbols are an error.
