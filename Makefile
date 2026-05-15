SHELL=/bin/bash

LINK_CMD=python3 -m toyld.linker
LIB_CMD=python3 -m toyld.librarian
SYMWRAP_CMD=python3 -m toyld.symwrap

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

BUILD_DIR=build
OUT=$(BUILD_DIR)/a.out.lk

.PHONY: all
all:
	@passed=0; total=37; \
	for t in $$(seq 1 37); do \
		$(MAKE) --no-print-directory -s test$$t >/dev/null 2>&1; \
		if [ $$? -eq 0 ]; then \
			passed=$$((passed+1)); \
			printf "$(GREEN)Test %2d passed$(RESET)\n" $$t; \
		else \
			printf "$(RED)Test %2d FAILED$(RESET)\n" $$t; \
		fi; \
	done; \
	printf "\n"; \
	if [ $$passed -eq $$total ]; then \
		printf "$(GREEN)$$passed/$$total tests passed$(RESET)\n"; \
	else \
		printf "$(RED)$$passed/$$total tests passed$(RESET)\n"; \
	fi

.PHONY: ci
ci:
	# Run all tests verbosely; print output for each; exit non-zero if any failed
	@passed=0; failed=0; total=37; \
	for t in $$(seq 1 37); do \
		printf "=== Test $$t ===\n"; \
		$(MAKE) --no-print-directory test$$t 2>&1; \
		if [ $$? -eq 0 ]; then \
			passed=$$((passed+1)); \
		else \
			failed=$$((failed+1)); \
		fi; \
		printf "\n"; \
	done; \
	printf "=== Summary ===\n"; \
	if [ $$failed -eq 0 ]; then \
		printf "$(GREEN)$$passed/$$total tests passed$(RESET)\n"; \
	else \
		printf "$(RED)$$passed/$$total tests passed, $$failed failed$(RESET)\n"; \
		exit 1; \
	fi

test1: TEST_DIR=tests/testcase1
test1:
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 1 passed$(RESET)""\n" || { printf "$(RED)Test 1 failed$(RESET)""\n"; false; }

test2: TEST_DIR=tests/testcase2
test2:
	# Test 2 for project 4.1: simple UNIX-style storage allocation
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,california,massachusetts,newyork}.lk --output $(OUT) --skip-symbols --skip-relocations --skip-data \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 2 passed$(RESET)""\n" || { printf "$(RED)Test 2 failed$(RESET)""\n"; false; }

test3: TEST_DIR=tests/testcase3
test3:
	# Test 3 for project 4.2: UNIX-style common blocks
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,california,massachusetts,newyork}.lk --output $(OUT) --skip-symbols --skip-relocations --skip-data \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 3 passed$(RESET)""\n" || { printf "$(RED)Test 3 failed$(RESET)""\n"; false; }

test4: TEST_DIR=tests/testcase4
test4:
	# Test 4 for project 4.3: Arbitrary segments
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,california,massachusetts,newyork}.lk --output $(OUT) --skip-symbols --skip-relocations --skip-data \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 4 passed$(RESET)""\n" || { printf "$(RED)Test 4 failed$(RESET)""\n"; false; }

test5: TEST_DIR=tests/testcase5
test5:
	# Test 5 for project 5.1: Symbol name resolution
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,calif}.lk --output $(OUT) --skip-relocations --skip-data \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 5 passed$(RESET)""\n" || { printf "$(RED)Test 5 failed$(RESET)""\n"; false; }

test6: TEST_DIR=tests/testcase6
test6:
	# Test 6 for project 6.1: Create directory format library
	# stat inode flag differs by platform: -c %i on Linux, -f %i on macOS; || fallback handles both
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libfoo.pds $(TEST_DIR)/{foo,bar}.lk \
		&& diff -r $(BUILD_DIR)/libfoo.pds $(TEST_DIR)/cmp \
		&& [ $$(stat -c %i $(BUILD_DIR)/libfoo.pds/foo 2>/dev/null || stat -f %i $(BUILD_DIR)/libfoo.pds/foo) -eq $$(stat -c %i $(BUILD_DIR)/libfoo.pds/helper 2>/dev/null || stat -f %i $(BUILD_DIR)/libfoo.pds/helper) ] \
		&& printf "$(GREEN)Test 6 passed$(RESET)""\n" || { printf "$(RED)Test 6 failed$(RESET)""\n"; false; }

test7: TEST_DIR=tests/testcase7
test7:
	# Test 7 for project 6.2: Link main.lk against five independent directory-format
	# libraries. The linker must search libraries recursively across a multi-level chain:
	#   main needs printf, sprintf             (libprintf)
	#   printf needs format_str, write, errno  (libfmt, libunistd, liberrno)
	#   sprintf needs format_str, strlen       (libfmt, libstr)
	#   format_str needs strlen                (libstr)
	# libprintf:  printf + sprintf         (both loaded — main needs both)
	# libfmt:     format_str + format_int  (only format_str loaded)
	# libstr:     strlen + strchr          (only strlen loaded)
	# libunistd:  write + read             (write loaded by printf; read comes along for free)
	# liberrno:   errno + strerror         (only errno loaded)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libprintf.pds $(TEST_DIR)/{printf,sprintf}.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libfmt.pds $(TEST_DIR)/{format_str,format_int}.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libstr.pds $(TEST_DIR)/{strlen,strchr}.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libunistd.pds $(TEST_DIR)/unistd.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/liberrno.pds $(TEST_DIR)/{errno,strerror}.lk \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(BUILD_DIR)/lib{printf,fmt,str,unistd,errno}.pds --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 7 passed$(RESET)""\n" || { printf "$(RED)Test 7 failed$(RESET)""\n"; false; }

test8: TEST_DIR=tests/testcase8
test8:
	# Test 8 for project 6.3: Create file format library
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/libfoo.a $(TEST_DIR)/{foo,bar}.lk \
		&& diff -U 1 $(BUILD_DIR)/libfoo.a $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 8 passed$(RESET)""\n" || { printf "$(RED)Test 8 failed$(RESET)""\n"; false; }

