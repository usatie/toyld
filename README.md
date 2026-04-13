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
| 6.4 | Ch. 6 | linker | Linking against file-format libraries |
| 7.1 | Ch. 7 | linker | A4 relocation — absolute segment reference |
| 7.1 | Ch. 7 | linker | R4 relocation — PC-relative segment reference |
| 7.1 | Ch. 7 | linker | AS4 relocation — absolute symbol reference |
| 7.1 | Ch. 7 | linker | RS4 relocation — PC-relative symbol reference |
| 7.1 | Ch. 7 | linker | U2 relocation — upper 16-bit symbol address |
| 7.1 | Ch. 7 | linker | L2 relocation — lower 16-bit symbol address |
| 7.1 | Ch. 7 | linker | Combined all 6 relocation types, big-endian |
| 7.2 | Ch. 7 | linker | Little-endian byte order (`--byteorder little`) |
| 8.1 | Ch. 8 | linker | Symbol wrapping (`--wrap`) against object files |
| 8.1 | Ch. 8 | linker | Symbol wrapping against directory-format libraries |
| 8.1 | Ch. 8 | linker | Symbol wrapping against file-format libraries |
| 8.2 | Ch. 8 | symwrap | Standalone symbol wrapper program for object files |
| 8.3 | Ch. 8 | linker | GP4 relocation — GOT pointer (external symbol via GOT) |
| 8.3 | Ch. 8 | linker | GA4 relocation — GOT address (PC-relative distance to GOT) |
| 8.3 | Ch. 8 | linker | GR4 relocation — GOT-relative local address |
| 8.3 | Ch. 8 | linker | ER4 output — executable-relative entries from A4/AS4 inputs and GOT slots |
| 9.1 | Ch. 9 | linker | Static shared library creation with directory-format stub (`--shared`) |
| 9.1 | Ch. 9 | linker | Static shared library with cross-library dependency in directory-format stub |
| 9.1 | Ch. 9 | linker | Static shared library creation with file-format stub (`--stub-format file`) |
| 9.1 | Ch. 9 | linker | Static shared library using file-format input stub, producing file-format output stub |

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

**Relocation types:** `A4` (Absolute [Segment] reference), `R4` (Relative [Segment] reference), `AS4` (Absolute Symbol reference), `RS4` (Relative Symbol reference), `U2` (Upper half reference), `L2` (Lower half reference), `GA4` (distance to GOT base), `GP4` (GOT pointer for external symbol), `GR4` (GOT-relative local address), `ER4` (executable-relative, output-only). See `docs/relocation.md` and `docs/got.md` for details.

## Usage

### Linker

```sh
./linker.py <input_files...> [options]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Output file name (default: `a.out.lk`) |
| `--skip-symbols` | Omit symbol table from output |
| `--skip-relocations` | Omit relocation entries from output |
| `--skip-data` | Omit data section from output |
| `--common` | Allocate common blocks at the end of `.bss` |
| `--byteorder big\|little` | Byte order for relocation patches (default: `little`) |
| `--wrap SYM`, `-w SYM` | Redirect references to `SYM` → `wrap_SYM`; rename `SYM` → `real_SYM` |
| `--shared` | Produce a static shared library; requires `--stub-output` |
| `--base-addr ADDR` | Base address for segment allocation in hex (default: `0x1000`) |
| `--stub-format directory\|file` | Format for the output stub library (default: `directory`) |
| `--stub-output PATH` | Output path for the stub library (required with `--shared`) |
| `--debug` | Print debug info to stderr |

### Symbol Wrapper

```sh
./symwrap.py <input_files...> [--wrap SYM] [-o <output_dir>]
```

Applies `--wrap` semantics to object files without linking them. Each input file is rewritten and written to the output directory with a `wrapped_` prefix.

**Options:**

| Flag | Description |
|------|-------------|
| `--wrap SYM`, `-w SYM` | Symbol to wrap (can be specified multiple times) |
| `--output-dir`, `-o` | Output directory for wrapped files (default: current directory) |

For each wrapped symbol `SYM`:
- Undefined references to `SYM` are renamed to `wrap_SYM`.
- A defined `SYM` is renamed to `real_SYM`, and an undefined `wrap_SYM` symbol is inserted.

### Librarian

```sh
./librarian.py <input_files...> [--output <output_dir>] [--format <format>]
```

**Options:**

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Output library name |
| `--format`, `-f` | Library format: `directory` (default) or `file` |

Libraries use a distinct extension from plain object files (`.lk`) to make the type unambiguous at a glance:

| Format | Extension | Heritage |
|--------|-----------|---------|
| Directory | `.pds` | IBM OS/360 Partitioned Data Set |
| File | `.a` | Unix `ar` archive |

### Shared Libraries

The linker can produce a **static shared library** from a regular library input using `--shared`. A shared library is a fully linked object file (all symbols resolved, no outstanding relocations) allocated at a fixed base address. Its extension is `.sso` (shared static object).

```sh
./librarian.py --output libfoo.pds foo.lk bar.lk
./linker.py libfoo.pds --shared --base-addr 0x5000 \
    --output lib/libfoo.sso \
    --stub-format directory --stub-output stublib/libfoo.sso
