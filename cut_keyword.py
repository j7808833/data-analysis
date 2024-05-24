import pandas as pd
import jieba
import jieba.analyse
import os

# 預先載入 jieba 字典
jieba.initialize()

# 讀取 CSV 檔案
csv_file = "./test.csv"
txt_file = "./combined_fullcontent.txt"
output_csv_file = "./top_20_words_per_line.csv"

# 將 CSV 檔案的第三欄位內容合併成一個 TXT 檔案
def save_fullcontent_as_txt(csv_file, txt_file):
    with open(txt_file, 'w', encoding='utf-8') as txt_f:
        for chunk in pd.read_csv(csv_file, chunksize=1000):
            for content in chunk["FullContent"]:
                txt_f.write(content + '\n')
    print(f"Combined FullContent saved to {txt_file}")

save_fullcontent_as_txt(csv_file, txt_file)

# 分析 TXT 檔案的每一行，找出最常出現的 20 個詞彙，並存成新的 CSV 檔案
def analyze_txt_to_csv(txt_file, output_csv_file):
    with open(txt_file, 'r', encoding='utf-8') as txt_f:
        lines = txt_f.readlines()

    result_list = []

    for idx, line in enumerate(lines):
        words = jieba.analyse.extract_tags(line, topK=20, withWeight=False, allowPOS=('n', 'v', 'a'))
        result_list.append(words)
        print(f"Processed line {idx+1}/{len(lines)}")

    result_df = pd.DataFrame(result_list)
    result_df.to_csv(output_csv_file, index=False, encoding='utf-8')
    print(f"Results saved to {output_csv_file}")

analyze_txt_to_csv(txt_file, output_csv_file)
