import pandas as pd

# Creating the DataFrame
data = {
    'StudentID': [1, 2, 3, 4, 5, 6, 7],
    'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace'],
    'Math': [85, 78, 92, 76, 89, 90, 85],
    'Science': [92, 85, 87, 83, 91, 88, 93],
    'English': [88, 79, 94, 85, 92, 86, 90],
    'History': [74, 82, 90, 75, 88, 79, 86],
    'Geography': [81, 80, 89, 78, 84, 85, 87],
    'Age': [15, 16, 15, 14, 15, 16, 14],
    'Gender': ['F', 'M', 'M', 'M', 'F', 'M', 'F']
}

df = pd.DataFrame(data)
gender_mean_scores = df.groupby('Gender')[['Math', 'Science', 'English', 'History', 'Geography']].mean()
print(gender_mean_scores)
