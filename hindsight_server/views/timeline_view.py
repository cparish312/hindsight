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
from PIL import Image, ImageDraw, ImageFont

import tzlocal
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from hindsight_server.db import HindsightDB
from hindsight_server.utils import get_ids_to_images

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
        images_df = db.get_screenshots(impute_applications=False)
        images_df = images_df.dropna(subset=['video_chunk_path'])
    elif front_camera:
        images_df = db.get_frames(applications=["frontCamera"])
    else:
        images_df = db.get_frames(applications=["backCamera"])

    images_df = images_df.loc[images_df['source'] != "rem"].reset_index(drop=True)
    # images_df = images_df.loc[images_df['source'].isnull()].reset_index(drop=True)
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
    width, height = screenshot.image.size
    size_ratios = float(max_width) / float(width), float(max_height) / float(height)
    scaling_factor = min(size_ratios)
    # max 1 is a hack to prevent / 0 exceptions on startup
    display_size = (max(1, int(width * scaling_factor)), max(1, int(height * scaling_factor)))
    xoffset, yoffset = 0, 0
    if size_ratios.index(scaling_factor) == 0:
        yoffset = (max_height - display_size[1]) / 2.0
    else:
        xoffset = (max_width - display_size[0]) / 2.0
    screenshot.image = screenshot.image.resize(display_size, Image.Resampling.LANCZOS)
    if screenshot.text_df is not None:
        screenshot.text_df.loc[:, 'x'] = screenshot.text_df['x'] * scaling_factor + xoffset
        screenshot.text_df.loc[:, 'y'] = screenshot.text_df['y'] * scaling_factor + yoffset
        screenshot.text_df.loc[:, 'w'] = screenshot.text_df['w'] * scaling_factor
        screenshot.text_df.loc[:, 'h'] = screenshot.text_df['h'] * scaling_factor
    
    return screenshot

def get_ocr_results(db: HindsightDB, images_df: pd.DataFrame):
    """Get's a df with ocr_results for the first 1000 frames in the images_df"""
    retrieve_ocr_frame_ids = list(images_df.iloc[0:1000]['id'])
    return db.get_frames_with_ocr(frame_ids=retrieve_ocr_frame_ids)

