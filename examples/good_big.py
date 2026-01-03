import math

# ----- globals -----
nums_int = [1, 2, 3, 4]
nums_float = [1.5, 2.5, 3.5, 4.5]
names = ["alice", "bob", "carol", "dave"]

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

def max_of_two(a, b):
    max_val = a
    if a > b:
        max_val = a
    else:
        max_val = b
    return max_val

def first_two(names):
    out1 = names[0]
    out2 = names[1]
    return out1

# ----- usage -----
result1 = add(3, 4)
result2 = add(2.5, 1.5)

sum_ints = square_sum(nums_int)
avg_ints = average(nums_int)

biggest_int = max_of_two(nums_int[2], nums_int[3])
biggest_float = max_of_two(nums_float[1], nums_float[2])
first_name = first_two(names)

root = math.sqrt(avg_ints)

print(result1)
print(result2)
print(sum_ints)
print(avg_ints)
print(biggest_int)
print(biggest_float)
print(first_name)
print(root)
