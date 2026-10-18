# Still needed for a verified native PDS *writer*

Reading is implemented (see `PDS-FORMAT.md`). Writing a file Optitex accepts needs more, and can only be verified by opening the result in Optitex. Please provide (each zipped, so the binary survives upload):
1. A minimal `.pds`: one 10×10 cm square piece, one size. Then the same file after ONE change each: rename the piece; add a notch; add a drill; add a grainline; change seam allowance; add a curve point; set quantity 2; add a second size.
2. A second *intact* multi-size file from the same Optitex version (the shirt file arrived corrupted), plus files from other Optitex versions you use.
3. After a writer exists: you open the generated file in Optitex and tell me what it says (opens / error / differences).
