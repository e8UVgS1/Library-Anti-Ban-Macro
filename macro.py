from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import selenium.common.exceptions
import chromedriver_autoinstaller
from bs4 import BeautifulSoup
import time
import datetime
import os
import pgp
import true_email


def click_page(page_num):
    global driver
    page_num = int(page_num)
    req_ = driver.page_source
    soup_ = BeautifulSoup(req_, 'html.parser')
    soup_ = soup_.find(class_='pageNav')
    try:
        active_buttons = soup_.find_all(style='display: list-item;')
    except AttributeError:
        return
    page_string = 'pageNav' + str(page_num)
    for button in active_buttons:
        if page_string in str(button):
            click_button = button
            break
        elif 'next' in str(button):
            click_class = button['class'][0]
            driver.find_element(By.CLASS_NAME, click_class).click()
            click_page(page_num)
            return
    if 'currentPage' in str(click_button):
        return
    click_class = click_button['class'][0]
    driver.find_element(By.CLASS_NAME, click_class).click()


def get_driver():
    # 크롬 드라이버
    chrome_ver = chromedriver_autoinstaller.get_chrome_version().split('.')[0]  # 크롬 버전 확인
    chrome_option = webdriver.ChromeOptions()
    chrome_option.add_argument('--headless')
    chrome_option.add_argument('--no-sandbox')
    chrome_option.add_argument('--disable-dev-shm-usage')
    try:
        s = Service(f'/{chrome_ver}/chromedriver')
        driver_ = webdriver.Chrome(service=s, options=chrome_option)
    except selenium.common.exceptions.WebDriverException:
        chromedriver_autoinstaller.install(True)
        s = Service(f'/{chrome_ver}/chromedriver')
        driver_ = webdriver.Chrome(service=s, options=chrome_option)
    driver_.implicitly_wait(20)
    return driver_


# 크롬 드라이버
driver = get_driver()

snu_id = os.environ.get('SNU_ID')
snu_password = os.environ.get('SNU_PW')

# 도서관 페이지 열기
driver.get(url='http://k-rsv.snu.ac.kr:8011/NEW_SNU_BOOKING/pc/login/form')
driver.delete_all_cookies()

# 로그인
driver.find_element(By.NAME, 'id').send_keys(snu_id)
driver.find_element(By.NAME, 'pw').send_keys(snu_password)
time.sleep(3)
driver.find_element(By.ID, 'loginBtn').click()

# 예약 확인
driver.find_element(By.ID, 'tabMyBooking').click()  # 나의 예약현황

req = driver.page_source
soup = BeautifulSoup(req, 'html.parser')

soup = soup.find(id='bookListDiv')
book_list = soup.find_all('tr')

for book in book_list:
    if '예약완료' in str(book):  # 예약부도
        start_time = book.contents[3].div.string
        start_date = book.contents[1].div.string
        start_datetime = start_date + ' ' +start_time
        start_datetime = start_datetime.strip('\t')
        start_datetime = datetime.datetime.strptime(start_datetime, '%Y-%m-%d %H:%M')
        penalty_time = start_datetime + datetime.timedelta(minutes=30)
        remaining_time = penalty_time - datetime.datetime.now()
        remaining_time = remaining_time.total_seconds()
        if remaining_time < 600:  # 예약 부도까지 남은 시간이 10분 미만일 때
            page_num = book['class'][0]
            page_num = page_num.strip('page')
            click_page(page_num)
            cancel_button = book.find(class_='btn_studyroom_reservation')
            cancel_button = cancel_button.a.attrs['href']
            xpath = '//a[@href="' + cancel_button + '"]'
            cancel_button = driver.find_element(By.XPATH, xpath)
            cancel_button.click()
            time.sleep(1)
            driver.switch_to.alert.accept()  # 예약 취소하시겠습니까?
            time.sleep(1)
            driver.switch_to.alert.accept()  # 예약 취소되었습니다.
            print('예약 취소함')
            body = f'예약 취소함\n좌석 번호 : {book.contents[2].div.string}\n예약 시간 : {start_time}'
            true_email.self_email('도서관', pgp.encrypt(body))
    if '사용중' in str(book):  # 좌석 미반납
        end_time = book.contents[4].div.string
        end_date = book.contents[1].div.string
        end_datetime = end_date + ' ' + end_time
        end_datetime = end_datetime.strip('\t')
        end_datetime = datetime.datetime.strptime(end_datetime, '%Y-%m-%d %H:%M')
        remaining_time = end_datetime - datetime.datetime.now()
        remaining_time = remaining_time.total_seconds()
        if remaining_time < 600:  # 좌석 자동 반납까지 남은 시간이 10분 미만일 때
            page_num = book['class'][0]
            page_num = page_num.strip('page')
            click_page(page_num)
            cancel_button = book.find(class_='btn_studyroom_reservation')
            cancel_button = cancel_button.a.attrs['href']
            xpath = '//a[@href="' + cancel_button + '"]'
            cancel_button = driver.find_element(By.XPATH, xpath)
            cancel_button.click()
            time.sleep(1)
            driver.switch_to.alert.accept()  # 좌석을 반납하시겠습니까?
            time.sleep(1)
            driver.switch_to.alert.accept()  # 좌석 반납
            print('좌석 반납함')
            body = f'좌석 반납함\n좌석 번호 : {book.contents[2].div.string}\n반납 시간 : {end_time}'
            true_email.self_email('도서관', pgp.encrypt(body))

driver.quit()
