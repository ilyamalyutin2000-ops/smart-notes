[app]
title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# ТОЛЬКО САМОЕ НЕОБХОДИМОЕ
requirements = python3,kivy

orientation = portrait
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk_api = 21
warn_on_root = 0
