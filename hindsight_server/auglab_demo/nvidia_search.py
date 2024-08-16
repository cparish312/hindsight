import tkinter as tk

import sys

sys.path.insert(0, "../")
import utils
from db import HindsightDB
from timeline_view import TimelineViewer

db = HindsightDB()

# search_results = db.search(text="Nvidia", n_seconds=500)
# search_results_2 = db.search(text="NVDA", n_seconds=500)
# search_results_3 = db.search(text="Jensen Huang", n_seconds=500)
# res_frame_ids = set(search_results['id']) | set(search_results_2['id']) | set(search_results_3['id'])

# nvidia_df = db.get_frames(frame_ids=res_frame_ids)
# nvidia_df = utils.add_datetimes(nvidia_df)
# nvidia_df = nvidia_df.sort_values(by="datetime_local", ascending=False).reset_index(drop=True)

# maybe = [42375, 33651, 30073, 29645, 28126, 50158, 53182, 55401, 57836, 58578, 58264, 68418, 72581,
#          73294, 73711, 77405, 87933, 90771, 99093, 99766, 108067, 110166, 110047, 114019]
# nvidia_frame_ids = [48715, 47478, 44212, 42009, 40327, 40012, 40006, 39362, 39130, 38431, 35434, 35054,
#                     31998, 30186, 29333, 28415, 51163, 51633, 60145, 60244, 60272, 61842, 62721, 66021, 66086, 67706, 72945,
#                     72169, 73147, 77773, 81928, 85394, 89059, 92740, 95947, 98813, 99028, 100683, 101218, 103798, 104452, 106681,
#                     108271, 107569, 110035, 115009, 111802, 113269, 118242, 122937]

# 51163 Google text rec to add more NVDA

def main():
    root = tk.Tk()
    # app = TimelineViewer(root, images_df=nvidia_df, frame_id=nvidia_df.iloc[-1]['id'])
    app = TimelineViewer(root, frame_id=112500)
    root.protocol("WM_DELETE_WINDOW", app.on_window_close)  # Handle window close event
    root.mainloop()

if __name__ == "__main__":
    main()