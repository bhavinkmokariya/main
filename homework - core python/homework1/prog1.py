def q1(lst):
    sum=0
    for i in lst:
             if i%2==0:
                 sum=sum+i
    return sum
lis = [10,25,13,17,48,23,78]
a = q1(lis)
print("Sum is : ", a)
