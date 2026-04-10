"""
Main GUI Application
TikTok Multi-Poster Desktop App using CustomTkinter.
"""

import os
import time
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.account_manager import AccountManager
from core.auth import OAuthManager
from core.api import TikTokClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Configure CustomTkinter
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class TikTokMultiPoster(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("TikTok Multi-Poster")
        self.geometry("900x700")
        self.minsize(800, 600)

        self.account_manager = AccountManager()
        self.oauth_manager: OAuthManager | None = None

        self._build_ui()
        self._refresh_accounts()

    # ────────────────────────────────
    # UI Building
    # ────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self)
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.header.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header, text="TikTok Multi-Poster",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.add_account_btn = ctk.CTkButton(
            self.header, text="＋ Add Account",
            command=self._add_account,
        )
        self.add_account_btn.grid(row=0, column=2, padx=10, pady=10)

        # Main content
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Left panel: Accounts
        self.accounts_panel = ctk.CTkFrame(self.main_frame, width=250)
        self.accounts_panel.grid(
            row=0, column=0, sticky="nsew", padx=(0, 5), pady=0
        )
        self.accounts_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.accounts_panel, text="Accounts",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.accounts_scroll = ctk.CTkScrollableFrame(
            self.accounts_panel
        )
        self.accounts_scroll.grid(
            row=1, column=0, sticky="nsew", padx=5, pady=5
        )
        self.accounts_scroll.grid_columnconfigure(0, weight=1)

        self.account_checkboxes: dict = {}

        # Right panel: Upload
        self.upload_panel = ctk.CTkFrame(self.main_frame)
        self.upload_panel.grid(
            row=0, column=1, sticky="nsew", padx=(5, 0), pady=0
        )
        self.upload_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.upload_panel, text="Upload Video",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # File selection
        self.file_frame = ctk.CTkFrame(self.upload_panel)
        self.file_frame.grid(
            row=1, column=0, sticky="ew", padx=10, pady=5
        )
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_path_var = tk.StringVar()
        self.file_entry = ctk.CTkEntry(
            self.file_frame, textvariable=self.file_path_var,
            placeholder_text="Select video file (MP4)...",
            state="readonly",
        )
        self.file_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.browse_btn = ctk.CTkButton(
            self.file_frame, text="Browse",
            command=self._browse_file, width=80,
        )
        self.browse_btn.grid(row=0, column=1, padx=5, pady=5)

        # Description
        self.desc_label = ctk.CTkLabel(
            self.upload_panel, text="Description / Caption",
        )
        self.desc_label.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")

        self.desc_text = ctk.CTkTextbox(
            self.upload_panel, height=80,
        )
        self.desc_text.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        # Privacy
        self.privacy_label = ctk.CTkLabel(
            self.upload_panel, text="Privacy Level",
        )
        self.privacy_label.grid(
            row=4, column=0, padx=10, pady=(10, 0), sticky="w"
        )

        self.privacy_var = ctk.StringVar(value="SELF_ONLY")
        self.privacy_menu = ctk.CTkOptionMenu(
            self.upload_panel,
            values=["SELF_ONLY", "MUTUAL_FOLLOW_FRIENDS", "PUBLIC_TO_EVERYONE"],
            variable=self.privacy_var,
        )
        self.privacy_menu.grid(row=5, column=0, padx=10, pady=5, sticky="w")

        # Sandbox mode toggle
        self.sandbox_frame = ctk.CTkFrame(self.upload_panel)
        self.sandbox_frame.grid(
            row=6, column=0, padx=10, pady=(10, 0), sticky="w"
        )

        self.sandbox_var = tk.BooleanVar(value=True)
        self.sandbox_switch = ctk.CTkSwitch(
            self.sandbox_frame, text="Sandbox Mode (テスト用)",
            variable=self.sandbox_var,
        )
        self.sandbox_switch.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.sandbox_label = ctk.CTkLabel(
            self.sandbox_frame,
            text="※ Sandbox: 非公開投稿のみ／審査不要",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        self.sandbox_label.grid(row=1, column=0, padx=5, sticky="w")

        # Upload button
        self.upload_btn = ctk.CTkButton(
            self.upload_panel, text="Upload to Selected Accounts",
            command=self._start_upload, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.upload_btn.grid(row=7, column=0, padx=10, pady=20, sticky="ew")

        # Progress
        self.progress_label = ctk.CTkLabel(
            self.upload_panel, text="Ready",
        )
        self.progress_label.grid(
            row=7, column=0, padx=10, pady=(0, 5), sticky="w"
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.upload_panel,
        )
        self.progress_bar.grid(
            row=8, column=0, padx=10, pady=5, sticky="ew"
        )
        self.progress_bar.set(0)

        # Log
        self.log_text = ctk.CTkTextbox(
            self.upload_panel, height=150, state="disabled",
        )
        self.log_text.grid(
            row=9, column=0, sticky="nsew", padx=10, pady=10
        )
        self.upload_panel.grid_rowconfigure(9, weight=1)

    # ────────────────────────────────
    # Account Management
    # ────────────────────────────────

    def _refresh_accounts(self):
        """Refresh account list in UI."""
        # Clear existing
        for widget in self.accounts_scroll.winfo_children():
            widget.destroy()
        self.account_checkboxes.clear()

        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            ctk.CTkLabel(
                self.accounts_scroll,
                text="No accounts added.\nClick '＋ Add Account' to start.",
                text_color="gray",
            ).pack(pady=20)
            return

        for acc in accounts:
            var = tk.BooleanVar(value=False)
            frame = ctk.CTkFrame(self.accounts_scroll)
            frame.pack(fill="x", padx=5, pady=2)

            cb = ctk.CTkCheckBox(
                frame, text=acc.display_name or acc.account_id,
                variable=var,
            )
            cb.pack(side="left", padx=5, pady=5)

            remove_btn = ctk.CTkButton(
                frame, text="✕", width=30, height=30,
                fg_color="red", hover_fg_color="darkred",
                command=lambda aid=acc.account_id: self._remove_account(aid),
            )
            remove_btn.pack(side="right", padx=5, pady=5)

            self.account_checkboxes[acc.account_id] = var

    def _add_account(self):
        """Start OAuth flow to add a new account."""
        sandbox = self.sandbox_var.get()
        self.oauth_manager = OAuthManager(sandbox=sandbox)

        def on_success(result):
            try:
                open_id = result.get("open_id", result.get("access_token")[:12])
                account = self.account_manager.add_account(
                    account_id=open_id,
                    access_token=result["access_token"],
                    refresh_token=result.get("refresh_token", ""),
                    token_expires_at=time.time() + result.get("expires_in", 86400),
                    display_name=open_id[:12],
                )
                mode = "Sandbox" if sandbox else "Production"
                self._log(f"Account added ({mode}): {account.display_name}")
                self.after(0, self._refresh_accounts)
            except Exception as e:
                self._log(f"Failed to add account: {e}")

        self.oauth_manager.start_auth_flow(on_success=on_success)
        mode = "Sandbox" if sandbox else "Production"
        self._log(f"Opening browser for authentication ({mode})...")

    def _remove_account(self, account_id: str):
        """Remove an account."""
        if messagebox.askyesno(
            "Remove Account", "Are you sure you want to remove this account?"
        ):
            self.account_manager.remove_account(account_id)
            self._log(f"Account removed: {account_id}")
            self._refresh_accounts()

    # ────────────────────────────────
    # File Selection
    # ────────────────────────────────

    def _browse_file(self):
        """Open file dialog to select video."""
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")],
        )
        if path:
            self.file_path_var.set(path)
            self._log(f"Selected: {Path(path).name}")

    # ────────────────────────────────
    # Upload
    # ────────────────────────────────

    def _get_selected_accounts(self):
        """Get list of selected account IDs."""
        return [
            aid for aid, var in self.account_checkboxes.items() if var.get()
        ]

    def _start_upload(self):
        """Start upload to selected accounts."""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("No File", "Please select a video file.")
            return

        if not Path(file_path).exists():
            messagebox.showerror("File Not Found", f"File not found: {file_path}")
            return

        selected = self._get_selected_accounts()
        if not selected:
            messagebox.showwarning(
                "No Account", "Please select at least one account."
            )
            return

        description = self.desc_text.get("1.0", "end").strip()
        privacy = self.privacy_var.get()

        # Disable button during upload
        self.upload_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting upload...")

        # Run in thread
        thread = threading.Thread(
            target=self._upload_thread,
            args=(file_path, description, privacy, selected),
            daemon=True,
        )
        thread.start()

    def _upload_thread(
        self, file_path: str, description: str, privacy: str, accounts: list
    ):
        """Upload thread function."""
        try:
            total = len(accounts)
            sandbox = self.sandbox_var.get()
            for i, acc_id in enumerate(accounts, 1):
                account = self.account_manager.get_account(acc_id)
                if not account:
                    self._log(f"Account not found: {acc_id}")
                    continue

                client = TikTokClient(account, sandbox=sandbox)
                display_name = account.display_name or acc_id

                def progress(current, total_size, name=display_name):
                    pct = current / total_size
                    self.after(
                        0,
                        lambda p=pct: self.progress_bar.set(p),
                    )
                    self.after(
                        0,
                        lambda n=name, c=current, t=total_size: self.progress_label.configure(
                            text=f"{n}: {c}/{t} bytes"
                        ),
                    )

                self._log(f"[{i}/{total}] Uploading to: {display_name}")
                publish_id = client.publish_video(
                    file_path, description, privacy,
                    progress_callback=progress,
                )
                self._log(f"Upload complete. Publish ID: {publish_id}")
                self._log(f"Polling status for {display_name}...")

                status = client.poll_until_complete(publish_id)
                self._log(f"Final status: {status}")

            self.after(0, lambda: self.progress_label.configure(text="All uploads complete!"))
        except Exception as e:
            self._log(f"Error: {e}")
            self.after(
                0, lambda: self.progress_label.configure(text=f"Error: {e}")
            )
        finally:
            self.after(0, lambda: self.upload_btn.configure(state="normal"))

    # ────────────────────────────────
    # Logging
    # ────────────────────────────────

    def _log(self, message: str):
        """Append message to log textbox."""
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def main():
    app = TikTokMultiPoster()
    app.mainloop()


if __name__ == "__main__":
    main()
