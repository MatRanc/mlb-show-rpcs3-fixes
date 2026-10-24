"""Tiny Python model of RPCS3's rsx::draw_clause (rpcs3/Emu/RSX/NV47/FW/draw_call.hpp/.cpp) replaying
the crowd's draw pattern, to show both bugs without running the game.

Bug 1: rows submitted back-to-front (descending `first`) are sorted in front of the range that carries
       the batch's vertex-array-offset barrier, so they use the PREVIOUS batch's offsets.
Bug 2: the clause stores one `command` (arrays vs indexed); the last draw call type wins for every range.
"""


class Clause:
    def __init__(self, fix_barriers=False):
        self.ranges, self.barriers, self.cur, self.last_exec = [], [], 0, 0
        self.command = None
        self.fix = fix_barriers

    def append_draw_command(self, r):
        self.cur = len(self.ranges); self.ranges.append(r)

    def insert_draw_command(self, i, r):
        self.cur = i; self.ranges.insert(i, r)
        for b in self.barriers:   # upstream: if (barrier.draw_id >= index) barrier.draw_id++
            if b['id'] > i or (b['id'] == i and not self.fix):
                b['id'] += 1

    def set_offsets(self, batch):   # SET_VERTEX_DATA_ARRAY_OFFSET inside BEGIN/END -> execution barrier
        if not self.ranges:
            self.offsets_at_begin = batch; return
        if self.ranges[-1][1] > 0:
            self.append_draw_command([0, 0])
        else:
            self.cur = len(self.ranges) - 1
        self.barriers.append({'id': self.cur, 'batch': batch}); self.barriers.sort(key=lambda b: b['id'])
        self.last_exec = self.cur

    def draw(self, command, first, count):   # DRAW_ARRAYS / DRAW_INDEX_ARRAY
        self.command = command                # bug 2: overwritten every call
        if self.ranges:
            last = self.ranges[self.cur]
            if last[1] == 0:
                last[0], last[1] = first, count; return
            if last[0] + last[1] == first:
                last[1] += count; return
            for i in range(self.last_exec, len(self.ranges)):
                if self.ranges[i][0] > first:
                    self.insert_draw_command(i, [first, count]); return
        self.append_draw_command([first, count])

    def replay(self):
        offs, out = self.offsets_at_begin, []
        for i, (first, count) in enumerate(self.ranges):
            for b in self.barriers:
                if b['id'] == i:
                    offs = b['batch']
            out.append(f'  {self.command:7s} first={first:3d} count={count:3d} -> batch {offs} data')
        return out


def bug1(fix):
    c = Clause(fix)
    c.set_offsets('A'); c.draw('arrays', 0, 40)                 # batch A: one forward draw
    c.set_offsets('B')                                          # batch B: rows back-to-front
    for first, count in [(28, 12), (16, 12), (8, 8), (0, 8)]:
        c.draw('arrays', first, count)
    return c.replay()


def bug2():
    L = 1604                                                    # index table [L-1 .. 0]
    c = Clause()
    c.set_offsets('A'); c.draw('arrays', 0, 640)                # batch A: single DRAW_ARRAYS
    c.set_offsets('B'); c.draw('indexed', L - 504, 504)         # batch B: single DRAW_INDEX_ARRAY
    return c.replay() + [f'  -> batch A now reads index entries 0..639 = values {L-1}..{L-640}, not 0..639']


if __name__ == '__main__':
    print('Bug 1, current RPCS3:'); print('\n'.join(bug1(False)))
    print('Bug 1, barrier kept at segment start:'); print('\n'.join(bug1(True)))
    print('Bug 2, mixed draw types in one BEGIN/END:'); print('\n'.join(bug2()))
    # self-check: with the fix, every B row uses B's data; without it, some don't
    assert all('batch B' in l for l in bug1(True)[1:])
    assert any('batch A' in l for l in bug1(False)[1:])
