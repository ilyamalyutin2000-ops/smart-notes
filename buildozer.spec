[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# Убрали jnius
requirements = python3==3.9.16,hostpython3==3.9.16,kivy==2.3.0,requests

orientation = portrait
fullscreen = 0

# Только интернет, никаких запросов к памяти!
android.permissions = INTERNET

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk_api = 21

warn_on_root = 0
log_level = 2
