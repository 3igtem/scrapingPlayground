from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import time

def get_dow30():
    url = 'https://www.cnbc.com/dow-30/'

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    time.sleep(5)

    table = driver.find_element(By.CLASS_NAME, 'BasicTable-tableBody')
    rows = table.find_elements(By.TAG_NAME, 'tr')

    data = []
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')
        if len(cols) < 8:
            continue

        data.append({'Date': current_datetime,
                     'Symbol': cols[0].text.strip(),
                     'Name': cols[1].text.strip(),
                     'Price': cols[2].text.strip(),
                     'Change': cols[3].text.strip(),
                     '% Change': cols[4].text.strip(),
                     'Low': cols[5].text.strip(),
                     'High': cols[6].text.strip(),
                     'Previous Close': cols[7].text.strip()
                     })

    driver.quit()
    return data