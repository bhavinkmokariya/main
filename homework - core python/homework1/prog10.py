def q10(lst):
    ls=[]
    for i in lst:
        if i["age"]>=18:
            ls.append(i["name"])
    return ls

nl = [{"name":"bhavin","age":20},{"name":"aryan","age":21},{"name":"amit","age":16},{"name":"anish","age":14},{"name":"aman","age":25}]
ab = q10(nl)
print(ab)