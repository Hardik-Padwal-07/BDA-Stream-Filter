"""DGIM counting ones in a window - Module 4.5."""
from collections import defaultdict


class DGIM:
    def __init__(self, N: int = 1000):
        if N <= 0:
            raise ValueError("N must be positive")
        self.N = N
        self.time = 0
        # list of (timestamp, size), oldest -> newest
        self.buckets: list[tuple[int, int]] = []

    def _evict(self):
        cutoff = self.time - self.N
        self.buckets = [(t, s) for (t, s) in self.buckets if t > cutoff]

    def _compress(self):
        # ensure at most 2 buckets per size, merge oldest two
        # sizes are powers of two
        changed = True
        while changed:
            changed = False
            by_size: dict[int, list[int]] = defaultdict(list)
            for idx, (_, s) in enumerate(self.buckets):
                by_size[s].append(idx)
            for size, idxs in by_size.items():
                if len(idxs) > 2:
                    # merge the two oldest (smallest idx) of this size
                    i1, i2 = idxs[0], idxs[1]
                    # timestamp of merged = newer of the two
                    new_t = self.buckets[i2][0]
                    # remove both, insert merged
                    # remove higher idx first
                    del self.buckets[i2]
                    del self.buckets[i1]
                    # find insert position to keep sorted by timestamp
                    ins = 0
                    while ins < len(self.buckets) and self.buckets[ins][0] < new_t:
                        ins += 1
                    self.buckets.insert(ins, (new_t, size * 2))
                    changed = True
                    break

    def update(self, bit: int) -> None:
        self.time += 1
        if bit:
            self.buckets.append((self.time, 1))
            self._compress()
        self._evict()

    def count(self) -> int:
        """Query answering in DGIM: sum - oldest/2."""
        if not self.buckets:
            return 0
        total = sum(s for _, s in self.buckets)
        oldest_size = self.buckets[0][1]
        return total - oldest_size // 2

    def memory_buckets(self) -> int:
        return len(self.buckets)