test9: SRC_DIR=tests/testcase7
test9: CMP_DIR=tests/testcase9
test9:
	# Test 9 for project 6.4: Link main.lk against five file-format libraries.
	# Same dependency graph as test 7, but libraries are single-file archives
	# instead of directories. The linker must detect LIBRARY header and seek to
	# each module's offset to load it on demand.
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/libprintf.a $(SRC_DIR)/{printf,sprintf}.lk \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/libfmt.a $(SRC_DIR)/{format_str,format_int}.lk \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/libstr.a $(SRC_DIR)/{strlen,strchr}.lk \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/libunistd.a $(SRC_DIR)/unistd.lk \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/liberrno.a $(SRC_DIR)/{errno,strerror}.lk \
		&& $(LINK_CMD) $(SRC_DIR)/main.lk $(BUILD_DIR)/lib{printf,fmt,str,unistd,errno}.a --output $(OUT) \
		&& diff -U 1 $(OUT) $(CMP_DIR)/cmp \
		&& printf "$(GREEN)Test 9 passed$(RESET)""\n" || { printf "$(RED)Test 9 failed$(RESET)""\n"; false; }

test10: TEST_DIR=tests/testcase10
test10:
	# Test 10 for project 7.1: A4 relocation — absolute segment reference
	#
	# Summary of the test case:
	#
	# ┌──────────┬───────────────────────────────────────────┬──────────┬─────────┐
	# │   File   │                   .text                   │  .data   │  .bss   │
	# ├──────────┼───────────────────────────────────────────┼──────────┼─────────┤
	# │ main.lk  │ 8 bytes — dummy instructions              │ 16 bytes │ 8 bytes │
	# ├──────────┼───────────────────────────────────────────┼──────────┼─────────┤
	# │ other.lk │ 4 bytes                                   │  4 bytes │ 4 bytes │
	# └──────────┴───────────────────────────────────────────┴──────────┴─────────┘
	#
	# main.lk: A4 relocation (6 2 3 A4) writes the base address of main.lk's
	# .bss (segment 3) into the pointer slot at offset 6 of .data.
	# After storage allocation, main.lk's .bss lands at 0x2014.
	#
	# other.lk: A4 relocation (0 2 3 A4) writes the base address of other.lk's
	# .bss (segment 3) into the pointer slot at offset 0 of .data.
	# other.lk's .bss lands at 0x201c (after main.lk's 8-byte .bss).
	#
	# The expected merged output data:
	# - .text: 0011223344556677|deadbeef
	# - .data: aaaaaaaaaaaa|00002014|bbbbbbbbbbbb|0000201c
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big --skip-relocation \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 10 passed$(RESET)""\n" || { printf "$(RED)Test 10 failed$(RESET)""\n"; false; }

test11: TEST_DIR=tests/testcase11
test11:
	# Test 11 for project 7.1: R4 relocation — PC-relative segment reference
	#
	# Summary of the test case:
	#
	# ┌──────────┬───────────────────────────────────────────┬──────────┬─────────┐
	# │   File   │                   .text                   │  .data   │  .bss   │
	# ├──────────┼───────────────────────────────────────────┼──────────┼─────────┤
	# │ main.lk  │ 8 bytes — 4B instr + 4B R4-patched slot   │  4 bytes │ 8 bytes │
	# ├──────────┼───────────────────────────────────────────┼──────────┼─────────┤
	# │ other.lk │ 8 bytes — 4B instr + 4B R4-patched slot   │  4 bytes │ 4 bytes │
	# └──────────┴───────────────────────────────────────────┴──────────┴─────────┘
	#
	# main.lk: R4 relocation (4 1 2 R4) patches the call slot at offset 4 of
	# .text with the PC-relative offset to main.lk's .data (segment 2).
	# After storage allocation, main.lk's .text is at 0x1000 and .data is at 0x2000.
	# value = 0x2000 - (0x1000 + 4 + 4) = 0xff8
	#
	# other.lk: R4 relocation (4 1 2 R4) patches the call slot at offset 4 of
	# .text with the PC-relative offset to other.lk's .data (segment 2).
	# After storage allocation, other.lk's .text is at 0x1008 and .data is at 0x2004.
	# value = 0x2004 - (0x1008 + 4 + 4) = 0xff4
	#
	# The expected merged output data:
	# - .text: deadbeef|00000ff8|aabbccdd|00000ff4
	# - .data: cafebabe|11223344
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 11 passed$(RESET)""\n" || { printf "$(RED)Test 11 failed$(RESET)""\n"; false; }

test12: TEST_DIR=tests/testcase12
test12:
	# Test 12 for project 7.1: AS4 relocation — absolute symbol reference
	#
	# Summary of the test case:
	#
	# ┌──────────┬─────────────────────────────────────────────────────────┬──────────────────┬──────────┐
	# │   File   │                        .text (16B)                      │    .data (8B)    │  .bss    │
	# ├──────────┼─────────────────────────────────────────────────────────┼──────────────────┼──────────┤
	# │ main.lk  │ 4B body | 4B AS4 fn-ptr | 4B sep | 4B AS4 arr-ptr       │ arr[0] | arr[1]  │  (none)  │
	# ├──────────┼─────────────────────────────────────────────────────────┼──────────────────┼──────────┤
	# │ other.lk │ 4B body | 4B AS4 fn-ptr | 4B sep | 4B AS4 struct-ptr    │  (none)          │  8B (s)  │
	# └──────────┴─────────────────────────────────────────────────────────┴──────────────────┴──────────┘
	#
	# 'arr' is an initialized global in .data (2 int members, member1 at offset 4).
	# 's' is an uninitialized global in .bss (2 int members, member1 at offset 4).
	#
	# main.lk: two AS4 relocations in .text —
	#   (4 1 3 AS4) patches .text[4:8] with absolute address of 'helper' (zero addend).
	#   After allocation, helper is at 0x1010, so mem[4..7] = 00001010.
	#
	#   (c 1 2 AS4) patches .text[12:16] with &arr[1] = arr_base + addend 4.
	#   After allocation, arr is at 0x2000, so mem[12..15] = 0x2000+4 = 00002004.
	#
	# other.lk: two AS4 relocations in .text —
	#   (4 1 3 AS4) patches .text[20:24] with absolute address of 'main' (zero addend).
	#   After allocation, main is at 0x1000, so mem[20..23] = 00001000.
	#
	#   (c 1 2 AS4) patches .text[28:32] with &s.member1 = s_base + addend 4.
	#   After allocation, s is at 0x2008 (start of .bss), so mem[28..31] = 0x2008+4 = 0000200c.
	#
	# The expected merged output data:
	# - .text: deadbeef|00001010|aabbccdd|00002004|11223344|00001000|aabbccdd|0000200c
	# - .data: deadbeef|cafebabe
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big --skip-relocation \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 12 passed$(RESET)""\n" || { printf "$(RED)Test 12 failed$(RESET)""\n"; false; }

