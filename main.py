import tkinter as tk
from tkinter import font as tkfont
import time
import os


# ============================================================
# 大按钮：用原生 tk.Button + 超大尺寸 + 双层边框模拟精致感
#   （Canvas 自定义圆角在 PyInstaller 打包的 Tk 里会崩，所以用最稳的原生实现）
# ============================================================
class BigButton(tk.Button):
    """大号、好看、可靠的按钮 —— 点上去有亮/暗反馈，禁用时灰掉"""

    NORMAL = "normal"
    ACTIVE = "active"
    DISABLED = "disabled"

    def __init__(self, master, text, command, bg, hover_bg, pressed_bg,
                 fg="#ffffff", width_chars=12, font_size=16, bold=True,
                 border_color=None):
        self._bg = bg
        self._hover = hover_bg
        self._pressed = pressed_bg
        self._fg = fg
        self._disabled_bg = "#353547"
        self._disabled_fg = "#8a8da6"
        self._border = border_color or self._lighten(bg, 0.18)

        family = "Microsoft YaHei UI"
        self._font = (family, font_size, "bold" if bold else "normal")

        super().__init__(
            master,
            text=text,
            command=command,
            bg=self._bg,
            fg=self._fg,
            font=self._font,
            activebackground=self._pressed,   # 按下瞬间
            activeforeground=self._fg,
            disabledforeground=self._disabled_fg,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=2,
            highlightbackground=self._border,
            highlightcolor=self._border,
            cursor="hand2",
            width=width_chars,
            padx=8,
            pady=10,   # 上下加厚，让按钮变高（点得准）
            anchor="center",
            justify="center",
        )
        # hover / leave 用 Enter/Leave 模拟
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        # 按下瞬间压暗一点（比 activebackground 过渡更自然）
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")

    # ---------- 颜色工具 ----------
    @staticmethod
    def _lighten(hex_color, ratio=0.18):
        c = hex_color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        r = min(255, int(r + (255 - r) * ratio))
        g = min(255, int(g + (255 - g) * ratio))
        b = min(255, int(b + (255 - b) * ratio))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ---------- Hover / Press 反馈 ----------
    def _on_enter(self, _):
        if str(self["state"]) == tk.DISABLED:
            return
        try:
            self.config(bg=self._hover)
        except tk.TclError:
            pass

    def _on_leave(self, _):
        if str(self["state"]) == tk.DISABLED:
            return
        try:
            self.config(bg=self._bg)
        except tk.TclError:
            pass

    def _on_press(self, _):
        # 按下时背景
        if str(self["state"]) == tk.DISABLED:
            return
        try:
            self.config(bg=self._pressed)
        except tk.TclError:
            pass

    def _on_release(self, _):
        if str(self["state"]) == tk.DISABLED:
            return
        try:
            self.config(bg=self._hover)
        except tk.TclError:
            pass

    # ---------- 对外 API ----------
    def set_enabled(self, enabled):
        if enabled:
            self.config(state=tk.NORMAL, cursor="hand2", bg=self._bg)
        else:
            self.config(state=tk.DISABLED, cursor="arrow", bg=self._disabled_bg)

    def set_text(self, text):
        self.config(text=text)


