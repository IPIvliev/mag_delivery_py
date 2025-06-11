import sys
import os
import pandas as pd
import logging
from PyQt5 import QtWidgets, QtCore
from main_window import Ui_MainWindow
import main
from threading import Thread

from datetime import datetime

# Nuitka for compilation

class QTextEditLogger(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.widget = text_widget
        self.colors = {
            logging.DEBUG: "gray",
            logging.INFO: "black",
            logging.WARNING: "orange",
            logging.ERROR: "red",
            logging.CRITICAL: "darkred"
        }

    def emit(self, record):
        msg = self.format(record)
        color = self.colors.get(record.levelno, "black")
        QtCore.QMetaObject.invokeMethod(
            self.widget,
            'appendHtml',
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, f"<span style='color:{color}'>{msg}</span>")
        )

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.file_path = None
        self.df = None
        
        self.init_logger()
        self.setup_connections()
        
        logging.info("Приложение запущено")
        self.log_text.setMaximumBlockCount(1000)

    def setup_connections(self):
        self.btn_load.clicked.connect(self.load_file)
        self.btn_calculate.clicked.connect(self.calculate_data)

    def init_logger(self):
        os.makedirs('logs', exist_ok=True)
        log_file = f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"
        
        text_handler = QTextEditLogger(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
                text_handler
            ]
        )

    def load_file(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "Выберите файл Excel", 
            "", 
            "Excel Files (*.xlsx *.xls)", 
            options=options
        )
        
        if file_path:
            self.file_path = file_path
            self.label_path.setText(f"Выбран файл: {os.path.basename(file_path)}")
            self.btn_calculate.setEnabled(True)
            logging.info(f"Загружен файл: {file_path}")

    def calculate_data(self):
        self.btn_calculate.setEnabled(False)
        self.btn_calculate.setText("Идёт расчёт")

        if not self.file_path:
            self.show_error("Файл не выбран!")
            return
        
        try:
            logging.info(f"Чтение файла: {self.file_path}")
            
            # self.main_point = (float(56.2509833), float(43.8318333)) # База
            self.latitude = float(self.latitude.text())
            self.longitude = float(self.longitude.text())
            self.main_point = (self.latitude, self.longitude) # Полигон
           
            # Загрузка данных из файлов
            file_path = self.file_path
            self.kp_data = pd.read_excel(file_path, sheet_name='КП')
            self.auto_data = pd.read_excel(file_path, sheet_name='Авто')
            self.containers_data = pd.read_excel(file_path, sheet_name='Виды контейнеров')
            self.working_time = int(self.working_time.text())
            self.to_kg = float(self.to_kg.text())
            self.accuracy = int(self.accuracy.text()+'000')

            self.process_data()
            
        except Exception as e:
            self.show_error(f"Ошибка: {str(e)}")

    def process_data(self):
        try:
            try:
                os.remove(f"results/result.xlsx")
                os.remove(f"results/result_optimize.xlsx")
            except:
                pass
            logging.info("Обработка данных")
            t1 = Thread(target=main.main, args=(self.kp_data, self.auto_data, self.main_point, self.containers_data, self.working_time, int(self.accuracy), float(self.to_kg), logging), daemon=True)
            t1.start()
            
        except Exception as e:
            logging.error(f"Ошибка обработки данных: {str(e)}")
            raise

    # def save_results(self):
    #     try:
    #         os.makedirs('results', exist_ok=True)
    #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #         output_file = f"results/result_{timestamp}.xlsx"
    #         self.df.to_excel(output_file, index=False)
    #         logging.info(f"Результаты сохранены: {output_file}")
    #     except Exception as e:
    #         logging.error(f"Ошибка сохранения файла: {str(e)}")
    #         raise

    def show_error(self, message):
        logging.error(message)
        QtWidgets.QMessageBox.critical(
            self, 
            "Ошибка", 
            message, 
            QtWidgets.QMessageBox.Ok
        )

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())