test13: TEST_DIR=tests/testcase13
test13:
	# Test 13 for project 7.1: RS4 relocation — PC-relative symbol reference
	# Covers RS4 targeting symbols in .text, .data, and .bss.
	#
	# Summary of the test case:
	#
	# ┌──────────┬───────────────────────────────────────────────────────────────┬──────────┬──────────┐
	# │   File   │                        .text (24B)                            │  .data   │   .bss   │
	# ├──────────┼───────────────────────────────────────────────────────────────┼──────────┼──────────┤
	# │ main.lk  │ 4B body | 4B RS4→helper | 4B | 4B RS4→gvar | 4B | 4B RS4→gbuf │ (none)   │  (none)  │
	# ├──────────┼───────────────────────────────────────────────────────────────┼──────────┼──────────┤
	# │ other.lk │ 4B body | 4B RS4→main                                         │  4B gvar │  4B gbuf │
	# └──────────┴───────────────────────────────────────────────────────────────┴──────────┴──────────┘
	#
	# After allocation: main=0x1000, helper=0x1018, gvar=0x2000, gbuf=0x2004
	#
	# main.lk RS4 relocations in .text —
	#   (4  1 2 RS4) → helper(.text): 0x1018 - (0x1004+4) = 0x10   (forward call)
	#   (c  1 3 RS4) → gvar(.data):   0x2000 - (0x100c+4) = 0xff0  (RIP-relative to data)
	#   (14 1 4 RS4) → gbuf(.bss):    0x2004 - (0x1014+4) = 0xfec  (RIP-relative to bss)
	#
	# other.lk RS4 relocation in .text —
	#   (4 1 4 RS4) → main(.text): 0x1000 - (0x101c+4) = 0xffffffe0 (backward call)
	#
	# The expected merged output data:
	# - .text: deadbeef|00000010|cafebabe|00000ff0|aabbccdd|00000fec|11223344|ffffffe0
	# - .data: 05060708
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 13 passed$(RESET)""\n" || { printf "$(RED)Test 13 failed$(RESET)""\n"; false; }

test14: TEST_DIR=tests/testcase14
test14:
	# Test 14 for project 7.1: U2 relocation — upper 16-bit symbol address.
	# main.lk's artificially large .bss (0x1cd43674 bytes, no file data) acts as
	# padding to push other.lk's .bss to a high address with a visually clear
	# non-trivial upper half. Big-endian 2-byte write assumed throughout.
	#
	# ┌──────────┬──────────────────┬──────────┬──────────────────────┐
	# │   File   │      .text       │  .data   │        .bss          │
	# ├──────────┼──────────────────┼──────────┼──────────────────────┤
	# │ main.lk  │ 8B (U2 slot @4)  │  (none)  │ 0x1cd43674B padding  │
	# ├──────────┼──────────────────┼──────────┼──────────────────────┤
	# │ other.lk │ 4B body          │  4B      │ 4B (gbss here)       │
	# └──────────┴──────────────────┴──────────┴──────────────────────┘
	#
	# After allocation: gbss = 0x2004 + 0x1cd43674 = 0x1cd45678
	#
	# main.lk relocation in .text —
	#   (4 1 2 U2) → upper 16 of gbss (big-endian): (0x1cd45678 >> 16) & 0xffff = 0x1cd4
	#
	# The expected merged output data:
	# - .text: cafebabe|1cd4|beef|11223344
	# - .data: 05060708
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 14 passed$(RESET)""\n" || { printf "$(RED)Test 14 failed$(RESET)""\n"; false; }

test15: TEST_DIR=tests/testcase15
test15:
	# Test 15 for project 7.1: L2 relocation — lower 16-bit symbol address.
	# Mirror of test 14: same structure, but writes the lower half of the address.
	# Big-endian 2-byte write assumed throughout.
	#
	# ┌──────────┬──────────────────┬──────────┬──────────────────────┐
	# │   File   │      .text       │  .data   │        .bss          │
	# ├──────────┼──────────────────┼──────────┼──────────────────────┤
	# │ main.lk  │ 8B (L2 slot @6)  │  (none)  │ 0x1cd43674B padding  │
	# ├──────────┼──────────────────┼──────────┼──────────────────────┤
	# │ other.lk │ 4B body          │  4B      │ 4B (gbss here)       │
	# └──────────┴──────────────────┴──────────┴──────────────────────┘
	#
	# After allocation: gbss = 0x2004 + 0x1cd43674 = 0x1cd45678
	#
	# main.lk relocation in .text —
	#   (6 1 2 L2) → lower 16 of gbss (big-endian): 0x1cd45678 & 0xffff = 0x5678
	#
	# The expected merged output data:
	# - .text: cafebabe|dead|5678|11223344
	# - .data: 05060708
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 15 passed$(RESET)""\n" || { printf "$(RED)Test 15 failed$(RESET)""\n"; false; }

test16: TEST_DIR=tests/testcase16
test16:
	# Test 16 for project 7.1: combined test exercising all 6 relocation types in one link.
	# main.lk has 6 relocations in .text targeting segments and symbols from both files.
	# other.lk defines helper (.text), gvar (.data), and gbuf (.bss) — no relocations.
	# main.lk's large .bss padding (0xfe00 bytes) pushes gbuf to 0x11e08,
	# giving U2 a non-trivial upper half (0x0001) and L2 a non-trivial lower half (0x1e08).
	#
	# ┌──────────┬──────────────────────────────────────────────────────────────┬──────────┬────────────────────┐
	# │   File   │                        .text (0x1c B)                        │  .data   │       .bss         │
	# ├──────────┼──────────────────────────────────────────────────────────────┼──────────┼────────────────────┤
	# │ main.lk  │ 4B body | A4 | R4 | AS4 | RS4 | U2(2B) | L2(2B) | 4B tail  │  4B data │ 0xfe00B padding    │
	# ├──────────┼──────────────────────────────────────────────────────────────┼──────────┼────────────────────┤
	# │ other.lk │ 4B body (helper)                                             │  4B gvar │ 4B (gbuf)          │
	# └──────────┴──────────────────────────────────────────────────────────────┴──────────┴────────────────────┘
	#
	# After allocation:
	#   main=0x1000, helper=0x101c, gvar=0x2004, gbuf=0x11e08
	#
	# main.lk relocations in .text —
	#   (4  1 2 A4 ) → base(.data):          0x2000                           = 00002000
	#   (8  1 3 R4 ) → .bss rel:             0x2008 - (0x1008+4) = 0x0ffc    = 00000ffc
	#   (c  1 2 AS4) → helper abs:           0x101c + 0          = 0x101c    = 0000101c
	#   (10 1 3 RS4) → gvar rel:             0x2004 - (0x1010+4) = 0x0ff0    = 00000ff0
	#   (14 1 4 U2 ) → upper 16 of gbuf:     0x11e08 >> 16       = 0x0001    = 0001
	#   (16 1 4 L2 ) → lower 16 of gbuf:     0x11e08 & 0xffff    = 0x1e08    = 1e08
	#
	# The expected merged output data:
	# - .text: 11223344|00002000|00000ffc|0000101c|00000ff0|0001|1e08|aabbccdd|55667788
	# - .data: deadbeef|99aabbcc
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big --skip-relocation \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 16 passed$(RESET)""\n" || { printf "$(RED)Test 16 failed$(RESET)""\n"; false; }

