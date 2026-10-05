from __future__ import annotations


class SpatialHash:
    """Uniform grid for neighbour queries; rebuilt every tick (O(n))."""

    def __init__(self, cell: float):
        self.cell = cell
        self.cells: dict = {}

    def clear(self):
        self.cells = {}

    def insert(self, o):
        self.cells.setdefault((int(o.x // self.cell), int(o.y // self.cell)), []).append(o)

    def query(self, x, y, r):
        c = self.cell
        out = []
        for gx in range(int((x - r) // c), int((x + r) // c) + 1):
            for gy in range(int((y - r) // c), int((y + r) // c) + 1):
                b = self.cells.get((gx, gy))
                if b:
                    out.extend(b)
        return out
