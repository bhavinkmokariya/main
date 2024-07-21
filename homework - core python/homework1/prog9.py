def q9(lst):
    ls=[]
    for i in lst:
        if i > 1:
            for j in range(2, i):
                if (i % j) == 0:
                    break
            else:
                ls.append(i)
    return ls

a =[7,15,4,8,45,89,75,22,46]
b = q9(a)

print(b)
