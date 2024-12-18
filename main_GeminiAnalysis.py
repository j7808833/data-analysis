import requests
from bs4 import BeautifulSoup
import time
import random
import csv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

# API 金鑰與 API URL 配置
GEMINI_API_KEY = "AIzaSyD_bkUIDtfzwqU5O4lgbP_9ugOrS9iZaqw"
API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent'

# 定義請求網頁的函式，包含重試機制
def fetch_page(url, data=None):
    """
    發送 GET 或 POST 請求以獲取網頁內容。
    如果請求失敗，啟用重試機制。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    session = requests.Session()
    retries = Retry(total=10, backoff_factor=2, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    try:
        time.sleep(random.uniform(2, 5))  # 模擬人工延遲
        response = session.post(url, headers=headers, data=data, timeout=15) if data else session.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"網頁請求失敗: {e}")
        return None

# 解析主頁面，提取 iframe 的 URL
def parse_main_page(content):
    """
    解析主頁內容，找到 iframe 的 URL。
    """
    soup = BeautifulSoup(content, 'html.parser')
    iframe = soup.find('iframe', {'id': 'iframe-data'})
    return iframe.get('src') if iframe else ""

# 分析結果頁面，提取案件標題和連結
def parse_results_page(content):
    """
    從結果頁面中提取案件標題、連結和相關資料。
    """
    soup = BeautifulSoup(content, 'html.parser')
    titles = soup.select('.hlTitle_scroll')
    if not titles:
        return [], []
    data, links = [], []
    for title in titles:
        link = title['href']
        parent = title.find_parent('tr')
        second_column = parent.find_all('td')[3].get_text(strip=True) if parent else ""  # 獲取裁判案由
        data.append({'Title': title.get_text(strip=True), 'SecondColumn': second_column, 'Link': link})
        links.append(link)
    return data, links

# 清理網頁內容，移除 HTML 標籤
def clean_content(raw_content):
    """
    清理 HTML 內容，僅保留純文本，並限制字數。
    """
    soup = BeautifulSoup(raw_content, 'html.parser')
    return soup.get_text(strip=True)[:5000]

# 提取裁判日期，並轉換為西元日期格式
def extract_judgment_date(content):
    """
    從裁判詳細頁面中提取裁判日期，並轉換為西元日期。
    """
    soup = BeautifulSoup(content, 'html.parser')
    date_element = soup.find(text=re.compile("裁判日期："))
    if date_element:
        date_text = date_element.find_next().get_text(strip=True)
        return convert_date_to_ad(date_text)
    return "未知"

# 將民國日期轉換為西元日期
def convert_date_to_ad(date_text):
    """
    將民國日期轉換為西元日期。
    """
    match = re.search(r"民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", date_text)
    if match:
        year = int(match.group(1)) + 1911
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year}-{month:02d}-{day:02d}"
    return date_text

# 調用 API 分析案件內容
def analyze_content_with_api(content):
    """
    使用 API 分析內容，判斷案件類型。
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"請分析以下內容，判斷是否涉及懲罰性違約金或損害賠償性違約金：{content}"}]
        }]
    }
    try:
        response = requests.post(API_URL, params={'key': GEMINI_API_KEY}, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if 'candidates' in result and len(result['candidates']) > 0:
            analyzed_text = result['candidates'][0]['content']['parts'][0]['text']
            if "懲罰性違約金" in analyzed_text:
                return "懲罰性違約金"
            elif "損害賠償性違約金" in analyzed_text:
                return "損害賠償性違約金"
            elif "未提及違約金" in analyzed_text:
                return "未提及違約金"
            else:
                return "未知分類"
        return "未提及違約金"
    except requests.exceptions.RequestException as e:
        print(f"API 呼叫失敗: {e}")
        return "分析失敗"

# 將案件類型映射為數字代碼
def map_case_type_to_code(case_type):
    """
    將案件類型轉換為對應的數字代碼。
    """
    case_type_mapping = {
        "懲罰性違約金": 1,
        "損害賠償性違約金": 2,
        "未提及違約金": 3,
        "未知分類": 4,
        "分析失敗": 0
    }
    return case_type_mapping.get(case_type, 0)

# 儲存案件資料到 judgment_data_analysis.csv
def save_to_csv(data, filename):
    """
    保存案件資料到 judgment_data_analysis.csv 文件。
    """
    fieldnames = ['序號', '案件名稱', '裁判日期', '裁判案由', '違約金類型', '案件類型數字']
    try:
        with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(data)
    except Exception as e:
        print(f"CSV 寫入失敗: {e}")

# 儲存案件類型數字到 Target.csv
def save_to_target_csv(case_type_code, filename):
    """
    保存案件類型數字到 Target.csv 文件。
    """
    try:
        with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow([case_type_code])
    except Exception as e:
        print(f"Target.csv 寫入失敗: {e}")

# 主函式
def main():
    """
    主函式，處理資料爬取、自動化生成 judgment_data_analysis.csv 和 Target.csv。
    """
    base_url = 'https://judgment.judicial.gov.tw/FJUD/default.aspx'
    details_base_url = 'https://judgment.judicial.gov.tw/FJUD/'
    search_url_template = 'https://judgment.judicial.gov.tw/FJUD/qryresultlst.aspx?q=dbd2b7b8c6282852972ea728025a1297&sort=DS&page={page}&ot=in'

    initial_content = fetch_page(base_url)
    if not initial_content:
        return
    soup = BeautifulSoup(initial_content, 'html.parser')
    viewstate = soup.find(id="__VIEWSTATE")['value']
    viewstategenerator = soup.find(id="__VIEWSTATEGENERATOR")['value']
    eventvalidation = soup.find(id="__EVENTVALIDATION")['value']
    data = {
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstategenerator,
        '__EVENTVALIDATION': eventvalidation,
        'txtKW': '契約',
        'judtype': 'JUDBOOK',
        'whosub': '0',
        'ctl00$cp_content$btnSimpleQry': '送出查詢'
    }
    content = fetch_page(base_url, data=data)
    if not content:
        return
    iframe_src = parse_main_page(content)
    if not iframe_src:
        return
    iframe_url = details_base_url + iframe_src
    current_page_content = fetch_page(iframe_url)
    if not current_page_content:
        return

    fetched_count = 0
    page_number = 0
    output_file = 'judgment_data_analysis.csv'
    target_file = 'Target.csv'

    # 初始化 CSV 文件（覆蓋舊文件）
    with open(output_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=['序號', '案件名稱', '裁判日期', '裁判案由', '違約金類型', '案件類型數字'])
        writer.writeheader()
    with open(target_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['Target'])

    while fetched_count < 500:
        page_data, links = parse_results_page(current_page_content)
        if not page_data or not links:
            break
        for index, link in enumerate(links):
            if fetched_count >= 500:
                break
            detail_url = f"{details_base_url}{link}"
            detail_content = fetch_page(detail_url)
            if not detail_content:
                continue
            full_content = clean_content(detail_content)

            judgment_date = extract_judgment_date(detail_content)
            analysis_result = analyze_content_with_api(full_content)
            case_type_code = map_case_type_to_code(analysis_result)
            
            case_data = {
                '序號': fetched_count + 1,
                '案件名稱': page_data[index]['Title'],
                '裁判日期': judgment_date,
                '裁判案由': page_data[index]['SecondColumn'],
                '違約金類型': analysis_result,
                '案件類型數字': case_type_code
            }
            save_to_csv(case_data, output_file)
            save_to_target_csv(case_type_code, target_file)  # 同步寫入 Target.csv
            fetched_count += 1
        page_number += 1
        next_page_full_url = search_url_template.format(page=page_number)
        current_page_content = fetch_page(next_page_full_url)

if __name__ == '__main__':
    main()
