import smtplib
from time import sleep
from bs4 import BeautifulSoup
from lxml import etree
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from email.mime.text import MIMEText


def is_there_internet_connection():
    return (lambda a: True if 0 == a.system('ping 8.8.8.8 -n 3 -l 32 -w 3') else False)(__import__('os'))


def send_mail(from_mail_address, from_mail_password, to_mail_address, text):
    try:
        mail = smtplib.SMTP("smtp.gmail.com", 587)
        mail.ehlo()
        mail.starttls()
        mail.login(from_mail_address, from_mail_password)
        message = MIMEText(text, "plain", "utf-8")
        mail.sendmail(from_mail_address, to_mail_address, message.as_string())
        print("Mail successfully sent.")
        mail.close()
        return True
    except Exception as e:
        print("Unable to send mail:", e)
        return False


class GradeFetcherBot:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
       # self.sis_firat = webdriver.Chrome(options=chrome_options)
        self.sis_firat = webdriver.Chrome("chromedriver.exe")
        self.grades_page_url = ""

    def is_found(self, by, value):
        found = False
        try:
            self.sis_firat.find_element(by=by, value=value)
            found = True
        except Exception as e:
            print("Element not found:", e)
        finally:
            return found

    def login(self, username, password):
        self.sis_firat.get("https://jasig.firat.edu.tr/cas/login?service=https://obs.firat.edu.tr/oibs/ogrenci")
        self.sis_firat.find_element(by=By.NAME, value="username").send_keys(username)
        self.sis_firat.find_element(by=By.NAME, value="password").send_keys(password)
        self.sis_firat.find_element(by=By.CSS_SELECTOR, value="input[type=submit]").click()

        message = ""
        user_info = {}
        if self.is_found(By.ID, "msg"):
            message = "Username or password is incorrect"
        elif self.is_found(By.ID, "lblSonuclar"):
            message = "An unexpected error occurred, unable to login."
        else:
            try:
                user_page = self.sis_firat.page_source
                soup = BeautifulSoup(user_page, 'lxml')
                student_number_name_surname = soup.find("span", {"id": "lblOgrenciAdSoyad"}).text
                student_number = student_number_name_surname[0:9]
                name_surname = student_number_name_surname[12:]
                photo = soup.find("img", {"id": "imgPhoto"})['src']
                photo = photo.split("?")[1]
                message = "True"
                user_info = {
                    "student_number": student_number,
                    "name_surname": name_surname,
                    "photo": photo
                }

            except Exception as e:
                print("Error retrieving user information:", e)

        return message, user_info

    def logout(self):
        try:
            self.sis_firat.refresh()
            self.sis_firat.find_element(by=By.XPATH, value="//*[@id='form1']/div[6]/nav/ul[2]/li[3]").click()
            self.sis_firat.find_element(by=By.ID, value="btnLogout").click()
            self.sis_firat.get("https://jasig.firat.edu.tr/cas/login?service=https://obs.firat.edu.tr/oibs/ogrenci")
        except Exception as e:
            print("An error occurred while logging out:", e)

    def navigate_to_grades(self):
        try:
            WebDriverWait(self.sis_firat, 20).until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='proMenu']/li[3]"))).click()
            WebDriverWait(self.sis_firat, 20).until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='proMenu']/li[3]/ul/li[2]"))).click()
            self.grades_page_url = self.sis_firat.current_url
            self.sis_firat.switch_to.frame(self.sis_firat.find_element(by=By.ID, value="IFRAME1"))
        except Exception as e:
            print("An error occurred while navigating to the grades page:", e)

    def get_semesters(self):
        try:
            semesters = self.sis_firat.find_element(By.XPATH, "//*[@id='cmbDonemler']").text
            semesters = semesters.split('\n')
            return semesters
        except Exception as e:
            print("An error occurred while fetching semesters:", e)

    def select_semester(self, semester_index):
        try:
            self.sis_firat.find_element(By.XPATH, "//*[@id='cmbDonemler']/option[" + str(semester_index) + "]").click()
            sleep(1)
        except Exception as e:
            print("An error occurred while selecting the semester:", e)

    def fetch_grades(self):
        try:
            grades_page_html = self.sis_firat.page_source
            soup = BeautifulSoup(grades_page_html, 'lxml')
            grade_list = soup.find("table", {"class": "grdStyle"})
            lesson_count = len(grade_list.findAll("tr")) - 1
            dom = etree.HTML(str(grade_list))
            lesson_data = []
            for i in range(lesson_count):
                lesson_name = dom.xpath('//*[@id="grd_not_listesi"]/tbody/tr[' + str(i + 2) + ']/td[3]')[0].text
                midterm_grade = grade_list.find("span", {"id": "grd_not_listesi_lblSnv1_" + str(i)}).text.strip()
                final_grade = grade_list.find("span", {"id": "grd_not_listesi_lblSnv2_" + str(i)}).text.strip()
                makeup_grade = grade_list.find("span", {"id": "grd_not_listesi_lblSnv3_" + str(i)}).text.strip()
                mean = dom.xpath('//*[@id="grd_not_listesi"]/tbody/tr[' + str(i + 2) + ']/td[6]')[0].text
                letter_grade = dom.xpath('//*[@id="grd_not_listesi"]/tbody/tr[' + str(i + 2) + ']/td[7]')[0].text
                lesson_data.append({
                    "lesson_name": lesson_name,
                    "midterm_grade": midterm_grade if midterm_grade != "" else "--",
                    "final_grade": final_grade if final_grade != "" else "--",
                    "makeup_grade": makeup_grade if makeup_grade != "" else "--",
                    "letter_grade": mean + "/" + letter_grade
                })

            self.sis_firat.get(self.grades_page_url)
            return lesson_data

        except Exception as e:
            print("An error occurred while fetching grades:", e)

    def quit(self):
        self.sis_firat.quit()
