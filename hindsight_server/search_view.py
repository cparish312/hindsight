import platform
import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from db import HindsightDB
from timeline_view import Screenshot

class SearchViewer:
    def __init__(self, master, db = None, num_images_per_row=6):
        self.master = master
        self.db = db if db is not None else HindsightDB()
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()

        self.max_width = self.screen_width - 100
        self.max_height = self.screen_height

        self.num_images_per_row = self.calculate_num_images_per_row()

        self.scroll_frame_num = 0
        self.scroll_frame_num_var = tk.StringVar()

        self.search_results = None
        self.setup_gui()

    def calculate_num_images_per_row(self):
        # Assuming each image takes 200 pixels width including padding
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
        print(event.delta)
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
        if search_text:
            search_results = self.db.search_text(search_text,  n_seconds=300)
            self.search_results = search_results
            self.display_frames()

    def display_frames(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if self.search_results is None:
            return

        row = 0
        col = 0
        for i, im_row in self.search_results.iterrows():
            screenshot = self.get_screenshot(im_row)
            self.display_frame(screenshot, row, col)
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

    def display_frame(self, screenshot, row, col):
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        
        frame = ttk.Frame(self.scroll_frame)
        frame.grid(row=row, column=col, padx=10, pady=10)

        label = ttk.Label(frame, image=imgtk)
        label.image = imgtk  # Keep a reference to avoid garbage collection
        label.pack()
        
        timestamp_label = ttk.Label(frame, text=f"Time: {screenshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", font=("Arial", 16))
        timestamp_label.pack()

    def on_window_close(self):
        self.master.destroy()

def main():
    root = tk.Tk()
    app = SearchViewer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()

