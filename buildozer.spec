[app]



title = Умный конспект
package.name = smartnotes
package.domain = org.smartnotes
version = 0.1



source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json
source.exclude_dirs = .git,.github,.buildozer,bin,pycache



requirements = python3,kivy,requests



orientation = portrait
fullscreen = 0



android.permissions = INTERNET,ACCESS_NETWORK_STATE



android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True



warn_on_root = 0
