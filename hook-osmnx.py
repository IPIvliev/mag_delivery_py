from PyInstaller.utils.hooks import copy_metadata

# Скопировать все метаданные (dist-info) для пакета osmnx
datas = copy_metadata('osmnx')