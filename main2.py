import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import csv


DEBUG = False


def fetch_page(url, data=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    session = requests.Session()
    retries = Retry(total=10, backoff_factor=2, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        # 隨機延遲
        time.sleep(random.uniform(0.5, 1))
        if data:
            response = session.post(url, headers=headers, data=data, timeout=15)
        else:
            response = session.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch page: {url}, error: {e}")
        return None

    return response.text


def parse_main_page(content):
    soup = BeautifulSoup(content, 'html.parser')
    iframe_src = soup.find('iframe', {'id': 'iframe-data'})['src']
    return iframe_src


def parse_results_page(content):
    soup = BeautifulSoup(content, 'html.parser')
    titles = soup.select('.hlTitle_scroll')
    data = []
    links = []
    for title in titles:
        title_text = title.get_text(strip=True)
        link = title['href']
        links.append(link)

        # 找到同一層的下兩個 td 元素中的文字
        parent = title.find_parent('tr')
        if parent:
            tds = parent.find_all('td')
            second_text = tds[3].get_text(strip=True)
        else:
            second_text = ""

        data.append({'Title': title_text, 'SecondColumn': second_text, 'Link': link})

    return data, links


def parse_details_page(content):
    soup = BeautifulSoup(content, 'html.parser')
    full_content_element = soup.select_one('.htmlcontent')
    full_content = full_content_element.get_text(strip=True) if full_content_element else ""
    return full_content


def save_to_csv(data, filename):
    fieldnames = ['Title', 'SecondColumn', 'FullContent']
    filtered_data = {key: data[key] for key in fieldnames}
    with open(filename, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:  # write header only if file is empty
            writer.writeheader()
        writer.writerow(filtered_data)


def main():
    base_url = 'https://judgment.judicial.gov.tw/FJUD/default.aspx'
    details_base_url = 'https://judgment.judicial.gov.tw/FJUD/'
    search_url_template = 'https://judgment.judicial.gov.tw/FJUD/qryresultlst.aspx?q=dbd2b7b8c6282852972ea728025a1297&sort=DS&page={page}&ot=in'

    initial_content = fetch_page(base_url)
    if not initial_content:
        print("Failed to fetch the initial page.")
        return

    soup = BeautifulSoup(initial_content, 'html.parser')
    viewstate = soup.find(id="__VIEWSTATE")['value']
    viewstategenerator = soup.find(id="__VIEWSTATEGENERATOR")['value']
    eventvalidation = soup.find(id="__EVENTVALIDATION")['value']

    data = {
        '__VIEWSTATE': viewstate,
        '__VIEWSTATEGENERATOR': viewstategenerator,
        '__EVENTVALIDATION': eventvalidation,
        'txtKW': '工程契約&(懲罰性違約金+損害賠償性違約金)',
        'judtype': 'JUDBOOK',
        'whosub': '0',
        'ctl00$cp_content$btnSimpleQry': '送出查詢'
    }
    content = fetch_page(base_url, data=data)
    if not content:
        print("Failed to fetch the search results page.")
        return

    iframe_src = parse_main_page(content)
    iframe_url = details_base_url + iframe_src
    current_page_content = fetch_page(iframe_url)
    if not current_page_content:
        print("Failed to fetch the iframe content.")
        return

    if DEBUG:
        with open('debug_iframe_content_2.html', 'w', encoding='utf-8') as file:
            file.write(current_page_content)

    fetched_count = 0
    page_number = 0
    retry_attempts = 3
    retry_wait_time = 10  # 10 seconds
    output_file = 'judgment_data_2.csv'

    while fetched_count < 500:
        page_data, links = parse_results_page(current_page_content)
        if not page_data or not links:
            print("Failed to parse the results page.")
            break

        for index, link in enumerate(links):
            if fetched_count >= 500:
                break
            detail_url = details_base_url + link
            print(f"Fetching detail page: {detail_url}")
            detail_content = fetch_page(detail_url)
            if not detail_content:
                print(f"Failed to fetch detail page: {detail_url}")
                continue
            full_content = parse_details_page(detail_content)

            if page_data[index]['Title'] and page_data[index]['SecondColumn'] and full_content:
                page_data[index]['FullContent'] = full_content
                save_to_csv(page_data[index], output_file)
                fetched_count += 1

        # 構建下一頁的 URL
        page_number += 1
        next_page_full_url = search_url_template.format(page=page_number)
        print(f"Fetching next page: {next_page_full_url}")

        # 隨機延遲以避免被屏蔽
        time.sleep(random.uniform(3, 5))

        for attempt in range(retry_attempts):
            current_page_content = fetch_page(next_page_full_url)
            if current_page_content and "系統忙碌中" not in current_page_content:
                break
            print(
                f"Failed to fetch the next page, attempt {attempt + 1}/{retry_attempts}. Retrying in {retry_wait_time} seconds...")
            time.sleep(retry_wait_time)

        if not current_page_content or "系統忙碌中" in current_page_content:
            print("Failed to fetch the next page after several attempts. Exiting...")
            break

        with open(f'debug_page_{fetched_count}_2.html', 'w', encoding='utf-8') as file:
            file.write(current_page_content)


if __name__ == '__main__':
    main()
