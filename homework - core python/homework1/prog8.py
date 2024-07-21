def q8(grade):
    if(grade>=90):
        print("A grade")
    elif(grade>=80):
        print("B grade")
    elif(grade>=70):
        print("C grade")
    elif(grade>=60):
        print("D grade")
    else:
        print("F grade")

grd = int(input("Enter your score : "))
if(grd>=0 and grd<=100):
    q8(grd)
else:
    print("Enter valid score")