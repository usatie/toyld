# Linkers & Loaders — Project Code

Source: [linker.iecc.com](https://linker.iecc.com/)
Book: *Linkers and Loaders* by John R. Levine (Morgan-Kaufmann, 1999)

## Files

| File | Description |
|------|-------------|
| `readobj.pl` | Library: read/write object files (`.lk` format) |
| `linkproj03.pl` | Project 3-1: read an object file and write it back out |
| `linkproj04-1.pl` | Project 4-1: simple UNIX-style storage allocation (.text/.data/.bss) |
| `linkproj04-2.pl` | Project 4-2: Unix-style common blocks |
| `linkproj04-3.pl` | Project 4-3: arbitrary segments with attributes |
| `ch4main.lk` | Sample object file: main module |
| `ch4calif.lk` | Sample object file: California |
| `ch4mass.lk` | Sample object file: Massachusetts |
| `ch4newyork.lk` | Sample object file: New York |

## Running

All scripts require `readobj.pl` to be in the include path. Run with `-I.`:

```sh
# Project 3-1: read and write
perl -I. linkproj03.pl ch4main.lk

# Project 4-1: link multiple object files
perl -I. linkproj04-1.pl ch4main.lk ch4calif.lk ch4mass.lk ch4newyork.lk

# Project 4-2
perl -I. linkproj04-2.pl ch4main.lk ch4calif.lk ch4mass.lk ch4newyork.lk

# Project 4-3
perl -I. linkproj04-3.pl ch4main.lk ch4calif.lk ch4mass.lk ch4newyork.lk
```
