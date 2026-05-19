from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import host


HOST_SUBCOMMAND = "--run-host"


class GBNLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GBN Host Launcher")
        self.root.geometry("860x620")

        self.base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        self.host_program = self._resolve_host_program()
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.reader_thread: threading.Thread | None = None

        self.config_var = tk.StringVar(value=str(self.base_dir / "configs" / "host1.ini"))
        self.mode_var = tk.StringVar(value="send")
        self.file_var = tk.StringVar(value=str(self.base_dir / "test_3mb.bin"))
        self.output_dir_var = tk.StringVar(value=str(self.base_dir / "received"))
        self.log_var = tk.StringVar(value=str(self.base_dir / "logs" / "launcher_run.jsonl"))
        self.target_name_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._refresh_field_state()
        self.root.after(100, self._drain_output_queue)

    def _resolve_host_program(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [str(Path(sys.executable).resolve()), HOST_SUBCOMMAND]
        host_script = self.base_dir / "host.py"
        return [sys.executable, str(host_script)]

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

        self._add_path_row(frame, 0, "Config", self.config_var, self._choose_config)
        self._add_combo_row(frame, 1, "Mode", self.mode_var, ["send", "recv", "duplex"], self._refresh_field_state)
        self._add_path_row(frame, 2, "File", self.file_var, self._choose_file)
        self._add_path_row(frame, 3, "Output Dir", self.output_dir_var, self._choose_output_dir)
        self._add_path_row(frame, 4, "Log", self.log_var, self._choose_log)
        self._add_entry_row(frame, 5, "Target Name", self.target_name_var)

        button_row = ttk.Frame(frame)
        button_row.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 8))
        self.start_button = ttk.Button(button_row, text="Start", command=self.start_process)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(button_row, text="Stop", command=self.stop_process, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Clear Output", command=self._clear_output).pack(side="left", padx=(8, 0))

        ttk.Label(frame, textvariable=self.status_var).grid(row=6, column=2, sticky="e")

        self.output_text = tk.Text(frame, wrap="word", height=20)
        self.output_text.grid(row=7, column=0, columnspan=3, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.output_text.yview)
        scrollbar.grid(row=7, column=3, sticky="ns")
        self.output_text.configure(yscrollcommand=scrollbar.set)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _add_path_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, browse_command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 8))
        setattr(self, f"{label.lower().replace(' ', '_')}_entry", entry)
        ttk.Button(parent, text="Browse", command=browse_command).grid(row=row, column=2, sticky="ew", pady=4)

    def _add_combo_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, values: list[str], callback) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 8))
        combo.bind("<<ComboboxSelected>>", lambda _event: callback())
        self.mode_combo = combo

    def _add_entry_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", pady=4, padx=(8, 0))
        setattr(self, f"{label.lower().replace(' ', '_')}_entry", entry)

    def _choose_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Select config file",
            initialdir=self.base_dir / "configs",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
        )
        if path:
            self.config_var.set(path)

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select file to send",
            initialdir=self.base_dir,
            filetypes=[("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def _choose_output_dir(self) -> None:
        path = filedialog.askdirectory(
            title="Select output directory",
            initialdir=self.base_dir,
        )
        if path:
            self.output_dir_var.set(path)

    def _choose_log(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select log path",
            initialdir=self.base_dir / "logs",
            defaultextension=".jsonl",
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")],
        )
        if path:
            self.log_var.set(path)

    def _refresh_field_state(self) -> None:
        mode = self.mode_var.get()
        file_state = "normal" if mode in {"send", "duplex"} else "disabled"
        target_state = "normal" if mode in {"send", "duplex"} else "disabled"

        self.file_entry.configure(state=file_state)
        self.target_name_entry.configure(state=target_state)

    def _clear_output(self) -> None:
        self.output_text.delete("1.0", "end")

    def _append_output(self, text: str) -> None:
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def _validate_inputs(self) -> bool:
        if not Path(self.config_var.get()).exists():
            messagebox.showerror("Invalid Config", "Config file does not exist.")
            return False
        if not self.log_var.get().strip():
            messagebox.showerror("Invalid Log", "Log path is required.")
            return False
        if self.mode_var.get() in {"send", "duplex"} and not Path(self.file_var.get()).exists():
            messagebox.showerror("Invalid File", "File to send does not exist.")
            return False
        return True

    def _build_command(self) -> list[str]:
        command = list(self.host_program)
        command.extend(["--config", self.config_var.get()])
        command.extend(["--mode", self.mode_var.get()])
        command.extend(["--output-dir", self.output_dir_var.get()])
        command.extend(["--log", self.log_var.get()])

        mode = self.mode_var.get()
        if mode in {"send", "duplex"}:
            command.extend(["--file", self.file_var.get()])
        if self.target_name_var.get().strip():
            command.extend(["--target-name", self.target_name_var.get().strip()])
        return command

    def start_process(self) -> None:
        if self.process is not None:
            messagebox.showinfo("Already Running", "A task is already running.")
            return
        if not self._validate_inputs():
            return

        command = self._build_command()
        self._append_output(f"$ {' '.join(command)}\n")
        self.status_var.set("Running")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        log_parent = Path(self.log_var.get()).resolve().parent
        log_parent.mkdir(parents=True, exist_ok=True)
        Path(self.output_dir_var.get()).mkdir(parents=True, exist_ok=True)

        self.process = subprocess.Popen(
            command,
            cwd=self.base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.reader_thread = threading.Thread(target=self._read_process_output, daemon=True)
        self.reader_thread.start()

    def _read_process_output(self) -> None:
        assert self.process is not None
        if self.process.stdout is not None:
            for line in self.process.stdout:
                self.output_queue.put(line)
        return_code = self.process.wait()
        self.output_queue.put(f"\n[process exited with code {return_code}]\n")
        self.output_queue.put("__PROCESS_DONE__")

    def _drain_output_queue(self) -> None:
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if item == "__PROCESS_DONE__":
                self.process = None
                self.reader_thread = None
                self.status_var.set("Ready")
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
            else:
                self._append_output(item)
        self.root.after(100, self._drain_output_queue)

    def stop_process(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        self._append_output("[launcher] Stop requested.\n")
        self.status_var.set("Stopping")

    def on_close(self) -> None:
        if self.process is not None:
            if not messagebox.askyesno("Exit", "A task is still running. Stop it and exit?"):
                return
            self.stop_process()
        self.root.destroy()


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == HOST_SUBCOMMAND:
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        host.main()
        return

    root = tk.Tk()
    app = GBNLauncherApp(root)
    if not app.host_program:
        messagebox.showerror("Startup Error", "Could not locate host program.")
        return
    root.mainloop()


if __name__ == "__main__":
    main()
