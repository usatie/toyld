LINKER_NAME=linker.py
LINK_CMD=./$(LINKER_NAME)

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

.PHONY: all
all: test1 test2

test1: TEST_DIR=tests/testcase1
test1: clean
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	$(LINK_CMD) $(TEST_DIR)/main.lk \
		&& diff -U 3 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 1 passed$(RESET)" || echo "$(RED)Test 1 failed$(RESET)"


test2: TEST_DIR=tests/testcase2
test2: clean
	# Test 2 for project 4.1: Compare the output of the linker with the expected output,
	$(LINK_CMD) $(TEST_DIR)/{main.lk,california.lk,massachusetts.lk,newyork.lk} \
		&& diff -U 3 a.out.lk $(TEST_DIR)/cmp \
		&& echo "$(GREEN)Test 2 passed$(RESET)" || echo "$(RED)Test 2 failed$(RESET)"


.PHONY: clean
clean:
	rm -f newobj a.out.lk
