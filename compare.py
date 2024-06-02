import pandas as pd

# 讀取兩個 CSV 檔案
new_version_df = pd.read_csv('new_version.csv')
judgment_data_2_df = pd.read_csv('judgment_data_2.csv')

# 過濾 judgment_data_2_df，只保留 Title 存在於 new_version_df 的資料
filtered_judgment_data_2_df = judgment_data_2_df[judgment_data_2_df['Title'].isin(new_version_df['Title'])]

# 將過濾後的資料儲存到新的 CSV 檔案中
filtered_judgment_data_2_df.to_csv('judgment_data_3.csv', index=False)
