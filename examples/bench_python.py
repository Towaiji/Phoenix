import time

values = [i for i in range(1000)]

start = time.time()

total = 0
for _ in range(10000):
    for v in values:
        total += v

end = time.time()

print("Result:", total)
print("Time:", end - start)
