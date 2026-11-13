from __future__ import annotations

import threading
import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import AutoClickController


class StatusWindow:
    BG = "#17131f"
    PANEL = "#241d30"
    BORDER = "#433650"
    TEXT = "#f4eff8"
    MUTED = "#a99db3"
    GREEN = "#3bd671"
    YELLOW = "#f3c951"
    PURPLE = "#9b6cff"

    def __init__(self, controller: AutoClickController) -> None:
        self.controller = controller
        self._show_requested = threading.Event()
        self.root = tk.Tk()
        self.root.title("KiroClick")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", controller.settings.window_always_on_top)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Escape>", lambda _event: self.hide())
        self._position_window(390, 372)

        outer = tk.Frame(self.root, bg=self.BG, padx=14, pady=14)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=self.BG)
        header.pack(fill="x")
        tk.Label(
            header,
            text="KiroClick",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 16),
        ).pack(side="left")
        self.status_dot = tk.Canvas(header, width=14, height=14, bg=self.BG, highlightthickness=0)
        self.status_dot.pack(side="right", padx=(8, 0))
        self.status_text = tk.Label(
            header,
            text="STARTING",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI Semibold", 10),
        )
        self.status_text.pack(side="right")

        card = tk.Frame(outer, bg=self.PANEL, highlightbackground=self.BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(12, 10))
        card_inner = tk.Frame(card, bg=self.PANEL, padx=13, pady=11)
        card_inner.pack(fill="both")

        self.detail = tk.Label(
            card_inner,
            text="Starting screen monitor…",
            anchor="w",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 10),
        )
        self.detail.pack(fill="x")
        self.last_click = tk.Label(
            card_inner,
            text="Last click: No clicks yet",
            anchor="w",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        )
        self.last_click.pack(fill="x", pady=(7, 0))
        self.stats = tk.Label(
            card_inner,
            text="Templates: 0     Clicks: 0",
            anchor="w",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        )
        self.stats.pack(fill="x", pady=(3, 0))
        self.activity = tk.Label(
            card_inner,
            text="",
            anchor="w",
            justify="left",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 8),
        )
        self.activity.pack(fill="x", pady=(9, 0))

        buttons = tk.Frame(outer, bg=self.BG)
        buttons.pack(fill="x")
        self.toggle_button = self._button(buttons, "Pause", self.controller.toggle, primary=True)
        self.toggle_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._button(buttons, "Reload", self.controller.reload_templates).pack(
            side="left", fill="x", expand=True, padx=5
        )
        self._button(buttons, "Templates", self.controller.open_templates).pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )

        footer = tk.Frame(outer, bg=self.BG)
        footer.pack(fill="x", pady=(12, 0))
        self.hotkey_label = tk.Label(
            footer,
            text="",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 8),
        )
        self.hotkey_label.pack(side="left")
        self._link_button(footer, "Hide to tray", self.hide).pack(side="right", padx=(12, 0))
        self._link_button(footer, "Quit", lambda: self.controller.request_stop("UI quit button")).pack(
            side="right"
        )

    def _position_window(self, width: int, height: int) -> None:
        screen_width = self.root.winfo_screenwidth()
        x = max(0, screen_width - width - 24)
        self.root.geometry(f"{width}x{height}+{x}+24")

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: object,
        primary: bool = False,
    ) -> tk.Button:
        color = self.PURPLE if primary else self.PANEL
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=self.TEXT,
            activebackground="#7f54dc" if primary else "#332940",
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=7,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
        )

    def _link_button(self, parent: tk.Widget, text: str, command: object) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.BG,
            fg=self.MUTED,
            activebackground=self.BG,
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            padx=0,
            cursor="hand2",
            font=("Segoe UI", 8, "underline"),
        )

    @staticmethod
    def _format_hotkey(value: str) -> str:
        return value.replace("<", "").replace(">", "").replace("+", " + ").upper()

    def request_show(self) -> None:
        self._show_requested.set()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.controller.settings.window_always_on_top)

    def hide(self) -> None:
        self.root.withdraw()

    def _poll(self) -> None:
        snapshot = self.controller.snapshot()
        if snapshot.stopping:
            self.root.destroy()
            return
        if self._show_requested.is_set():
            self._show_requested.clear()
            self.show()

        if snapshot.template_count == 0:
            label, color = "NEEDS TEMPLATE", self.YELLOW
        elif snapshot.active and snapshot.dry_run:
            label, color = "DRY RUN", self.YELLOW
        elif snapshot.active:
            label, color = "ACTIVE", self.GREEN
        else:
            label, color = "PAUSED", self.YELLOW
        self.status_text.configure(text=label, fg=color)
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline="")
        self.detail.configure(text=snapshot.status_detail)
        self.last_click.configure(text=f"Last activity: {snapshot.last_click_text}")
        self.stats.configure(
            text=f"Templates: {snapshot.template_count}     Clicks this session: {snapshot.click_count}"
        )
        if snapshot.recent_events:
            self.activity.configure(text="Recent:\n" + "\n".join(snapshot.recent_events))
        else:
            self.activity.configure(text="Recent:\nNo activity yet")
        self.toggle_button.configure(text="Pause" if snapshot.active else "Resume")
        self.hotkey_label.configure(text=f"Toggle: {self._format_hotkey(snapshot.hotkey)}")
        self.root.after(250, self._poll)

    def run(self) -> None:
        self._poll()
        self.root.mainloop()

