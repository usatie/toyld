LINKER_NAME=linker.py
LINK_CMD=./$(LINKER_NAME)

.PHONY: all
all: test1

test1: clean
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	$(LINK_CMD) tests/testcase1/main.lk && diff -U 3 newobj tests/testcase1/cmp && echo "Test 1 passed" || echo "Test 1 failed"


test2: clean
	# Test 2 for project 4.1: Compare the output of the linker with the expected output,
	$(LINK_CMD) tests/testcase2/{main.lk,california.lk,massachusetts.lk,newyork.lk} && diff -U 3 a.out.lk cmp && echo "Test 2 passed" || echo "Test 2 failed"


.PHONY: clean
clean:
	rm -f newobj
