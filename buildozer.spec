[app]
title = TestApp
package.name = testapp
package.domain = org.testapp
source.dir = .
source.include_exts = py
version = 0.1

# Жестко фиксируем версии, чтобы ничего не сломалось
requirements = python3==3.9.16,hostpython3==3.9.16,kivy==2.3.0

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk_api = 21

warn_on_root = 0
log_level = 2
