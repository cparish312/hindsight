import cv2
import glob
from datetime import datetime
import platform
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

import tzlocal
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from hindsight_server import RAW_SCREENSHOTS_DIR

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

@dataclass
class Screenshot:
    image: np.array
    timestamp: datetime.timestamp

class TimelineViewer:
    def __init__(self, master, screenshots_dir, max_width=1536, max_height=800):
        self.master = master
        self.screenshots_dir = screenshots_dir
        self.images_df = self.get_images_df(screenshots_dir)
        self.max_width = max_width
        self.max_height = max_height
        self.scroll_frame_num = 0
        self.scroll_frame_num_var = tk.StringVar()

        self.setup_gui()

        self.exit_flag = False

    def get_images_df(self, screenshots_dir):
        images_l = list()
        for f in glob.glob(f"{screenshots_dir}/*/*/*/*/*.jpg"):
            filename = f.split('/')[-1]
            filename_s = filename.replace(".jpg", "").split("_")
            application = filename_s[0]
            timestamp = int(filename_s[1])
            images_l.append({"path" : f, "timestamp" : timestamp, "app" : application})
        images_df = pd.DataFrame(images_l)
        images_df['datetime_utc'] = pd.to_datetime(images_df['timestamp'] / 1000, unit='s', utc=True)
        images_df['datetime_local'] = images_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
        return images_df.sort_values(by='datetime_local', ascending=False)
    
    def resize_screenshot(self, image, max_width, max_height):
        height, width, _ = image.shape
        if width > max_width or height > max_height:
            scaling_factor = min(max_width / width, max_height / height)
            new_size = (int(width * scaling_factor), int(height * scaling_factor))
            return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    def get_screenshot(self, i):
        im_row = self.images_df.iloc[i]
        image = cv2.imread(im_row['path'])
        image_resized = self.resize_screenshot(image, self.max_width, self.max_height)
        return Screenshot(image=image_resized, timestamp=im_row['datetime_local'])
        
    def setup_gui(self):
        self.master.title("Trackpad-Controlled Video Timeline")
        
        self.video_label = ttk.Label(self.master)
        self.video_label.pack()

        self.time_label = ttk.Label(self.master, textvariable=str(self.scroll_frame_num_var), font=("Arial", 24), anchor="e")
        self.time_label.pack()
        self.bind_scroll_event()
        
        self.displayed_frame_num = 0
        screenshot = self.get_screenshot(self.displayed_frame_num)
        self.display_frame(screenshot, self.displayed_frame_num)
        self.master.after(40, self.update_frame_periodically)

    def update_frame_periodically(self):
        # Check if the current scroll position has a preloaded frame
        if self.scroll_frame_num != self.displayed_frame_num:
            screenshot = self.get_screenshot(self.scroll_frame_num)
            self.display_frame(screenshot, self.scroll_frame_num)

        # Schedule the next update
        if not self.exit_flag:
            self.master.after(10, self.update_frame_periodically)

    def display_frame(self, screenshot, frame_num):
        print(frame_num)
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.scroll_frame_num_var.set(f"Time: {screenshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self.displayed_videoframe = screenshot
        self.displayed_frame_num = frame_num
    
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
            self.scroll_frame_num += int(event.delta / 120)
        else:  # macOS
            self.scroll_frame_num -= int(event.delta)

        if self.scroll_frame_num < 0:
            self.scroll_frame_num = 0

    def on_scroll_up(self, event):
        # Linux scroll up
        if self.scroll_frame_num > 0:
            self.scroll_frame_num -= 1

    def on_scroll_down(self, event):
        # Linux scroll down
        self.scroll_frame_num += 1

    # When the window is closed, you should also gracefully exit the preload thread
    def on_window_close(self):
        self.exit_flag = True
        self.preload_thread.join()
        for _, video_manager in self.video_timeline_manager.video_managers:
            video_manager.cap.release()
        self.master.destroy()

def main():
    root = tk.Tk()
    app = TimelineViewer(root, screenshots_dir=RAW_SCREENSHOTS_DIR)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()