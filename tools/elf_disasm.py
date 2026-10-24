"""Disassemble a range of a PS3 EBOOT.elf with capstone (pip install capstone).

usage: python elf_disasm.py EBOOT.elf START END     (hex addresses)
"""
import sys, capstone
from ps3elf import Elf

elf = Elf(sys.argv[1])
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)
for ins in md.disasm(elf.read(lo, hi - lo), lo):
    print(f'{ins.address:08x}  {ins.bytes.hex()}  {ins.mnemonic:8s} {ins.op_str}')
