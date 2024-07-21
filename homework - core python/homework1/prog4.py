def q4(lst1,lst2):
    res={}
    res = set(lst1).intersection(lst1,lst2)
    return res


lst1 = [1,2,3,4,5,6,7]
lst2 = [6,7,2,9,10,11]
fin = q4(lst1,lst2)
print(fin)