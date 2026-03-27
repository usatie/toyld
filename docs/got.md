# Chapter 8 Project — GOT and Position-Independent Code

## Background: Why PIC?

A normal executable is linked assuming a **fixed load address**. This works fine for standalone programs, but shared libraries (`.so`) may be mapped at different addresses in different processes. If absolute addresses are embedded in the code, every load requires rewriting the code itself — preventing it from being shared across processes.

Position-Independent Code (PIC) solves this by **never embedding absolute addresses directly in code**. Instead, all address references go through a level of indirection.

---

## The Global Offset Table (GOT)

The GOT is a linker-generated data segment that acts as a runtime address table.

```
Code (never modified after load)
  │
  │  PC-relative offset (fixed at link time)
  ▼
GOT (one copy per process, filled at load time)
  │
  │  absolute address (filled by OS loader or dynamic linker)
  ▼
Target (function, variable, data)
```

**Key properties:**

- The GOT is placed **immediately before the `.data` segment** by the linker.
- The distance from any code location to the GOT is a **fixed PC-relative offset** — it does not change regardless of where the executable is loaded.
- Each entry in the GOT is a 4-byte absolute address slot, filled at load time.

---

## The 4 New Relocation Types

Each relocation entry still follows the same format as before:

```
loc seg ref type
```

---

### 1. GA4 — GOT Address (4 bytes)

**Description:** Write the distance from the current location (`seg:loc`) to the beginning of the GOT into the 4 bytes at `loc`. This allows code to find the GOT at runtime using a PC-relative computation.

| Field | Role |
|-------|------|
| `loc` | Offset within segment `seg` where the distance is written |
| `seg` | Segment containing `loc` (typically `.text`) |
| `ref` | **Unused** |

**Formula:**
```
mem[loc] = GOT_base - (seg.start + loc)
```

**Example:**

```
GA4 entry:  10 1 - GA4
.text starts at 0x1000, GOT starts at 0x3000

mem[0x10] = 0x3000 - (0x1000 + 0x10) = 0x1FF0
```

**Typical use:** The first step in any GOT-relative access. Code loads this value into a register to obtain the GOT's absolute address at runtime:

```asm
call  __get_pc       ; get current PC into EBX
add   ebx, <GA4>     ; EBX now points to GOT base
```

---

### 2. GP4 — GOT Pointer (4 bytes)

**Description:** Allocate a slot in the GOT for symbol `ref` (if not already allocated), and write that slot's **offset from the GOT base** into the 4 bytes at `loc`.

| Field | Role |
|-------|------|
| `loc` | Offset within segment `seg` where the GOT-slot offset is written |
| `seg` | Segment containing `loc` (typically `.text`) |
| `ref` | **Symbol number** of the target (e.g., an external function or variable) |

**Formula:**
```
mem[loc] = GOT_offset(symbol[ref])
// GOT_offset is the byte offset of the symbol's slot from GOT base
// The slot itself is filled at load time by the dynamic linker
```

**Example:**

Symbol table:
```
printf  0000  0  U   (symbol number 2, undefined)
```

GP4 entry:
```
20 1 2 GP4
```

Linker allocates `printf` at GOT offset `0x8`:
```
mem[0x20] = 0x8
```

At load time, the dynamic linker fills `GOT[0x8]` with the absolute address of `printf`.

At runtime, code accesses `printf` as:
```
EBX (GOT base) + mem[0x20] (= 0x8)  →  absolute address of printf
```

**Typical use:** Accessing **external symbols** (functions or variables defined in shared libraries). This is the PIC equivalent of AS4.

> **Note:** GP4 has two effects: it causes a GOT slot to be **created** (first pass), and it causes the GOT-relative offset to be **written to `loc`** (second pass). The symbol remains `U` (undefined) in the output — the dynamic linker resolves it at load time.

---

### 3. GR4 — GOT Relative (4 bytes)

**Description:** The 4 bytes at `loc` currently hold an address within segment `ref` (as a segment-relative offset). Replace that value with the **offset from the GOT base to that address**.

| Field | Role |
|-------|------|
| `loc` | Offset within segment `seg` where the replacement is written |
| `seg` | Segment containing `loc` (typically `.data`) |
| `ref` | **Segment number** that the address at `loc` currently points into |

**Formula:**
```
target_address = segment[ref].start + mem[loc]
mem[loc] = target_address - GOT_base
```

**Example:**

```
.text starts at 0x1000
GOT  starts at 0x3000
.data starts at 0x3100

GR4 entry:  4 3 1 GR4
```

Meaning: "At offset `0x4` in segment 3 (`.data`), there is an address in segment 1 (`.text`). Replace it with its GOT-relative offset."

