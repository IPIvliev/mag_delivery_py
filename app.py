import sys
import os
import pandas as pd
import logging
from html import escape
from services.input_validation import InputValidationError
from PyQt5 import QtWidgets, QtCore
from main_window import Ui_MainWindow
import main
from threading import Thread

from datetime import datetime

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
            QtCore.Q_ARG(str, f"<span style='color:{color}'>{escape(msg)}</span>")
        )

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    calculation_failed = QtCore.pyqtSignal(str)
    calculation_finished = QtCore.pyqtSignal()

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
        self.calculation_failed.connect(self.show_error)
        self.calculation_finished.connect(self.reset_calculation_button)
        self.btn_calculate.setEnabled(False)

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
        if not self.file_path:
            self.show_error("Файл не выбран!")
            return

        self.btn_calculate.setEnabled(False)
        self.btn_load.setEnabled(False)
        self.latitude.setEnabled(False)
        self.longitude.setEnabled(False)
        self.btn_calculate.setText("Идёт расчёт")
        
        try:
            logging.info(f"Чтение файла: {self.file_path}")
            
            self.main_point = (
                float(self.latitude.text().strip().replace(',', '.')),
                float(self.longitude.text().strip().replace(',', '.')),
            )
            logging.info(f"Координаты полигона: {self.main_point}")
           
            # Загрузка данных из файлов
            file_path = self.file_path
            self.kp_data = pd.read_excel(file_path, sheet_name='КП')
            self.auto_data = pd.read_excel(file_path, sheet_name='Авто')
            self.containers_data = pd.read_excel(file_path, sheet_name='Виды контейнеров')
            self.working_time_minutes = int(self.working_time.text())
            self.weight_coefficient = float(self.to_kg.text())
            self.map_distance_meters = int(self.accuracy.text()) * 1000
            self.fallback_distance_meters = int(self.distance.text())

            self.process_data()
            
        except Exception as e:
            self.reset_calculation_button()
            self.show_error(f"Ошибка: {str(e)}")

    def process_data(self):
        logging.info("Обработка данных")
        args = (self.kp_data, self.auto_data, self.main_point,
                self.containers_data, self.working_time_minutes,
                self.map_distance_meters, self.weight_coefficient,
                self.fallback_distance_meters, logging, self.checkBox.isChecked())
        self.calculation_thread = Thread(target=self.run_calculation, args=(args,), daemon=True)
        self.calculation_thread.start()

    def run_calculation(self, args):
        try:
            main.main(*args)
        except InputValidationError as error:
            self.calculation_failed.emit(str(error))
        except Exception as error:
            logging.exception("Расчёт остановлен")
            self.calculation_failed.emit(str(error))
        finally:
            self.calculation_finished.emit()

    def reset_calculation_button(self):
        self.btn_calculate.setText("Рассчитать")
        self.btn_calculate.setEnabled(bool(self.file_path))
        self.btn_load.setEnabled(True)
        self.latitude.setEnabled(True)
        self.longitude.setEnabled(True)

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