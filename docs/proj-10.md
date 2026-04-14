# Project

It's impractical to build an entire dynamic linking system for our project linker, since much of the work of dynamic linking happens at runtime, not link time. Much of the work of building a shared library was already done in project 8-3 that created PIC executables. A dynamically linked shared library is just a PIC executable with a well-defined list of imported and exported symbols and a list of other libraries on which it depends. To mark the file as a shared library or an executable that uses shared libraries, the first line is:

```
LINKLIB lib1 lib2 ...
```

or

```
LINK lib1 lib2 ...
```

where the `lib`s are the names of other shared libraries on which this one depends.

## Project 10-1:

Starting with the version of the linker from project 8-3, extend the linker to produce shared libraries and executables that need shared libraries. The linker needs to take as its input a list of input files to combine into the output executable or library, as well as other shared libraries to search. The output file contains a symbol table with defined (exported) and undefined (imported) symbols. Relocation types are the ones for PIC files along with `AS4` and `RS4` for references to imported symbols.

## Project 10-2:

Write a run-time binder, that is, a program that takes an executable that uses shared libraries and resolves its references. It should read in the executable, then read in the necessary libraries, relocating them to non-overlapping available addresses, and creating a logically merged symbol table. (You may want to actually create such a table, or use a list of per-file tables as ELF does.) Then resolve all of the relocations and external references. When you're done, all code and data should be assigned memory addresses, and all addresses in the code and data should be resolved and relocated to the assigned addresses.
