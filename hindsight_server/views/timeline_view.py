"""GUI for scrolling through screenshots timeline."""
import cv2
from datetime import datetime
import platform
import matplotlib
import numpy as np
import pandas as pd
import colorcet as cc
from tkinter import Tk, ttk
from tkinter import StringVar, Canvas, messagebox, Toplevel
from PIL import Image, ImageTk

import tzlocal
from zoneinfo import ZoneInfo
from dataclasses import dataclass

import sys
sys.path.insert(0, "../")
sys.path.insert(0, "./")

from db import HindsightDB

@dataclass
class Screenshot:
    image: np.array
    text_df: pd.DataFrame
    timestamp: datetime.timestamp

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")
timeline_scrollbar_height = 50

def get_images_df(db: HindsightDB, front_camera):
    """Gets a DataFrame of all images at the time of inititation"""
    if front_camera is None:
        images_df = db.get_screenshots()
    elif front_camera:
        images_df = db.get_frames(applications=["frontCamera"])
    else:
        images_df = db.get_frames(applications=["backCamera"])
    images_df['datetime_utc'] = pd.to_datetime(images_df['timestamp'] / 1000, unit='s', utc=True)
    images_df['datetime_local'] = images_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
    return images_df.sort_values(by='datetime_local', ascending=False)

def get_app_color_map(images_df: pd.DataFrame):
    # Generate a color map for each app, ensuring colors are distinguishable
    unique_apps = images_df['application'].unique()
    num_apps = len(unique_apps)
    
    # Choose a colormap with a sufficient number of colors
    cmap = cc.cm['rainbow']  # 'rainbow', 'colorwheel', etc., could also be good choices
    
    # Generate color indices spaced evenly throughout the colormap
    colors = [cmap(i / (num_apps - 1)) if num_apps > 1 else cmap(0.5) for i in range(num_apps)]

    hex_colors = [matplotlib.colors.to_hex(color) for color in colors]
    
    return {app: hex_colors[i] for i, app in enumerate(unique_apps)}

def resize_screenshot(screenshot: Screenshot, max_width: int, max_height: int):
    print((max_width, max_height))
    height, width, _ = screenshot.image.shape
    if width > max_width or height > max_height:
        scaling_factor = min(float(max_width) / width, float(max_height) / height)
        (sizex, sizey) = (int(width * scaling_factor), int(height * scaling_factor))
        # max is a hack to prevent / 0 exceptions on startup
        sizex = max(1, sizex)
        sizey = max(1, sizey)
        print('sizes:',(sizex, sizey))
        screenshot.image = cv2.resize(screenshot.image, (sizex, sizey), interpolation=cv2.INTER_AREA)
        if screenshot.text_df is not None:
            screenshot.text_df.loc[:, 'x'] = screenshot.text_df['x'] * scaling_factor
            screenshot.text_df.loc[:, 'y'] = screenshot.text_df['y'] * scaling_factor
            screenshot.text_df.loc[:, 'w'] = screenshot.text_df['w'] * scaling_factor
            screenshot.text_df.loc[:, 'h'] = screenshot.text_df['h'] * scaling_factor
    return screenshot

