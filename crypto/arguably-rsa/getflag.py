
##breaks encryption due to short unpadded cyphertext and low exponent.
##third root of cyphertext is plaintext in decimals
e = 3
cyphertext = 1266507512685188734024296480701217581859146439942347294025678664710736028242110814178564722387216936848563225483182112016293134304921336892062989162597050141119966157468365997335060553829

def find_cube_root(n):
    lo = 0
    hi = n
    while lo < hi:
        mid = (lo+hi)//2
        if mid**3 < n:
            lo = mid+1
        else:
            hi = mid
    return lo

def is_perfect_cube(n):
    return find_cube_root(n)**3 == n

def printflag(input):
    decimalflag = find_cube_root(input)
    hexflag = hex(decimalflag)
    flag = bytes.fromhex(hexflag[2:]).decode('utf-8')
    return flag

print(printflag(cyphertext))
