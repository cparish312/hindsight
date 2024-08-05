"""GUI for scrolling through screenshots timeline."""
import cv2
from datetime import datetime
import platform
import matplotlib
import numpy as np
import pandas as pd
import tkinter as tk
import colorcet as cc
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk

import tzlocal
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from db import HindsightDB

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

@dataclass
class Screenshot:
    image: np.array
    text_df: pd.DataFrame
    timestamp: datetime.timestamp

class TimelineViewer:
    def __init__(self, master, frame_id = None, max_width=1536, max_height=800, images_df=None, front_camera=None):
        self.master = master
        self.db = HindsightDB()
        self.images_df = self.get_images_df(front_camera) if images_df is None else images_df
        self.num_frames = len(self.images_df)
        self.max_frames_index = max(self.images_df.index)
        self.app_color_map = self.get_app_color_map()
        self.max_width = max_width
        self.max_height = max_height - 200

        self.screenshots_on_timeline = 40 

        if frame_id is None:
            self.scroll_frame_num = 0
        else:
            self.scroll_frame_num = self.images_df.index.get_loc(self.images_df[self.images_df['id'] == frame_id].index[0])
        self.scroll_frame_num_var = tk.StringVar()

        # For mouse dragging
        self.dragging = False
        self.drag_start = None
        self.drag_end = None

        self.setup_gui()

        self.exit_flag = False

    def get_images_df(self, front_camera):
        """Gets a DataFrame of all images at the time of inititation"""
        if front_camera is None:
            images_df = self.db.get_screenshots()
        elif front_camera:
            images_df = self.db.get_frames(applications=["frontCamera"])
        else:
            images_df = self.db.get_frames(applications=["backCamera"])
        images_df['datetime_utc'] = pd.to_datetime(images_df['timestamp'] / 1000, unit='s', utc=True)
        images_df['datetime_local'] = images_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
        return images_df.sort_values(by='datetime_local', ascending=False)
    
    def get_app_color_map(self):
        # Generate a color map for each app, ensuring colors are distinguishable
        unique_apps = self.images_df['application'].unique()
        num_apps = len(unique_apps)
        
        # Choose a colormap with a sufficient number of colors
        cmap = cc.cm['rainbow']  # 'rainbow', 'colorwheel', etc., could also be good choices
        
        # Generate color indices spaced evenly throughout the colormap
        colors = [cmap(i / (num_apps - 1)) if num_apps > 1 else cmap(0.5) for i in range(num_apps)]

        hex_colors = [matplotlib.colors.to_hex(color) for color in colors]
        
        return {app: hex_colors[i] for i, app in enumerate(unique_apps)}
    
    def setup_gui(self):
        self.master.title("Trackpad-Controlled Video Timeline")

        self.top_frame = ttk.Frame(self.master)
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)

        self.search_button = ttk.Button(self.top_frame, text="Search", command=self.open_search_view)
        self.search_button.pack(side=tk.RIGHT)
        
        self.video_label = ttk.Label(self.master)
        self.video_label.pack()
        self.video_label.bind("<Button-1>", self.start_drag)
        self.video_label.bind("<B1-Motion>", self.on_drag)
        self.video_label.bind("<ButtonRelease-1>", self.end_drag)

        self.time_label = ttk.Label(self.master, textvariable=str(self.scroll_frame_num_var), font=("Arial", 24), anchor="e")
        self.time_label.pack()
        self.bind_scroll_event()

        self.timeline_canvas = tk.Canvas(self.master, height=50)
        self.timeline_canvas.pack(fill=tk.X, padx=5, pady=5)
        self.master.bind('<Configure>', lambda e: self.update_timeline(self.displayed_frame_num)) # Update timeline when frame changed
        
        self.displayed_frame_num = self.scroll_frame_num
        screenshot = self.get_screenshot(self.displayed_frame_num)
        self.display_frame(screenshot, self.displayed_frame_num)
        self.master.after(40, self.update_frame_periodically)
    
    def resize_screenshot(self, screenshot, max_width, max_height):
        height, width, _ = screenshot.image.shape
        if width > max_width or height > max_height:
            scaling_factor = min(max_width / width, max_height / height)
            new_size = (int(width * scaling_factor), int(height * scaling_factor))
            screenshot.image = cv2.resize(screenshot.image, new_size, interpolation=cv2.INTER_AREA)
            if screenshot.text_df is not None:
                screenshot.text_df.loc[:, 'x'] = screenshot.text_df['x'] * scaling_factor
                screenshot.text_df.loc[:, 'y'] = screenshot.text_df['y'] * scaling_factor
                screenshot.text_df.loc[:, 'w'] = screenshot.text_df['w'] * scaling_factor
                screenshot.text_df.loc[:, 'h'] = screenshot.text_df['h'] * scaling_factor
        return screenshot


    def get_screenshot(self, i):
        """Loads and resizes the screenshot."""
        im_row = self.images_df.iloc[i]
        image = cv2.imread(im_row['path'])
        text_df = self.db.get_ocr_results(frame_id=im_row['id'])
        if set(text_df['text']) == {None}:
            text_df = None
        screenshot = Screenshot(image=image, text_df=text_df, timestamp=im_row['datetime_local'])
        screenshot_resized = self.resize_screenshot(screenshot, self.max_width, self.max_height)
        return screenshot_resized

    def update_frame_periodically(self):
        # Check if the current scroll position has a preloaded frame
        if self.scroll_frame_num != self.displayed_frame_num:
            screenshot = self.get_screenshot(self.scroll_frame_num)
            self.display_frame(screenshot, self.scroll_frame_num)

        # Schedule the next update
        if not self.exit_flag:
            self.master.after(10, self.update_frame_periodically)

    def get_apps_near(self, current_frame_num):
        timeline_border = self.screenshots_on_timeline // 2
        apps_before = self.images_df.iloc[current_frame_num+1:current_frame_num+timeline_border+1]['application']
        apps_after = self.images_df.iloc[max(current_frame_num-timeline_border, 0):current_frame_num]['application']
        return apps_before, apps_after

    def update_timeline(self, current_frame_num):
        self.timeline_canvas.delete("all")  # Clear existing drawings
        width = self.timeline_canvas.winfo_width()
        apps_before, apps_after = self.get_apps_near(current_frame_num)  # Implement this function

        timeline_screenshot_width = width / self.screenshots_on_timeline

        start_pos = width / 2 # start in the middle of the timeline
        for app in apps_before: # Reverse order of list to start at current screenshot
            color = self.app_color_map[app]
            self.timeline_canvas.create_rectangle(start_pos, 0, start_pos-timeline_screenshot_width, 50, fill=color, outline='')
            start_pos -= timeline_screenshot_width

        start_pos = (width / 2)  + timeline_screenshot_width # start in the middle of the timeline
        for app in apps_after[::-1]: # Reverse order of list to start at current screenshot
            color = self.app_color_map[app]
            self.timeline_canvas.create_rectangle(start_pos, 0, start_pos+timeline_screenshot_width, 50, fill=color, outline='')
            start_pos += timeline_screenshot_width

        # Draw current app
        start_pos = width / 2 # start in the middle of the timeline
        current_app = self.images_df.iloc[current_frame_num]['application']
        color = self.app_color_map[current_app]
        self.timeline_canvas.create_rectangle(start_pos, 0, start_pos+timeline_screenshot_width, 50, fill=color, outline="black")

    def display_frame(self, screenshot, frame_num):
        im_row = self.images_df.iloc[frame_num]
        print(f"frame_num: {frame_num} frame_id: {im_row['id']}")
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.scroll_frame_num_var.set(f"Time: {screenshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self.update_timeline(frame_num)
        self.displayed_image = screenshot
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
        
        if self.scroll_frame_num > self.max_frames_index:
            self.scroll_frame_num = self.max_frames_index

    def on_scroll_up(self, event):
        # Linux scroll up
        if self.scroll_frame_num > 0:
            self.scroll_frame_num -= 1

    def on_scroll_down(self, event):
        # Linux scroll down
        self.scroll_frame_num += 1
        if self.scroll_frame_num > self.max_frames_index:
            self.scroll_frame_num = self.max_frames_index
    def start_drag(self, event):
        self.dragging = True
        self.drag_start = (event.x, event.y)

    def on_drag(self, event):
        if self.dragging:
            self.drag_end = (event.x, event.y)

    def end_drag(self, event):
        if not self.dragging:
            return
        self.dragging = False
        self.copy_texts_within_drag_area()

    def rectangles_overlap(self, rect1, rect2):
        """Check if two rectangles overlap. Rectangles are defined as (x1, y1, x2, y2)."""
        x1, y1, x2, y2 = rect1
        rx1, ry1, rx2, ry2 = rect2
        return not (rx1 > x2 or rx2 < x1 or ry1 > y2 or ry2 < y1)

    def copy_texts_within_drag_area(self):
        """Gets all text in the area the user has dragged"""
        if self.drag_start is None or self.drag_end is None:
            return
        x1 = min(self.drag_start[0], self.drag_end[0]) 
        y1 = min(self.drag_start[1], self.drag_end[1])
        x2 = max(self.drag_start[0], self.drag_end[0]) 
        y2 = max(self.drag_start[1], self.drag_end[1])

        text_df = self.displayed_image.text_df
        selected_texts = []
        if text_df is not None:
            texts_in_area = text_df.apply(lambda row: self.rectangles_overlap((x1, y1, x2, y2), (row['x'], row['y'], row['x'] + row['w'], row['y'] + row['h'])), axis=1)
            overlapping_texts = text_df[texts_in_area]
            selected_texts.extend(overlapping_texts['text'].tolist())
        
        if selected_texts:
            self.copy_to_clipboard("\n".join(selected_texts))
        else:
            messagebox.showinfo("No Text Selected", "No text found within the selected area.")

    def copy_to_clipboard(self, text):
        """Copy provided text to clipboard."""
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        messagebox.showinfo("Text Copied", f"Text has been copied to clipboard:\n{text}")

    def open_search_view(self):
        # Import SearchViewer here to avoid circular import issues
        from search_view import SearchViewer

        search_window = tk.Toplevel(self.master)
        SearchViewer(search_window)

    # When the window is closed, you should also gracefully exit the preload thread
    def on_window_close(self):
        self.exit_flag = True
        self.master.destroy()

def main():
    root = tk.Tk()
    app = TimelineViewer(root, front_camera=True)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()