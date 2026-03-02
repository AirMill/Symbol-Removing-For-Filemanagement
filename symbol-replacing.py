#!/usr/bin/env python3
"""
mac_renamer_gui.py
Simple macOS-friendly GUI app to batch rename files in a folder (optionally recursive),
removing selected symbols and/or replacing them with a new string.
"""

import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Characters that are commonly “special” in filenames. User can also type custom ones.
PRESET_SYMBOLS = r'<>:"/\|?*[](){}!@#$%^&+=;,\''


def iter_files(root_folder: str, recursive: bool):
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
    """
    For each char in remove_chars, replace it with replace_with (can be empty).
    """
    # We'll do this using regex char class. Escape characters for safe regex.
    # Example: remove_chars=" _-" replace_with="" -> remove underscores/spaces/dashes
    escaped = re.escape(remove_chars)
    pattern = re.compile(f"[{escaped}]")
    return pattern, replace_with


def make_unique_path(dirpath: str, filename: str):
    """
    If target exists, append _001, _002, ...
    """
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(dirpath, filename)
    if not os.path.exists(candidate):
        return candidate

    i = 1
    while True:
        new_name = f"{base}_{i:03d}{ext}"
        candidate = os.path.join(dirpath, new_name)
        if not os.path.exists(candidate):
            return candidate
        i += 1


class RenamerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple File Renamer (macOS)")
        self.geometry("920x560")
        self.minsize(820, 520)

        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)

        self.use_preset_var = tk.BooleanVar(value=True)
        self.custom_symbols_var = tk.StringVar(value="")
        self.replace_with_var = tk.StringVar(value="_")  # default replacement
        self.dry_run_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        # Top: folder pick
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Folder:").pack(side="left")
        ttk.Entry(top, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(top, text="Choose…", command=self.choose_folder).pack(side="left")

        # Options row
        opts = ttk.Frame(self)
        opts.pack(fill="x", **pad)

        ttk.Checkbutton(opts, text="Include subfolders", variable=self.recursive_var).pack(side="left")

        ttk.Checkbutton(
            opts, text="Use preset symbols", variable=self.use_preset_var, command=self._toggle_preset
        ).pack(side="left", padx=(18, 0))

        self.preset_label = ttk.Label(opts, text=f"Preset: {PRESET_SYMBOLS}")
        self.preset_label.pack(side="left", padx=8)

        # Custom symbols
        custom = ttk.Frame(self)
        custom.pack(fill="x", **pad)

        ttk.Label(custom, text="Symbols to remove/replace:").pack(side="left")
        ttk.Entry(custom, textvariable=self.custom_symbols_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(custom, text="Replace with:").pack(side="left")
        ttk.Entry(custom, textvariable=self.replace_with_var, width=10).pack(side="left", padx=(8, 0))

        # Dry run + actions
        actions = ttk.Frame(self)
        actions.pack(fill="x", **pad)

        ttk.Checkbutton(actions, text="Preview only (no changes)", variable=self.dry_run_var).pack(side="left")
        ttk.Button(actions, text="Preview", command=self.preview).pack(side="right")
        ttk.Button(actions, text="Rename", command=self.rename_files).pack(side="right", padx=(0, 8))

        # Results table
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, **pad)

        cols = ("path", "old", "new", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("path", text="Folder")
        self.tree.heading("old", text="Old name")
        self.tree.heading("new", text="New name")
        self.tree.heading("status", text="Status")

        self.tree.column("path", width=330)
        self.tree.column("old", width=210)
        self.tree.column("new", width=210)
        self.tree.column("status", width=120)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Footer
        self.footer_var = tk.StringVar(value="Choose a folder, set symbols, click Preview.")
        footer = ttk.Label(self, textvariable=self.footer_var)
        footer.pack(fill="x", padx=10, pady=(0, 10))

        self._toggle_preset()

    def _toggle_preset(self):
        # Just update the preset label visibility (the preset itself is used automatically when checked)
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
            raise ValueError("Please provide at least one symbol/character to remove/replace.")

        replace_with = self.replace_with_var.get()
        pattern, repl = build_translation(remove_chars, replace_with)

        changes = []
        for dirpath, old_name in iter_files(folder, self.recursive_var.get()):
            new_name = pattern.sub(repl, old_name)
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
            self.footer_var.set("No files would change with these settings.")
            return

        for dirpath, old_name, new_name in changes[:5000]:
            self.tree.insert("", "end", values=(dirpath, old_name, new_name, "PREVIEW"))

        more = "" if len(changes) <= 5000 else f" (showing first 5000 of {len(changes)})"
        self.footer_var.set(f"Preview ready: {len(changes)} file(s) would be renamed.{more}")

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
            messagebox.showinfo("Preview only enabled", "Disable 'Preview only' to actually rename files.")
            return

        # Confirm
        if not messagebox.askyesno("Confirm rename", f"Rename {len(changes)} file(s)? This cannot be undone."):
            return

        self._clear_tree()
        renamed = 0
        skipped = 0
        errors = 0

        for dirpath, old_name, new_name in changes:
            old_path = os.path.join(dirpath, old_name)

            # Make unique target if needed
            target_path = make_unique_path(dirpath, new_name)
            target_name = os.path.basename(target_path)

            try:
                os.rename(old_path, target_path)
                renamed += 1
                self.tree.insert("", "end", values=(dirpath, old_name, target_name, "RENAMED"))
            except Exception as e:
                errors += 1
                self.tree.insert("", "end", values=(dirpath, old_name, new_name, f"ERROR: {e}"))

        self.footer_var.set(f"Done. Renamed: {renamed}, Errors: {errors}, Total planned: {len(changes)}")


def main():
    # Improve macOS Tk behavior a bit (optional)
    try:
        import tkinter
        tkinter.Tk().destroy()
    except Exception:
        pass

    app = RenamerApp()
    app.mainloop()


if __name__ == "__main__":
    main()