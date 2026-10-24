"""Minimal reader for a decrypted PS3 EBOOT.elf (64-bit big-endian ELF): map virtual addresses to bytes."""
import struct


class Elf:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        assert self.data[:4] == b'\x7fELF' and self.data[4] == 2 and self.data[5] == 2, 'not a 64-bit big-endian ELF'
        phoff, = struct.unpack_from('>Q', self.data, 0x20)
        phentsize, phnum = struct.unpack_from('>HH', self.data, 0x36)
        self.segments = []   # (file offset, vaddr, size, executable)
        for i in range(phnum):
            p_type, p_flags, off, vaddr, _, filesz = struct.unpack_from('>IIQQQQ', self.data, phoff + i * phentsize)
            if p_type == 1 and filesz:
                self.segments.append((off, vaddr, filesz, bool(p_flags & 1)))

    def read(self, va, n):
        for off, vaddr, size, _ in self.segments:
            if vaddr <= va < vaddr + size:
                return self.data[off + va - vaddr: off + va - vaddr + n]
        raise ValueError(f'{va:#x} is not in a loaded segment')

    def code_words(self):
        """Yield (vaddr, u32) for every instruction word in executable segments."""
        for off, vaddr, size, x in self.segments:
            if x:
                for o in range(0, size - 3, 4):
                    yield vaddr + o, struct.unpack_from('>I', self.data, off + o)[0]
