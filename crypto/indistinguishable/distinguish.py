#!/usr/bin/python3
import sys
import socket
from time import sleep

HOST = sys.argv[1]
PORT = int(sys.argv[2])
MORE = int(sys.argv[3])

print("Attacking RC4 on " + sys.argv[1] + " at port "+sys.argv[2])


def distinguish_rc4(lines):
    max = 0
    sums = []
    for start in range(0, 31, 2):
        zeroes = 0
        for line in lines:
            # Get the second byte
            char = line.strip()[start:start+2]
            if char == "00":
                zeroes += 1

        sums.append(zeroes)
        if(zeroes > max):
            max = zeroes

    print()
    print("Average number of zeroes:")
    for sum in sums:
        print(sum / len(lines))

    # If the max was at index 1, we assume it is RC4
    rc4 = sums.index(max) == 1
    if rc4:
        return "rc4"
    else:
        return "aes"


def read_n(file, n):
    lines = []
    for i in range(n):
        line = file.readline()
        lines.append(line.strip())

    return lines


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    input = s.makefile("r")

    # Read the header
    read_n(input, 3)

    for round in range(42):
        print()
        print("Attacking round "+str(round+1))

        lines = []
        for more in range(MORE):
            if (more + 1) % int(MORE/10.0) == 0:
                print(" getting data {}/{}".format(more+1, MORE))

            lines.extend(read_n(input, 32))
            sleep(0.01)

            # Read the prompt
            input.read(2)
            if more < MORE-1:
                # Ask for more
                s.sendall(b'more\n')
                sleep(0.01)

        guess = distinguish_rc4(lines)

        print()
        print(" Guess: {}".format(guess))
        s.sendall(bytes("{}\n".format(guess), "utf-8"))

        sleep(0.01)

        # Read round header
        result = input.readline()
        print("Result: {}".format(result))
        if result == "Wrong":
            exit(1)

        next = read_n(input, 2)
        if round == 41:
            print(next[1])
