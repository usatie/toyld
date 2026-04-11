# Project
We’ll extend the linker to support static shared libraries. This involves several subprojects, first to create the shared libraries, and then to link exectables with the shared libraries.

A shared library in our system is merely an object file which is linked at a given address. There can be no relocations and no unresolved symbol references, although references to other shared libraries are OK. Stub libraries are normal directory-format or file-format libraries, with each entry in the library containing the exported (absolute) and imported symbols for the corresponding library member but no text or data. Each stub library has to tell the linker the name of the corresponding shared library. If you use directory format stub libraries, a file called "LIBRARY NAME" contains lines of text. The first line is the name of the corresponding shared library, and the rest of the lines are the names of other shared libraries upon which this one depends. (The space prevents name collisions with symbols.) If you use file format libraries, the initial line of the library has extra fields:

```
LIBRARY nnnn pppppp fffff ggggg hhhhh ...
```

where fffff is the name of the shared library and the subsequent fields are the names of any other shared libraries on which it depends.

## Project 9-1:
Make the linker produce static shared libraries and stub libraries from regular directory or file format libraries. If you haven’t already done so, you’ll have to add a linker flag to set the base address at which the linker allocates the segments. The input is a regular library, and stub libraries for any other shared libraries on which this one depends.  The output is an executable format shared library containing the segments of all of the members of the input library, and a stub library with a stub member corresponding to each member of the input library.

## Project 9-2:
Extend the linker to create executables using static shared libraries. Project 9-1 already has most of the work of searching stub libraries symbol resolution, since the way that an executable refers to symbols in a shared library is the same as the way that one shared library refers to another. The linker needs to put the names of the required libraries in the output file, so that the runtime loader knows what to load.  Have the linker create a segment called .lib that contains the names of the shared libraries as strings with a null byte separating the strings and two null bytes at the end. Create a symbol _SHARED_LIBRARIES that refers to the beginning of the .lib section to which code in the startup routine can refer.
