[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

# ФИКСИРУЕМ PYTHON 3.9 (чтобы pyjnius не сломался)
requirements = python3==3.9.16,hostpython3==3.9.16,kivy,requests

orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# Отключаем проверку root
warn_on_root = 0
log_level = 2
