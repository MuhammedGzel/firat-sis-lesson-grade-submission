import os
import sys
from datetime import datetime
from threading import Thread

from time import sleep

import requests
from PyQt5 import uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QIntValidator, QPixmap
from PyQt5.QtWidgets import QLineEdit, QMessageBox, QApplication, QMainWindow, QTableWidgetItem
from bot import GradeFetcherBot, is_there_internet_connection
from database_operations import GradeDatabase


def show_message(msg_type, title, text):
    msg_box = QMessageBox()
    if msg_type == "information":
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    if msg_type == "error":
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    if msg_type == "question":
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
    msg_box.setWindowIcon(QIcon("GUI/images/firat_logo.png"))
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    return msg_box.exec_()


class FetchGradesThread(QThread):
    insert_table_signal = pyqtSignal(list)
    stop_signal = pyqtSignal()

    def __init__(self, grade_fetcher_bot, grade_database, semester):
        super().__init__()
        self.grade_fetcher_bot = grade_fetcher_bot
        self.grade_database = grade_database
        self.semester = semester
        self.running = False

    def run(self):
        try:
            semester_current_index = self.semester.currentIndex()
            semester = self.semester.currentText()

            self.running = True
            while self.running:
                if self.grade_database.is_table_empty(semester):
                    self.fetch_grades_and_insert_database(semester_current_index + 1, semester)
                lesson_data = self.grade_database.fetch_grades_from_database(semester)
                self.insert_table_signal.emit(lesson_data)
                print("Running")
        except Exception as e:
            print(e)

    def fetch_grades_and_insert_database(self, semester_current_index, semester):
        self.grade_fetcher_bot.navigate_to_grades()
        self.grade_fetcher_bot.select_semester(semester_current_index)
        lesson_data = self.grade_fetcher_bot.fetch_grades()
        self.grade_database.create_semester_table(semester)
        self.grade_database.insert_grades_to_database(semester, lesson_data)

    def stop(self):
        self.running = False
        self.stop_signal.emit()


class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()
        uic.loadUi("GUI/interface.ui", self)
        self.set_ui_for_login_screen()
        self.main_directory = os.getcwd()
        self.show_hide_password_control = False
        self.grade_fetcher_bot = GradeFetcherBot()
        self.grade_database = GradeDatabase(self.main_directory + "/grades.accdb")
        self.fetch_grades_thread = FetchGradesThread(self.grade_fetcher_bot, self.grade_database, self.semester)

        self.username.setValidator(QIntValidator())

        self.connect_signals()
        self.set_grade_table_columns()

    def set_grade_table_columns(self):
        column_widths = [260, 80, 50, 80, 80]
        for i, width in enumerate(column_widths):
            self.grade_table.setColumnWidth(i, width)

    def connect_signals(self):
        self.show_hide_password.clicked.connect(self.show_hide_password_action)
        self.login.clicked.connect(self.login_action)
        self.semester.currentIndexChanged.connect(self.start_fetch_grades_thread)
        self.fetch_grades_thread.insert_table_signal.connect(self.insert_grades_to_table)
        self.logout.clicked.connect(self.logout_action)

    def set_login_screen_state(self, state):
        self.login_screen_widget.setVisible(state)
        self.login_screen_widget.setEnabled(state)

    def set_grades_screen_state(self, state):
        self.grades_screen_widget.setVisible(state)
        self.grades_screen_widget.setEnabled(state)

    def set_ui_for_login_screen(self):
        self.set_grades_screen_state(False)
        self.mail_host.setCurrentIndex(0)
        self.semester.clear()
        self.grade_table.setRowCount(0)
        self.username.setText("")
        self.password.setText("")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.set_login_screen_state(True)
        self.setFixedHeight(425)

    def set_ui_for_grades_screen(self):
        self.mail_username.setText(self.username.text())
        self.set_login_screen_state(False)
        self.set_grades_screen_state(True)
        self.setFixedHeight(815)

    def show_hide_password_action(self):
        if not self.show_hide_password_control:
            self.show_hide_password.setIcon(QIcon("GUI/images/gizle.png"))
            self.password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_hide_password_control = True
        else:
            self.show_hide_password.setIcon(QIcon("GUI/images/goster.png"))
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_hide_password_control = False

    def login_action(self):
        if is_there_internet_connection():
            message, user_info = self.grade_fetcher_bot.login(self.username.text(), self.password.text())
            if message == "True":
                self.name_surname.setText(user_info['name_surname'])
                self.student_number.setText(user_info['student_number'])
                self.download_profile_photo("https://obs.firat.edu.tr/oibs/zfs.aspx?" + user_info['photo'])
                self.grade_fetcher_bot.navigate_to_grades()
                self.semester.addItems(self.grade_fetcher_bot.get_semesters())
                self.set_ui_for_grades_screen()
            else:
                show_message("error", "Error", message)
        else:

            show_message("error", "Error", "Check your internet connection")

    def download_profile_photo(self, photo_url):
        try:
            print(photo_url)
            response = requests.get(photo_url, stream=True)
            if response.status_code == 200:
                with open("GUI/images/user_image.jpg", 'wb') as file:
                    file.write(response.content)
                pixmap = QPixmap("GUI/images/user_image.jpg")
                self.photo.setPixmap(pixmap.scaled(85, 85))
                self.photo.setStyleSheet("border:2px; border-radius:22px")
            else:
                print("Photo download failed.")
        except Exception as e:
            print("Photo could not be added.", e)

    def insert_grades_to_table(self, lesson_data):
        self.grade_table.setRowCount(len(lesson_data))
        for i, lesson in enumerate(lesson_data):
            for j in range(5):
                self.grade_table.setRowHeight(i, 5)
                self.grade_table.setItem(i, j, QTableWidgetItem(lesson[j]))
                if j != 0:
                    self.grade_table.item(i, j).setTextAlignment(Qt.AlignCenter)

    def start_fetch_grades_thread(self):
        try:
            if self.fetch_grades_thread.running:
                self.fetch_grades_thread.terminate()
            self.fetch_grades_thread.start()
        except Exception as e:
            print(e)

    def logout_action(self):
        self.fetch_grades_thread.stop()
        if is_there_internet_connection():
            self.grade_fetcher_bot.logout()
        self.set_ui_for_login_screen()

    def closeEvent(self, event):
        ques = show_message("question", "Close Program", "Are you sure you want to close the program?")
        if ques == QMessageBox.Yes:
            self.fetch_grades_thread.exit()
            self.grade_fetcher_bot.quit()
            self.grade_database.close()
            os.system('wmic process where name="chromedriver.exe" delete')
            os.system('wmic process where name="python.exe" delete')
            event.accept()
        else:
            event.ignore()


app = QApplication(sys.argv)
UIWindow = UI()
UIWindow.show()
app.exec_()