```

Along with the shared library itself the linker writes a **stub library** — a directory-format or file-format library whose entries are data-trimmed copies of the shared library. Each entry has the same segment layout as the `.sso` (with the `P` flag removed from each segment) and all exported symbols at their absolute addresses, but no data bytes. All entries in the stub are hard links to the same content.

Stub libraries share the `.sso` extension with the shared library they describe but are placed in a separate directory (conventionally `stublib/`).

#### Directory-format stub

The stub is a directory. A special file `LIBRARY NAME` records the name of the shared library on its first line, followed by the names of any other shared libraries it depends on:

```
LIBRARY NAME
libfoo.sso
libbar.sso        ← dependency
```

Each defined symbol in the shared library becomes a filename inside the directory. All entries are hard links to the same data-trimmed `.sso` content:

```
stublib/libfoo.sso/
├── LIBRARY NAME  ← dependency list
├── foo           ← hard link (inode A)
└── bar           ← hard link (inode A, same content)
```

#### File-format stub

The stub is a single file. The header line has extra fields beyond the standard `LIBRARY <nmods> <diroff>`:

```
LIBRARY <nmods> <diroff> <libname> [<dep1> <dep2> ...]
```

`<libname>` is the name of the shared library this stub describes; subsequent fields are dependency library names. The rest of the format (module contents and directory) is identical to a regular file-format library, with one module per defined symbol group — in practice one module containing the data-trimmed shared library content, with all defined symbols listed in the directory entry.

### Directory format

The output is a directory (`.pds`). Each defined symbol in the input object files becomes a hard link inside the output directory pointing to the object file that defines it. This allows a linker to load only the modules needed to resolve undefined symbols by looking up a symbol name directly as a filename in the directory.

Example for a library containing `foo.lk` (defines `foo` and `helper`) and `bar.lk` (defines `bar`):

```
libfoo.pds/
├── foo     ← hard link to foo.lk content  (inode A)
├── helper  ← hard link to foo.lk content  (inode A, same file)
└── bar     ← hard link to bar.lk content  (inode B)
```

To resolve a symbol, the linker opens `libfoo.pds/<symbol>`. Because `foo` and `helper` share an inode, loading either one loads the same object module, which defines both symbols.

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
make           # Run all tests (test1–test29)
make test1     # Run individual test
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
./librarian.py --output libfoo.pds tests/testcase6/foo.lk tests/testcase6/bar.lk
```

### Test 7 — Linking against directory-format libraries (Project 6.2)
Links `main.lk` against five directory-format libraries. The linker searches each library and loads only the modules needed to resolve undefined symbols, repeating until all symbols are satisfied.

```sh
./librarian.py --output libprintf.pds tests/testcase7/{printf,sprintf}.lk
./linker.py tests/testcase7/main.lk libprintf.pds ...
```

### Test 8 — File-format library (Project 6.3)
Creates a file-format library from two object files. The library is a single file: a header line, the concatenated module contents, and a directory at the end mapping each symbol to its module's offset and size.

```sh
./librarian.py --format file --output libfoo.a tests/testcase8/foo.lk tests/testcase8/bar.lk
```

### Test 9 — Linking against file-format libraries (Project 6.4)
Same dependency graph as Test 7, but all five libraries are single-file archives created with `--format file`. The linker detects the `LIBRARY` header, reads the directory at `diroff`, and seeks to each module's offset on demand.