test17: TEST_DIR=tests/testcase17
test17:
	# Test 17 for project 7.2: same structure as test 16, but all relocations written little-endian.
	# Identical input files; only the expected byte order in the output differs.
	#
	# ┌──────────┬──────────────────────────────────────────────────────────────┬──────────┬────────────────────┐
	# │   File   │                        .text (0x1c B)                        │  .data   │       .bss         │
	# ├──────────┼──────────────────────────────────────────────────────────────┼──────────┼────────────────────┤
	# │ main.lk  │ 4B body | A4 | R4 | AS4 | RS4 | U2(2B) | L2(2B) | 4B tail  │  4B data │ 0xfe00B padding    │
	# ├──────────┼──────────────────────────────────────────────────────────────┼──────────┼────────────────────┤
	# │ other.lk │ 4B body (helper)                                             │  4B gvar │ 4B (gbuf)          │
	# └──────────┴──────────────────────────────────────────────────────────────┴──────────┴────────────────────┘
	#
	# After allocation:
	#   main=0x1000, helper=0x101c, gvar=0x2004, gbuf=0x11e08
	#
	# main.lk relocations in .text (values identical to test 16, but stored little-endian) —
	#   (4  1 2 A4 ) → 0x2000    → LE: 00200000
	#   (8  1 3 R4 ) → 0x0ffc    → LE: fc0f0000
	#   (c  1 2 AS4) → 0x101c    → LE: 1c100000
	#   (10 1 3 RS4) → 0x0ff0    → LE: f00f0000
	#   (14 1 4 U2 ) → 0x0001    → LE: 0100
	#   (16 1 4 L2 ) → 0x1e08    → LE: 081e
	#
	# The expected merged output data:
	# - .text: 11223344|00200000|fc0f0000|1c100000|f00f0000|0100|081e|aabbccdd|55667788
	# - .data: deadbeef|99aabbcc
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --skip-relocation \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 17 passed$(RESET)""\n" || { printf "$(RED)Test 17 failed$(RESET)""\n"; false; }

test18: TEST_DIR=tests/testcase18
test18:
	# Test 18 for project 8.1: --wrap option wraps malloc
	#
	# Three input files exercise all wrap cases with both RS4 and AS4 relocations:
	#   main.lk        — RS4 call + AS4 fn-ptr to malloc (undefined); both redirected to wrap_malloc
	#   malloc.lk      — defines malloc; RS4 self-call + AS4 self-ptr; all redirected to wrap_malloc
	#                    malloc itself renamed to real_malloc
	#   wrap_malloc.lk — defines wrap_malloc; RS4 call to real_malloc
	#
	# ┌────────────────┬──────────────────────────────┬──────────────────────────────┐
	# │     File       │       .text (8B/12B)         │       .data (8B)             │
	# ├────────────────┼──────────────────────────────┼──────────────────────────────┤
	# │ main.lk        │ body | RS4 call → malloc     │ data | AS4 fn-ptr → malloc   │
	# ├────────────────┼──────────────────────────────┼──────────────────────────────┤
	# │ malloc.lk      │ body | RS4 self-call→mallc   │ data | AS4 self-ptr → malloc │
	# ├────────────────┼──────────────────────────────┼──────────────────────────────┤
	# │ wrap_malloc.lk │ body | RS4 call → real_malloc│           (none)             │
	# └────────────────┴──────────────────────────────┴──────────────────────────────┘
	#
	# After -w malloc and allocation:
	#   main        = 0x1000  (.text[0x1000..0x1007],  8B)
	#   real_malloc = 0x1008  (.text[0x1008..0x1013], 12B, malloc.lk renamed)
	#   wrap_malloc = 0x1014  (.text[0x1014..0x101b],  8B)
	#   .data: main.lk at 0x2000, malloc.lk at 0x2008
	#
	# RS4 patches (big-endian):
	#   main.lk .text[4]       → wrap_malloc(0x1014) - (0x1004+4) = 0xc    → 0000000c
	#   malloc.lk .text[4]     → wrap_malloc(0x1014) - (0x100c+4) = 0x4    → 00000004
	#   wrap_malloc.lk .text[4]→ real_malloc(0x1008) - (0x1018+4) = -0x14  → ffffffec
	#
	# AS4 patches (big-endian):
	#   main.lk .data[4]       → wrap_malloc(0x1014) + 0 = 0x1014           → 00001014
	#   malloc.lk .data[4]     → wrap_malloc(0x1014) + 0 = 0x1014           → 00001014
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/malloc.lk $(TEST_DIR)/wrap_malloc.lk --output $(OUT) --byteorder big -w malloc --skip-relocation \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 18 passed$(RESET)""\n" || { printf "$(RED)Test 18 failed$(RESET)""\n"; false; }

