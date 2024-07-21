def q3(newde):
    a=[]
    for i,j in newde:
            if j>10:
                a.append(i)
    return a

newde = [("abc",8),("def",15),("ghi",7),("jkl",18),("mno",5)]
b = q3(newde)
print(b)