### Test 10 — A4 relocation (Project 7.1)
Links two object files containing `A4` relocations. Each patched slot receives the absolute address of the referenced segment's base.

### Test 11 — R4 relocation (Project 7.1)
Links two object files containing `R4` relocations. Each patched slot receives the PC-relative offset from the end of the relocation slot to the target segment's base.

### Test 12 — AS4 relocation (Project 7.1)
Links two object files containing `AS4` relocations. Each patched slot receives the absolute address of the referenced symbol, plus the addend stored in the slot.

### Test 13 — RS4 relocation (Project 7.1)
Links two object files containing `RS4` relocations targeting symbols in `.text`, `.data`, and `.bss`. Each patched slot receives the PC-relative offset from the end of the slot to the target symbol.

### Test 14 — U2 relocation (Project 7.1)
Links two object files where one contains a `U2` relocation. The upper 16 bits of the referenced symbol's address are written as a big-endian 2-byte value into the slot.

### Test 15 — L2 relocation (Project 7.1)
Mirror of Test 14 using `L2`. The lower 16 bits of the referenced symbol's address are written as a big-endian 2-byte value into the slot.

### Test 16 — All 6 relocation types combined, big-endian (Project 7.1)
Links two object files where `main.lk` exercises all six relocation types (`A4`, `R4`, `AS4`, `RS4`, `U2`, `L2`) in a single `.text` section. A large `.bss` padding block pushes `gbuf` to a high address so that `U2` and `L2` produce visually distinct non-trivial values.

```sh
./linker.py tests/testcase16/main.lk tests/testcase16/other.lk --byteorder big
```

### Test 17 — Little-endian byte order (Project 7.2)
Same structure and computed values as Test 16, but patches are written in little-endian byte order (the default). Verifies that `--byteorder little` produces byte-swapped output for all relocation widths.

```sh
./linker.py tests/testcase17/main.lk tests/testcase17/other.lk
```

### Test 18 — `--wrap` with object files (Project 8.1)
Links `main.lk`, `malloc.lk`, and `wrap_malloc.lk` with `-w malloc`. All references to `malloc` are redirected to `wrap_malloc`; the definition of `malloc` is renamed to `real_malloc`. Covers both `RS4` and `AS4` relocations in `.text` and `.data`.

```sh
./linker.py tests/testcase18/{main,malloc,wrap_malloc}.lk --byteorder big -w malloc
```

### Test 19 — `--wrap` with a directory-format library (Project 8.1)
Same three-module wrap scenario as Test 18, but `malloc.lk` is loaded from a directory-format library. Verifies that wrap semantics are applied to library modules pulled in during symbol resolution.

```sh
./librarian.py --output build/libmalloc.pds tests/testcase19/malloc.lk
./linker.py tests/testcase19/{main,wrap_malloc}.lk build/libmalloc.pds --byteorder big -w malloc
```

### Test 20 — `--wrap` with a file-format library (Project 8.1)
Mirror of Test 19 using a single-file archive (`--format file`) instead of a directory library. The linker seeks to the module's offset inside the archive, loads `malloc.lk`, and applies wrap semantics. Expected output is identical to Test 19.

```sh
./librarian.py --format file --output build/libmalloc.a tests/testcase19/malloc.lk
./linker.py tests/testcase19/{main,wrap_malloc}.lk build/libmalloc.a --byteorder big -w malloc
```

### Test 21 — Standalone symbol wrapper (Project 8.2)
Uses `symwrap.py` to rewrite two object files with `--wrap malloc` without linking. `caller.lk` (defines `main`, references `malloc`) has its undefined `malloc` renamed to `wrap_malloc`. `impl.lk` (defines `malloc`) has `malloc` renamed to `real_malloc` and a new undefined `wrap_malloc` symbol inserted. Each output is written with a `wrapped_` prefix.

```sh
./symwrap.py --wrap malloc tests/testcase21/caller.lk tests/testcase21/impl.lk -o build/symwrap
```

### Test 22 — GP4 relocation (Project 8.3)
Links two object files where `main.lk` references two external symbols (`gfunc` in `.text`, `gvar` in `.data`) via `GP4`. The linker builds a 2-entry GOT and writes each symbol's GOT-relative offset at the relocation site. Both GOT slots hold absolute addresses, producing two `ER4` entries in the output.

