"""Flajolet-Martin distinct counting - Module 4.4."""
import hashlib
import statistics


def _hash32(item: str, seed: int) -> int:
    h = hashlib.md5(f"{seed}:{item}".encode()).digest()
    return int.from_bytes(h[:4], "big")


def _trailing_zeros(x: int, max_bits: int = 32) -> int:
    if x == 0:
        return max_bits
    r = 0
    while (x & 1) == 0 and r < max_bits:
        r += 1
        x >>= 1
    return r


class FlajoletMartin:
    def __init__(self, num_hashes: int = 10):
        if num_hashes <= 0:
            raise ValueError("num_hashes must be positive")
        self.num_hashes = num_hashes
        self.max_zeros = [0] * num_hashes
        self.n_seen = 0

    def add(self, item: str) -> None:
        for i in range(self.num_hashes):
            h = _hash32(item, seed=i)
            r = _trailing_zeros(h)
            if r > self.max_zeros[i]:
                self.max_zeros[i] = r
        self.n_seen += 1

    def estimates(self):
        return [2 ** r for r in self.max_zeros]

    def estimate(self) -> float:
        """Median combining (syllabus: Combining Estimates)."""
        return float(statistics.median(self.estimates()))

    def memory_bytes(self) -> int:
        # only stores num_hashes small ints
        return self.num_hashes * 4
