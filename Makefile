LINKER_NAME=linker.py
LINK_CMD=./$(LINKER_NAME)

LIBRARIAN_NAME=librarian.py
LIB_CMD=./$(LIBRARIAN_NAME)

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

BUILD_DIR=build
OUT=$(BUILD_DIR)/a.out.lk

.PHONY: all
all: test1 test2 test3 test4 test5 test6 test7 test8

test1: TEST_DIR=tests/testcase1
test1: clean
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 1 passed$(RESET)" || echo "$(RED)Test 1 failed$(RESET)"

test2: TEST_DIR=tests/testcase2
test2: clean
	# Test 2 for project 4.1: simple UNIX-style storage allocation
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,california,massachusetts,newyork}.lk --output $(OUT) --skip-symbols --skip-relocations --skip-data \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 2 passed$(RESET)" || echo "$(RED)Test 2 failed$(RESET)"

test3: TEST_DIR=tests/testcase3
test3: clean
	# Test 3 for project 4.2: UNIX-style common blocks
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,california,massachusetts,newyork}.lk --output $(OUT) --skip-symbols --skip-relocations --skip-data --common \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 3 passed$(RESET)" || echo "$(RED)Test 3 failed$(RESET)"

test4: TEST_DIR=tests/testcase4
test4: clean
	# Test 4 for project 4.3: Arbitrary segments
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,california,massachusetts,newyork}.lk --output $(OUT) --skip-symbols --skip-relocations --skip-data --common \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 4 passed$(RESET)" || echo "$(RED)Test 4 failed$(RESET)"

test5: TEST_DIR=tests/testcase5
test5: clean
	# Test 5 for project 5.1: Symbol name resolution
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main,calif}.lk --output $(OUT) --skip-relocations --skip-data --common \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 5 passed$(RESET)" || echo "$(RED)Test 5 failed$(RESET)"

test6: TEST_DIR=tests/testcase6
test6: clean
	# Test 6 for project 6.1: Create directory format library
	mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --output $(BUILD_DIR)/lib.lk $(TEST_DIR)/{foo,bar}.lk \
		&& diff -r $(BUILD_DIR)/lib.lk $(TEST_DIR)/cmp \
		&& [ $$(stat -f %i $(BUILD_DIR)/lib.lk/foo) -eq $$(stat -f %i $(BUILD_DIR)/lib.lk/helper) ] \
		&& echo "$(GREEN)Test 6 passed$(RESET)" || echo "$(RED)Test 6 failed$(RESET)"

test7: TEST_DIR=tests/testcase7
test7: clean
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
	mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libprintf.lk $(TEST_DIR)/{printf,sprintf}.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libfmt.lk $(TEST_DIR)/{format_str,format_int}.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libstr.lk $(TEST_DIR)/{strlen,strchr}.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libunistd.lk $(TEST_DIR)/unistd.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/liberrno.lk $(TEST_DIR)/{errno,strerror}.lk \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(BUILD_DIR)/lib{printf,fmt,str,unistd,errno}.lk --output $(OUT) \
		&& diff -U 1 $(OUT) $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 7 passed$(RESET)" || echo "$(RED)Test 7 failed$(RESET)"

test8: TEST_DIR=tests/testcase8
test8: clean
	# Test 8 for project 6.3: Create file format library
	mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --format file --output $(BUILD_DIR)/lib.lk $(TEST_DIR)/{foo,bar}.lk \
		&& diff -U 1 $(BUILD_DIR)/lib.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 8 passed$(RESET)" || echo "$(RED)Test 8 failed$(RESET)"

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)
