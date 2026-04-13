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

A text-based format; all numbers are hexadecimal, lines starting with `#` are comments. See [docs/formats.md](docs/formats.md) for the full specification including segment flags, symbol types, and relocation types.

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

See [docs/formats.md](docs/formats.md) for directory and file format details.

### Shared Libraries

The linker can produce a **static shared library** from a regular library input using `--shared`. A shared library is a fully linked object file (all symbols resolved, no outstanding relocations) allocated at a fixed base address. Its extension is `.sso` (shared static object).

```sh
./librarian.py --output libfoo.pds foo.lk bar.lk
./linker.py libfoo.pds --shared --base-addr 0x5000 \
    --output lib/libfoo.sso \
    --stub-format directory --stub-output stublib/libfoo.sso
```

See [docs/shared-libraries.md](docs/shared-libraries.md) for stub library format details.

## Running Tests

```sh
make           # Run all tests (test1–test29)
make test1     # Run individual test
```

## Test Cases

See [docs/test-cases.md](docs/test-cases.md) for full descriptions of all 29 test cases.

## Reference

- [docs/formats.md](docs/formats.md) — Object file format, library formats, storage allocation, symbol resolution
- [docs/shared-libraries.md](docs/shared-libraries.md) — Static shared library and stub library details
- [docs/relocation.md](docs/relocation.md) — Relocation types (A4, R4, AS4, RS4, U2, L2)
- [docs/got.md](docs/got.md) — GOT and PIC relocation types (GA4, GP4, GR4, ER4)
- [docs/test-cases.md](docs/test-cases.md) — Full test case descriptions
