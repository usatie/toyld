# Static Shared Libraries

The linker can produce a **static shared library** from a regular library input using `--shared`. A shared library is a fully linked object file (all symbols resolved, no outstanding relocations) allocated at a fixed base address. Its extension is `.sso` (shared static object).

```sh
./librarian.py --output libfoo.pds foo.lk bar.lk
./linker.py libfoo.pds --shared --base-addr 0x5000 \
    --output lib/libfoo.sso \
    --stub-format directory --stub-output stublib/libfoo.sso
```

Along with the shared library itself the linker writes a **stub library** — a directory-format or file-format library whose entries are data-trimmed copies of the shared library. Each entry has the same segment layout as the `.sso` (with the `P` flag removed from each segment) and all exported symbols at their absolute addresses, but no data bytes. All entries in the stub are hard links to the same content.

Stub libraries share the `.sso` extension with the shared library they describe but are placed in a separate directory (conventionally `stublib/`).

## Directory-Format Stub

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

## File-Format Stub

The stub is a single file. The header line has extra fields beyond the standard `LIBRARY <nmods> <diroff>`:

```
LIBRARY <nmods> <diroff> <libname> [<dep1> <dep2> ...]
```

`<libname>` is the name of the shared library this stub describes; subsequent fields are dependency library names. The rest of the format (module contents and directory) is identical to a regular file-format library, with one module per defined symbol group — in practice one module containing the data-trimmed shared library content, with all defined symbols listed in the directory entry.

## Project Background

See [proj-9.md](proj-9.md) for the original project specification from *Linkers and Loaders*.