def rectangles_overlap(rect1, rect2):
    """Check if two rectangles overlap. Rectangles are defined as (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = rect1
    rx1, ry1, rx2, ry2 = rect2
    return not (rx1 > x2 or rx2 < x1 or ry1 > y2 or ry2 < y1)

class TimelineViewer:
    def __init__(self, root: Tk, database: HindsightDB, front_camera=None, images_df=None, frame_id=None, annotations=None):
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
        self.annotations = annotations
        self.images_df = get_images_df(self.db, front_camera) if images_df is None else images_df
        self.ocr_results = get_ocr_results(self.db, self.images_df)
        self.max_frames_index = int(max(self.images_df.index)) # cast to int to ensure we have the right datatype
        self.app_color_map = get_app_color_map(self.images_df)
        self.max_width = max_width
        self.max_height = max_height
        self.full_screen = False

        self.screenshots_on_timeline = 80 

        if frame_id is None:
            self.scroll_frame_num = 0 # lower index is most recent, index is 0 - based
        else:
            self.scroll_frame_num = self.images_df.index.get_loc(self.images_df[self.images_df['id'] == frame_id].index[0])
        
        self.frame_timestamp = StringVar(master=self.master, value='--------------')

        # For mouse dragging
        self.dragging = False
        self.drag_start = None
        self.drag_end = None
        self.exit_flag = False
        self.timeline_skip_delta = 0 # 0 implies no scrolling

        # draw containers
        self.setup_gui()
        # draw initial frame
        self.update_frame()
    
    def setup_gui(self):
        self.top_frame = ttk.Frame(self.master, padding='5 5 5 5', style='1.TFrame')
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
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_press)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self.on_timeline_release)

        self.time_label = ttk.Label(self.master, textvariable=self.frame_timestamp, font=("Arial", 24), anchor="e")
        self.time_label.grid(column=0, row=3)
        
        self.bind_scroll_event()
        self.master.bind('<Configure>', self.handle_resize)
        self.master.bind('<Destroy>', self.on_window_close)
        
        self.master.winfo_toplevel().bind('<Escape>', self.handle_escape)
        self.master.winfo_toplevel().bind('f', self.switch_fullscreen)
        self.master.winfo_toplevel().bind('F', self.switch_fullscreen)

        self.master.winfo_toplevel().bind("<Right>", self.handle_right)
        self.master.winfo_toplevel().bind("<Left>", self.handle_left)

        self.master.winfo_toplevel().update() # evaluate geometry manager for cases such as fullscreen and startup

    def handle_resize(self, event):
        self.max_width = self.master.winfo_toplevel().winfo_width()
        self.max_height = self.master.winfo_toplevel().winfo_height()
        print('resized to', (self.max_width, self.max_height))
        self.update_frame()

    def switch_fullscreen(self, event=None):
        self.full_screen = not self.full_screen
        self.master.winfo_toplevel().wm_attributes("-fullscreen", 1 if self.full_screen else 0)
        self.master.winfo_toplevel().update() # evaluate geometry manager for cases such as fullscreen and startup
        self.update_frame()

    def handle_escape(self, event):
        if self.full_screen:
            self.switch_fullscreen()
        else:
            self.master.winfo_toplevel().destroy()

    def get_screenshot(self, i):
        """Loads and resizes the screenshot."""
        im_df = self.images_df.iloc[[i]]
        id_to_images = get_ids_to_images(im_df)
        im_row = im_df.iloc[0]
        image_array = list(id_to_images.values())[0]
        image = Image.fromarray(image_array)
        # image = cv2.imread(im_row['path'])
        # image = Image.open(im_row['path'])
        text_df = self.ocr_results.loc[self.ocr_results["frame_id"] == im_row['id']]
        # text_df = self.db.get_ocr_results(frame_id=im_row['id'])
        if set(text_df['text']) == {None} or len(text_df) == 0:
            text_df = None
        print("Number of OCR results for frame", len(text_df))

        if self.annotations is not None:
            frame_annotations = self.annotations.loc[self.annotations['frame_id'] == im_df['id']]
            if len(frame_annotations) > 0:
                font = ImageFont.load_default()

                draw = ImageDraw.Draw(image)
                for i, row in frame_annotations.iterrows():
                    draw.rectangle((row['x'], row['y'], row['x'] + row['w'], row['y'] + row['h']), outline="red", width=5)
                    text_position = (row['x'], row['y'] - 10)
                    try:
                        draw.text(text_position, row['label'], fill="white", font=font)
                    except:
                        print("Couldn't draw", row['label'])
        return Screenshot(image=image, text_df=text_df, timestamp=im_row['datetime_local'])

    def get_apps_near(self, current_frame_num: int):
        timeline_border = self.screenshots_on_timeline // 2
        apps_before = self.images_df.iloc[current_frame_num+1:current_frame_num+timeline_border+1]['application']
        apps_after = self.images_df.iloc[max(current_frame_num-timeline_border, 0):current_frame_num]['application']
        return apps_before, apps_after

    def get_timeline_screenshot_width(self):
        width = self.timeline_canvas.winfo_width()
        return width / self.screenshots_on_timeline
    
    def get_current_app_timeline_offset(self):
        width = self.timeline_canvas.winfo_width()
        timeline_screenshot_width = self.get_timeline_screenshot_width()
        return (width - timeline_screenshot_width) / 2
    
    def update_timeline(self):
        self.timeline_canvas.delete("all")  # Clear existing drawings
        apps_before, apps_after = self.get_apps_near(self.scroll_frame_num)  # Implement this function
        timeline_screenshot_width = self.get_timeline_screenshot_width()

        start_pos = self.get_current_app_timeline_offset()
        for app in apps_before: # Reverse order of list to start at current screenshot
            color = self.app_color_map[app]
            self.timeline_canvas.create_rectangle(start_pos, 0, start_pos-timeline_screenshot_width, timeline_scrollbar_height, fill=color, outline='')
            start_pos -= timeline_screenshot_width

        start_pos = self.get_current_app_timeline_offset() + timeline_screenshot_width
        for app in apps_after[::-1]: # Reverse order of list to start at current screenshot
            color = self.app_color_map[app]
            self.timeline_canvas.create_rectangle(start_pos, 0, start_pos+timeline_screenshot_width, timeline_scrollbar_height, fill=color, outline='')
            start_pos += timeline_screenshot_width

        # Draw current app
        start_pos = self.get_current_app_timeline_offset()
        current_app = self.images_df.iloc[self.scroll_frame_num]['application']
        color = self.app_color_map[current_app]
        self.timeline_canvas.create_rectangle(start_pos, 0, start_pos+timeline_screenshot_width, timeline_scrollbar_height, fill=color, outline="black")

    def update_frame(self):
        self.update_screenshot()
        self.update_timeline()
        self.frame_timestamp.set(f"{self.displayed_screenshot.timestamp.strftime('%A, %Y-%m-%d %H:%M:%S')}")

    def update_screenshot(self):
        width, height = ( self.video_label.winfo_width(), self.video_label.winfo_height() )
        screenshot = resize_screenshot(
            self.get_screenshot(self.scroll_frame_num),
            width,
            height
        )
        im_row = self.images_df.iloc[self.scroll_frame_num]
        print(f"frame_num: {self.scroll_frame_num} frame_id: {im_row['id']}")
        # cv2image = cv2.cvtColor(screenshot.image, cv2.COLOR_BGR2RGB)
        # img = Image.fromarray(cv2image)
        img = screenshot.image
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.displayed_screenshot = screenshot

    def should_update_frame(self):
        return not self.exit_flag and self.timeline_skip_delta != 0
    
    def update_scroll_periodically(self):
        if not self.should_update_frame():
            return
        self.scroll_frames(self.timeline_skip_delta)
        self.master.after(20, self.update_scroll_periodically)

    def on_timeline_press(self, event):
        self.on_timeline_drag(event)
        self.update_scroll_periodically()
    
    def on_timeline_drag(self, event):
        delta_from_first_app = (event.x - self.get_current_app_timeline_offset()) / self.get_timeline_screenshot_width()
        self.timeline_skip_delta = - int(delta_from_first_app)

    def on_timeline_release(self, event):
        self.timeline_skip_delta = 0

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

    def handle_left(self, event):
        self.scroll_frames(1)

    def handle_right(self, event):
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

    def copy_texts_within_drag_area(self):
        """Gets all text in the area the user has dragged"""
        if self.drag_start is None or self.drag_end is None:
            return
        x1 = min(self.drag_start[0], self.drag_end[0]) 
        y1 = min(self.drag_start[1], self.drag_end[1])
        x2 = max(self.drag_start[0], self.drag_end[0]) 
        y2 = max(self.drag_start[1], self.drag_end[1])

        text_df = self.displayed_screenshot.text_df
        selected_texts = []
        if text_df is not None:
            texts_in_area = text_df.apply(lambda row: rectangles_overlap((x1, y1, x2, y2), (row['x'], row['y'], row['x'] + row['w'], row['y'] + row['h'])), axis=1)
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
    def on_window_close(self, event):
        print('setting exit flag')
        self.exit_flag = True

def main():
    root = Tk()
    # Initialize style
    s = ttk.Style()
    # frame styles for debugging
    # s.configure('TFrame', background='green') # default frame style
    # s.configure('1.TFrame', background='red')
    # s.configure('1.TLabel', background='blue')

    root.title("Hindsight Server GUI")
    app = TimelineViewer(root, database=HindsightDB(), front_camera=None)
    root.mainloop()

if __name__ == "__main__":
    main()