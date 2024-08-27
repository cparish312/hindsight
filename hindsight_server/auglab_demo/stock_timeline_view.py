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
import matplotlib.dates as mdates
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
    def __init__(self, master, frame_id = None, max_width=2400, max_height=1000, images_df=None, front_camera=None):
        self.master = master
        # self.master.attributes('-fullscreen', True)
        # self.full_screen = False

        self.db = HindsightDB(db_file="./data/auglabdemo.db")
        self.images_df = self.get_images_df(front_camera) if images_df is None else images_df
        self.num_frames = len(self.images_df)
        self.max_frames_index = max(self.images_df.index)
        self.app_color_map = self.get_app_color_map()
        self.max_width = max_width
        self.max_height = max_height - 200

        self.all_nvda_frames = pd.read_csv("./all_nvda_frames.csv")
        self.all_nvda_frames = utils.add_datetimes(self.all_nvda_frames)

        if frame_id is None:
            self.scroll_frame_num = self.images_df.index[-1]
        else:
            self.scroll_frame_num = self.images_df.index.get_loc(self.images_df[self.images_df['id'] == frame_id].index[0])
        self.scroll_frame_num_var = tk.StringVar()

        self.setup_gui()
    
        self.exit_flag = False

    def create_stock_plot(self):
        # Example data for the plot

        self.stock_data = pd.read_csv('./data/nvidia_stock_during.csv')
        self.stock_data = utils.add_datetimes(self.stock_data)
        self.stock_data = self.stock_data.iloc[:300]
        self.start_date = min(self.stock_data['datetime_local']).date()
        self.end_date = max(self.stock_data['datetime_local']).date()

        self.all_nvda_frames = self.all_nvda_frames.loc[self.all_nvda_frames['datetime_local'] <= max(self.stock_data['datetime_local'])]
        
        self.figure = plt.Figure(figsize=(11, 4), dpi=100)
    
        self.ax = self.figure.add_subplot(111)
        self.ax.plot(self.stock_data['Adj Close']) 
        self.ax.set_title('NVDA Stock Prices from {} to {}'.format(self.start_date, 
                                                self.end_date))

        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha="right") 
        # self.ax.legend()
        
        self.stock_canvas = FigureCanvasTkAgg(self.figure, self.left_frame)
        self.stock_canvas_widget = self.stock_canvas.get_tk_widget()
        self.stock_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def get_interpolated_stock_price(self, current_datetime):
        data_with_distance = self.stock_data.copy()
        data_with_distance['distance'] = data_with_distance['datetime_local'] - current_datetime
        before = data_with_distance[data_with_distance['distance'] <= pd.Timedelta(0)].iloc[-1] if not data_with_distance[data_with_distance['distance'] <= pd.Timedelta(0)].empty else None
        after = data_with_distance[data_with_distance['distance'] > pd.Timedelta(0)].iloc[0] if not data_with_distance[data_with_distance['distance'] > pd.Timedelta(0)].empty else None
        
        if before['datetime_local'] == current_datetime:
            # Exact match
            interpolated_value = before['Adj Close']
        elif before is None or after is None:
            raise ValueError("Couldn't interpolate")
        else:
            # Linear interpolation
            total_seconds = (after['datetime_local'] - before['datetime_local']).total_seconds()
            weight = (current_datetime - before['datetime_local']).total_seconds() / total_seconds
            interpolated_value = before['Adj Close'] + (after['Adj Close'] - before['Adj Close']) * weight
        return interpolated_value

    def update_stock_plot(self, current_datetime):
        # Clear previous points
        self.ax.clear()
        # Redraw the plot
        self.ax.plot(self.stock_data['datetime_local'], self.stock_data['Adj Close'])
        # Draw a point for the current frame

        interpolated_stock_price = self.get_interpolated_stock_price(current_datetime)

        self.ax.scatter([current_datetime], [interpolated_stock_price], color='red', s=100)  # Red point
        self.ax.annotate(f'${round(interpolated_stock_price,2)}', (current_datetime, interpolated_stock_price), 
                         textcoords="offset points", xytext=(-80,30), ha='center', 
                         arrowprops=dict(arrowstyle="->", connectionstyle="arc3", color='red'))
        
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha="right") 
        self.ax.set_title('NVDA Stock Prices from {} to {}'.format(self.start_date, 
                                                self.end_date))
        
        # buy_datetime, buy_value = (datetime(2022, 4, 22), 19.53)
        # self.ax.scatter([buy_datetime], [buy_value], color='blue', s=200)
        # self.ax.annotate(f'Connor buys NVDA at {buy_value}', (buy_datetime, buy_value), 
        #                  textcoords="offset points", xytext=(0,40), ha='center', 
        #                  arrowprops=dict(arrowstyle="->", connectionstyle="arc3", color='red'))
        
        # self.ax.legend()
        self.stock_canvas.draw()

    def final_stock_plot(self):
        self.ax.clear()
        # Redraw the plot
        self.ax.plot(self.stock_data['datetime_local'], self.stock_data['Adj Close'])
        # Draw a point for the current frame
        
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha="right") 
        self.ax.set_title('All Times I Saw Information About Nvidia'.format(self.start_date, 
                                                self.end_date))

        applications = self.all_nvda_frames['application'].unique()
        colors = plt.cm.jet(np.linspace(0, 1, len(applications)))
        color_dict = dict(zip(applications, colors))  
        
        for i, row in self.all_nvda_frames.iterrows():
            dt = row['datetime_local']
            app = row['application']
            interpolated_stock_price = self.get_interpolated_stock_price(dt)
            self.ax.scatter([dt], [interpolated_stock_price], color=color_dict[app], s=100, label=app if app not in self.ax.get_legend_handles_labels()[1] else "")


        earning_date = datetime(2024, 5, 22)
        self.ax.axvline(x=earning_date, color='r', label="earning date")
        # buy_datetime, buy_value = (datetime(2022, 4, 22), 19.53)
        # self.ax.scatter([buy_datetime], [buy_value], color='blue', s=200)
        # self.ax.annotate(f'Connor buys NVDA at {buy_value}', (buy_datetime, buy_value), 
        #                  textcoords="offset points", xytext=(0,40), ha='center', 
        #                  arrowprops=dict(arrowstyle="->", connectionstyle="arc3", color='red'))
        
        # self.ax.legend()

        def skip_app(a):
            if a[:4] == "com-":
                return True
            if a == "screenshot":
                return True
            return False
        
        handles, labels = self.ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))  # removing duplicates in legend
        by_label = {a : c for a, c in by_label.items() if not skip_app(a)}
        self.ax.legend(by_label.values(), by_label.keys())
        self.stock_canvas.draw()

    def get_images_df(self, front_camera):
        """Gets a DataFrame of all images at the time of inititation"""
        maybe = {110047}
        nvidia_frame_ids = {48715, 47478, 44212, 42010, 40327, 40012, 40006, 39362, 39130, 38431, 35434, 35054,
                            31998, 30186, 29333, 28415, 51163, 51633, 60145, 60244, 60272, 61842, 62721, 66021, 66086, 67706, 72945,
                            72169, 73147, 77773, 81928, 85394, 89059, 92740, 95947, 98751, 99028, 100683, 101218, 103798, 104452, 106681,
                            108271, 107569, 110035, 115009, 111802, 122937}
        need_frame_ids = {48715, 44212, 42010, 40327, 40006, 39130, 51163, 60272, 72945, 85394, 98751}

        actually_need_frame_ids = {40006, 39130, 51163, 60272, 72945, 106681, 107569, 111802}
        actually_probably_frame_ids = {42010, 40327, 35434, 28415, 66086, 72169, 77773, 81928, 85394, 95947, 115009}
        probably_frame_ids = {44212, 42010, 40327, 39362, 35434, 28415, 28415, 61842, 66021, 66086, 67706, 72169, 
                              77773, 81928, 85394, 95947, 98751, 99028, 101218, 108271, 110035, 115009}
        
        final_frame_ids = {40327, 40006, 39130, 28415, 51163, 72945, 85394, 95947, 106681, 107569, 111802}
        
        # 115009 tweet about Nvidia 5 years ago stock
        # 60145 boob
        # nvidia_frames = maybe | nvidia_frame_ids
        # nvidia_frames = nvidia_frame_ids | maybe
        # nvidia_frames = actually_need_frame_ids | actually_probably_frame_ids
        nvidia_frames = final_frame_ids
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
        self.left_frame.grid(row=0, column=0, sticky="nswe", padx=(0,10))
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

        self.video_container = ttk.Frame(self.right_frame)
        self.video_container.pack(expand=True, fill=tk.BOTH)

        self.time_label = ttk.Label(self.video_container, textvariable=str(self.scroll_frame_num_var), font=("Arial", 24), anchor="w")
        self.time_label.pack(fill=tk.X)

        self.video_label = ttk.Label(self.video_container)
        self.video_label.pack(expand=True, fill=tk.BOTH)

        self.master.bind("<Right>", self.click_right)
        self.master.bind("<Left>", self.click_left)
        self.master.bind("<Configure>", self.on_window_resize)

        self.displayed_frame_num = self.scroll_frame_num
        screenshot = self.get_screenshot(self.displayed_frame_num)
        self.display_frame(screenshot, self.displayed_frame_num)
        self.master.after(40, self.update_frame_periodically)

    def on_window_resize(self, event=None):
        # Adjust the max width and height according to the new window size
        self.max_width = self.master.winfo_width()
        self.max_height = self.master.winfo_height() - 20
        print(self.max_width, self.max_height)
        if hasattr(self, 'displayed_image'):
            self.display_frame(self.displayed_image, self.displayed_frame_num)
    
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
        print(self.right_frame.winfo_width(), self.right_frame.winfo_height())
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

        self.video_container.configure(width=imgtk.width())
        self.scroll_frame_num_var.set(f"{screenshot.timestamp.strftime('%A, %Y-%m-%d %H:%M')}")
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
        else:
            print("Showing final stock plot")
            self.final_stock_plot()

def main():
    root = tk.Tk()
    app = TimelineViewer(root, front_camera=True)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()