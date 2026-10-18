[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3==3.10.12,hostpython3==3.10.12,kivy,requests
orientation = portrait
fullscreen = 0

# Настройки Android
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET
android.allow_backup = True
android.accept_sdk_license = True
