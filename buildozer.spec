[app]
title = Nexus Core
package.name = nexuscore
package.domain = org.nexus

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0

# المكتبات المطلوبة: kivy للواجهة، pycryptodome للتشفير، plyer لمنتقي الملفات
requirements = python3,kivy==2.3.0,pyjnius==1.6.1,pycryptodome,plyer

orientation = portrait
fullscreen = 1

# صلاحيات أندرويد المطلوبة للوصول للملفات
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 21
android.ndk = 25c
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
