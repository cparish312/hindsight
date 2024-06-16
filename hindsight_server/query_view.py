import platform
import threading
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
from run_chromadb_ingest import get_chroma_collection
from timeline_view import Screenshot, TimelineViewer
import query

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

class QueryViewer:
    def __init__(self, master):
        self.master = master
        self.db = HindsightDB()
        self.images_df = self.get_images_df()
        self.chroma_collection = get_chroma_collection()
        self.first_date = min(self.images_df['datetime_local'])
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()

        self.max_width = self.screen_width - 50
        self.max_height = self.screen_height

        self.timeline_viewer = None

        self.setup_gui()

    def get_images_df(self):
        """Gets a DataFrame of all images at the time of inititation"""
        images_df = self.db.get_frames()
        images_df['datetime_utc'] = pd.to_datetime(images_df['timestamp'] / 1000, unit='s', utc=True)
        images_df['datetime_local'] = images_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
        return images_df.sort_values(by='datetime_local', ascending=False)
    
    def setup_gui(self):
        self.master.title("Query Manager")

        self.query_frame = ttk.Frame(self.master)
        self.query_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.query_label = ttk.Label(self.query_frame, text="New Query:")
        self.query_label.pack(side=tk.LEFT, padx=(0, 5))

        self.query_entry = ttk.Entry(self.query_frame)
        self.query_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.query_entry.bind("<Return>", lambda event: self.enter_new_query())

        self.date_range_label = ttk.Label(self.query_frame, text="Sources Date Range:")
        self.date_range_label.pack(side=tk.LEFT, padx=(20, 5))

        # Bug with blank calendar https://github.com/j4321/tkcalendar/issues/41
        self.start_date_entry = DateEntry(self.query_frame)
        self.start_date_entry.set_date(self.first_date)
        self.start_date_entry.pack(side=tk.LEFT, padx=(0, 5))

        self.end_date_label = ttk.Label(self.query_frame, text="to")
        self.end_date_label.pack(side=tk.LEFT, padx=(0, 5))

        self.end_date_entry = DateEntry(self.query_frame)
        self.end_date_entry.pack(side=tk.LEFT, padx=(0, 5))

        longest_app = max(self.images_df['application'], key=len)
        # Create applications selection option
        self.app_list = tk.Listbox(self.query_frame, selectmode = "multiple", width=len(longest_app)) 
        self.app_list.pack(side=tk.LEFT, padx=(0, 5)) 
        for app in sorted(list(set(self.images_df['application']))):
            self.app_list.insert(tk.END, app)

        self.button_frame = ttk.Frame(self.query_frame)
        self.button_frame.pack(fill=tk.X, expand=True)
        
        self.query_button = ttk.Button(self.button_frame, text="Enter Query", command=self.enter_new_query)
        self.query_button.pack(side=tk.TOP, padx=(10, 5), pady=10)

        self.refresh_button = ttk.Button(self.button_frame, text="Refresh", command=self.display_queries)
        self.refresh_button.pack(side=tk.TOP, padx=(5, 10), pady=10)
        
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
        self.display_queries()

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

    def convert_date_to_utc_milliseconds(self, date):
        datetime_date = pd.to_datetime(date).tz_localize(tzlocal.get_localzone())
        utc_date = datetime_date.tz_convert('UTC')
        return int(utc_date.timestamp() * 1000)

    def enter_new_query(self):
        query_text = self.query_entry.get()

        utc_milliseconds_start_date = self.convert_date_to_utc_milliseconds(self.start_date_entry.get_date())
        # Want to include all times within the end date
        utc_milliseconds_end_date = self.convert_date_to_utc_milliseconds(self.end_date_entry.get_date() + timedelta(hours=24))

        selected_apps = list()
        for i in self.app_list.curselection():
            selected_apps.append(self.app_list.get(i))
        selected_apps = selected_apps if len(selected_apps) > 0 else list(set(self.images_df['application']))

        query_id = self.db.insert_query(query=query_text)
        query_thread = threading.Thread(target=query.query, 
                                        args=(query_id, query_text, selected_apps, utc_milliseconds_start_date, utc_milliseconds_end_date))

        query_thread.start()

        self.display_queries()

    def display_queries(self):
        """Displays all active queries"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        queries = self.db.get_active_queries()

        if queries is not None and len(queries) == 0:
            return
        
        queries = queries.sort_values(by='timestamp', ascending=False)

        row_num = 0
        for q_row in queries.itertuples():
            self.display_query(q_row, row_num)

             # Adding a horizontal separator for visual distinction
            separator = ttk.Separator(self.scroll_frame, orient='horizontal')
            separator.grid(row=row_num + 1, column=0, sticky='ew', padx=10, pady=10, columnspan=3)

            row_num += 2 # Add for seperator

        # Update the window to ensure geometry calculations are correct
        self.master.update_idletasks()
        
        self.master.geometry(f"{self.screen_width}x{self.max_height}")

    def display_query(self, q_row, row):
        frame = ttk.Frame(self.scroll_frame)
        frame.grid(row=row, column=0, sticky='ew', padx=10, pady=0, columnspan=3)  # Ensure no vertical padding

        query_text = f"Query: {q_row.query}\nResult: {q_row.result}\n\nSources:"
        query_label = ttk.Label(frame, text=query_text, wraplength=self.max_width - 20)
        query_label.pack(fill='x', expand=True, padx=0, pady=0)  # No padding around the text label

        # Can't figure out how to get rid of the pad at the top of the scrollbar
        if q_row.source_frame_ids:
            source_frame_ids = q_row.source_frame_ids.split(',')
            source_frame_ids = [int(id_str.strip()) for id_str in source_frame_ids]
            for frame_id in source_frame_ids:
                id_label = tk.Label(frame, text=f"{frame_id}", fg="blue", cursor="hand2", padx=5)
                id_label.pack(side='left', padx=5, pady=0)
                id_label.bind("<Button-1>", lambda e, fid=frame_id: self.open_timeline_view(fid, source_frame_ids), add='+')

    def open_timeline_view(self, frame_id, query_source_ids):
        """Opens timeline view at the clicked frame"""
        if self.timeline_viewer is not None:
            self.timeline_viewer.master.destroy()
        
        sources_df = self.images_df.loc[self.images_df['id'].isin(query_source_ids)].reset_index(drop=True)
        timeline_window = tk.Toplevel(self.master)
        self.timeline_viewer = TimelineViewer(timeline_window, frame_id=frame_id, images_df=sources_df)

    def on_window_close(self):
        self.master.destroy()

def main():
    root = tk.Tk()
    app = QueryViewer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()

