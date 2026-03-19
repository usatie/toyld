LINKER_NAME=linker.py
LINK_CMD=./$(LINKER_NAME)

LIBRARIAN_NAME=librarian.py
LIB_CMD=./$(LIBRARIAN_NAME)

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

BUILD_DIR=build

.PHONY: all
all: test1 test2 test3 test4 test5 test6 test7

test1: TEST_DIR=tests/testcase1
test1: clean
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk --output $(BUILD_DIR)/a.out.lk \
		&& diff -U 1 $(BUILD_DIR)/a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 1 passed$(RESET)" || echo "$(RED)Test 1 failed$(RESET)"

test2: TEST_DIR=tests/testcase2
test2: clean
	# Test 2 for project 4.1: simple UNIX-style storage allocation
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} --output $(BUILD_DIR)/a.out.lk --skip-symbols --skip-relocations --skip-data \
		&& diff -U 1 $(BUILD_DIR)/a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 2 passed$(RESET)" || echo "$(RED)Test 2 failed$(RESET)"

test3: TEST_DIR=tests/testcase3
test3: clean
	# Test 3 for project 4.2: UNIX-style common blocks
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} --output $(BUILD_DIR)/a.out.lk --skip-symbols --skip-relocations --skip-data --common \
		&& diff -U 1 $(BUILD_DIR)/a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 3 passed$(RESET)" || echo "$(RED)Test 3 failed$(RESET)"

test4: TEST_DIR=tests/testcase4
test4: clean
	# Test 4 for project 4.3: Arbitrary segments
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} --output $(BUILD_DIR)/a.out.lk --skip-symbols --skip-relocations --skip-data --common \
		&& diff -U 1 $(BUILD_DIR)/a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 4 passed$(RESET)" || echo "$(RED)Test 4 failed$(RESET)"

test5: TEST_DIR=tests/testcase5
test5: clean
	# Test 5 for project 5.1: Symbol name resolution
	mkdir -p $(BUILD_DIR) \
		&& $(LINK_CMD) $(TEST_DIR)/{main.lk,calif.lk} --output $(BUILD_DIR)/a.out.lk --skip-relocations --skip-data --common \
		&& diff -U 1 $(BUILD_DIR)/a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 5 passed$(RESET)" || echo "$(RED)Test 5 failed$(RESET)"

test6: TEST_DIR=tests/testcase6
test6: clean
	# Test 6 for project 6.1: Create directory format library
	mkdir -p $(BUILD_DIR) \
		&& $(LIB_CMD) --output $(BUILD_DIR)/lib.lk $(TEST_DIR)/foo.lk $(TEST_DIR)/bar.lk \
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
		&& $(LIB_CMD) --output $(BUILD_DIR)/libprintf.lk $(TEST_DIR)/printf.lk $(TEST_DIR)/sprintf.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libfmt.lk $(TEST_DIR)/format_str.lk $(TEST_DIR)/format_int.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libstr.lk $(TEST_DIR)/strlen.lk $(TEST_DIR)/strchr.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/libunistd.lk $(TEST_DIR)/unistd.lk \
		&& $(LIB_CMD) --output $(BUILD_DIR)/liberrno.lk $(TEST_DIR)/errno.lk $(TEST_DIR)/strerror.lk \
		&& $(LINK_CMD) $(TEST_DIR)/main.lk $(BUILD_DIR)/libprintf.lk $(BUILD_DIR)/libfmt.lk $(BUILD_DIR)/libstr.lk $(BUILD_DIR)/libunistd.lk $(BUILD_DIR)/liberrno.lk --output $(BUILD_DIR)/a.out.lk \
		&& diff -U 1 $(BUILD_DIR)/a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 7 passed$(RESET)" || echo "$(RED)Test 7 failed$(RESET)"

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)
