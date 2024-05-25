import pandas as pd

# 讀取 CSV 檔案
keyword_counts_df = pd.read_csv('./keyword_counts_per_line.csv')
target_df = pd.read_csv('./Target.csv')

# 根據 Target 的值更新 Target 欄位
def update_target(value):
    if value == 1:
        return "punitive"
    elif value == 2:
        return "compensatory"
    else:
        return "notdefine"

# 新增 Target 欄位並更新值
keyword_counts_df['Target'] = target_df['Target'].apply(update_target)

# 儲存更新後的 DataFrame 到新的 CSV 檔案
output_path = './updated_keyword_counts_per_line.csv'
keyword_counts_df.to_csv(output_path, index=False)

# 顯示更新後的 DataFrame
keyword_counts_df.head()
