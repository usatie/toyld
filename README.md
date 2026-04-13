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

See [docs/test-cases.md](docs/test-cases.md) for full descriptions of all 29 test cases.

## Storage Allocation Strategy

1. **Text group** (`RP` segments): placed starting at `0x1000`, each segment word-aligned (4-byte).
2. **Data group** (`RWP` segments): placed at the next 4KB page boundary after the text group.
3. **BSS group** (`RW` segments): placed at the next word boundary after the data group. Common blocks are appended word-aligned at the end of `.bss`.

## Symbol Resolution

- **Defined symbols** (`D`): value = segment's assigned address + symbol's offset within the segment.
- **Common blocks** (`U` with nonzero value): the largest declaration across all input files is kept; the symbol is assigned an address at the end of `.bss`.
- **Undefined symbols** (`U` with zero value): must be satisfied by a definition in another input file; an error is raised if unresolved.
- Multiply-defined symbols are an error.
