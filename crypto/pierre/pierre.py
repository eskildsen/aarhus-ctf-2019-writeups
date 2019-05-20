#!/usr/bin/python3
import sys
import gmpy2

def fermat_factorise(n):
    a = gmpy2.isqrt(n)
    b2 = a*a - n
    b = gmpy2.isqrt(n)
    count = 0
    while b*b != b2:
        a = a + 1
        b2 = a*a - n
        b = gmpy2.isqrt(b2)
        count += 1
    p = a+b
    q = a-b
    return p, q

def xgcd(a, b):
    """return (g, x, y) such that a*x + b*y = g = gcd(a, b)"""
    x0, x1, y0, y1 = 0, 1, 1, 0
    while a != 0:
        q, b, a = b // a, a, b % a
        y0, y1 = y1, y0 - q * y1
        x0, x1 = x1, x0 - q * x1

    return b, x0, y0


c = gmpy2.mpz(int(open(sys.argv[1]).readline().strip(), 16))

pk = open(sys.argv[2])
n = gmpy2.mpz(int(pk.readline().strip()[2:], 16))
e = gmpy2.mpz(int(pk.readline().strip()[2:], 16))

p, q = fermat_factorise(n)
phi = (p - 1)*(q - 1)
gcd, d, b = xgcd(e, phi)
plaintext = gmpy2.powmod(c, gmpy2.mpz(d), n)
bin = bytearray(gmpy2.to_binary(plaintext))

print('p = {}\n\nq = {}\n'.format(p, q))
print('d = {}\n'.format(d))

print('Plaintext (little endian): {}'.format(bin))
bin.reverse()
print('Plaintext    (big endian): {}'.format(bin))

