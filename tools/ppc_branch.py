"""Encode a PowerPC unconditional branch `b target` placed at `addr`, for RPCS3 be32 patches.

usage: python ppc_branch.py 0x9bd544 0x9bd7d8   ->  0x48000294
"""
import sys

addr, target = int(sys.argv[1], 16), int(sys.argv[2], 16)
off = target - addr
assert off % 4 == 0 and -(1 << 25) <= off < (1 << 25), 'target out of range for a relative branch'
print(f'{0x48000000 | (off & 0x03fffffc):#010x}   # b {target:#x}  (from {addr:#x})')
print('nop is 0x60000000')
