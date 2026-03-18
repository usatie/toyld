LINKER_NAME=linker.py
LINK_CMD=./$(LINKER_NAME)

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

.PHONY: all
LIBRARIAN_NAME=librarian.py
LIB_CMD=./$(LIBRARIAN_NAME)

all: test1 test2 test3 test4 test5 test6

test1: TEST_DIR=tests/testcase1
test1: clean
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	$(LINK_CMD) $(TEST_DIR)/main.lk \
		&& diff -U 1 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 1 passed$(RESET)" || echo "$(RED)Test 1 failed$(RESET)"


test2: TEST_DIR=tests/testcase2
test2: clean
	# Test 2 for project 4.1: simple UNIX-style storage allocation
	$(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} --skip-symbols --skip-relocations --skip-data \
		&& diff -U 1 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 2 passed$(RESET)" || echo "$(RED)Test 2 failed$(RESET)"

test3: TEST_DIR=tests/testcase3
test3: clean
	# Test 3 for project 4.2: UNIX-style common blocks
	$(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} --skip-symbols --skip-relocations --skip-data --common \
		&& diff -U 1 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 3 passed$(RESET)" || echo "$(RED)Test 3 failed$(RESET)"

test4: TEST_DIR=tests/testcase4
test4: clean
	# Test4 for project 4.3: Arbitrary segments
	$(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} --skip-symbols --skip-relocations --skip-data --common \
		&& diff -U 1 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 4 passed$(RESET)" || echo "$(RED)Test 4 failed$(RESET)"

test5: TEST_DIR=tests/testcase5
test5: clean
	# Test5 for project 5.1: Symbol name resolution
	$(LINK_CMD) $(TEST_DIR)/{main.lk,calif.lk} --skip-relocations --skip-data --common \
		&& diff -U 1 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 5 passed$(RESET)" || echo "$(RED)Test 5 failed$(RESET)"


test6: TEST_DIR=tests/testcase6
test6: clean
	# Test 6 for project 6.1: Create directory format library
	$(LIB_CMD) --output lib.lk $(TEST_DIR)/foo.lk $(TEST_DIR)/bar.lk \
		&& diff -r lib.lk $(TEST_DIR)/cmp \
		&& [ $$(stat -f %i lib.lk/foo) -eq $$(stat -f %i lib.lk/helper) ] \
		&& echo "$(GREEN)Test 6 passed$(RESET)" || echo "$(RED)Test 6 failed$(RESET)"


.PHONY: clean
clean:
	rm -f newobj a.out.lk
	rm -rf lib.lk
