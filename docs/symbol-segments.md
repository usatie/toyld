# Defined-Symbol Segment Numbers: Absolute vs. Segment-Relative

The object file format encodes a defined symbol as either:

- `<name> <value> 0 D` — **absolute**: `value` is a final address; nothing slides at load time.
- `<name> <value> N D` (N ≥ 1) — **segment-relative**: `value` is the symbol's **offset within segment `N`**. At load time the loader resolves the symbol to `runtime_base_of_segment_N + value`; the link-time base of segment `N` (in the segment table) is irrelevant to consumers.

Both forms appear in this project's outputs. The choice depends on **whether the symbol table is consumed by a dynamic linker that needs to relocate the symbol at load time.**

## The rule

A defined symbol must be **segment-relative** (seg ≥ 1) if and only if it is **exported to a dynamic linker** that resolves cross-binary references at load time.

In our format, that condition is met by exactly one kind of output: a **dynamic shared library** (`LINKLIB ...` header, written by `--shared --dynamic`). Every other output uses `seg = 0` for defined symbols.

## Why "exported to a dynamic linker" is the discriminator

A segment number on a defined symbol is only useful to a *consumer* who needs to slide that symbol when the binary is loaded at a different base. Walking through every output kind:

| Output | Who reads the defined-symbol table? | Sliding needed? | Seg form |
|---|---|---|---|
| Static executable | Nobody (loader uses a fixed entry-point convention) | No | `seg = 0` |
| Static shared library (`.sso`) | The linker, at *link* time, when this lib is a dependency. VAs are already final. | No | `seg = 0` |
| Self-contained PIC executable (uses GOT + ER4) | Nobody. ER4 carries all load-time fix-ups; the symbol table is metadata. | No (irrelevant) | `seg = 0` |
| **Dynamic shared library** (`.dso`) | **Another binary's dynamic linker, at load time, to satisfy `AS4`/`RS4` against an exported symbol.** | **Yes** | **`seg ≥ 1`** |
| Dynamic executable / PIE | Nobody. The executable imports symbols (those are `U` with `seg = 0`); its own defined symbols are not looked up by anyone. | No | `seg = 0` |

Even a PIE binary that genuinely slides at load time keeps `seg = 0` for its defined symbols, because nothing reads them dynamically. The fact that the binary slides is encoded in `ER4` records (and in the `LINK <deps>` header that tells the loader to invoke the dynamic linker), not in the symbol table.

## Worked examples

**Static executable** (testcase 5, 10–25, 30–33). Self-contained, possibly PIC with a GOT and `ER4` records — but no exported symbols.

```
main 1000 0 D    ← seg 0 even though .text might slide via ER4
gfunc 1010 0 D
```

**Static shared library** (testcase 26–29). Linked at a fixed base (e.g. `0x5000`); consumers link against this lib at *link* time, not load time.

```
add 5000 0 D    ← seg 0; absolute address is final
```

**Dynamic shared library** (testcase 34, 35). The dynamic linker of any consumer must slide these exports.

```
add 0 1 D    ← seg 1: "offset 0 within .text"
sub 4 1 D    ← seg 1: "offset 4 within .text"
mul 8 1 D    ← seg 1: "offset 8 within .text"
```

The segment table records each segment's link-time base (e.g. `.text 1000 c RP`), but the symbol's `value` is independent of that base — it is just the byte offset from the start of the segment. A consumer's loader places segment `N` at some runtime address and adds `value` to obtain the final symbol address; the link-time base in the producing `.dso` plays no role.

**Dynamic-linked executable / PIE** (testcase 36, 37). The binary itself uses dynamic libraries, but exports nothing dynamically.

```
main 1000 0 D    ← seg 0; same convention as static executables
add 0 0 U        ← seg 0 (undefined import; resolved by name, not segment)
```

## Undefined symbols

Undefined symbols (`U`) are always `seg = 0`. They have no segment to be relative to — the dynamic or static linker resolves them by name and patches the importing relocation. The segment of the *defining* binary's matching export is what governs sliding, not anything on the import side.
