[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# ЖЕСТКО ФИКСИРУЕМ PYTHON 3.9 (спасает от багов с jnius и long)
# Убрали plyer, оставили только рабочие библиотеки
requirements = python3==3.9.16,hostpython3==3.9.16,kivy==2.3.0,requests,jnius

orientation = portrait
fullscreen = 0

# РАЗРЕШЕНИЯ: Интернет + Доступ к файлам (для чтения фото из памяти)
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.ndk_api = 21

# Отключаем проверку на root (чтобы не было вопросов в GitHub Actions)
warn_on_root = 0
log_level = 2