test19: SRC_DIR=tests/testcase19
test19: CMP_DIR=tests/testcase19
test19:
	# Test 19 for project 8.1: --wrap option with a directory-format library
	#
	# Same three-module wrap scenario as test 18, but malloc.lk is loaded from a
	# directory library instead of being a direct object file.  The linker must
	# apply wrap semantics to the library module after pulling it in.
	#
	# Input files in tests/testcase19/:
	#   main.lk        — 12B .text (body|RS4 call→malloc|tail), 8B .data (body|AS4 fn-ptr→malloc)
	#   wrap_malloc.lk — 12B .text (body|RS4 call→real_malloc|tail)
	#   libmalloc.pds/ — directory library containing malloc.lk (same as testcase18)
	#                    malloc (D) → renamed real_malloc; wrap_malloc added as U
	#
	# After -w malloc and allocation:
	#   main        = 0x1000  (12B .text)
	#   wrap_malloc = 0x100c  (12B .text, direct object)
	#   real_malloc = 0x1018  (12B .text, loaded from library)
	#   .data: main.lk at 0x2000, malloc.lk at 0x2008
	#
	# RS4 patches (big-endian):
	#   main.lk .text[4]        → wrap_malloc(0x100c) - (0x1004+4) =  0x4    → 00000004
	#   wrap_malloc.lk .text[4] → real_malloc(0x1018) - (0x1010+4) =  0x4    → 00000004
	#   malloc.lk .text[4]      → wrap_malloc(0x100c) - (0x101c+4) = -0x14   → ffffffec
	#
	# AS4 patches (big-endian):
	#   main.lk .data[4]   → wrap_malloc(0x100c) → 0000100c
	#   malloc.lk .data[4] → wrap_malloc(0x100c) → 0000100c
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libmalloc.pds $(SRC_DIR)/malloc.lk \
		&& $(LINK_CMD) $(SRC_DIR)/main.lk $(SRC_DIR)/wrap_malloc.lk $(BUILD_DIR)/libmalloc.pds --output $(OUT) --byteorder big -w malloc --skip-relocation \
		&& diff -U 1 $(OUT) $(CMP_DIR)/cmp \
		&& printf "$(GREEN)Test 19 passed$(RESET)""\n" || { printf "$(RED)Test 19 failed$(RESET)""\n"; false; }

test20: SRC_DIR=tests/testcase19
test20: CMP_DIR=tests/testcase20
test20:
	# Test 20 for project 8.1: --wrap option with a file-format library
	#
	# Mirror of test 19 using a single-file archive instead of a directory library.
	# The linker must seek to the module's offset inside the archive, load malloc.lk,
	# and apply the same wrap semantics.  Expected output is identical to test 19.
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/libmalloc.a $(SRC_DIR)/malloc.lk \
		&& $(LINK_CMD) $(SRC_DIR)/main.lk $(SRC_DIR)/wrap_malloc.lk $(BUILD_DIR)/libmalloc.a --output $(OUT) --byteorder big -w malloc --skip-relocation \
		&& diff -U 1 $(OUT) $(CMP_DIR)/cmp \
		&& printf "$(GREEN)Test 20 passed$(RESET)""\n" || { printf "$(RED)Test 20 failed$(RESET)""\n"; false; }

test21: TEST_DIR=tests/testcase21
test21:
	# Test 21 for project 8.2: Standalone symbol wrapper program for object files
	#
	# caller.lk defines main and has an undefined reference to malloc (AS4 reloc).
	# impl.lk defines malloc.
	#
	# After --wrap malloc:
	#   caller.lk: malloc (U) → wrap_malloc (U)   — reloc ref unchanged, header correct
	#   impl.lk:   malloc (D) → wrap_malloc (U) + real_malloc (D) — num_symbols must be 2
	#
	# wrapped_caller.lk: num_symbols stays 2 (main + wrap_malloc), reloc still refs sym 2
	# wrapped_impl.lk:   num_symbols must be updated to 2 (wrap_malloc U + real_malloc D)
	rm -rf $(BUILD_DIR)/symwrap && mkdir -p $(BUILD_DIR)/symwrap \
		&& $(SYMWRAP_CMD) --wrap malloc $(TEST_DIR)/caller.lk $(TEST_DIR)/impl.lk -o $(BUILD_DIR)/symwrap \
		&& diff -r $(BUILD_DIR)/symwrap $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 21 passed$(RESET)""\n" || { printf "$(RED)Test 21 failed$(RESET)""\n"; false; }

test22: TEST_DIR=tests/testcase22
test22:
	# Test 22 for project 8.3: GP4 — GOT pointer relocation
	#
	# main.lk references two external symbols (gfunc in .text, gvar in .data) via GP4.
	# The linker builds a 2-entry GOT and stores each symbol's GOT-relative offset at
	# the relocation site.  Both GOT entries contain absolute addresses → two ER4 entries
	# in the output.
	#
	# After allocation:
	#   .text: 0x1000 (main.lk 0x10 + other.lk 0x8 = 0x18 bytes)
	#   .got:  0x2000 (8 bytes: GOT[0]=gfunc abs=0x1010, GOT[1]=gvar abs=0x2008)
	#   .data: 0x2008 (other.lk 4 bytes)
	#
	# GP4 patches:
	#   main.lk .text[4] → GOT offset of gfunc = 0 → 00000000
	#   main.lk .text[c] → GOT offset of gvar  = 4 → 00000004
	#
	# ER4 output (loc = segment-relative offset, seg = segment number, ref unused = 0):
	#   0 2 0 ER4  (GOT[0] at .got offset 0, address relative to beginning of executable: gfunc=0x1010)
	#   4 2 0 ER4  (GOT[1] at .got offset 4, address relative to beginning of executable: gvar=0x2008)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 22 passed$(RESET)""\n" || { printf "$(RED)Test 22 failed$(RESET)""\n"; false; }

test23: TEST_DIR=tests/testcase23
test23:
	# Test 23 for project 8.3: GA4 — distance to GOT
	#
	# main.lk uses GA4 to store the PC-relative distance to the GOT at offset 4 in
	# .text, and GP4 to get the GOT-relative offset of an external variable gvar.
	#
	# After allocation:
	#   .text: 0x1000 (main.lk 0x10 bytes only)
	#   .got:  0x2000 (4 bytes: GOT[0]=gvar abs=0x2004)
	#   .data: 0x2004 (other.lk 4 bytes)
	#
	# GA4 patch at .text[4]:
	#   mem[4] = GOT_base - (seg.start + loc) = 0x2000 - (0x1000 + 4) = 0xffc → 00000ffc
	#
	# GP4 patch at .text[c]:
	#   GOT offset of gvar = 0 → 00000000
	#
	# ER4 output (loc = segment-relative offset, seg = segment number, ref unused = 0):
	#   0 2 0 ER4  (GOT[0] at .got offset 0, address relative to beginning of executable: gvar=0x2004)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 23 passed$(RESET)""\n" || { printf "$(RED)Test 23 failed$(RESET)""\n"; false; }

