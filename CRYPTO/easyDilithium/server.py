#!/usr/bin/env python3
"""
Leaky Dilithium - A vulnerable ML-DSA-like signature service.
"""

import hashlib
import os
import random
import sys

# ================== Parameters ==================
n = 64
q = 65537
k = 2
l = 2
eta = 2
tau = 20
gamma1 = 8192
gamma2 = 256
beta = tau * eta

NOISE_BOUND = 15

TARGET_MSG = "Please give me the flag"
FLAG = os.environ.get("FLAG")


# ================== Polynomial arithmetic ==================
class Poly:
    """Polynomial in Z_q[x]/(x^n+1), stored with coefficients in 0..q-1."""

    def __init__(self, coeffs=None):
        if coeffs is None:
            self.coeffs = [0] * n
        else:
            self.coeffs = [c % q for c in coeffs]
            if len(self.coeffs) != n:
                raise ValueError(f"Length must be {n}")

    def __add__(self, other):
        return Poly([(a + b) % q for a, b in zip(self.coeffs, other.coeffs)])

    def __sub__(self, other):
        return Poly([(a - b) % q for a, b in zip(self.coeffs, other.coeffs)])

    def __mul__(self, other):
        """Convolution modulo x^n+1 and q."""
        res = [0] * (2 * n)
        for i in range(n):
            if self.coeffs[i] == 0:
                continue
            for j in range(n):
                res[i + j] += self.coeffs[i] * other.coeffs[j]

        final = [0] * n
        for i in range(2 * n - 1):
            idx = i % n
            val = res[i] % q
            if i < n:
                final[idx] = (final[idx] + val) % q
            else:
                final[idx] = (final[idx] - val) % q
        return Poly(final)

    def __eq__(self, other):
        return self.coeffs == other.coeffs

    def to_int_list(self):
        return self.coeffs

    def centered_list(self):
        half = q // 2
        return [c if c <= half else c - q for c in self.coeffs]


def poly_vec_add(v1, v2):
    return [a + b for a, b in zip(v1, v2)]


def matrix_vec_mul(mat, vec):
    res = []
    for row in mat:
        acc = Poly()
        for a, v in zip(row, vec):
            acc = acc + (a * v)
        res.append(acc)
    return res


def poly_vec_scalar_mul(c, vec):
    return [c * v for v in vec]


# ================== Helpers ==================
def sample_small_poly():
    return Poly([random.randint(-eta, eta) for _ in range(n)])


def sample_uniform_poly():
    return Poly([random.randint(0, q - 1) for _ in range(n)])


def sample_y():
    y = []
    for _ in range(l):
        coeffs = [random.randint(-gamma1 + 1, gamma1) for _ in range(n)]
        y.append(Poly(coeffs))
    return y


def high_bits(r, gamma2):
    r = r % q
    r0 = r % gamma2
    if r0 > gamma2 // 2:
        r0 -= gamma2
    return (r - r0) // gamma2


def poly_high_bits(poly, gamma2):
    return [high_bits(c, gamma2) for c in poly.coeffs]


def serialize_w1(w1_list):
    data = b""
    for coeffs in w1_list:
        for v in coeffs:
            data += v.to_bytes(2, "big")
    return data


def generate_challenge(msg, w1_list):
    data = msg.encode() + serialize_w1(w1_list)
    seed = hashlib.sha256(data).digest()
    rng = random.Random(seed)

    c_coeffs = [0] * n
    positions = rng.sample(range(n), tau)
    for pos in positions:
        c_coeffs[pos] = 1 if rng.randint(0, 1) == 0 else -1
    return Poly(c_coeffs)


# ================== Key generation ==================
def keygen():
    A = [[sample_uniform_poly() for _ in range(l)] for _ in range(k)]
    s1 = [sample_small_poly() for _ in range(l)]
    t = matrix_vec_mul(A, s1)
    return A, t, s1


# ================== Signature ==================
def sign(msg, A, s1):
    while True:
        y = sample_y()
        w = matrix_vec_mul(A, y)
        w1_list = [poly_high_bits(p, gamma2) for p in w]
        c = generate_challenge(msg, w1_list)
        cs1 = poly_vec_scalar_mul(c, s1)
        z = poly_vec_add(y, cs1)

        z_centered = [coeff for p in z for coeff in p.centered_list()]
        if max(abs(v) for v in z_centered) >= gamma1 - beta:
            continue

        noise = [
            [random.randint(-NOISE_BOUND, NOISE_BOUND) for _ in range(n)]
            for _ in range(l)
        ]
        r = [Poly([y[i].coeffs[j] + noise[i][j] for j in range(n)]) for i in range(l)]
        return c, z, r


# ================== Verification ==================
def verify(msg, c, z, A, t):
    z_centered = [coeff for p in z for coeff in p.centered_list()]
    if max(abs(v) for v in z_centered) >= gamma1 - beta:
        return False

    Az = matrix_vec_mul(A, z)
    ct = poly_vec_scalar_mul(c, t)
    w_prime = [Az[i] - ct[i] for i in range(k)]
    w1_prime = [poly_high_bits(p, gamma2) for p in w_prime]
    c_prime = generate_challenge(msg, w1_prime)
    return c == c_prime


# ================== Server interaction ==================
def main():
    random.seed(os.urandom(8))
    print("=== Leaky Dilithium Signature Service ===", flush=True)
    A, t, s1 = keygen()
    print("[+] Key generated.", flush=True)

    while True:
        print("\nMenu:", flush=True)
        print("1. Get public key", flush=True)
        print("2. Request signature", flush=True)
        print("3. Submit admin signature", flush=True)
        print("0. Exit", flush=True)
        choice = input("> ").strip()

        if choice == "1":
            print("Public key (A, t):", flush=True)
            print("A:", flush=True)
            for row in A:
                for poly in row:
                    print(poly.to_int_list(), flush=True)
            print("t:", flush=True)
            for poly in t:
                print(poly.to_int_list(), flush=True)

        elif choice == "2":
            msg = input("Message to sign: ").strip()
            if msg == TARGET_MSG:
                print("[-] Sorry, cannot sign the target message!", flush=True)
                continue

            c, z, r = sign(msg, A, s1)
            print("Signature:", flush=True)
            print("c:", c.coeffs, flush=True)
            print("z:", flush=True)
            for poly in z:
                print(poly.centered_list(), flush=True)
            print("r (debug):", flush=True)
            for poly in r:
                print(poly.centered_list(), flush=True)

        elif choice == "3":
            print("Submit your signature for: " + TARGET_MSG, flush=True)
            msg = TARGET_MSG
            print("Enter c (list of int, length 64):", flush=True)
            c_data = input().strip()
            try:
                c_coeffs = [int(x) for x in c_data.strip("[]").split(",")]
                c = Poly(c_coeffs)
            except Exception:
                print("Invalid format.", flush=True)
                continue

            z_vec = []
            for i in range(l):
                print(f"Enter z[{i}] (64 ints):", flush=True)
                z_data = input().strip()
                try:
                    z_coeffs = [int(x) for x in z_data.strip("[]").split(",")]
                    z_vec.append(Poly(z_coeffs))
                except Exception:
                    print("Invalid format.", flush=True)
                    break

            if len(z_vec) != l:
                continue

            if verify(msg, c, z_vec, A, t):
                print("[+] Signature valid! Here is your flag: " + FLAG, flush=True)
            else:
                print("[-] Invalid signature.", flush=True)
            break

        elif choice == "0":
            print("Bye!", flush=True)
            sys.exit(0)
        else:
            print("Unknown option.", flush=True)


if __name__ == "__main__":
    main()
