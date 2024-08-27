import sys
import base64
import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, "../")
from db import HindsightDB
import utils
import matplotlib.pyplot as plt
from config import RAW_SCREENSHOTS_DIR

from scipy.cluster.hierarchy import linkage, dendrogram
import matplotlib.pyplot as plt

from flask import Flask, send_from_directory
import dash
from dash import html, dcc
import plotly.figure_factory as ff
import plotly.graph_objects as go
from dash.dependencies import Input, Output

db = HindsightDB()

frames = db.get_frames(impute_applications=False)
frames = utils.add_datetimes(frames)
frames = frames.sort_values(by='datetime_local', ascending=False)

df = frames.loc[frames['application'] == 'Whatsapp'].iloc[:100]

ocr_res = db.get_frames_with_ocr(frame_ids=set(df['id']))
for c in ['x', 'y', 'w', 'h']:
    ocr_res[c] = ocr_res[c].round()

ocr_res['text_box'] = ocr_res.apply(lambda row: (row['text'], row['x'], row['y']), axis=1)

item_sets = ocr_res.groupby('frame_id')['text_box'].apply(set).to_dict()

frame_ids = list(item_sets.keys())
n = len(frame_ids)
similarity_matrix = np.zeros((n, n))

for i in range(n):
    for j in range(n):
        if i != j:
            intersection = len(item_sets[frame_ids[i]].intersection(item_sets[frame_ids[j]]))
            print(intersection)
            similarity_matrix[i, j] = intersection
            # union = len(item_sets[frame_ids[i]].union(item_sets[frame_ids[j]]))
            # similarity_matrix[i, j] = intersection / union if union != 0 else 0

distance_matrix = 1 - similarity_matrix

# Create a Dash application
server = Flask(__name__)
app = dash.Dash(__name__, server=server)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('ascii')

dendro_fig = ff.create_dendrogram(similarity_matrix, labels=frame_ids)
dendro_fig.update_layout(width=800, height=500)

# Add scatter plot for clickable nodes
leaf_positions = dendro_fig['layout']['xaxis']['tickvals']
leaf_labels = dendro_fig['layout']['xaxis']['ticktext']

dendro_fig.add_trace(go.Scatter(
    x=leaf_positions,
    y=[0]*len(leaf_positions),  # Assuming the leaves are at y = 0
    mode='markers',
    marker=dict(size=12, color='rgb(140, 86, 75)'),  # Adjust size and color as needed
    text=leaf_labels,
    hoverinfo='text',
    showlegend=False
))

# Callback for handling clicks on the dendrogram and updating the image
@app.callback(
    Output('image-display', 'src'),
    Input('dendrogram-graph', 'clickData')
)
def display_image(clickData):
    if clickData is not None:
        frame_id = int(clickData['points'][0]['text'])
        print(frame_id)
        im_path = db.get_frames(frame_ids=[frame_id]).iloc[0]['path']
        encoded_image = encode_image(im_path)
        return f"data:image/jpg;base64,{encoded_image}"
    return ''  # return an empty string if no image is found

app.layout = html.Div([
    dcc.Graph(id='dendrogram-graph', figure=dendro_fig),
    html.Img(id='image-display', src='', style={'max-width': '500px', 'max-height': '500px'})
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
