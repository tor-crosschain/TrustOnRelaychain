import math


def numOpt(n: int):
    x = math.log(n, 2)
    if 2 ** int(x) != n:
        x = int(x) + 1
    x = int(x)
    return x


def numTree(n: int):
    x = math.log(n, 2)
    if 2 ** int(x) != n:
        x = int(x) + 1
    x = int(x)
    return 2 ** int(x) - 1


for i in range(1, 1000):
    print(f"numOpt: {i, numOpt(i)}")
    print(f"numTree: {i, numTree(i)}")
