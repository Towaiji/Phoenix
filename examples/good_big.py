import math

# Static data
values = [1, 4, 9, 16, 25]

# Accumulate sum
total = 0
for i in range(5):
    total = total + values[i]

# More arithmetic
average = total / 5
rounded = int(average)

# Another loop with static bounds
squares = [0, 0, 0, 0, 0]
for i in range(5):
    squares[i] = values[i] * values[i]

# Final computation
result = math.sqrt(rounded)
final = int(result)