test24: TEST_DIR=tests/testcase24
test24:
	# Test 24 for project 8.3: GR4 — GOT-relative segment address with non-zero offset
	#
	# main.lk uses GR4 to compute the GOT-relative address of .bss[0x1234] (offset=0x1234),
	# and GP4 to reference an external symbol gext (which creates the GOT).
	#
	# After allocation:
	#   .text: 0x1000 (main.lk 8 bytes only)
	#   .got:  0x2000 (4 bytes: GOT[0]=gext abs=0x200c)
	#   .data: 0x2004 (main.lk 8 bytes + other.lk 4 bytes = 0xc bytes)
	#   .bss:  0x2010 (main.lk 0x1238 bytes)
	#
	# GP4 patch at .text[4]:
	#   GOT offset of gext = 0 → 00000000
	#
	# GR4 patch at .data[0] (ref = main.lk .bss, offset = 0x1234):
	#   mem[0] = base(.bss) + 0x1234 - GOT_base = 0x2010 + 0x1234 - 0x2000 = 0x1244 → 00001244
	#
	# ER4 output (loc = segment-relative offset, seg = segment number, ref unused = 0):
	#   0 2 0 ER4  (GOT[0] at .got offset 0, address relative to beginning of executable: gext=0x200c)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 24 passed$(RESET)""\n" || { printf "$(RED)Test 24 failed$(RESET)""\n"; false; }

test25: TEST_DIR=tests/testcase25
test25:
	# Test 25 for project 8.3: ER4 output from A4/AS4 inputs
	#
	# main.lk has an A4 (absolute segment ref) and an AS4 (absolute symbol ref) into
	# its .data segment.  No GP4 → no GOT.  The linker must emit ER4 relocations in the
	# output for every location whose final value is an absolute address, so that a
	# loader can fix them up if the file is mapped at a non-nominal address.
	#
	# After allocation:
	#   .text: 0x1000 (main.lk 8 + other.lk 8 = 0x10 bytes)
	#   .data: 0x2000 (main.lk 8 bytes)
	#
	# A4 patch at .data[0] (ref = seg 1 = .text):
	#   mem[0] = absolute address of .text = 0x1000 → 00001000
	#
	# AS4 patch at .data[4] (ref = sym func, addend = 0):
	#   mem[4] = absolute address of func = 0x1008 → 00001008
	#
	# ER4 output (loc = segment-relative offset, seg = segment number, ref unused = 0):
	#   0 2 0 ER4  (.data offset 0, absolute value 0x1000)
	#   4 2 0 ER4  (.data offset 4, absolute value 0x1008)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/other.lk --output $(OUT) --byteorder big \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 25 passed$(RESET)""\n" || { printf "$(RED)Test 25 failed$(RESET)""\n"; false; }

test26: TEST_DIR=tests/testcase26
test26:
	# Test 26 for project 9.1: Create shared library (directory format, no external deps)
	#
	# add.lk: defines add (text[0..3]) and sub (text[4..7]); total 8 bytes of .text
	# mul.lk: defines mul; total 4 bytes of .text
	#
	# Linked at --base-addr 0x5000 (all text starts at 0x5000):
	#   add.lk .text → 0x5000 (8 bytes): add=0x5000, sub=0x5004
	#   mul.lk .text → 0x5008 (4 bytes): mul=0x5008
	#
	# Shared library output (lib/libmath.sso): one .text segment, 3 absolute symbols.
	#
	# Stub library (stublib/libmath.sso, directory format):
	#   LIBRARY NAME  → "libmath.sso\n"
	#   add, sub      → hard-linked stub for add.lk:  { add 5000 D, sub 5004 D }
	#   mul           → stub for mul.lk:               { mul 5008 D }
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR)/lib $(BUILD_DIR)/stublib \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libmath.pds $(TEST_DIR)/{add,mul}.lk --format file \
		&& $(LINK_CMD) $(BUILD_DIR)/libmath.pds --shared --base-addr 0x5000 \
		   --stub-format directory --stub-output $(BUILD_DIR)/stublib/libmath.sso \
		   --output $(BUILD_DIR)/lib/libmath.sso \
		&& diff -U 1 $(BUILD_DIR)/lib/libmath.sso $(TEST_DIR)/cmp/lib/libmath.sso \
		&& diff -r $(BUILD_DIR)/stublib/libmath.sso $(TEST_DIR)/cmp/stublib/libmath.sso \
		&& [ $$(stat -c %i $(BUILD_DIR)/stublib/libmath.sso/add 2>/dev/null || stat -f %i $(BUILD_DIR)/stublib/libmath.sso/add) \
		     -eq $$(stat -c %i $(BUILD_DIR)/stublib/libmath.sso/sub 2>/dev/null || stat -f %i $(BUILD_DIR)/stublib/libmath.sso/sub) ] \
		&& printf "$(GREEN)Test 26 passed$(RESET)\n" || { printf "$(RED)Test 26 failed$(RESET)\n"; false; }

test27: TEST_DIR=tests/testcase27
test27:
	# Test 27 for project 9.1: Create shared library with external shared-library dependency
	#
	# printf.lk: defines printf (.text 8B), imports write (U) via AS4 relocation at .text[4]
	# sprintf.lk: defines sprintf (.text 4B), no external refs
	# libio.sso: directory-format input stub; provides write=0x3000 from libio.sso
	#
	# Linked at --base-addr 0x8000 (big-endian) with libio stub:
	#   printf.lk .text → 0x8000 (8 bytes): printf=0x8000
	#   sprintf.lk .text → 0x8008 (4 bytes): sprintf=0x8008
	#   AS4 reloc in printf.lk: .text[4:8] ← write=0x3000 → 00003000
	#
	# Shared library output (lib/libprint.sso): printf and sprintf only; write not exported.
	#
	# Stub (stublib/libprint.sso, directory format):
	#   LIBRARY NAME  → "libprint.sso\nlibio.sso\n"  (libio.sso listed as dependency)
	#   printf        → data-trimmed libprint.sso: { .text 8000 c R, printf 8000 D, sprintf 8008 D }
	#   sprintf       → data-trimmed libprint.sso: (same content, hard-linked)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR)/lib $(BUILD_DIR)/stublib \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libprint.pds $(TEST_DIR)/{printf,sprintf}.lk \
		&& $(LINK_CMD) $(BUILD_DIR)/libprint.pds $(TEST_DIR)/libio.sso --shared --base-addr 0x8000 \
		   --stub-format directory --stub-output $(BUILD_DIR)/stublib/libprint.sso \
		   --output $(BUILD_DIR)/lib/libprint.sso --byteorder big \
		&& diff -U 1 $(BUILD_DIR)/lib/libprint.sso $(TEST_DIR)/cmp/lib/libprint.sso \
		&& diff -r $(BUILD_DIR)/stublib/libprint.sso $(TEST_DIR)/cmp/stublib/libprint.sso \
		&& printf "$(GREEN)Test 27 passed$(RESET)\n" || { printf "$(RED)Test 27 failed$(RESET)\n"; false; }

