# Test Cases

## Test 1 — Single object file pass-through (Project 3.1)
Parses `tests/testcase1/main.lk` and re-emits it. Verifies that the parser and writer round-trip a single object file correctly.

```sh
./linker.py tests/testcase1/main.lk
```

## Test 2 — Storage allocation (Project 4.1)
Links four object files. Merges `.text`, `.data`, and `.bss` segments from all inputs and assigns load addresses. Text starts at `0x1000`; data starts on the next 4KB-aligned page; BSS follows data.

```sh
./linker.py tests/testcase2/{main,california,massachusetts,newyork}.lk \
    --skip-symbols --skip-relocations --skip-data
```

## Test 3 — Common blocks (Project 4.2)
Same as Test 2, but with `--common` to allocate UNIX-style common blocks at the end of `.bss`. The largest common block definition wins.

```sh
./linker.py tests/testcase3/{main,california,massachusetts,newyork}.lk \
    --skip-symbols --skip-relocations --skip-data --common
```

## Test 4 — Arbitrary segments (Project 4.3)
Links files that contain segments beyond `.text`/`.data`/`.bss`. Segments are grouped by permission flags (`RP`, `RWP`, `RW`) to form the text, data, and BSS groups.

```sh
./linker.py tests/testcase4/{main,california,massachusetts,newyork}.lk \
    --skip-symbols --skip-relocations --skip-data --common
```

## Test 5 — Symbol resolution (Project 5.1)
Links two object files and resolves both symbol names and values. Each global symbol is assigned its final virtual address based on which segment it belongs to and where that segment was placed.

```sh
./linker.py tests/testcase5/{main,calif}.lk \
    --skip-relocations --skip-data --common
```

## Test 6 — Directory-format library (Project 6.1)
Creates a directory-format library from two object files. Each defined symbol becomes a hard link inside the output directory pointing to the object file that defines it.

```sh
./librarian.py --output libfoo.pds tests/testcase6/foo.lk tests/testcase6/bar.lk
```

## Test 7 — Linking against directory-format libraries (Project 6.2)
Links `main.lk` against five directory-format libraries. The linker searches each library and loads only the modules needed to resolve undefined symbols, repeating until all symbols are satisfied.

```sh
./librarian.py --output libprintf.pds tests/testcase7/{printf,sprintf}.lk
./linker.py tests/testcase7/main.lk libprintf.pds ...
```

## Test 8 — File-format library (Project 6.3)
Creates a file-format library from two object files. The library is a single file: a header line, the concatenated module contents, and a directory at the end mapping each symbol to its module's offset and size.

```sh
./librarian.py --format file --output libfoo.a tests/testcase8/foo.lk tests/testcase8/bar.lk
```

## Test 9 — Linking against file-format libraries (Project 6.4)
Same dependency graph as Test 7, but all five libraries are single-file archives created with `--format file`. The linker detects the `LIBRARY` header, reads the directory at `diroff`, and seeks to each module's offset on demand.

## Test 10 — A4 relocation (Project 7.1)
Links two object files containing `A4` relocations. Each patched slot receives the absolute address of the referenced segment's base.

## Test 11 — R4 relocation (Project 7.1)
Links two object files containing `R4` relocations. Each patched slot receives the PC-relative offset from the end of the relocation slot to the target segment's base.

## Test 12 — AS4 relocation (Project 7.1)
Links two object files containing `AS4` relocations. Each patched slot receives the absolute address of the referenced symbol, plus the addend stored in the slot.

## Test 13 — RS4 relocation (Project 7.1)
Links two object files containing `RS4` relocations targeting symbols in `.text`, `.data`, and `.bss`. Each patched slot receives the PC-relative offset from the end of the slot to the target symbol.

## Test 14 — U2 relocation (Project 7.1)
Links two object files where one contains a `U2` relocation. The upper 16 bits of the referenced symbol's address are written as a big-endian 2-byte value into the slot.

## Test 15 — L2 relocation (Project 7.1)
Mirror of Test 14 using `L2`. The lower 16 bits of the referenced symbol's address are written as a big-endian 2-byte value into the slot.

## Test 16 — All 6 relocation types combined, big-endian (Project 7.1)
Links two object files where `main.lk` exercises all six relocation types (`A4`, `R4`, `AS4`, `RS4`, `U2`, `L2`) in a single `.text` section. A large `.bss` padding block pushes `gbuf` to a high address so that `U2` and `L2` produce visually distinct non-trivial values.

```sh
./linker.py tests/testcase16/main.lk tests/testcase16/other.lk --byteorder big
```

## Test 17 — Little-endian byte order (Project 7.2)
Same structure and computed values as Test 16, but patches are written in little-endian byte order (the default). Verifies that `--byteorder little` produces byte-swapped output for all relocation widths.

```sh
./linker.py tests/testcase17/main.lk tests/testcase17/other.lk
```

## Test 18 — `--wrap` with object files (Project 8.1)
Links `main.lk`, `malloc.lk`, and `wrap_malloc.lk` with `-w malloc`. All references to `malloc` are redirected to `wrap_malloc`; the definition of `malloc` is renamed to `real_malloc`. Covers both `RS4` and `AS4` relocations in `.text` and `.data`.

```sh
./linker.py tests/testcase18/{main,malloc,wrap_malloc}.lk --byteorder big -w malloc
```

## Test 19 — `--wrap` with a directory-format library (Project 8.1)
Same three-module wrap scenario as Test 18, but `malloc.lk` is loaded from a directory-format library. Verifies that wrap semantics are applied to library modules pulled in during symbol resolution.

```sh
./librarian.py --output build/libmalloc.pds tests/testcase19/malloc.lk
./linker.py tests/testcase19/{main,wrap_malloc}.lk build/libmalloc.pds --byteorder big -w malloc
```

