# This is a self-impose LeMans challenge to build a web-scraper of the data provided freely from LeMans at https://live.24h-lemans.com/en/live.
# I have used Selenium to get the data and PyQt5 for the UI. I have also used QtDesigner for making the base UI.
# I must say that although this is not the best piece of code, I had much fun doing it and I have learnt a lot. 
# I am really tired, I have barely slept and maybe there are some nosense here or there :-)
# Happy coding!

# Robert Kubica Driver błyskawica
# Zawsze na wyścigach czadu da za trzech
# Robert Kubica cały świat zachwyca
# Gdy po torach śmiga aż zapiera dech

import time
import re
import sys
from datetime import datetime
from PyQt5 import uic
from PyQt5.QtCore import QObject, QThreadPool, pyqtSignal, pyqtSlot, QRunnable
from PyQt5.QtWidgets import QMainWindow, QApplication, QTableWidgetItem
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class Data:
    """ Manages all the data of the app. """

    def __init__(self, flag_state, weather_stats, drivers):
        self.flag = flag_state
        self.wind, self.air_temp, self.humidity, self.track_temp, self.pressure = weather_stats

        self.overall = drivers
        self.classes()

    def classes(self):
        """ Filter the main list into categories. Probably, this is not the best solution
            but is the simpler in order to avoid using a database."""

        print("--- CLASSES ---")

        self.hypercar = []
        self.lmp2 = []
        self.lmgtepro = []
        self.lmgteam = []

        for driver_stats in self.overall:
            # Driver class
            if re.match(driver_stats[2], "lm p2", re.IGNORECASE):
                self.lmp2.append(driver_stats)
            elif re.match(driver_stats[2], "lm gte am", re.IGNORECASE):
                self.lmgteam.append(driver_stats)
            elif re.match(driver_stats[2], "lm gte pro", re.IGNORECASE):
                self.lmgtepro.append(driver_stats)
            elif re.match(driver_stats[2], "hypercar h", re.IGNORECASE):
                self.hypercar.append(driver_stats)


class RefreshDataSignals(QObject):
    """ RefreshData's signals. """

    progress = pyqtSignal(object)


class RefreshData(QRunnable):
    """ Refresh all the data of the UI each 30 seconds. """

    def __init__(self):
        super(RefreshData, self).__init__()

        self.signals = RefreshDataSignals()

        service = Service(executable_path=ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument("start-maximized")
        options.add_argument("log-level=3")
        options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(20)
    
    @pyqtSlot()
    def run(self):
        # Open and wait to load info
        self.driver.get("https://live.24h-lemans.com/en/live")
        time.sleep(20)

        while True:
            print("--- Get the data from the web ---")
            # Get the flag state (green, yellow, red...)
            flag_state = self.driver.find_elements(By.XPATH, '//div[contains(@class,"race-state")]')[0].get_attribute("innerHTML")

            # Get the weather stats (wind, humidity...)
            weather_list = self.driver.find_elements(By.XPATH, '//div[@class="fcy"]//div[@class="weather-entry"]/div[@class="info"]')[1:]
            weather_stats = [weather.get_attribute("innerHTML") for weather in weather_list]

            # Get the overal leaderboard
            drivers = []
            leaderboard = self.driver.find_elements(By.XPATH, '//tbody[@class="tbody"]/tr')
            selectors = [".ranking span", ".status span", ".class span", ".team span", ".driver span span", ".car .model-wrapper  div:nth-child(2)", ".lap", ".classement", ".gap", ".int", ".last", ".spd", ".pit"]
            for stats in leaderboard:
                driver_stats = []
                for selector in selectors:
                    driver_stats.append(stats.find_element(By.CSS_SELECTOR, selector).get_attribute("innerHTML"))
                drivers.append(driver_stats)

            print("--- RefreshData: all data collected ---")
            self.signals.progress.emit(Data(flag_state, weather_stats, drivers))

            time.sleep(30)


class RemainingTimeSignals(QObject):
    """ Signals of RemainingTime's class. """

    progress = pyqtSignal(str)

class RemainingTime(QRunnable):
    """ Refresh the remaining time counter of the UI. """

    def __init__(self):
        super(RemainingTime, self).__init__()
        self.deadline = datetime(2022,6,12,16)
        self.signals = RemainingTimeSignals()
    
    @pyqtSlot()
    def run(self):
        while datetime.now() <= self.deadline:
            self.time_left = str(self.deadline - datetime.now()).split(".")[0]
            self.signals.progress.emit(self.time_left)
            time.sleep(1)


class LeMansUI(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("lemans.ui", self)

        # ThreadPool to manage two different threads at the same time.
        self.threadpool = QThreadPool()
        self.remaining_time()
        self.refresh_data()

        # Events

        self.show()

    def print_remaining_time(self, rt):
        """ Updates the counter in the UI. """

        self.lb_remaining_time.setText(rt)

    def remaining_time(self):
        """ Starts the counter of the remaining time. """

        print("--- Starting 'remaining_time' thread ---")

        rt = RemainingTime()
        self.threadpool.start(rt)
        rt.signals.progress.connect(self.print_remaining_time)
    
    def print_refreshed_data(self, data):
        """ Refresh the data gotten from the web page in the UI. """

        print("--- Refresh the data in the UI ---")
        # Flag
        self.lb_flag.setText(data.flag)
        self.lb_flag.setStyleSheet(f"background-color: {data.flag.split()[0].lower()}")

        # Weather stats
        self.lb_wind.setText(f"Wind: {data.wind}")
        self.lb_air_temp.setText(f"Air temp: {data.air_temp}")
        self.lb_humidity.setText(f"Humidity: {data.humidity}")
        self.lb_track_temp.setText(f"Track temp: {data.track_temp}")
        self.lb_pressure.setText(f"Pressure: {data.pressure}")

        # Leaderboard
        # Probably this is not the best option (or the most efficient) but the laziest one.
        # Overall, Hypercar, LM P2, LM GTE PRO, LM GTE AM
        tables = [self.tw_overall, self.tw_hypercar, self.tw_lmp2, self.tw_lmgtepro, self.tw_lmgteam]
        lists = [data.overall, data.hypercar, data.lmp2, data.lmgtepro, data.lmgteam]
        # print(tabs, tab_lists)
        for self.table, driver_list in zip(tables, lists):
            for row, driver_stats in enumerate(driver_list):
                # Inserts a new row
                self.table.removeRow(row)
                self.table.insertRow(row)
                # Insert value in the columns
                for column, stat in enumerate(driver_stats):
                    self.table.setItem(row, column, QTableWidgetItem(stat))

    def refresh_data(self):
        """ Starts the thread for refreshing the data each 30 seconds. """

        print("--- Starting 'refresh_data' thread ---")

        rd = RefreshData()
        self.threadpool.start(rd)
        rd.signals.progress.connect(self.print_refreshed_data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LeMansUI()
    win.show()
    sys.exit(app.exec())