test28: TEST_DIR=tests/testcase28
test28:
	# Test 28 for project 9.1: Create shared library + file-format stub (no external deps)
	#
	# Same modules as test 26 (add.lk, mul.lk), same shared library output.
	# Key difference: stub output is a single file-format archive (stublib/libmath.sso).
	#
	# File-format stub layout (libmath.sso):
	#   Header:   LIBRARY 1 79 libmath.sso  (25 bytes = 0x19)
	#   Module 1: data-trimmed libmath.sso at 0x19  (96 bytes = 0x60): { .text 5000 c R, .data 6000 0 RW, .bss 6000 0 RW, add 5000 D, sub 5004 D, mul 5008 D }
	#   Directory at 0x79:
	#     19 60 add sub mul
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR)/lib $(BUILD_DIR)/stublib \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libmath.pds $(TEST_DIR)/{add,mul}.lk \
		&& $(LINK_CMD) $(BUILD_DIR)/libmath.pds --shared --base-addr 0x5000 \
		   --stub-format file --stub-output $(BUILD_DIR)/stublib/libmath.sso \
		   --output $(BUILD_DIR)/lib/libmath.sso \
		&& diff -U 1 $(BUILD_DIR)/lib/libmath.sso $(TEST_DIR)/cmp/lib/libmath.sso \
		&& diff -U 1 $(BUILD_DIR)/stublib/libmath.sso $(TEST_DIR)/cmp/stublib/libmath.sso \
		&& printf "$(GREEN)Test 28 passed$(RESET)\n" || { printf "$(RED)Test 28 failed$(RESET)\n"; false; }

test29: TEST_DIR=tests/testcase29
test29:
	# Test 29 for project 9.1: Create shared library using a file-format input stub,
	# and produce a file-format output stub that records the cross-library dependency.
	#
	# printf.lk: defines printf (.text 8B), imports write via AS4 reloc at .text[4]
	# sprintf.lk: defines sprintf (.text 4B), no external refs
	# libio.sso: file-format input stub; provides write=0x3000 from libio.sso
	#   Header: LIBRARY 1 5f libio.sso  (23 bytes = 0x17)
	#   Module 1: write stub at 0x17   (72 bytes = 0x48): { .text 3000 4 R, .data 4000 0 RW, .bss 4000 0 RW, write 3000 D }
	#   Directory at 0x5f: 17 48 write
	#
	# Linked at --base-addr 0x8000 (big-endian):
	#   printf.lk .text → 0x8000: printf=0x8000; AS4 patch → write(0x3000) → 00003000
	#   sprintf.lk .text → 0x8008: sprintf=0x8008
	#
	# File-format output stub (stublib/libprint.sso):
	#   Header:   LIBRARY 1 7e libprint.sso libio.sso  (36 bytes = 0x24)
	#   Module 1: data-trimmed libprint.sso at 0x24   (90 bytes = 0x5a): { .text 8000 c R, .data 9000 0 RW, .bss 9000 0 RW, printf 8000 D, sprintf 8008 D }
	#   Directory at 0x7e:
	#     24 5a printf sprintf
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR)/lib $(BUILD_DIR)/stublib \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libprint.pds $(TEST_DIR)/{printf,sprintf}.lk \
		&& $(LINK_CMD) $(BUILD_DIR)/libprint.pds $(TEST_DIR)/libio.sso --shared --base-addr 0x8000 \
		   --stub-format file --stub-output $(BUILD_DIR)/stublib/libprint.sso \
		   --output $(BUILD_DIR)/lib/libprint.sso --byteorder big \
		&& diff -U 1 $(BUILD_DIR)/lib/libprint.sso $(TEST_DIR)/cmp/lib/libprint.sso \
		&& diff -U 1 $(BUILD_DIR)/stublib/libprint.sso $(TEST_DIR)/cmp/stublib/libprint.sso \
		&& printf "$(GREEN)Test 29 passed$(RESET)\n" || { printf "$(RED)Test 29 failed$(RESET)\n"; false; }

test30: TEST_DIR=tests/testcase30
test30:
	# Test 30 for project 9.2: Link executable against directory-format stub (single library, no deps)
	#
	# main.lk: defines main (.text 12B), imports add (GP4@4) and sub (AS4@8)
	# libmath.sso: directory-format stub; no deps; add=0x5000, sub=0x5004, mul=0x5008
	#
	# Linked at 0x1000 (big-endian):
	#   .text 0x1000 12B: GP4→add (GOT offset 0→00000000), AS4→sub (0x5004→00005004)
	#   .lib  0x100c 0xd B (RP, text group): "libmath.sso\0\0"
	#   .got  0x2000 4B: add=0x5000 → 00005000
	#   .data 0x2004 0B; .bss 0x2004 0B
	#   _SHARED_LIBRARIES = 0x100c; ER4: .got[0] (seg3), text[8] (seg1)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/libmath.sso --byteorder big --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 30 passed$(RESET)\n" || { printf "$(RED)Test 30 failed$(RESET)\n"; false; }

test31: TEST_DIR=tests/testcase31
test31:
	# Test 31 for project 9.2: Link executable against file-format stub (single library, no deps)
	#
	# Same as test 30 but libmath.sso is a single-file archive (LIBRARY header + one module).
	# libmath.sso: LIBRARY 1 79 libmath.sso; module at 0x19 (96 bytes); add, sub, mul in dir
	# Expected output is identical to test 30 (GP4→add, AS4→sub, .lib before .got).
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/libmath.sso --byteorder big --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 31 passed$(RESET)\n" || { printf "$(RED)Test 31 failed$(RESET)\n"; false; }

