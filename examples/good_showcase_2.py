# Dynamic lists, slicing, while, comparisons, and functions.

def scale_list(values, factor):
    out = [values[0] * factor]
    for i in range(1, 3):
        out.append(values[i] * factor)
    return out


values = [3]
values.append(1)
values.append(4)
values.append(1)
values.append(5)

first_three = values[0:3]
scaled = scale_list(first_three, 2)

idx = 0
while idx < 5:
    values[idx] = values[idx] + 1
    idx += 1

sum_vals = sum(values)
min_val = min(values)
max_val = max(values)

cmp_ok = 1 < 2 < 3
logic_ok = (min_val < max_val) and not (sum_vals < 0)

note = "sum=" + sum_vals + ", min=" + min_val + ", max=" + max_val
note = note.replace("min", "lo").replace("max", "hi")

print(first_three.pop())
print(scaled[1])
print(cmp_ok)
print(logic_ok)
print(note.upper().strip())
