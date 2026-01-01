import math

# ----- globals -----
nums_int = [1, 2, 3, 4]
nums_float = [1.5, 2.5, 3.5]

x = 10
y = 2.5
z = x + y        # int + float -> float

# ----- functions -----
def add(a, b):
    return a + b

def square_sum(values):
    total = 0
    for i in range(4):
        total = total + values[i]
    return total

def average(values):
    total = square_sum(values)
    return total / 4

# ----- usage -----
result1 = add(3, 4)
result2 = add(2.5, 1.5)

sum_ints = square_sum(nums_int)
avg_ints = average(nums_int)

root = math.sqrt(avg_ints)

print(result1)
print(result2)
print(sum_ints)
print(avg_ints)
print(root)
