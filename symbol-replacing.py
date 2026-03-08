#!/usr/bin/env python3
"""
sith_file_renamer.py

Dark "Sith mode" batch file renamer.
Safely renames only the filename stem while preserving the final extension
(e.g. .mp3, .avi, .txt) exactly as it is.
"""

import os
import re
import tkinter as tk

from tkinter import ttk, filedialog, messagebox


# Characters commonly treated as "special" in filenames.
PRESET_SYMBOLS = r'<>:"/\|?*[](){}!@#$%^&+=;,\''


def iter_files(root_folder: str, recursive: bool):
    """Yield (dirpath, filename) for all files in the selected folder."""
    if recursive:
        for dirpath, _, filenames in os.walk(root_folder):
            for fn in filenames:
                yield dirpath, fn
    else:
        for fn in os.listdir(root_folder):
            full = os.path.join(root_folder, fn)
            if os.path.isfile(full):
                yield root_folder, fn


def build_translation(remove_chars: str, replace_with: str):
    """Create a regex that replaces any chosen character with replace_with."""
    escaped = re.escape(remove_chars)
    pattern = re.compile(f"[{escaped}]")
    return pattern, replace_with


def split_name_preserve_extension(filename: str):
    """
    Split filename into (stem, ext), preserving only the final extension.

    Examples:
        "song.file.mp3" -> ("song.file", ".mp3")
        "video.avi"     -> ("video", ".avi")
        ".bashrc"       -> (".bashrc", "")
        "README"        -> ("README", "")
    """
    stem, ext = os.path.splitext(filename)

    # For dotfiles like ".bashrc", treat as no extension
    if not stem and ext:
        return filename, ""

    return stem, ext


def transform_filename(filename: str, pattern, replacement: str):
    """
    Rename only the stem of the file, never the extension.
    """
    stem, ext = split_name_preserve_extension(filename)
    new_stem = pattern.sub(replacement, stem)

    # Cleanup: avoid whitespace-only names
    new_stem = new_stem.strip()

    # Prevent invalid/empty result
    if not new_stem:
        new_stem = "renamed_file"

    return new_stem + ext


def make_unique_path(dirpath: str, filename: str):
    """
    If target exists, append _001, _002, ...
    Keeps the extension intact.
    """
    stem, ext = split_name_preserve_extension(filename)
    candidate = os.path.join(dirpath, filename)

    if not os.path.exists(candidate):
        return candidate

    i = 1
    while True:
        new_name = f"{stem}_{i:03d}{ext}"
        candidate = os.path.join(dirpath, new_name)
        if not os.path.exists(candidate):
            return candidate
        i += 1


class RenamerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sith File Renamer")
        self.geometry("1120x680")
        self.minsize(980, 600)
        self.configure(bg="#0b0b0b")

        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)

        self.use_preset_var = tk.BooleanVar(value=True)
        self.custom_symbols_var = tk.StringVar(value="")
        self.replace_with_var = tk.StringVar(value="_")
        self.dry_run_var = tk.BooleanVar(value=True)

        self.footer_var = tk.StringVar(value="Select a folder. Preview your changes before renaming.")

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg = "#0b0b0b"
        panel = "#141414"
        field = "#1d1d1d"
        red = "#b31217"
        red_hover = "#d11f27"
        text = "#f2f2f2"
        muted = "#b0b0b0"
        border = "#3a0d0f"

        style.configure(".", background=bg, foreground=text, font=("Segoe UI", 10))
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=panel, relief="flat")
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Muted.TLabel", background=bg, foreground=muted)
        style.configure("Title.TLabel", background=bg, foreground="#ff4d4d", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", background=bg, foreground="#ff7878", font=("Segoe UI", 10, "bold"))

        style.configure(
            "TEntry",
            fieldbackground=field,
            foreground=text,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            insertcolor=text,
            padding=6,
        )

        style.configure(
            "TCheckbutton",
            background=bg,
            foreground=text,
        )

        style.configure(
            "Red.TButton",
            background=red,
            foreground="white",
            borderwidth=0,
            focusthickness=0,
            padding=(14, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Red.TButton",
            background=[("active", red_hover), ("pressed", "#8d0e13")],
            foreground=[("disabled", "#888888"), ("!disabled", "white")],
        )

        style.configure(
            "Ghost.TButton",
            background=field,
            foreground=text,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(12, 8),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#2a2a2a"), ("pressed", "#151515")],
        )

        style.configure(
            "Treeview",
            background="#111111",
            foreground=text,
            fieldbackground="#111111",
            rowheight=28,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
        )
        style.configure(
            "Treeview.Heading",
            background="#1a1a1a",
            foreground="#ff6b6b",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", "#5a0c10")],
            foreground=[("selected", "white")],
        )

        style.configure(
            "Vertical.TScrollbar",
            background="#1a1a1a",
            troughcolor="#0f0f0f",
            bordercolor=border,
            arrowcolor="#ff6b6b",
        )

    def _build_ui(self):
        root_pad = {"padx": 14, "pady": 10}

        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", **root_pad)

        ttk.Label(header, text="SITH FILE RENAMER", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Rename files in bulk while protecting extensions like .mp3, .avi, .txt",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # Folder section
        folder_card = ttk.Frame(self, style="Card.TFrame")
        folder_card.pack(fill="x", **root_pad)

        ttk.Label(folder_card, text="TARGET FOLDER", style="Section.TLabel").pack(anchor="w", padx=12, pady=(12, 6))

        folder_row = ttk.Frame(folder_card, style="Card.TFrame")
        folder_row.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(folder_row, text="Browse", style="Ghost.TButton", command=self.choose_folder).pack(side="left")

        # Rules section
        rules_card = ttk.Frame(self, style="Card.TFrame")
        rules_card.pack(fill="x", **root_pad)

        ttk.Label(rules_card, text="RENAME RULES", style="Section.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(12, 8)
        )

        ttk.Checkbutton(
            rules_card,
            text="Include subfolders",
            variable=self.recursive_var,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=6)

        ttk.Checkbutton(
            rules_card,
            text="Use preset symbols",
            variable=self.use_preset_var,
            command=self._toggle_preset,
        ).grid(row=1, column=1, sticky="w", padx=12, pady=6)

        self.preset_label = ttk.Label(
            rules_card,
            text=f"Preset: {PRESET_SYMBOLS}",
            style="Muted.TLabel",
        )
        self.preset_label.grid(row=1, column=2, columnspan=2, sticky="w", padx=12, pady=6)

        ttk.Label(rules_card, text="Symbols to remove/replace:").grid(
            row=2, column=0, sticky="w", padx=12, pady=8
        )
        ttk.Entry(rules_card, textvariable=self.custom_symbols_var).grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=12, pady=8
        )

        ttk.Label(rules_card, text="Replace with:").grid(row=2, column=3, sticky="w", padx=(12, 6), pady=8)
        ttk.Entry(rules_card, textvariable=self.replace_with_var, width=12).grid(
            row=2, column=4, sticky="w", padx=(0, 12), pady=8
        )

        ttk.Checkbutton(
            rules_card,
            text="Preview only (no changes)",
            variable=self.dry_run_var,
        ).grid(row=3, column=0, sticky="w", padx=12, pady=(0, 12))

        for col in (1, 2):
            rules_card.columnconfigure(col, weight=1)

        # Action section
        action_row = ttk.Frame(self, style="TFrame")
        action_row.pack(fill="x", **root_pad)

        ttk.Button(action_row, text="Preview", style="Ghost.TButton", command=self.preview).pack(side="right")
        ttk.Button(action_row, text="Rename Files", style="Red.TButton", command=self.rename_files).pack(
            side="right", padx=(0, 8)
        )

        # Table
        table_card = ttk.Frame(self, style="Card.TFrame")
        table_card.pack(fill="both", expand=True, **root_pad)

        ttk.Label(table_card, text="RESULTS", style="Section.TLabel").pack(anchor="w", padx=12, pady=(12, 8))

        table_frame = ttk.Frame(table_card, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        cols = ("path", "old", "new", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")

        self.tree.heading("path", text="Folder")
        self.tree.heading("old", text="Old name")
        self.tree.heading("new", text="New name")
        self.tree.heading("status", text="Status")

        self.tree.column("path", width=360, anchor="w")
        self.tree.column("old", width=240, anchor="w")
        self.tree.column("new", width=240, anchor="w")
        self.tree.column("status", width=140, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        footer = ttk.Label(self, textvariable=self.footer_var, style="Muted.TLabel")
        footer.pack(fill="x", padx=16, pady=(0, 12))

        self._toggle_preset()

    def _toggle_preset(self):
        if self.use_preset_var.get():
            self.preset_label.state(["!disabled"])
        else:
            self.preset_label.state(["disabled"])

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose folder")
        if folder:
            self.folder_var.set(folder)

    def _get_remove_chars(self) -> str:
        chars = ""
        if self.use_preset_var.get():
            chars += PRESET_SYMBOLS
        chars += self.custom_symbols_var.get()

        # Deduplicate while keeping order
        seen = set()
        out = []
        for c in chars:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return "".join(out)

    def _compute_changes(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            raise ValueError("Please choose a valid folder.")

        remove_chars = self._get_remove_chars()
        if not remove_chars:
            raise ValueError("Please provide at least one symbol/character to remove or replace.")

        replace_with = self.replace_with_var.get()
        pattern, repl = build_translation(remove_chars, replace_with)

        changes = []
        for dirpath, old_name in iter_files(folder, self.recursive_var.get()):
            new_name = transform_filename(old_name, pattern, repl)

            if new_name != old_name:
                changes.append((dirpath, old_name, new_name))

        return changes

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def preview(self):
        try:
            changes = self._compute_changes()
        except Exception as e:
            messagebox.showerror("Preview error", str(e))
            return

        self._clear_tree()

        if not changes:
            self.footer_var.set("No files would change with these rules.")
            return

        for dirpath, old_name, new_name in changes[:5000]:
            self.tree.insert("", "end", values=(dirpath, old_name, new_name, "PREVIEW"))

        extra = "" if len(changes) <= 5000 else f" Showing first 5000 of {len(changes)}."
        self.footer_var.set(f"Preview ready. {len(changes)} file(s) would be renamed.{extra}")

    def rename_files(self):
        try:
            changes = self._compute_changes()
        except Exception as e:
            messagebox.showerror("Rename error", str(e))
            return

        if not changes:
            messagebox.showinfo("Nothing to do", "No files match your rename rules.")
            return

        if self.dry_run_var.get():
            messagebox.showinfo("Preview only enabled", "Disable 'Preview only' to apply the renaming.")
            return

        if not messagebox.askyesno(
            "Confirm rename",
            f"Rename {len(changes)} file(s)?\n\nExtensions will be preserved.\nThis cannot be undone.",
        ):
            return

        self._clear_tree()
        renamed = 0
        errors = 0

        for dirpath, old_name, new_name in changes:
            old_path = os.path.join(dirpath, old_name)
            target_path = make_unique_path(dirpath, new_name)
            target_name = os.path.basename(target_path)

            try:
                os.rename(old_path, target_path)
                renamed += 1
                self.tree.insert("", "end", values=(dirpath, old_name, target_name, "RENAMED"))
            except Exception as e:
                errors += 1
                self.tree.insert("", "end", values=(dirpath, old_name, new_name, f"ERROR: {e}"))

        self.footer_var.set(f"Completed. Renamed: {renamed} | Errors: {errors} | Planned: {len(changes)}")


def main():
    app = RenamerApp()
    app.mainloop()


if __name__ == "__main__":
    main()