class TimelineViewer:
    def __init__(self, root: Tk, database: HindsightDB, front_camera=None):
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        max_width = int(screen_width * 0.75)
        max_height = int(screen_height * 0.75)
        root.geometry('%dx%d-100-100' % (max_width, max_height)) # fill 3/4 of screen, position 100 px from top right
        
        self.master = ttk.Frame(root, borderwidth=5, relief='ridge', padding='10 10 10 10')
        self.master.grid(column=0, row=0, sticky='nswe')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.db = database
        self.images_df = get_images_df(self.db, front_camera)
        self.num_frames = len(self.images_df)
        self.max_frames_index = int(max(self.images_df.index)) # cast to int to ensure we have the right datatype
        self.app_color_map = get_app_color_map(self.images_df)
        self.max_width = max_width
        self.max_height = max_height
        self.full_screen = False

        self.screenshots_on_timeline = 40 

        self.scroll_frame_num = 0 # lower index is most recent, index is 0 - based
        # self.scroll_frame_num = self.images_df.index.get_loc(self.images_df[self.images_df['id'] == frame_id].index[0]) # does this even work??
        
        self.frame_timestamp = StringVar(master=self.master, value='--------------')

        # For mouse dragging
        self.dragging = False
        self.drag_start = None
        self.drag_end = None
        self.exit_flag = False

        self.setup_gui()
    
    def setup_gui(self):

        self.top_frame = ttk.Frame(self.master, padding='5 5 5 5', style='Frame1.TFrame')
        self.top_frame.grid(column=0, row=0, sticky='ew')
        self.top_frame.columnconfigure(0, weight=1) # expand top row's column to fill container

        self.search_button = ttk.Button(self.top_frame, text="Search", command=self.open_search_view)
        self.search_button.grid(column=0, row=0, sticky='e')
        
        self.video_label = ttk.Label(self.master, anchor='center', style='1.TLabel')
        self.video_label.grid(column=0, row=1, sticky='nsew')
        self.master.rowconfigure(1, weight=1) # expand canvas row to fit space
        self.video_label.bind("<Button-1>", self.start_drag)
        self.video_label.bind("<B1-Motion>", self.on_drag)
        self.video_label.bind("<ButtonRelease-1>", self.end_drag)

        self.timeline_canvas = Canvas(self.master, height=timeline_scrollbar_height, background='gray75')
        self.timeline_canvas.grid(column=0, row=2, sticky='ew')

        self.time_label = ttk.Label(self.master, textvariable=self.frame_timestamp, font=("Arial", 24), anchor="e")
        self.time_label.grid(column=0, row=3)
        
        self.bind_scroll_event()
        self.master.bind('<Configure>', lambda e: self.handle_resize())
        self.master.bind('<Destroy>', lambda e: self.on_window_close())
        
        self.master.winfo_toplevel().bind('<Escape>', lambda e: self.master.winfo_toplevel().destroy())
        self.master.winfo_toplevel().bind('f', lambda e: self.switch_fullscreen())
        self.master.winfo_toplevel().bind('F', lambda e: self.switch_fullscreen())

        self.master.winfo_toplevel().bind("<Right>", self.click_right)
        self.master.winfo_toplevel().bind("<Left>", self.click_left)

        # draw initial frame
        self.update_frame()

    def handle_resize(self):
        self.max_width = self.master.winfo_toplevel().winfo_width()
        self.max_height = self.master.winfo_toplevel().winfo_height()
        print('size ', (self.max_width, self.max_height))
        self.master.winfo_toplevel().update() # evaluate geometry manager for cases such as fullscreen and startup
        self.update_frame()

    def switch_fullscreen(self, back_forth=True):
        self.full_screen = not self.full_screen if back_forth else False
        self.master.winfo_toplevel().attributes("-fullscreen", 1 if self.full_screen else 0)

    def get_screenshot(self, i):
        """Loads and resizes the screenshot."""
        im_row = self.images_df.iloc[i]
        image = cv2.imread(im_row['path'])
        text_df = self.db.get_ocr_results(frame_id=im_row['id'])
        if set(text_df['text']) == {None}:
            text_df = None
        return Screenshot(image=image, text_df=text_df, timestamp=im_row['datetime_local'])

    def get_apps_near(self, current_frame_num: int):
        timeline_border = self.screenshots_on_timeline // 2
        apps_before = self.images_df.iloc[current_frame_num+1:current_frame_num+timeline_border+1]['application']
        apps_after = self.images_df.iloc[max(current_frame_num-timeline_border, 0):current_frame_num]['application']
        return apps_before, apps_after

    def update_timeline(self):
        self.timeline_canvas.delete("all")  # Clear existing drawings
        width = self.timeline_canvas.winfo_width()
        apps_before, apps_after = self.get_apps_near(self.scroll_frame_num)  # Implement this function

        timeline_screenshot_width = width / self.screenshots_on_timeline

        start_pos = width / 2 # start in the middle of the timeline
        for app in apps_before: # Reverse order of list to start at current screenshot
            color = self.app_color_map[app]
            self.timeline_canvas.create_rectangle(start_pos, 0, start_pos-timeline_screenshot_width, timeline_scrollbar_height, fill=color, outline='')
            start_pos -= timeline_screenshot_width

        start_pos = (width / 2)  + timeline_screenshot_width # start in the middle of the timeline
        for app in apps_after[::-1]: # Reverse order of list to start at current screenshot
            color = self.app_color_map[app]
            self.timeline_canvas.create_rectangle(start_pos, 0, start_pos+timeline_screenshot_width, timeline_scrollbar_height, fill=color, outline='')
            start_pos += timeline_screenshot_width

        # Draw current app
        start_pos = width / 2 # start in the middle of the timeline
        current_app = self.images_df.iloc[self.scroll_frame_num]['application']
        color = self.app_color_map[current_app]
        self.timeline_canvas.create_rectangle(start_pos, 0, start_pos+timeline_screenshot_width, timeline_scrollbar_height, fill=color, outline="black")

    def update_frame(self):
        self.update_screenshot()
        self.update_timeline()
        self.frame_timestamp.set(f"{self.displayed_image.timestamp.strftime('%A, %Y-%m-%d %H:%M')}")

    def update_screenshot(self):
        screenshot = resize_screenshot(
            self.get_screenshot(self.scroll_frame_num),
            self.video_label.winfo_width(),
            self.video_label.winfo_height()
        )
        im_row = self.images_df.iloc[self.scroll_frame_num]
        print(f"frame_num: {self.scroll_frame_num} frame_id: {im_row['id']}")
        cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.displayed_image = screenshot

    def bind_scroll_event(self):
        # Detect platform and bind the appropriate event
        os_name = platform.system()
        if os_name == "Linux":
            self.master.winfo_toplevel().bind("<Button-4>", self.on_scroll_up)
            self.master.winfo_toplevel().bind("<Button-5>", self.on_scroll_down)
        else:  # Windows and macOS
            self.master.winfo_toplevel().bind("<MouseWheel>", self.on_mouse_wheel)
    
    def scroll_frames(self, delta: int):
        next_frame_num = self.scroll_frame_num + delta

        if next_frame_num > self.max_frames_index:
            next_frame_num = self.max_frames_index
        if next_frame_num < 0:
            next_frame_num = 0
        
        if next_frame_num != self.scroll_frame_num:
            self.scroll_frame_num = next_frame_num
            self.update_frame()

    def on_mouse_wheel(self, event):
        # Windows and macOS handle scroll direction differently
        if platform.system() == "Windows":
            self.scroll_frames( int(event.delta / 120) )
        else:  # macOS
            self.scroll_frames( - int(event.delta) )

    def on_scroll_up(self, event):
        self.scroll_frames(-1)

    def on_scroll_down(self, event):
        self.scroll_frames(1)

    def click_left(self, event):
        self.scroll_frames(1)

    def click_right(self, event):
        self.scroll_frames(-1)

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

        search_window = Toplevel(self.master)
        SearchViewer(search_window)

    # When the window is closed, you should also gracefully exit the preload thread
    def on_window_close(self):
        print('setting exit flag')
        self.exit_flag = True

def main():
    root = Tk()
    # Initialize style
    s = ttk.Style()
    # Create style used by default for all Frames
    s.configure('TFrame', background='green')
    s.configure('Frame1.TFrame', background='red')
    s.configure('1.TLabel', background='blue')

    root.title("Hindsight Server GUI")
    app = TimelineViewer(root, database=HindsightDB(), front_camera=None)
    root.mainloop()

if __name__ == "__main__":
    main()