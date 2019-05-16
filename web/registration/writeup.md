# Registration
## Challenge description
> Just register for a flag - if they have more left at least.

## Solution
Here at the beginning if we send an email and name, we can see that only flugel knutz is allowed to have the flag, but I want it!

![](images/challenge.jpg) 

Let's check JavaScript

![](images/javascript.png) 

It is indeed using JavaScript.

![](images/javascript_disabled.png) 
 
Let's fire up burp suite

![](images/burp.png) 

And capture some legit input

![](images/burp_capture.png) 
 
We can see it's sending a captcha, let's grab that otherwise you will see this.

![](images/bots.jpg)

Let's send some legit input but modify it.

![](images/burp_modified.png) 

I'm invincible!

![](images/flag.jpg) 
 

---
*Writeup by Oskar Anderberg*