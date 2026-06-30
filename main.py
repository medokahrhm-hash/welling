# main.py
#
# نقطة التشغيل الرئيسية. الفرق الجوهري عن PyQt5:
# - QFileDialog (سطح مكتب فقط) -> استبدلناه بـ plyer.filechooser الذي
#   يفتح منتقي الملفات الأصلي لأندرويد (Storage Access Framework).
# - QMainWindow + setGeometry الثابتة -> استبدلناها بتخطيطات Kivy المرنة
#   (BoxLayout/FloatLayout) التي تتكيف تلقائياً مع كل أحجام الشاشات.

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window

from database import NexusDB
from wheel_widget import WheelWidget

try:
    from plyer import filechooser
    HAS_FILECHOOSER = True
except Exception:
    HAS_FILECHOOSER = False


class RootLayout(FloatLayout):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.wheel = WheelWidget(db, size_hint=(1, 1))
        self.add_widget(self.wheel)

        # شريط أزرار سفلي (بديل اللوحتين الجانبيتين الثابتتين بالنسخة الأصلية،
        # على الموبايل الشاشة ضيقة فجمعناها بشريط واحد قابل للمس)
        bottom_bar = BoxLayout(
            orientation="horizontal", spacing=8, padding=8,
            size_hint=(1, None), height=60,
            pos_hint={"x": 0, "y": 0},
        )

        btn_back = Button(text="⬅ رجوع")
        btn_back.bind(on_release=lambda *_: self.wheel.go_to_parent_folder())

        btn_lock = Button(text="🔒 قفل/تشفير")
        btn_lock.bind(on_release=lambda *_: self.wheel.trigger_lock_active_item())

        btn_add = Button(text="➕ إضافة ملف")
        btn_add.bind(on_release=lambda *_: self.add_real_file())

        btn_left = Button(text="◀")
        btn_left.bind(on_release=lambda *_: self.wheel.swipe_left())

        btn_right = Button(text="▶")
        btn_right.bind(on_release=lambda *_: self.wheel.swipe_right())

        for b in (btn_back, btn_left, btn_right, btn_lock, btn_add):
            bottom_bar.add_widget(b)

        self.add_widget(bottom_bar)

    def add_real_file(self):
        """يفتح منتقي ملفات النظام (يعمل على أندرويد وسطح المكتب عبر plyer)"""
        if not HAS_FILECHOOSER:
            self.wheel._info_popup("SYSTEM", "منتقي الملفات غير متاح على هذه المنصة.")
            return

        def on_selection(selection):
            if not selection:
                return
            path = selection[0]
            import os
            name = os.path.basename(path)
            self.db.add_item(self.wheel.current_folder_id, name, path, "File", 0, 0)
            self.wheel.load_data()
            self.wheel.redraw()

        try:
            filechooser.open_file(on_selection=on_selection)
        except Exception as e:
            self.wheel._info_popup("ERROR", f"فشل فتح منتقي الملفات: {e}")


class NexusApp(App):
    def build(self):
        Window.clearcolor = (0.01, 0.03, 0.04, 1)
        self.db = NexusDB()
        return RootLayout(self.db)


if __name__ == "__main__":
    NexusApp().run()
