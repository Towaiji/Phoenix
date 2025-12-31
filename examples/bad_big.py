import math

x = 5
x = "oops"          # Rule 1: type mutation

data = [1, "two"]   # Rule 2: mixed list

eval("print(x)")    # Rule 3: eval

n = 10
for i in range(n):  # Rule 4: dynamic loop bound
    print(i)

y = 0
while y < 5:        # Rule 4: while loop
    y = y + 1

mod = __import__("math")  # Rule 3: dynamic import
