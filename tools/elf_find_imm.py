"""Find instructions that load a 16-bit immediate (li/addi, ori, lis/addis) - e.g. GCM method numbers or
register values you saw in RenderDoc. Prints matches, then addresses where ALL values occur within 0x400 bytes.

usage: python elf_find_imm.py EBOOT.elf 0x0c32,0x0444,0x0822
"""
import sys
from ps3elf import Elf

elf = Elf(sys.argv[1])
targets = [int(t, 16) for t in sys.argv[2].split(',')]
hits = {t: [] for t in targets}
for va, w in elf.code_words():
    if (w >> 26) in (14, 15, 24) and (w & 0xffff) in hits:   # addi/li, addis/lis, ori
        hits[w & 0xffff].append(va)
for t in targets:
    print(f'{t:#06x}: {len(hits[t])} hits', ' '.join(f'{a:08x}' for a in hits[t][:30]))
first, rest = hits[targets[0]], targets[1:]
near = [a for a in first if all(any(abs(a - b) < 0x400 for b in hits[t]) for t in rest)]
print('all values within 0x400 of each other:', ' '.join(f'{a:08x}' for a in near))
