# Aarhus CTF - Indistinquishable

In this flag we were given the task to determine if a bunch of text has been encrypted with RC4 or AES. This is a variation of the classic cryptographic problem: Is a given text an encrypted message or random data? We therefore have to perform a [distinguishing attack](https://en.wikipedia.org/wiki/Distinguishing_attack) on the text at hand. 

## The challenge 

We are given access to a server and the source code for said server. The server produces 32 lines of text and asks if it is AES or RC4. Each line is encrypted with a random key and for each line the plaintext is 16 bytes long containing only zeroes. You then type `aes` or `rc4` to the server and it responds with `Correct!` or `Wrong`. You can ask the server for 32 more lines by typing `more`. Guessing randomly will not help us since the probability of success for guessing 42 successive rounds correctly is: $\frac{1}{2^{42}} \approx \frac{1}{4.4 \cdot 10^{12}} \approx 0.00000000000023$. Given our time constraints and guessing over the network: zero.

## The cryptography

AES is a very good cipher that produces ciphertexts that look VERY much like random, uniform data. The best attacks against AES[^aes] require a lot of ciphertext and have time complexities in the order of ~$2^{40}$. We do not have a lot of ciphertext (only 16 byte per key) and not a enough time for brute force. 

RC4 on the other hand has some flaws. It works by taking your key as input and creating a keystream. The keystream is XORed with the plaintext and you have your ciphertext. Decrypting is simple, you just encrypt the ciphertext and due to XOR magic you have your original plaintext! 

There are a couple of known attacks that work against RC4, but most of them require lots of ciphertext. Since the plaintext is only zeroes the cipher actually leaks it's internal state, but since the ciphertexts are only 16 bytes there's not enough data to derive anything of value.
In 2001 Shamir showed that the second output byte of the cipher is biased towards zero with a probability of 1/128 instead of 1/256.[^rc4]  The second byte of the output has double the probability of being zero than any other byte. If we observe 256 lines  there will, on average, be 1 occurrence of 0 when it's AES and 2 occurrences when it's RC4. Now we're talking! How much data do we *actually* need to observe before we can be certain? Let's run some tests and find out.

## Distinguishing RC4 with Python

Let's start by writing the code that does the distinguishing of the bytes. First we generate some testdata. This can be done by modifying `indistinguishable.py` to dump the lines to a file. The code needs look at the distribution of the bytes on every position in the ciphertext. The ciphertext is encoded as HEX.

The first version iterates all the lines and calculates the number of zeroes for every byte.
It then prints the number of zeroes at the given byte position.

````python
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

    # Print the average number of zeroes per position.
    for sum in sums:
        print(sum / len(lines))

    # If the max was at index 1, we assume it is RC4
    return sums.index(max) == 1
````

Let's look at some output. For 1 round of 32 lines we get basically all zeroes. For 320 lines around half of the lines are zero. Bumping this to 3200 we get (we're showing the first 8 bytes):

| Byte | AES       | RC4       |
|------|-----------|-----------|
|   1  | 0.0050000 | 0.0028125 |
|   2  | 0.0053125 | 0.0103125 |
|   3  | 0.0053125 | 0.0031250 |
|   4  | 0.0037500 | 0.0043750 |
|   5  | 0.0018750 | 0.0046875 |
|   6  | 0.0056250 | 0.0037500 |
|   7  | 0.0046875 | 0.0056250 |
|   8  | 0.0031250 | 0.0062500 |

In the AES column the numbers differ at the third decimal whereas in RC4 the occurrences of zero in the second byte is noticably larger. You can see that while the values are not `1/128` and `1/256`, they are close to 2x. The more data we analyze the closer the frequencies will resemble `1/128` and `1/256` respectively. For demonstration purposes let's try with a 
million lines:

| Byte | AES       | RC4       |
|------|-----------|-----------|
|   1  | 0.0038320 | 0.0038190 |
|   2  | 0.0040420 | 0.0077910 |
|   3  | 0.0039300 | 0.0037490 |
|   4  | 0.0039220 | 0.0039170 |
|   5  | 0.0038650 | 0.0039120 |
|   6  | 0.0039320 | 0.0039700 |
|   7  | 0.0039370 | 0.0037490 |
|   8  | 0.0038650 | 0.0039240 |

As you can see the numbers are much closer to the ideals of `1/128 = 0.0078125` and `1/256 = 0.00390625`. 

## Getting the flag

Now that we have an algorithm to distinguish RC4 from randomness, we can now attack the server! 

The server starts by sending a header that looks like this:

````
Welcome to the distinguishing game!
````

Every round starts with the following text (n is round number, starting from 0):

````
===== Round n =====
Is this AES or RC4?
````

Following directly after you see 32 lines of hex-encoded ciphertext. After the ciphertext there is a prompt. A whole round looks like this:



````
===== Round n =====
Is this AES or RC4?
[ 32 lines go here]
> 
````

This means we can simply use a blocking socket to get the data we need. First we need to read one line to get past the initial header. For every round we read two lines which we ignore. We store the next 32 lines and then read another two bytes that is the prompt.
We send `more` to the server until we have enough data and finally we send our guess. Let's have a look at the code:

````python
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
            if (more + 1) % int(MORE/10) == 0:
                print(" getting data {}/{}".format(more+1, MORE))

            # Read the 32 lines of ciphertext
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

        # Read result
        result = input.readline()
        print("Result: {}".format(result))

        if result == "Wrong":
            # If the result was wrong, exit.
            exit(1)

        # Read next round header
        next = read_n(input, 2)
        if round == 41:
            # If this was the last round, print out the result.
            print(next[1])
````


Let's take it from the top. This script takes a couple of commandline parameters: the hostname, port and number of `more` calls to send. Assuming your server is `localhost` on port `8080` and you want to call more 200 times, you run the `distinguish.py` script ([download it here](distinguish.py)):

````
$ ./distinguish.py localhost 8080 200
```` 


Our function `distinguish_rc4` has changed a little and now returns either `rc4` or `aes` for convenience. The next function is called `read_n` which simply reads `n` lines from a given file. Next up we have the actual network code. 

First we create a socket and connect to it. Then we use the `socket.makefile` function to be able to read lines from the socket instead of raw bytes. We then iterate through a range of our rounds (0 to 41). For every round we read the lines and ask for more data the number of times you specified.  There are a couple of calls to `sleep` to avoid buffering issues. After we have enough lines we run our previously explained algorithm on said lines and send the result to the server. If the server responds with `Wrong` we exit the program.

If all goes well and the 41st round was correct, we print the last line containing the flag.


## Conclusion

This challenge demonstrates just how even the smallest leak of information from a cipher can lead to an attacker gaining an advantage. RC4 is a little dated but was  used in something as common as the WiFi security protocol WEP and ultimately led to WEP being a security swiss cheese. Crypto is very hard to get right and the takeaway here is: Use AES :()

---
*Writeup by Jesenko Mehmedbašić*


[^aes]: https://en.wikipedia.org/wiki/Advanced_Encryption_Standard
[^rc4]: https://en.wikipedia.org/wiki/RC4