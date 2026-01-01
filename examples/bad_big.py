import math

# ----- type instability -----
x = 5
x = "hello"          # ❌ type change

# ----- mixed list -----
bad_list = [1, 2.0]  # ❌ mixed types

# ----- dynamic loop -----
n = 10
for i in range(n):   # ❌ dynamic bound
    print(i)

# ----- forbidden execution -----
eval("x + 1")        # ❌ eval

# ----- unsupported call -----
def f(a):
    return a

y = f("string")      # ❌ wrong type usage

# ----- invalid list usage -----
nums = [1, 2, 3]
nums[0] = 1.5        # ❌ list[int] mutated with float

# ----- invalid math -----
z = math.sqrt("hi")  # ❌ sqrt on string