If `mem[0x4]` currently holds `0x50` (an offset into `.text`):
```
target_address = 0x1000 + 0x50 = 0x1050
mem[0x4] = 0x1050 - 0x3000 = -0x1FB0  (stored as signed 32-bit)
```

**Typical use:** Accessing **local data** (within the same executable) via GOT-relative addressing. Unlike GP4, no new GOT slot is allocated — the target address is a known offset computable at link time.

> **GP4 vs GR4:**
> - GP4: target is an **external symbol** resolved at load time → GOT slot allocated, dynamic linker fills it
> - GR4: target is a **local address** known at link time → no GOT slot, offset computed directly

---

### 4. ER4 — Executable Relative (4 bytes)

**Description:** The 4 bytes at `loc` hold an address relative to the beginning of the executable. This entry is **carried through to the output file as-is** — the OS loader will patch it at load time by adding the actual load base address.

| Field | Role |
|-------|------|
| `loc` | Offset within segment `seg` where the absolute address will be written at load time |
| `seg` | Segment containing `loc` |
| `ref` | **Unused** |

**Formula (performed by OS loader, not the linker):**
```
mem[loc] += load_base_address
```

**Example:**

```
.text starts at 0x1000; foo is at 0x1010, bar is at 0x1020.
.data segment contains a function pointer table:
  offset 0x00: address of foo  (= 0x1010, address relative to beginning of executable)
  offset 0x04: address of bar  (= 0x1020, address relative to beginning of executable)

ER4 entries in output:
  0 2 - ER4
  4 2 - ER4
```

At load time, if the executable is loaded at `0x7f000000`:
```
mem[0x00] = 0x1010 + 0x7f000000 = 0x7f001010
mem[0x04] = 0x1020 + 0x7f000000 = 0x7f001020
```

**Typical use:** Any data location that holds an absolute address and cannot be expressed as a GOT-relative reference — most commonly **function pointer tables** and **data-to-data pointers** initialized at compile time.

**Source of ER4 entries:** Every `A4` or `AS4` relocation entry in the input becomes an `ER4` entry in the output. Additionally, the GOT itself may contain absolute addresses that require ER4 entries (see note below).

> **Don't forget the GOT.** GOT slots filled with absolute addresses at load time also require ER4 entries in the output, so the OS loader knows to patch them.

---

## Summary Table

| Type | Size | `ref` targets | GOT slot? | Value written to `loc` | Who resolves | Typical use |
|------|------|---------------|-----------|------------------------|--------------|-------------|
| GA4  | 4 bytes | *(unused)* | No | Distance from `loc` to GOT base | Linker | Code locating the GOT |
| GP4  | 4 bytes | Symbol | **Yes** (allocated) | GOT-slot offset from GOT base | Dynamic linker (at load time) | External symbol access |
| GR4  | 4 bytes | Segment | No | GOT-relative offset of local address | Linker | Local data access via GOT |
| ER4  | 4 bytes | *(unused)* | No | Passed through; loader adds base | OS loader (at load time) | Embedded absolute addresses |

---

## Two-Pass Implementation

### Pass 1 — Build the GOT

Scan all input files for `GP4` entries only.

```
for each GP4 entry:
    if symbol[ref] not yet in GOT:
        allocate a new 4-byte slot in the GOT
        record: symbol[ref] → GOT offset

GOT size is now known.
```

Assign segment addresses in this order:
```
[ .text  ]
[ GOT    ]  ← immediately before .data
[ .data  ]
[ .bss   ]
```

### Pass 2 — Apply Relocations

Process all four new relocation types:

```
GA4:  mem[loc] = GOT_base - (segment[seg].start + loc)

GP4:  mem[loc] = GOT_offset(symbol[ref])
      // also: emit symbol[ref] as U in output symbol table

GR4:  target = segment[ref].start + mem[loc]
      mem[loc] = target - GOT_base

ER4 (input A4/AS4 → output ER4):
      mem[loc] = address relative to beginning of executable  (written by the linker)
      carry loc/seg through to the output relocation table    (OS loader will add load base)
```

### Output Relocation Table

The output file must contain `ER4` entries for every location that requires load-time patching:

1. Every `A4` / `AS4` entry in the input.
2. Every GOT slot (each slot holds an absolute address filled by the dynamic linker).

---

## Relationship to Existing Relocation Types

| Input type | PIC handling |
|------------|--------------|
| `A4`  | Becomes `ER4` in output (absolute address, needs load-time patch) |
| `AS4` | Becomes `ER4` in output (same reason) |
| `R4`  | No change needed (already PC-relative, position-independent) |
| `RS4` | No change needed (same) |
| `GP4` | New: external symbol via GOT |
| `GR4` | New: local address via GOT-relative offset |
| `GA4` | New: code locating GOT base |
| `ER4` | New: output-only, consumed by OS loader |
