"""Deterministic synthetic integer multiplication aliasing tests."""

import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from support import translate_lines, mrt0_words

MASK32 = 0xFFFFFFFF
SEEDS = (7, 19, 43)
OPS = ("v_mul_lo_u32", "v_mul_hi_u32", "v_mul_hi_i32")

BOUNDARIES = (
    0, 1, 2, 0x7FFFFFFF, 0x80000000,
    0x80000001, 0xFFFFFFFE, 0xFFFFFFFF,
)


def signed32(word):
    return int.from_bytes(
        (word & MASK32).to_bytes(4, "little"),
        "little",
        signed=True,
    )


def reference(op, a, b):
    if op == "v_mul_hi_i32":
        product = signed32(a) * signed32(b)
    else:
        product = (a & MASK32) * (b & MASK32)

    if op != "v_mul_lo_u32":
        product >>= 32

    return product & MASK32


def operand_pairs(seed):
    rng = random.Random(seed)
    for edge in BOUNDARIES:
        word = rng.getrandbits(32)
        yield edge, word
        yield word, edge


def listing(op, a, b, destination):
    return [
        f"v_mov_b32 v1, {a:#010x}",
        f"v_mov_b32 v2, {b:#010x}",
        f"{op} {destination}, v1, v2",
        f"exp mrt0 {destination}, v1, v2, {destination} done vm",
        "s_endpgm",
    ]


def expected_words(op, a, b, destination):
    result = reference(op, a, b)
    return (
        result,
        result if destination == "v1" else a,
        result if destination == "v2" else b,
        result,
    )


class IntegerMulAliasing(unittest.TestCase):
    def test_seeded_destination_aliasing(self):
        count = 0
        for seed in SEEDS:
            for op in OPS:
                for a, b in operand_pairs(seed):
                    for destination in ("v0", "v1", "v2"):
                        lines = listing(op, a, b, destination)
                        with self.subTest(
                            seed=seed, op=op,
                            a=hex(a), b=hex(b),
                            destination=destination,
                        ):
                            spv = translate_lines("ps_mul_alias", lines)
                            got = tuple(mrt0_words(spv))
                            want = expected_words(
                                op, a, b, destination
                            )
                            self.assertEqual(
                                got, want, "\n".join(lines)
                            )
                        count += 1

        self.assertEqual(count, 432)


if __name__ == "__main__":
    unittest.main()
