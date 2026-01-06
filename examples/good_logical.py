def score_ok(a, b):
    both_positive = (a > 0) and (b > 0)
    small_enough = 0 < a < 10 and 1 <= b < 5
    allowed = both_positive or small_enough
    return allowed and not (a > 8 and b > 8)


result = score_ok(3, 4)
if result:
    print(1)
else:
    print(0)
