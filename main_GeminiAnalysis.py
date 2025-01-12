from bs4 import BeautifulSoup
import time
import random
import csv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import requests  # 匯入 requests 模組

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
            "parts": [{"text": (
                f"以下是一段契約內容，請協助判斷其中內容是懲罰性還是損害賠償性，\n\n"
                f"分析依據：\n"
                f"懲罰性 (編號1)：\n"
                f"1. 涉及刑法或刑事內容。\n"
                f"2. 提及額外罰金。\n"
                f"3. 契約金或債權本金超出實際損害合理比例（損害20%-30%）以上。\n\n"
                f"損害賠償性(編號2)：\n"
                f"1. 條款內容提到返還、不當得利返還或程序費用，且沒有提及額外罰金。\n"
                f"2. 符合合理比例（損害20%-30%），且完全無超過30%以上。\n"
                f"3. 涉及當事方協商的和解金額，且沒有涉及刑法或刑事內容。\n\n"
                f"契約金額為第一優先級，契約金額接近於超出實際損害3倍以上，就是判定為懲罰性(編號1)。\n"
                f"契約內容只要一項符合懲罰性，就是優先判定為懲罰性(編號1)。\n"
                f"契約內容若無法確定，請務必選擇最接近的分類：(編號1)或(編號2)，不允許未知分類。\n\n"
                f"內容如下：\n{content}"
            )}]
        }]
    }
    try:
        response = requests.post(API_URL, params={'key': GEMINI_API_KEY}, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            analyzed_text = result['candidates'][0]['content']['parts'][0]['text']
            return refined_classification(content, analyzed_text)
        return "損害賠償性 (編號2)"
    except requests.exceptions.RequestException as e:
        print(f"API 呼叫失敗: {e}")
        return "損害賠償性 (編號2)"

# 進一步細化分類
def refined_classification(content, initial_classification):
    """
    通過文本特徵進一步細化的分類，優先判定為懲罰性。
    """
    # 強化懲罰性條件：即使沒有刑法或刑事條文，只要提到逾期、罰金等，仍然判定為懲罰性
    if any(keyword in content for keyword in ["判定為懲罰性"]):
        return "懲罰性 (編號1)"
    return initial_classification

# 將案件類型映射為數字代碼
def map_case_type_to_code(case_type):
    """
    將案件類型文字描述轉換為對應的數字代碼：
    懲罰性 (編號1) => 1, 損害賠償性 (編號2) => 2
    """
    if "(編號1)" in case_type:
        return 1
    elif "(編號2)" in case_type:
        return 2
    return 0

# 儲存案件資料到 judgment_data_analysis.csv
def save_to_csv(data, filename):
    """
    保存案件資料到 CSV 文件，包含新增的「最終違約金類型」欄位。
    """
    fieldnames = ['序號', '案件名稱', '裁判日期', '裁判案由', '違約金類型', '最終違約金類型', '案件類型數字']
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
    主函式，負責爬取資料並將結果儲存至 CSV 檔案。
    """
    base_url = 'https://judgment.judicial.gov.tw/FJUD/default.aspx'
    details_base_url = 'https://judgment.judicial.gov.tw/FJUD/'
    # search_url_template 變數在此整合範例中未使用，但可保留以防未來需要

    output_file = 'judgment_data_analysis.csv'
    target_file = 'Target.csv'

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

    # 初始化 CSV 文件（覆蓋舊文件），使用新增的欄位
    with open(output_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=['序號', '案件名稱', '裁判日期', '裁判案由', '違約金類型', '最終違約金類型', '案件類型數字'])
        writer.writeheader()
    with open(target_file, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['案件類型數字'])

    while fetched_count < 450:
        page_data, links = parse_results_page(current_page_content)
        if not page_data or not links:
            break
        for index, link in enumerate(links):
            if fetched_count >= 450:
                break
            detail_url = f"{details_base_url}{link}"
            detail_content = fetch_page(detail_url)
            if not detail_content:
                continue
            full_content = clean_content(detail_content)

            judgment_date = extract_judgment_date(detail_content)
            # 呼叫 API 分析內容，獲取最終分類結果
            final_type = analyze_content_with_api(full_content)
            case_type_code = map_case_type_to_code(final_type)

            case_data = {
                '序號': fetched_count + 1,
                '案件名稱': page_data[index]['Title'],
                '裁判日期': judgment_date,
                '裁判案由': page_data[index]['SecondColumn'],
                '違約金類型': final_type,           # 使用分析結果作為違約金類型
                '最終違約金類型': final_type,       # 最終違約金類型與分析結果相同
                '案件類型數字': case_type_code
            }
            save_to_csv(case_data, output_file)
            save_to_target_csv(case_type_code, target_file)  # 將案件類型數字寫入 Target.csv
            fetched_count += 1

        print(f"完成第 {page_number} 頁資料爬取，共計 {fetched_count} 筆資料...")
        page_number += 1

if __name__ == '__main__':
    main()
