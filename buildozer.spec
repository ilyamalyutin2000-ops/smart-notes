[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

requirements = python3,kivy

orientation = portrait
fullscreen = 0

# РАЗРЕШЕНИЯ ДЛЯ ANDROID 13+
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# API 33 (Android 13)
android.api = 33
android.minapi = 21

# NDK 25b (совместим с Android 13)
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk_api = 21
warn_on_root = 0
