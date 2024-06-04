import platform
import cv2
import tzlocal
from zoneinfo import ZoneInfo
import pandas as pd
import tkinter as tk
from tkinter import ttk
from datetime import timedelta
from PIL import Image, ImageTk
from tkcalendar import DateEntry

from db import HindsightDB
from timeline_view import Screenshot, TimelineViewer

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

class SearchViewer:
    def __init__(self, master, max_results=200):
        self.master = master
        self.db = HindsightDB()
        self.max_results = max_results
        self.images_df = self.get_images_df()
        self.first_date = min(self.images_df['datetime_local'])
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()

        self.max_width = self.screen_width - 100
        self.max_height = self.screen_height

        self.num_images_per_row = self.calculate_num_images_per_row()

        self.timeline_viewer = None

        self.search_results = None
        self.setup_gui()

    def get_images_df(self):
        """Gets a DataFrame of all images at the time of inititation"""
        images_df = self.db.get_frames()
        images_df['datetime_utc'] = pd.to_datetime(images_df['timestamp'] / 1000, unit='s', utc=True)
        images_df['datetime_local'] = images_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
        return images_df.sort_values(by='datetime_local', ascending=False)

    def calculate_num_images_per_row(self):
        # Assuming each image takes 300 pixels width including padding
        return max(1, self.screen_width // 300)
    
    def setup_gui(self):
        self.master.title("Search Timeline")

        self.search_frame = ttk.Frame(self.master)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))

        self.search_entry = ttk.Entry(self.search_frame)
        self.search_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind("<Return>", lambda event: self.get_search_results())

        self.date_range_label = ttk.Label(self.search_frame, text="Date Range:")
        self.date_range_label.pack(side=tk.LEFT, padx=(20, 5))

        # Bug with blank calendar https://github.com/j4321/tkcalendar/issues/41
        self.start_date_entry = DateEntry(self.search_frame)
        self.start_date_entry.set_date(self.first_date)
        self.start_date_entry.pack(side=tk.LEFT, padx=(0, 5))

        self.end_date_label = ttk.Label(self.search_frame, text="to")
        self.end_date_label.pack(side=tk.LEFT, padx=(0, 5))

        self.end_date_entry = DateEntry(self.search_frame)
        self.end_date_entry.pack(side=tk.LEFT, padx=(0, 5))

        longest_app = max(self.images_df['application'], key=len)
        # Create applications selection option
        self.app_list = tk.Listbox(self.search_frame, selectmode = "multiple", width=len(longest_app)) 
        self.app_list.pack(side=tk.LEFT, padx=(0, 5)) 
        for app in sorted(list(set(self.images_df['application']))):
            self.app_list.insert(tk.END, app)

        self.search_button = ttk.Button(self.search_frame, text="Search", command=self.get_search_results)
        self.search_button.pack(side=tk.LEFT)
        
        self.canvas = tk.Canvas(self.master)
        self.scroll_y = ttk.Scrollbar(self.master, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")

        self.bind_scroll_event()

    def bind_scroll_event(self):
        # Detect platform and bind the appropriate event
        os_name = platform.system()
        if os_name == "Linux":
            self.master.bind("<Button-4>", self.on_scroll_up)
            self.master.bind("<Button-5>", self.on_scroll_down)
        else:  # Windows and macOS
            self.master.bind("<MouseWheel>", self.on_mouse_wheel)
    
    def on_mouse_wheel(self, event):
        # Windows and macOS handle scroll direction differently
        if platform.system() == "Windows":
            if event.delta > 0:
                self.canvas.yview_scroll(1, "units")
            else:
                self.canvas.yview_scroll(-1, "units")
        else:  # macOS
            if event.delta > 0:
                self.canvas.yview_scroll(-1, "units")
            else:
                self.canvas.yview_scroll(1, "units")

    def on_scroll_up(self, event):
        # Linux scroll up
        self.canvas.yview_scroll(1, "units")

    def on_scroll_down(self, event):
        # Linux scroll down
        self.canvas.yview_scroll(-1, "units")

    def get_search_results(self):
        search_text = self.search_entry.get()
        start_date =pd.to_datetime(self.start_date_entry.get_date()).tz_localize(tzlocal.get_localzone())
        # Want to include all times within the end date
        end_date = pd.to_datetime(self.end_date_entry.get_date() + timedelta(hours=24)).tz_localize(tzlocal.get_localzone())
        selected_apps = set()
        for i in self.app_list.curselection():
            selected_apps.add(self.app_list.get(i))
        selected_apps = selected_apps if len(selected_apps) > 0 else None

        search_results = self.db.search(text=search_text, start_date=start_date, end_date=end_date, apps=selected_apps, n_seconds=300)
        self.search_results = search_results.iloc[:self.max_results]
        self.display_frames()

    def display_frames(self):
        """Displays all frames in self.search_results in grid format"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if self.search_results is None or len(self.search_results) == 0:
            return

        row = 0
        col = 0
        for i, im_row in self.search_results.iterrows():
            screenshot = self.get_screenshot(im_row)
            self.display_frame(screenshot, im_row, row, col)
            col += 1
            if col >= self.num_images_per_row:
                col = 0
                row += 1

        # Update the window to ensure geometry calculations are correct
        self.master.update_idletasks()
        
        # Get the required height of a single frame
        if self.scroll_frame.winfo_children():
            frame_height = self.scroll_frame.winfo_children()[0].winfo_reqheight() + 20

        # Adjust window size to fit all frames
        total_rows = (len(self.search_results) + self.num_images_per_row - 1) // self.num_images_per_row
        window_height = min(total_rows * frame_height + 200, self.max_height)  # Additional space for search bar and padding
        self.master.geometry(f"{self.max_width}x{window_height}")

    def resize_screenshot(self, screenshot, max_width, max_height):
        height, width, _ = screenshot.image.shape
        if width > max_width or height > max_height:
            scaling_factor = min(max_width / width, max_height / height)
            new_size = (int(width * scaling_factor), int(height * scaling_factor))
            screenshot.image = cv2.resize(screenshot.image, new_size, interpolation=cv2.INTER_AREA)
        return screenshot

    def get_screenshot(self, im_row):
        image = cv2.imread(im_row['path'])
        screenshot = Screenshot(image=image, text_df=None, timestamp=im_row['datetime_local'])
        screenshot_resized = self.resize_screenshot(screenshot, self.max_width // self.num_images_per_row, self.max_height // self.num_images_per_row)
        return screenshot_resized

    def display_frame(self, screenshot, im_row, row, col):
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        
        frame = ttk.Frame(self.scroll_frame)
        frame.grid(row=row, column=col, padx=10, pady=10)

        label = ttk.Label(frame, image=imgtk)
        label.image = imgtk  # Keep a reference to avoid garbage collection
        label.pack()

        # Bind the click event to open the timeline view
        label.bind("<Button-1>", lambda e, frame_id=im_row['id']: self.open_timeline_view(frame_id))
        
        timestamp_label = ttk.Label(frame, text=f"Time: {screenshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", font=("Arial", 16))
        timestamp_label.pack()

    def open_timeline_view(self, frame_id):
        """Opens timeline view at the clicked frame"""
        if self.timeline_viewer is not None:
            self.timeline_viewer.master.destroy()
        
        timeline_window = tk.Toplevel(self.master)
        self.timeline_viewer = TimelineViewer(timeline_window, frame_id=frame_id)

    def on_window_close(self):
        self.master.destroy()

def main():
    root = tk.Tk()
    app = SearchViewer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()

