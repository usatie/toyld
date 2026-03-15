NAME=linker
CC=gcc
CFLAGS=-Wall -Wextra -Werror

SRCS=$(wildcard *.c)
OBJS=$(SRCS:.c=.o)

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f $(OBJS)

test1:
	./$(NAME) main.lk