# ============================================================
# 主程序
# ============================================================
class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("计时器")
        self.root.geometry("620x280")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)    # 无边框
        self.root.attributes("-topmost", True)

        # ===== 真正透明（Windows） =====
        self.TRANSPARENT_KEY = "#010203"
        try:
            self.root.attributes("-transparentcolor", self.TRANSPARENT_KEY)
        except tk.TclError:
            self.TRANSPARENT_KEY = None

        self.T = self.TRANSPARENT_KEY or "#151520"
        self.root.configure(bg=self.T)

        # 计时状态
        self.running = False
        self.elapsed_ms = 0
        self._tick_base = 0
        self._after_id = None

        # 拖动
        self._drag = {"x": 0, "y": 0}

        self._build_ui()
        self._bind_drag()
        self._bind_shortcuts()
        self._refresh_label()

    # ====================================================================
    # UI：背景全部使用透明色 self.T —— 除了文字和按钮，屏幕直接透出来
    # ====================================================================
    def _build_ui(self):
        T = self.T

        # ---- 右上角关闭（加大，更点得到） ----
        top_bar = tk.Frame(self.root, bg=T)
        top_bar.pack(fill="x", padx=22, pady=(10, 0))

        self._close_btn = tk.Label(
            top_bar, text="✕  关闭",
            font=("Microsoft YaHei UI", 11, "bold"),
            fg="#9da0b5", bg=T, cursor="hand2",
        )
        self._close_btn.pack(side="right")
        self._close_btn.bind("<ButtonRelease-1>", lambda e: self._quit())
        self._close_btn.bind("<Enter>", lambda e: self._close_btn.config(fg="#ff6b6b"))
        self._close_btn.bind("<Leave>", lambda e: self._close_btn.config(fg="#9da0b5"))

        # ---- 时间大字（白色 + 超大） ----
        time_area = tk.Frame(self.root, bg=T)
        time_area.pack(pady=(6, 4))

        fonts = set(tkfont.families())
        if "Consolas" in fonts:
            time_font = ("Consolas", 68, "bold")
        elif "Courier New" in fonts:
            time_font = ("Courier New", 68, "bold")
        else:
            time_font = ("Segoe UI", 68, "bold")

        self.time_label = tk.Label(
            time_area, text="00:00:00",
            font=time_font,
            fg="#ffffff",
            bg=T,
        )
        self.time_label.pack()

        self.ms_label = tk.Label(
            time_area, text=".00",
            font=("Segoe UI", 20, "bold"),
            fg="#d8dae6",
            bg=T,
        )
        self.ms_label.pack(pady=(0, 2))

        # ---- 三个大按钮（绿/橙/红，每个 size 160x60 级别） ----
        btn_area = tk.Frame(self.root, bg=T)
        btn_area.pack(pady=(4, 12))

        self.start_btn = BigButton(
            btn_area, text="开始", command=self.on_start,
            bg="#2ea043", hover_bg="#38b550", pressed_bg="#228a34",
            width_chars=11, font_size=17,
        )
        self.start_btn.pack(side="left", padx=12, ipady=4)

        self.pause_btn = BigButton(
            btn_area, text="暂停", command=self.on_pause,
            bg="#c9820b", hover_bg="#e09720", pressed_bg="#a76a08",
            width_chars=11, font_size=17,
        )
        self.pause_btn.pack(side="left", padx=12, ipady=4)

        self.stop_btn = BigButton(
            btn_area, text="结束清零", command=self.on_stop,
            bg="#b02a37", hover_bg="#d03242", pressed_bg="#8c1f2a",
            width_chars=11, font_size=17,
        )
        self.stop_btn.pack(side="left", padx=12, ipady=4)

        self._refresh_buttons_state()

    # ====================================================================
    # 拖动：按住任何非按钮/非关闭的空白或时间都能拖
    # ====================================================================
    def _bind_drag(self):
        targets = []

        def walk(w):
            if isinstance(w, BigButton):
                return
            if w is self._close_btn:
                return
            targets.append(w)
            for c in w.winfo_children():
                walk(c)

        for c in self.root.winfo_children():
            walk(c)

        for w in targets:
            w.bind("<ButtonPress-1>", self._drag_start, add="+")
            w.bind("<B1-Motion>", self._drag_move, add="+")

    def _drag_start(self, e):
        self._drag["x"] = e.x_root - self.root.winfo_x()
        self._drag["y"] = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._drag["x"]
        y = e.y_root - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    # ====================================================================
    # 快捷键
    # ====================================================================
    def _bind_shortcuts(self):
        self.root.bind_all("<Escape>", lambda e: self._quit())
        self.root.bind_all("<Key-space>", lambda e: self._space_handler())
        self.root.bind_all("<Key-r>", lambda e: self.on_stop())
        self.root.bind_all("<Key-R>", lambda e: self.on_stop())

    def _space_handler(self):
        if self.running:
            self.on_pause()
        else:
            self.on_start()

    # ====================================================================
    # 按钮状态机
    # ====================================================================
    def _refresh_buttons_state(self):
        if self.running:
            self.start_btn.set_enabled(False)
            self.pause_btn.set_enabled(True)
            self.stop_btn.set_enabled(True)
        else:
            self.start_btn.set_enabled(True)
            self.start_btn.set_text("继续" if self.elapsed_ms > 0 else "开始")
            self.pause_btn.set_enabled(False)
            self.stop_btn.set_enabled(self.elapsed_ms > 0)

    def on_start(self):
        if self.running:
            return
        self.running = True
        self._tick_base = time.perf_counter() * 1000 - self.elapsed_ms
        self._schedule()
        self._refresh_buttons_state()

    def on_pause(self):
        if not self.running:
            return
        self.running = False
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self._refresh_buttons_state()

    def on_stop(self):
        self.running = False
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self.elapsed_ms = 0
        self._refresh_label()
        self._refresh_buttons_state()

    # ====================================================================
    # 计时核心（perf_counter 不怕系统时间变）
    # ====================================================================
    def _schedule(self):
        self._after_id = self.root.after(25, self._tick)

    def _tick(self):
        if not self.running:
            return
        now = time.perf_counter() * 1000
        self.elapsed_ms = int(now - self._tick_base)
        self._refresh_label()
        self._schedule()

    def _refresh_label(self):
        t = self.elapsed_ms
        s_all = t // 1000
        h = s_all // 3600
        m = (s_all % 3600) // 60
        s = s_all % 60
        cs = (t % 1000) // 10
        self.time_label.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        self.ms_label.config(text=f".{cs:02d}")

    # ====================================================================
    # 退出（保险到底）
    # ====================================================================
    def _quit(self):
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self.running = False
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass
        os._exit(0)


def main():
    root = tk.Tk()
    w, h = 620, 280
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = int(sh * 0.25)
    root.geometry(f"{w}x{h}+{x}+{y}")
    TimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
