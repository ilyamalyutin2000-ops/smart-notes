[app]
title = TestApp
package.name = testapp
package.domain = org.testapp
source.dir = .
source.include_exts = py
version = 0.1

# Только базовый Kivy (никаких requests, jnius и т.д.)
requirements = python3,kivy

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
