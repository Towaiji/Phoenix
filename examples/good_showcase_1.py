import math
import mod_utils

# Core types + control flow + math + strings + dict/set.

nums = [1, 2, 3, 4, 5]
total = 0

for i in range(5):
    total = total + nums[i]

avg = total / 5

msg = ""
if avg > 2 and avg < 4:
    msg = "mid"
elif avg >= 4:
    msg = "high"
else:
    msg = "low"

label = msg + " avg=" + avg

angles = [0.0, 1.0, 2.0]
trig = [math.sin(angles[0]), math.cos(angles[1]), math.tan(angles[2])]
min_trig = min(trig)
max_trig = max(trig)

data = {"a": 1, "b": 2}
data["c"] = 3
data["a"] = 4
del data["b"]

tags = {"fast", "safe"}
tags.add("static")
tags.remove("safe")

has_fast = "fast" in tags

score = mod_utils.add(total, data["c"])
score = score + mod_utils.CONST

print(label)
print(min_trig)
print(max_trig)
print(has_fast)
print(score)
