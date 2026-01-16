d = {"a": 1, "b": 2}
d["c"] = 3
d["a"] = 4
del d["b"]

s = {"x", "y"}
s.add("z")
s.remove("x")

if "z" in s:
    print(d["c"])
