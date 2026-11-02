"""Bloom Filter from scratch - Module 4.3 Filtering Streams."""
import hashlib
import math


class BloomFilter:
    def __init__(self, m: int = 20000, k: int = 3):
        """
        m: number of bits, k: number of hash functions
        """
        if m <= 0 or k <= 0:
            raise ValueError("m and k must be positive")
        self.m = m
        self.k = k
        self.bits = bytearray((m + 7) // 8)
        self.n_inserted = 0

    def _positions(self, item: str):
        for i in range(self.k):
            h = hashlib.md5(f"{item}#{i}".encode()).digest()
            yield int.from_bytes(h[:4], "big") % self.m

    def add(self, item: str) -> None:
        for pos in self._positions(item):
            self.bits[pos // 8] |= 1 << (pos % 8)
        self.n_inserted += 1

    def __contains__(self, item: str) -> bool:
        for pos in self._positions(item):
            if not (self.bits[pos // 8] >> (pos % 8)) & 1:
                return False
        return True

    def check(self, item: str) -> bool:
        return item in self

    def memory_bytes(self) -> int:
        return len(self.bits)

    def theory_fp_rate(self) -> float:
        """(1 - e^(-kn/m))^k"""
        if self.n_inserted == 0:
            return 0.0
        return (1 - math.exp(-self.k * self.n_inserted / self.m)) ** self.k

    def bits_set(self) -> int:
        return sum(bin(b).count("1") for b in self.bits)
