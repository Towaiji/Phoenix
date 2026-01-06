def misuse_and():
    return 1 and 2


def misuse_not():
    return not 5


def bad_chain_compare():
    return "a" < "b" < "c"
