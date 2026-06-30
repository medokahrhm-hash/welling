# wheel_widget.py
#
# الفرق الجوهري عن نسخة PyQt5:
# - PyQt5 يرسم عبر QPainter (واجهة سطح مكتب). Kivy يرسم عبر "canvas instructions"
#   (Mesh, Color, Line...) وهي أوامر GPU مباشرة تُبنى مرة وتبقى حتى تُعاد.
# - لا يوجد keyPressEvent على الموبايل، استبدلناه بـ on_touch_down/move/up
#   لرصد السحب (Swipe) كبديل لأسهم لوحة المفاتيح، والنقرة (Tap) كبديل لـ Enter.

import math
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, Mesh, Line, Ellipse
from kivy.properties import NumericProperty
from kivy.animation import Animation
from kivy.clock import Clock

from crypto_utils import encrypt_file_data, decrypt_file_data


def wedge_mesh_vertices(cx, cy, r_in, r_out, a_start, a_end, steps=14):
    """يبني شبكة مثلثات (triangle_strip) تُشكّل قطعة الكعكة (donut wedge)"""
    verts = []
    indices = []
    idx = 0
    for i in range(steps + 1):
        ang = a_start + (a_end - a_start) * i / steps
        rad = math.radians(ang)
        xin = cx + r_in * math.cos(rad)
        yin = cy + r_in * math.sin(rad)
        xout = cx + r_out * math.cos(rad)
        yout = cy + r_out * math.sin(rad)
        verts += [xin, yin, 0, 0, xout, yout, 0, 0]
        indices += [idx, idx + 1]
        idx += 2
    return verts, indices


