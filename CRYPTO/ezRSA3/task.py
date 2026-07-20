from sage.all import gcd, is_prime, prod, proof
from Crypto.Util.number import bytes_to_long, getPrime
from Crypto.Random.random import sample
from secret import flag

proof.arithmetic(False)

e = 65537
n = 10000
k = 10

s = set()
while len(s) < n:
    s.add(getPrime(50))

sops = sorted(s)

def get_p():
    while True:
        p = 2 * prod(sample(sops, k)) - 1
        if is_prime(p) and gcd(p - 1, e) == 1:
            return p

def get_q():
    while True:
        q = getPrime(512)
        if gcd(q - 1, e) == 1:
            return q

p = get_p()
q = get_q()
N = p * q
m = bytes_to_long(flag)
assert m < N
c = pow(m, e, N)

print(f"{sops=}")
print(f"{N=}")
print(f"{c=}")