```sh
./linker.py tests/testcase22/main.lk tests/testcase22/other.lk --byteorder big
```

### Test 23 — GA4 relocation (Project 8.3)
Links two object files where `main.lk` uses `GA4` to store the PC-relative distance to the GOT, and `GP4` to get the GOT-relative offset of an external variable. The GOT has one slot, producing one `ER4` entry in the output.

```sh
./linker.py tests/testcase23/main.lk tests/testcase23/other.lk --byteorder big
```

### Test 24 — GR4 relocation (Project 8.3)
Links two object files where `main.lk` uses `GR4` to compute the GOT-relative address of a local `.bss` location (with a non-zero offset), and `GP4` to reference an external symbol. The single GOT slot produces one `ER4` entry in the output.

```sh
./linker.py tests/testcase24/main.lk tests/testcase24/other.lk --byteorder big
```

### Test 25 — ER4 output from A4/AS4 inputs (Project 8.3)
Links two object files where `main.lk` has an `A4` (absolute segment reference) and an `AS4` (absolute symbol reference) into its `.data` segment, but no `GP4` — so no GOT is created. The linker emits `ER4` entries in the output for each location whose patched value is an absolute address, so an OS loader can fix them up at load time.

```sh
./linker.py tests/testcase25/main.lk tests/testcase25/other.lk --byteorder big
```

### Test 26 — Static shared library, directory-format stub, no external deps (Project 9.1)
Creates a shared library from `add.lk` (defines `add`, `sub`) and `mul.lk` (defines `mul`), allocated at base address `0x5000`. Produces `lib/libmath.sso` (the shared library) and `stublib/libmath.sso/` (a directory-format stub). The stub's `add`, `sub`, and `mul` entries are all hard links to the same data-trimmed copy of the shared library (segments without `P` flag, absolute symbol values, no data bytes).

```sh
./librarian.py --format file --output build/libmath.pds tests/testcase26/{add,mul}.lk
./linker.py build/libmath.pds --shared --base-addr 0x5000 \
    --output build/lib/libmath.sso \
    --stub-format directory --stub-output build/stublib/libmath.sso
```

### Test 27 — Static shared library with cross-library dependency, directory-format stub (Project 9.1)
Creates a shared library from `printf.lk` (defines `printf`, references external `write`) and `sprintf.lk` (defines `sprintf`), linked against the directory-format input stub `libio.sso` which provides `write=0x3000`. The `LIBRARY NAME` file in the output stub records both `libprint.sso` and `libio.sso`, so downstream linkers know the dependency chain. The `printf` and `sprintf` stub entries are hard links to the same data-trimmed `libprint.sso`.

```sh
./librarian.py --output build/libprint.pds tests/testcase27/{printf,sprintf}.lk
./linker.py build/libprint.pds tests/testcase27/libio.sso --shared --base-addr 0x8000 \
    --byteorder big --output build/lib/libprint.sso \
    --stub-format directory --stub-output build/stublib/libprint.sso
```

### Test 28 — Static shared library, file-format stub, no external deps (Project 9.1)
Same modules as Test 26 (`add.lk`, `mul.lk`), same shared library output. The difference is that the stub is a single-file archive (`--stub-format file`). The file contains one module — the data-trimmed shared library — and a directory entry listing all three symbols (`add`, `sub`, `mul`) pointing to that module.

```sh
./librarian.py --output build/libmath.pds tests/testcase28/{add,mul}.lk
./linker.py build/libmath.pds --shared --base-addr 0x5000 \
    --output build/lib/libmath.sso \
    --stub-format file --stub-output build/stublib/libmath.sso
```

### Test 29 — Static shared library using file-format input stub, file-format output stub (Project 9.1)
Same modules as Test 27, but `libio.sso` is a file-format input stub. Produces a file-format output stub `libprint.sso` whose header names both `libprint.sso` and `libio.sso` as the dependency chain. The stub contains one module (the data-trimmed shared library) with both `printf` and `sprintf` in its directory entry.

```sh
./librarian.py --output build/libprint.pds tests/testcase29/{printf,sprintf}.lk
./linker.py build/libprint.pds tests/testcase29/libio.sso --shared --base-addr 0x8000 \
    --byteorder big --output build/lib/libprint.sso \
    --stub-format file --stub-output build/stublib/libprint.sso
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
