import pandas as pd
import numpy as np

// take in ground truth data  and put into pandas dataframe

df = pd.read_csv("tmp/sample2.csv", index_col="name")

// count total rows and columns

count_rows = data.shape[0]
count_cols = data.shape[1]

// create clean data data dataframe

clean_data = data.loc[(data["Clean"]==1)]
dirty_data = data.loc[(data["Clean"]==0)]

// count clean data rows
count_clean_rows = clean_data.shape[0]

dfc = pd.DataFrame(clean_data, columns = ['name', 'Clean'])
dfd = pd.DataFrame(dirty_data, columns = ['name', 'Clean'])

is_data_clean = df["Clean"]==1
is_data_clean_now = df[is_data_clean]
is_data_clean_now.shape
