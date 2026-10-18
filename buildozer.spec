[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# ПРИНУДИТЕЛЬНАЯ ЗАГРУЗКА С GITHUB (обход ошибки с 'long')
requirements = python3==3.9.16,hostpython3==3.9.16,kivy==https://github.com/kivy/kivy/archive/refs/tags/2.3.1.zip,jnius==https://github.com/kivy/pyjnius/archive/refs/tags/1.7.0.zip,requests

orientation = portrait
fullscreen = 0
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.ndk_api = 21

warn_on_root = 0
log_level = 2