class WheelWidget(Widget):
    angle = NumericProperty(0.0)

    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.current_folder_id = 1
        self.parent_folder_id = None
        self.folder_name = "ROOT"
        self.items = []
        self.labels = []  # عناصر Label فوق الرسم (Kivy لا يرسم نصاً داخل canvas مباشرة)

        self._touch_start_x = None
        self._touch_start_angle = 0.0
        self._dragged = False

        self.load_data()
        self.bind(angle=lambda *a: self.redraw())
        self.bind(size=lambda *a: self.redraw())
        self.bind(pos=lambda *a: self.redraw())
        Clock.schedule_once(lambda dt: self.redraw(), 0)

    # ---------- بيانات ----------
    def load_data(self):
        info = self.db.get_folder_details(self.current_folder_id)
        self.folder_name = info[0] if info else "ROOT"
        self.parent_folder_id = info[1] if info else None
        self.items = self.db.get_items_in_folder(self.current_folder_id)

    def get_active_index(self):
        if not self.items:
            return -1
        num = len(self.items)
        span = 360.0 / num
        for i in range(num):
            mid = (i * span) + self.angle - 90.0
            norm = (mid + 90.0) % 360.0
            if norm > 180:
                norm -= 360
            if abs(norm) < (span / 2.0):
                return i
        return 0

    # ---------- لمس بدل لوحة المفاتيح ----------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._touch_start_x = touch.x
        self._touch_start_angle = self.angle
        self._dragged = False
        return True

    def on_touch_move(self, touch):
        if self._touch_start_x is None:
            return False
        dx = touch.x - self._touch_start_x
        if abs(dx) > 8:
            self._dragged = True
        # كل 4 بكسل سحب = درجة دوران واحدة (يمكنك تعديل الحساسية هنا)
        self.angle = self._touch_start_angle + dx / 4.0
        return True

    def on_touch_up(self, touch):
        if self._touch_start_x is None:
            return False
        if not self._dragged:
            # نقرة بسيطة بدون سحب = تنفيذ العنصر النشط حالياً
            self.execute_active_item()
        else:
            # عند رفع الإصبع، نُلصق الدوران لأقرب عنصر (snap) بأنيميشن سلس
            self._snap_to_nearest()
        self._touch_start_x = None
        return True

    def _snap_to_nearest(self):
        if not self.items:
            return
        span = 360.0 / len(self.items)
        idx = self.get_active_index()
        target_offset = -(idx * span) + 0  # نعيد محاذاة العنصر النشط إلى 0
        # نحسب أقرب زاوية مكافئة لتفادي دوران طويل غير ضروري
        current = self.angle
        diff = (target_offset - current + 180) % 360 - 180
        anim = Animation(angle=current + diff, duration=0.25, t="out_quad")
        anim.start(self)

    def swipe_left(self):
        Animation(angle=self.angle - 45, duration=0.25, t="out_quad").start(self)

    def swipe_right(self):
        Animation(angle=self.angle + 45, duration=0.25, t="out_quad").start(self)

    # ---------- منطق التنفيذ (نفس منطق PyQt5 الأصلي) ----------
    def execute_active_item(self):
        idx = self.get_active_index()
        if idx == -1:
            return
        item_id, name, size, path, is_locked, is_app = self.items[idx]

        if is_locked == 1:
            self._ask_password(
                title=f"SECURITY ACCESS",
                message=f"الملف [{name}] مشفر! أدخل رمز الأمان لفك قفله:",
                on_submit=lambda pwd: self._do_unlock(item_id, path, pwd),
            )
            return

        if "Folder" in size:
            res = self.db.find_subfolder(name, self.current_folder_id)
            if res:
                self.current_folder_id = res[0]
            else:
                self.current_folder_id = self.db.add_folder(name, self.current_folder_id)
            self.load_data()
            self.angle = 0.0
            self.redraw()
            return

        self._info_popup("SYSTEM", f"محاولة فتح: {name}\n(فتح الملفات الخارجية على أندرويد يتطلب صلاحية Intent محددة)")

    def _do_unlock(self, item_id, path, pwd):
        if decrypt_file_data(path, pwd):
            self.db.update_lock_status(item_id, 0)
            self._info_popup("SUCCESS", "تم فك تشفير وقفل الملف بنجاح.")
            self.load_data()
            self.redraw()
        else:
            self._info_popup("ACCESS DENIED", "رمز الأمان خاطئ! فشل فك التشفير.")

    def go_to_parent_folder(self):
        if self.parent_folder_id is not None:
            self.current_folder_id = self.parent_folder_id
            self.load_data()
            self.angle = 0.0
            self.redraw()

    def trigger_lock_active_item(self):
        idx = self.get_active_index()
        if idx == -1:
            return
        item_id, name, size, path, is_locked, is_app = self.items[idx]
        if "Folder" in size:
            self._info_popup("SYSTEM", "تشفير المجلدات مباشرة غير مدعوم، يرجى تشفير الملفات بداخلها.")
            return

        self._ask_password(
            title="SECURE FILE",
            message=f"أدخل رمز الأمان لتشفير وقفل الملف [{name}]:",
            on_submit=lambda pwd: self._do_lock(item_id, path, pwd),
        )

    def _do_lock(self, item_id, path, pwd):
        import os
        if not os.path.exists(path):
            self._info_popup("SYSTEM", "لم يتم العثور على ملف حقيقي مرتبط بهذا العنصر بعد.\nاستخدم زر [ADD FILE] لربط ملف حقيقي أولاً.")
            return
        if encrypt_file_data(path, pwd):
            self.db.update_item_path(item_id, path)
            self._info_popup("SECURED", "تم قفل وتشفير محتويات الملف بنجاح عبر بروتوكول AES-256.")
            self.load_data()
            self.redraw()

    # ---------- نوافذ منبثقة بسيطة (بديل QInputDialog / QMessageBox) ----------
    def _ask_password(self, title, message, on_submit):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text=message))
        pwd_input = TextInput(password=True, multiline=False, size_hint_y=None, height=40)
        box.add_widget(pwd_input)
        btn_row = BoxLayout(size_hint_y=None, height=40, spacing=10)
        popup = Popup(title=title, content=box, size_hint=(0.85, 0.4))

        def submit(*_):
            popup.dismiss()
            if pwd_input.text:
                on_submit(pwd_input.text)

        ok_btn = Button(text="تأكيد")
        ok_btn.bind(on_release=submit)
        cancel_btn = Button(text="إلغاء")
        cancel_btn.bind(on_release=popup.dismiss)
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        box.add_widget(btn_row)
        popup.open()

    def _info_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.85, 0.35))
        popup.open()

    # ---------- الرسم ----------
    def redraw(self):
        self.canvas.clear()
        for lbl in self.labels:
            if lbl.parent:
                self.remove_widget(lbl)
        self.labels = []

        if self.width <= 0 or self.height <= 0:
            return

        cx, cy = self.center_x, self.center_y

        with self.canvas:
            Color(0.01, 0.03, 0.04, 1)
            from kivy.graphics import Rectangle
            Rectangle(pos=self.pos, size=self.size)

            Color(0, 1, 0.7, 0.25)
            Line(circle=(cx, cy, 130), width=1)

        # عنوان المجلد بالمنتصف
        title_lbl = Label(text="NEXUS CORE", bold=True, color=(0, 1, 0.78, 1),
                           font_size="16sp", size_hint=(None, None), size=(200, 30),
                           pos=(cx - 100, cy + 8))
        self.add_widget(title_lbl)
        self.labels.append(title_lbl)

        path_lbl = Label(text=f"/{self.folder_name}", color=(1, 1, 1, 1),
                          font_size="12sp", size_hint=(None, None), size=(240, 20),
                          pos=(cx - 120, cy - 14))
        self.add_widget(path_lbl)
        self.labels.append(path_lbl)

        if not self.items:
            return

        num = len(self.items)
        span = 360.0 / num
        gap = 4.0
        inner_r, outer_r = min(150, self.width * 0.18), min(self.width, self.height) * 0.42

        for i, (item_id, name, size, path, is_locked, is_app) in enumerate(self.items):
            start_angle = (i * span) + self.angle - 90.0 - (span - gap) / 2.0
            end_angle = start_angle + (span - gap)
            mid_angle = (start_angle + end_angle) / 2.0

            norm = (mid_angle + 90.0) % 360.0
            if norm > 180:
                norm -= 360
            is_active = abs(norm) < (span / 2.0)

            shift = 15 if is_active else 0
            rad = math.radians(mid_angle)
            wx = cx + shift * math.cos(rad)
            wy = cy + shift * math.sin(rad)

            verts, indices = wedge_mesh_vertices(wx, wy, inner_r, outer_r, start_angle, end_angle)

            with self.canvas:
                if is_active:
                    if is_locked == 1:
                        Color(100 / 255, 20 / 255, 20 / 255, 0.94)
                    else:
                        Color(80 / 255, 60 / 255, 20 / 255, 0.94)
                else:
                    Color(10 / 255, 25 / 255, 30 / 255, 0.82)
                Mesh(vertices=verts, indices=indices, mode="triangle_strip")

                if is_active:
                    Color(230 / 255, 180 / 255, 50 / 255, 0.9) if not is_locked else Color(1, 0.2, 0.2, 0.9)
                else:
                    Color(0, 150 / 255, 130 / 255, 0.5)

            tx = wx + ((inner_r + outer_r) / 2.0) * math.cos(rad)
            ty = wy + ((inner_r + outer_r) / 2.0) * math.sin(rad)

            icon = "🔒" if is_locked == 1 else ("📁" if "Folder" in size else ("⚙️" if is_app else "📄"))
            item_lbl = Label(
                text=f"{icon}\n{name[:12]}",
                halign="center", valign="middle",
                color=(1, 1, 1, 1) if is_active else (0.6, 0.7, 0.75, 1),
                font_size="11sp", bold=is_active,
                size_hint=(None, None), size=(110, 40),
                pos=(tx - 55, ty - 20),
            )
            item_lbl.bind(size=item_lbl.setter("text_size"))
            self.add_widget(item_lbl)
            self.labels.append(item_lbl)
