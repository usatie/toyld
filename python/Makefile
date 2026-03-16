.PHONY: all
all: test1

test1: clean
	# Test 1 for project 3.1: Compare the output of the linker with the expected output,
	python3 linker.py tests/testcase1/main.lk && diff -U 3 newobj tests/testcase1/cmp && echo "Test 1 passed" || echo "Test 1 failed"

.PHONY: clean
clean:
	rm -f newobj