test32: TEST_DIR=tests/testcase32
test32:
	# Test 32 for project 9.2: Link executable against two stubs each with a cross-library dep
	#
	# main.lk: defines main (.text 12B), imports add (GP4@4) and printf (AS4@8)
	# libmath.sso (dir stub): add=0x5000, sub=0x5004, mul=0x5008; depends on libbase.sso
	# libprint.sso (dir stub): printf=0x8000, sprintf=0x8008; depends on libio.sso
	#
	# Linked at 0x1000 (big-endian):
	#   .text 0x1000 12B: GP4→add (GOT offset 0→00000000), AS4→printf (0x8000→00008000)
	#   .lib  0x100c 0x30B (RP, text group): "libmath.sso\0libbase.sso\0libprint.sso\0libio.sso\0\0"
	#     (names from each stub's LIBRARY NAME file, in symbol resolution order: add first, printf second)
	#   .got 0x2000 4B: add=0x5000 → 00005000
	#   .data 0x2004 0B; .bss 0x2004 0B
	#   _SHARED_LIBRARIES = 0x100c; ER4: .got[0] (seg3), text[8] (seg1)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/libmath.sso $(TEST_DIR)/libprint.sso --byteorder big --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 32 passed$(RESET)\n" || { printf "$(RED)Test 32 failed$(RESET)\n"; false; }

test33: TEST_DIR=tests/testcase33
test33:
	# Test 33 for project 9.2: Link executable against stub that has a transitive dep
	#
	# main.lk: defines main (.text 8B), imports printf (GP4@4)
	# libprint.sso (dir stub): printf=0x8000, sprintf=0x8008; depends on libio.sso
	#
	# Linked at 0x1000 (big-endian):
	#   .text 0x1000 8B: GP4→printf (GOT offset 0→00000000)
	#   .lib  0x1008 0x18B (RP, text group): "libprint.sso\0libio.sso\0\0"
	#   .got 0x2000 4B: printf=0x8000 → 00008000
	#   .data 0x2004 0B; .bss 0x2004 0B
	#   _SHARED_LIBRARIES = 0x1008; ER4: .got[0] (seg3)
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/libprint.sso --byteorder big --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 33 passed$(RESET)\n" || { printf "$(RED)Test 33 failed$(RESET)\n"; false; }

test34: TEST_DIR=tests/testcase34
test34:
	# Test 34 for project 10.1: Simplest dynamic shared library (no deps, no imports)
	#
	# add.lk: defines add, sub (.text 8B); mul.lk: defines mul (.text 4B). No relocations.
	#
	# Linked with --shared --dynamic at default base 0x1000:
	#   .text 0x1000 0xc B: add=0x1000, sub=0x1004, mul=0x1008
	#   .data 0x2000 0B; .bss 0x2000 0B
	#
	# Output libmath.dso: header "LINKLIB" (no deps), 3 defined symbols, 0 relocations.
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/add.lk $(TEST_DIR)/mul.lk --shared --dynamic --output $(BUILD_DIR)/libmath.dso \
		&& diff -U 1 $(BUILD_DIR)/libmath.dso $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 34 passed$(RESET)\n" || { printf "$(RED)Test 34 failed$(RESET)\n"; false; }

test35: TEST_DIR=tests/testcase35
test35:
	# Test 35 for project 10.1: Producer — dynamic shared library with imports + GOT + .data import + dep with own LINKLIB
	#
	# printf.lk: defines printf (.text 16B), imports write (AS4@4), log (GP4@8), stdout (GP4@c), errno (AS4 in .data[0])
	# libio.dso: fixture defining write/log/stdout/errno; has own header "LINKLIB libsys.dso" (libsys.dso NOT present)
	#
	# Linked with --shared --dynamic (default base 0x1000), big-endian:
	#   .text 0x1000 0x10B: GP4 sites patched to GOT-relative offsets (log→0, stdout→4) → no output relocs at .text[8], .text[c]
	#   .got  0x2000 8B: 2 slots (log, stdout) → AS4 at .got[0] (log), AS4 at .got[4] (stdout)
	#   .data 0x2008 4B: errno_ptr slot (binder fills) → AS4 at .data[0]
	#   .bss  0x200c 0B
	#
	# Output libprint.dso: header "LINKLIB libio.dso" (libsys.dso NOT propagated),
	# 5 symbols (printf D, write/log/stdout/errno U), 4 relocs (AS4×4).
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/printf.lk $(TEST_DIR)/libio.dso --shared --dynamic --byteorder big --output $(BUILD_DIR)/libprint.dso \
		&& diff -U 1 $(BUILD_DIR)/libprint.dso $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 35 passed$(RESET)\n" || { printf "$(RED)Test 35 failed$(RESET)\n"; false; }

test36: TEST_DIR=tests/testcase36
test36:
	# Test 36 for project 10.1: Consumer — simplest exe using one dynamic shared library
	#
	# main.lk: defines main (.text 8B), imports add via AS4@4 from libmath.dso
	# libmath.dso: fixture (same as test 34's expected output) defining add/sub/mul, no own deps
	#
	# Linked at default base 0x1000, big-endian:
	#   .text 0x1000 8B: AS4→add preserved (binder fills .text[4..7])
	#   .data 0x2000 0B; .bss 0x2000 0B
	#
	# Output a.out.lk: header "LINK libmath.dso", 2 symbols (main D, add U), 1 reloc (AS4).
	# No .lib segment, no _SHARED_LIBRARIES symbol (Project 10.1 drops both).
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/libmath.dso --byteorder big --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 36 passed$(RESET)\n" || { printf "$(RED)Test 36 failed$(RESET)\n"; false; }

test37: TEST_DIR=tests/testcase37
test37:
	# Test 37 for project 10.1: Consumer — exe with two deps; one dep has its own LINKLIB
	#
	# main.lk: defines main (.text 16B + .data 4B), imports add (AS4@4), printf (RS4@8), puts (GP4@c), errno (AS4 in .data[0])
	# libmath.dso: fixture (same as test 34 cmp) — defines add/sub/mul, no own deps
	# libprint.dso: fixture defining printf/puts/errno; has own header "LINKLIB libio.dso" (libio.dso NOT present)
	#
	# Linked at default base 0x1000, big-endian:
	#   .text 0x1000 0x10B: GP4→puts patched to GOT offset 0 (no output reloc at .text[c])
	#   .got  0x2000 4B: 1 slot for puts → AS4 at .got[0]
	#   .data 0x2004 4B: errno_ptr → AS4 at .data[0]
	#   .bss  0x2008 0B
	#
	# Output a.out.lk: header "LINK libmath.dso libprint.dso" (libio.dso NOT propagated),
	# 5 symbols (main D, others U), 4 relocs (AS4×3 + RS4×1).
	rm -rf $(BUILD_DIR) && mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(TEST_DIR)/libmath.dso $(TEST_DIR)/libprint.dso --byteorder big --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& printf "$(GREEN)Test 37 passed$(RESET)\n" || { printf "$(RED)Test 37 failed$(RESET)\n"; false; }

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)
