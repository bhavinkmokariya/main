def q2(dict2):
    newdict={}
    for name, grade in dict2.items():
        if grade > 75:
            newdict[name]=grade
    return newdict

a = int(input("Enter range: "))
ed={}
for i in range(1,a+1):
    key=input("Enter key: ")
    value=int(input("Enter values : "))
    ed[key]=value
abcd = q2(ed)
print(abcd)
