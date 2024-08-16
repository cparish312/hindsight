"""GUI for scrolling through screenshots timeline with a stock plot."""
import cv2
from datetime import datetime
import platform
import matplotlib
import numpy as np
import pandas as pd
import tkinter as tk
import colorcet as cc
import yfinance as yf 
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk

import tzlocal
from zoneinfo import ZoneInfo
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import sys
sys.path.insert(0, "../")

import utils
from db import HindsightDB

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

@dataclass
class Screenshot:
    image: np.array
    text_df: pd.DataFrame
    timestamp: datetime.timestamp

class TimelineViewer:
    def __init__(self, master, frame_id = None, max_width=2400, max_height=900, images_df=None, front_camera=None):
        self.master = master
        self.db = HindsightDB()
        self.images_df = self.get_images_df(front_camera) if images_df is None else images_df
        self.num_frames = len(self.images_df)
        self.max_frames_index = max(self.images_df.index)
        self.app_color_map = self.get_app_color_map()
        self.max_width = max_width
        self.max_height = max_height - 200

        if frame_id is None:
            self.scroll_frame_num = self.images_df.index[-1]
        else:
            self.scroll_frame_num = self.images_df.index.get_loc(self.images_df[self.images_df['id'] == frame_id].index[0])
        self.scroll_frame_num_var = tk.StringVar()

        self.setup_gui()
    
        self.exit_flag = False

    def create_stock_plot(self):
        # Example data for the plot

        start_date = datetime(2022, 1, 1) 
        end_date = datetime.now()
        self.stock_data = yf.download('NVDA', start = start_date, 
                        end = end_date) 
        self.last_stock_value = self.stock_data.iloc[-1].Open
        
        self.figure = plt.Figure(figsize=(11, 4), dpi=100)
    
        self.ax = self.figure.add_subplot(111)
        self.ax.plot(self.stock_data['Open']) 
        self.ax.set_title('NVDA Opening Prices from {} to {}'.format(start_date, 
                                                end_date)) 
        self.ax.legend()
        
        self.stock_canvas = FigureCanvasTkAgg(self.figure, self.left_frame)
        self.stock_canvas_widget = self.stock_canvas.get_tk_widget()
        self.stock_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_stock_plot(self, current_datetime):
        # Clear previous points
        self.ax.clear()
        # Redraw the plot
        self.ax.plot(self.stock_data['Open']) 
        # Draw a point for the current frame
        current_day = pd.Timestamp(current_datetime.normalize().date())
        if current_day in self.stock_data.index:
            current_value = self.stock_data.loc[current_day].Open
            self.last_stock_value = current_value
        else:
            current_value = self.last_stock_value
        self.ax.scatter([current_datetime], [current_value], color='red', s=100)  # Red point
        # self.ax.annotate(f'{current_value}', (current_datetime, current_value), textcoords="offset points", xytext=(0,10), ha='center')
        
        self.ax.legend()
        self.stock_canvas.draw()

    def get_images_df(self, front_camera):
        """Gets a DataFrame of all images at the time of inititation"""
        maybe = {42375, 33651, 30073, 29645, 28126, 50158, 53182, 55401, 57836, 58578, 58264, 68418, 72581,
                 73294, 73711, 77405, 87933, 90771, 99093, 99766, 108067, 110166, 110047, 114019}
        nvidia_frame_ids = {48715, 47478, 44212, 42009, 40327, 40012, 40006, 39362, 39130, 38431, 35434, 35054,
                            31998, 30186, 29333, 28415, 51163, 51633, 60145, 60244, 60272, 61842, 62721, 66021, 66086, 67706, 72945,
                            72169, 73147, 77773, 81928, 85394, 89059, 92740, 95947, 98813, 99028, 100683, 101218, 103798, 104452, 106681,
                            108271, 107569, 110035, 115009, 111802, 113269, 118242, 122937}
        nvidia_frames = maybe | nvidia_frame_ids
        images_df = self.db.get_frames(frame_ids=nvidia_frames)
        images_df = utils.add_datetimes(images_df)
        images_df = images_df.sort_values(by="datetime_local", ascending=False).reset_index(drop=True)
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

        # Main frames for layout
        self.left_frame = ttk.Frame(self.master)
        self.right_frame = ttk.Frame(self.master)

        # Grid layout
        self.left_frame.grid(row=0, column=0, sticky="nswe")
        self.right_frame.grid(row=0, column=1, sticky="nswe")

        # Configure columns to give them appropriate space allocation
        self.master.grid_columnconfigure(0, weight=1)  # Stock plot column
        self.master.grid_columnconfigure(1, weight=3)  # Screenshots display column

        self.create_stock_plot()

        # Stock plot is already created and packed, re-pack it in the left frame
        self.stock_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Remaining UI elements in the right frame
        self.top_frame = ttk.Frame(self.right_frame)
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)

        self.video_label = ttk.Label(self.right_frame)
        self.video_label.pack(expand=True, fill=tk.BOTH)

        self.time_label = ttk.Label(self.right_frame, textvariable=str(self.scroll_frame_num_var), font=("Arial", 24), anchor="e")
        self.time_label.pack(fill=tk.X)

        self.master.bind("<Right>", self.click_right)
        self.master.bind("<Left>", self.click_left)

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

    def display_frame(self, screenshot, frame_num):
        im_row = self.images_df.iloc[frame_num]
        print(f"frame_num: {frame_num} frame_id: {im_row['id']}")
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.scroll_frame_num_var.set(f"Time: {screenshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self.displayed_image = screenshot
        self.displayed_frame_num = frame_num
        self.update_stock_plot(screenshot.timestamp)

    # When the window is closed, you should also gracefully exit the preload thread
    def on_window_close(self):
        self.exit_flag = True
        self.master.destroy()

    def click_left(self, event):
        """Move to the next frame on the right."""
        if self.scroll_frame_num < self.max_frames_index:
            self.scroll_frame_num += 1
            self.update_frame_periodically()  # Force update to display the new frame

    def click_right(self, event):
        """Move to the previous frame on the left."""
        if self.scroll_frame_num > 0:
            self.scroll_frame_num -= 1
            self.update_frame_periodically() 

def main():
    root = tk.Tk()
    app = TimelineViewer(root, front_camera=True)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()