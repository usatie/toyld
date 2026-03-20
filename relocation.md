# Chapter 7 Project — Relocation

## Background: Object File Format (from Chapter 3)

Each relocation entry has the format:

```
loc seg ref type ...
```

| Field | Description |
|-------|-------------|
| `loc` | Offset within the segment where the relocation is applied |
| `seg` | Segment number that contains `loc` |
| `ref` | Target segment number **or** symbol number |
| `type` | Relocation type (see below) |

All numbers in the object file are hexadecimal.

---

## The 6 Relocation Types

---

### 1. A4 — Absolute (Segment) Reference (4 bytes)

**Description:** Write the absolute base address of segment `ref` into the 4 bytes at `loc`.

**Formula:**
```
mem[loc] = base_address(segment[ref])
```

**Example:**

Relocation entry:
```
10 1 2 A4
```
Meaning: "At offset `0x10` in segment 1, write the absolute address of segment 2."

If the linker places segment 2 at `0x4000`:
```
mem[0x10] = 0x00004000
```

**Typical use:** Embedding a pointer to a data segment in another data section.

---

### 2. R4 — Relative (Segment) Reference (4 bytes)

**Description:** Write a PC-relative offset to segment `ref` into the 4 bytes at `loc`. The offset is calculated from the address *after* the field (`loc + 4`), matching the x86 relative jump/call encoding.

**Formula:**
```
mem[loc] = base_address(segment[ref]) - (loc + 4)
```

**Example:**

Relocation entry:
```
100 1 2 R4
```
Meaning: "At offset `0x100` in segment 1, write a relative offset to segment 2."

If segment 2 is placed at `0x3000`:
```
mem[0x100] = 0x3000 - (0x100 + 4) = 0x2EFC
```

**Typical use:** x86 `CALL rel32` / `JMP rel32` instructions within the same file.

---

### 3. AS4 — Absolute Symbol Reference (4 bytes)

**Description:** `ref` is a **symbol number** (not a segment number). Write the absolute address of symbol `ref` plus the **addend** (the value already stored at `loc`) into the 4 bytes at `loc`. The addend is usually zero.

**Formula:**
```
mem[loc] = symbol_address[ref] + addend
// where addend = value currently stored at loc
```

**Example:**

Symbol table:
```
printf  0000  0  U   (symbol number 3, undefined)
```

Relocation entry:
```
200 1 3 AS4
```

If the linker resolves `printf` to `0x8000` and the existing value at `loc` is `0x0000`:
```
mem[0x200] = 0x8000 + 0 = 0x00008000
```

**Typical use:** Pointers to external functions or global variables.

---

### 4. RS4 — Relative Symbol Reference (4 bytes)

**Description:** The relative-offset counterpart to AS4. Compute the PC-relative offset from `loc + 4` to the symbol, adding the addend stored at `loc`.

**Formula:**
```
mem[loc] = symbol_address[ref] + addend - (loc + 4)
```

**Example:**

Relocation entry:
```
50 1 5 RS4
```
Addend at `loc` = `0x0` (zero).

If symbol 5 (`external_func`) resolves to `0x9000`:
```
mem[0x50] = 0x9000 + 0 - (0x50 + 4) = 0x9000 - 0x54 = 0x8FAC
```

**Typical use:** `CALL` / `JMP` to external symbols (e.g., functions defined in another object file).

> **A4/R4 vs AS4/RS4:** A4 and R4 reference a *segment*; AS4 and RS4 reference a named *symbol*, enabling cross-file resolution.

---

### 5. U2 — Upper Half Reference (2 bytes)

**Description:** Write the **most significant 16 bits** of the symbol's address into the 2 bytes at `loc`.

**Formula:**
```
mem[loc] (2 bytes) = (symbol_address[ref] >> 16) & 0xFFFF
```

**Example:**

RISC architectures (e.g., MIPS, PowerPC) encode a 32-bit address across two instructions because each immediate field is only 16 bits wide:

```asm
lui  $t0, %hi(foo)      ; U2 relocation — upper 16 bits
ori  $t0, $t0, %lo(foo) ; L2 relocation — lower 16 bits
```

If symbol `foo` is placed at `0x12345678`:
```
U2: mem[loc] = 0x1234
```

**Typical use:** Loading a 32-bit address on RISC architectures (upper half).

---

### 6. L2 — Lower Half Reference (2 bytes)

**Description:** Write the **least significant 16 bits** of the symbol's address into the 2 bytes at `loc`.

**Formula:**
```
mem[loc] (2 bytes) = symbol_address[ref] & 0xFFFF
```

**Example (continued from U2):**

```
L2: mem[loc] = 0x5678
```

Together, U2 and L2 reconstruct the full 32-bit address `0x12345678` across two instructions.

**Typical use:** Loading a 32-bit address on RISC architectures (lower half).

---

## Summary Table

| Type | Size   | `ref` targets | Value written          | Typical use                          |
|------|--------|---------------|------------------------|--------------------------------------|
| A4   | 4 bytes | Segment       | Absolute address       | Data pointer to a segment            |
| R4   | 4 bytes | Segment       | PC-relative offset     | `JMP`/`CALL` within the same file    |
| AS4  | 4 bytes | Symbol        | Absolute addr + addend | Pointer to an external variable      |
| RS4  | 4 bytes | Symbol        | PC-relative + addend   | `CALL`/`JMP` to an external function |
| U2   | 2 bytes | Symbol        | Upper 16 bits          | RISC upper-half immediate load       |
| L2   | 2 bytes | Symbol        | Lower 16 bits          | RISC lower-half immediate load       |

---

## Project 7.1

After the linker has built the symbol table and assigned final addresses to all segments and symbols, process the relocation entries in each input file.

**Key point:** Relocations operate on the **actual byte values** of the object data, not on the hexadecimal text representation. You need to treat segment data as binary when performing arithmetic, then convert back to hex for output.

---

## Project 7.2

Identify which endianness you assumed in Project 7.1, then modify the linker to support the **opposite** endianness.

- If you assumed **little-endian** (e.g., x86), rewrite to handle **big-endian** (e.g., MIPS, PowerPC), and vice versa.
- Endianness determines the byte order in which multi-byte values (U2, L2, A4, R4, AS4, RS4) are written into the object data.

**Little-endian example** — writing `0x00004000` at `loc`:
```
mem[loc+0] = 0x00
mem[loc+1] = 0x40
mem[loc+2] = 0x00
mem[loc+3] = 0x00
```

**Big-endian example** — writing `0x00004000` at `loc`:
```
mem[loc+0] = 0x00
mem[loc+1] = 0x00
mem[loc+2] = 0x40
mem[loc+3] = 0x00
```
