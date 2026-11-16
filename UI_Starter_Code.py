import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from backend import FinPayEngine


class FinPayApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("FinPay - Transaction Manager")
        self.geometry("800x600")

        # Configure a consistent style
        style = ttk.Style(self)
        style.theme_use('clam')

        # Container to hold all the screens (frames)
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.engine = FinPayEngine()
        # Dictionary to keep track of the frames
        self.frames = {}

        # Initialize all three screens
        for F in (WelcomeScreen, UploadScreen, DashboardScreen):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame

            # Put all pages in the same location; the one on top will be visible.
            frame.grid(row=0, column=0, sticky="nsew")

        # Show the first screen
        self.show_frame("WelcomeScreen")

    def show_frame(self, page_name):
        """Brings the specified frame to the front."""
        frame = self.frames[page_name]
        frame.tkraise()


class WelcomeScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Center content
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        lbl_title = ttk.Label(self, text="Welcome to FinPay", font=("Helvetica", 24, "bold"))
        lbl_title.grid(row=1, column=0, pady=10)

        lbl_subtitle = ttk.Label(self, text="Internal Finance Department Portal", font=("Helvetica", 14))
        lbl_subtitle.grid(row=2, column=0, pady=10)

        btn_start = ttk.Button(self, text="Get Started", command=lambda: controller.show_frame("UploadScreen"))
        btn_start.grid(row=3, column=0, sticky="n", pady=20)


class UploadScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.filepath = None

        # Center content
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        lbl_header = ttk.Label(self, text="Load Transaction Data", font=("Helvetica", 18, "bold"))
        lbl_header.grid(row=0, column=0, pady=20, sticky="s")

        # Upload Box Area
        upload_frame = ttk.LabelFrame(self, text="File Upload", padding=40)
        upload_frame.grid(row=1, column=0, pady=20)

        lbl_info = ttk.Label(upload_frame, text="Browse to select a file.\nSupported formats: .csv, .json only.")
        lbl_info.pack(pady=10)

        self.lbl_filename = ttk.Label(upload_frame, text="No file selected", foreground="gray")
        self.lbl_filename.pack(pady=5)

        btn_browse = ttk.Button(upload_frame, text="Browse File", command=self.browse_file)
        btn_browse.pack(pady=10)

        # Navigation
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, pady=20)

        btn_back = ttk.Button(btn_frame, text="Back", command=lambda: controller.show_frame("WelcomeScreen"))
        btn_back.grid(row=0, column=0, padx=10)

        # In a real app, this should only enable after a file is selected
        self.btn_load = ttk.Button(btn_frame, text="Load Data",
                                   command=self.load_data)
        self.btn_load.grid(row=0, column=1, padx=10)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Transaction File",
            filetypes=(("CSV Files", "*.csv"), ("JSON Files", "*.json"), ("All Files", "*.*"))
        )
        if filename:
            self.lbl_filename.config(text=filename.split("/")[-1])  # Show just the file name
            self.filepath = filename

    def load_data(self):
        if self.filepath is None:
            messagebox.showwarning("No file", "Please choose a file first.")
            return
        try:
            self.controller.engine.load_data(self.filepath)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.controller.frames["DashboardScreen"].refresh()
        self.controller.show_frame("DashboardScreen")


class DashboardScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Time ranges: label -> (from, to)
        self.time_ranges = {
            "All": ("", ""),
            "Night 00-06": ("00:00:00", "05:59:59"),
            "Morning 06-12": ("06:00:00", "11:59:59"),
            "Afternoon 12-18": ("12:00:00", "17:59:59"),
            "Evening 18-24": ("18:00:00", "23:59:59"),
        }

        # Top Bar (Filters)
        filter_frame = ttk.Frame(self, padding=10)
        filter_frame.pack(side="top", fill="x")

        ttk.Label(filter_frame, text="Filter by:").pack(side="left", padx=5)

        # City Filter
        ttk.Label(filter_frame, text="City:").pack(side="left", padx=5)
        self.cb_city = ttk.Combobox(filter_frame, values=["All"], state="readonly", width=10)
        self.cb_city.current(0)
        self.cb_city.pack(side="left", padx=5)

        # Date Filter
        ttk.Label(filter_frame, text="Date:").pack(side="left", padx=5)
        self.cb_date = ttk.Combobox(filter_frame, values=["All"], state="readonly", width=11)
        self.cb_date.current(0)
        self.cb_date.pack(side="left", padx=5)

        # Time Filter
        ttk.Label(filter_frame, text="Time:").pack(side="left", padx=5)
        self.cb_time = ttk.Combobox(filter_frame, values=list(self.time_ranges),
                                    state="readonly", width=14)
        self.cb_time.current(0)
        self.cb_time.pack(side="left", padx=5)

        # Type Filter
        ttk.Label(filter_frame, text="Type:").pack(side="left", padx=5)
        self.cb_type = ttk.Combobox(filter_frame, values=["All", "Credit", "Debit"],
                                    state="readonly", width=8)
        self.cb_type.current(0)
        self.cb_type.pack(side="left", padx=5)

        # Buttons (second row so the window isn't too wide)
        button_frame = ttk.Frame(self, padding=(10, 0))
        button_frame.pack(side="top", fill="x")

        ttk.Button(button_frame, text="Apply Filters", command=self.apply_filters).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear Filters", command=self.clear_filters).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Revert Last Filter", command=self.revert_filter).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Back to Upload",
                   command=lambda: controller.show_frame("UploadScreen")).pack(side="right", padx=5)

        # Main Content Area (Treeview)
        columns = ("City", "Date", "Time", "Type", "Amount")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        self.tree.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Bottom Bar
        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(side="bottom", fill="x")

        self.lbl_count = ttk.Label(bottom_frame, text="Total Records Loaded: 0")
        self.lbl_count.pack(side="left")
        ttk.Button(bottom_frame, text="Export CSV", command=self.export_data).pack(side="right")

    def refresh(self, update_options=True):
        engine = self.controller.engine
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in engine.get_ui_rows():
            self.tree.insert("", tk.END, values=row)
        if update_options:
            self.cb_city["values"] = engine.get_city_options()
            self.cb_date["values"] = engine.get_date_options()
            self.cb_city.current(0)
            self.cb_date.current(0)
            self.cb_time.current(0)
            self.cb_type.current(0)
        self.lbl_count.config(text=f"Total Records Loaded: {len(engine.visible)}")

    def apply_filters(self):
        time_from, time_to = self.time_ranges[self.cb_time.get()]
        try:
            self.controller.engine.apply_filters(
                city=self.cb_city.get(), date=self.cb_date.get(),
                ttype=self.cb_type.get(),
                time_from=time_from, time_to=time_to)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.refresh(update_options=False)

    def clear_filters(self):
        self.controller.engine.clear_filters()
        self.cb_city.current(0)
        self.cb_date.current(0)
        self.cb_time.current(0)
        self.cb_type.current(0)
        self.refresh(update_options=False)

    def revert_filter(self):
        try:
            self.controller.engine.revert_last_filter()
        except Exception as e:
            messagebox.showinfo("Nothing to revert", str(e))
            return
        f = self.controller.engine.current_filters
        self.cb_city.set(f["city"])
        self.cb_date.set(f["date"])
        self.cb_type.set(f["type"])
        for label, rng in self.time_ranges.items():
            if rng == (f["time_from"], f["time_to"]):
                self.cb_time.set(label)
        self.refresh(update_options=False)

    def export_data(self):
        try:
            export_path, audit_path = self.controller.engine.export()
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return
        messagebox.showinfo("Done", f"Saved:\n{export_path}\n{audit_path}")



if __name__ == "__main__":
    app = FinPayApp()
    app.mainloop()