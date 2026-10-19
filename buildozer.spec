[app]
title = TestApp
package.name = testapp
package.domain = org.testapp
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

# Только базовый Kivy
requirements = python3,kivy

orientation = portrait
fullscreen = 0

# Никаких разрешений
android.api = 30
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk_api = 21

warn_on_root = 0