## Test 20 — `--wrap` with a file-format library (Project 8.1)
Mirror of Test 19 using a single-file archive (`--format file`) instead of a directory library. The linker seeks to the module's offset inside the archive, loads `malloc.lk`, and applies wrap semantics. Expected output is identical to Test 19.

```sh
./librarian.py --format file --output build/libmalloc.a tests/testcase19/malloc.lk
./linker.py tests/testcase19/{main,wrap_malloc}.lk build/libmalloc.a --byteorder big -w malloc
```

## Test 21 — Standalone symbol wrapper (Project 8.2)
Uses `symwrap.py` to rewrite two object files with `--wrap malloc` without linking. `caller.lk` (defines `main`, references `malloc`) has its undefined `malloc` renamed to `wrap_malloc`. `impl.lk` (defines `malloc`) has `malloc` renamed to `real_malloc` and a new undefined `wrap_malloc` symbol inserted. Each output is written with a `wrapped_` prefix.

```sh
./symwrap.py --wrap malloc tests/testcase21/caller.lk tests/testcase21/impl.lk -o build/symwrap
```

## Test 22 — GP4 relocation (Project 8.3)
Links two object files where `main.lk` references two external symbols (`gfunc` in `.text`, `gvar` in `.data`) via `GP4`. The linker builds a 2-entry GOT and writes each symbol's GOT-relative offset at the relocation site. Both GOT slots hold absolute addresses, producing two `ER4` entries in the output.

```sh
./linker.py tests/testcase22/main.lk tests/testcase22/other.lk --byteorder big
```

## Test 23 — GA4 relocation (Project 8.3)
Links two object files where `main.lk` uses `GA4` to store the PC-relative distance to the GOT, and `GP4` to get the GOT-relative offset of an external variable. The GOT has one slot, producing one `ER4` entry in the output.

```sh
./linker.py tests/testcase23/main.lk tests/testcase23/other.lk --byteorder big
```

## Test 24 — GR4 relocation (Project 8.3)
Links two object files where `main.lk` uses `GR4` to compute the GOT-relative address of a local `.bss` location (with a non-zero offset), and `GP4` to reference an external symbol. The single GOT slot produces one `ER4` entry in the output.

```sh
./linker.py tests/testcase24/main.lk tests/testcase24/other.lk --byteorder big
```

## Test 25 — ER4 output from A4/AS4 inputs (Project 8.3)
Links two object files where `main.lk` has an `A4` (absolute segment reference) and an `AS4` (absolute symbol reference) into its `.data` segment, but no `GP4` — so no GOT is created. The linker emits `ER4` entries in the output for each location whose patched value is an absolute address, so an OS loader can fix them up at load time.

```sh
./linker.py tests/testcase25/main.lk tests/testcase25/other.lk --byteorder big
```

## Test 26 — Static shared library, directory-format stub, no external deps (Project 9.1)
Creates a shared library from `add.lk` (defines `add`, `sub`) and `mul.lk` (defines `mul`), allocated at base address `0x5000`. Produces `lib/libmath.sso` (the shared library) and `stublib/libmath.sso/` (a directory-format stub). The stub's `add`, `sub`, and `mul` entries are all hard links to the same data-trimmed copy of the shared library (segments without `P` flag, absolute symbol values, no data bytes).

```sh
./librarian.py --format file --output build/libmath.pds tests/testcase26/{add,mul}.lk
./linker.py build/libmath.pds --shared --base-addr 0x5000 \
    --output build/lib/libmath.sso \
    --stub-format directory --stub-output build/stublib/libmath.sso
```

## Test 27 — Static shared library with cross-library dependency, directory-format stub (Project 9.1)
Creates a shared library from `printf.lk` (defines `printf`, references external `write`) and `sprintf.lk` (defines `sprintf`), linked against the directory-format input stub `libio.sso` which provides `write=0x3000`. The `LIBRARY NAME` file in the output stub records both `libprint.sso` and `libio.sso`, so downstream linkers know the dependency chain. The `printf` and `sprintf` stub entries are hard links to the same data-trimmed `libprint.sso`.

```sh
./librarian.py --output build/libprint.pds tests/testcase27/{printf,sprintf}.lk
./linker.py build/libprint.pds tests/testcase27/libio.sso --shared --base-addr 0x8000 \
    --byteorder big --output build/lib/libprint.sso \
    --stub-format directory --stub-output build/stublib/libprint.sso
```

## Test 28 — Static shared library, file-format stub, no external deps (Project 9.1)
Same modules as Test 26 (`add.lk`, `mul.lk`), same shared library output. The difference is that the stub is a single-file archive (`--stub-format file`). The file contains one module — the data-trimmed shared library — and a directory entry listing all three symbols (`add`, `sub`, `mul`) pointing to that module.

```sh
./librarian.py --output build/libmath.pds tests/testcase28/{add,mul}.lk
./linker.py build/libmath.pds --shared --base-addr 0x5000 \
    --output build/lib/libmath.sso \
    --stub-format file --stub-output build/stublib/libmath.sso
```

## Test 29 — Static shared library using file-format input stub, file-format output stub (Project 9.1)
Same modules as Test 27, but `libio.sso` is a file-format input stub. Produces a file-format output stub `libprint.sso` whose header names both `libprint.sso` and `libio.sso` as the dependency chain. The stub contains one module (the data-trimmed shared library) with both `printf` and `sprintf` in its directory entry.

```sh
./librarian.py --output build/libprint.pds tests/testcase29/{printf,sprintf}.lk
./linker.py build/libprint.pds tests/testcase29/libio.sso --shared --base-addr 0x8000 \
    --byteorder big --output build/lib/libprint.sso \
    --stub-format file --stub-output build/stublib/libprint.sso
```
