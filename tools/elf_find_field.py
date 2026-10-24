"""Find loads/stores of a structure field offset (lwz/stw/lhz/sth/lbz/stb with that displacement).
Good for "who writes obj+0x7e4?".

usage: python elf_find_field.py EBOOT.elf 0x7e4[,0x7f0...]
"""
import sys
from ps3elf import Elf

OPS = {32: 'lwz', 36: 'stw', 40: 'lhz', 44: 'sth', 34: 'lbz', 38: 'stb'}
elf = Elf(sys.argv[1])
for d in sys.argv[2].split(','):
    disp = int(d, 16); res = {}
    for va, w in elf.code_words():
        if (w >> 26) in OPS and (w & 0xffff) == disp:
            res.setdefault(OPS[w >> 26], []).append(va)
    for op, addrs in sorted(res.items()):
        print(f'{d} {op} x{len(addrs)}:', ' '.join(f'{a:08x}' for a in addrs[:40]))
