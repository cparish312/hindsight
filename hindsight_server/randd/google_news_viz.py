import pandas as pd
import numpy as np
import networkx as nx

import plotly.graph_objects as go

from mlx_embedding_models.embedding import EmbeddingModel
from sklearn.metrics.pairwise import cosine_similarity

import sys
sys.path.insert(0, "../")
from config import MLX_EMBDEDDING_MODEL
from db import HindsightDB

db = HindsightDB()

google_news_df = pd.read_csv("google_news_articles.csv")
google_news_df = google_news_df.loc[google_news_df['title_text'].str.len() >= 10]
titles = list(google_news_df['title_text'])[:300]

annotations_df = db.get_annotations()
annotations = list(annotations_df['text'])
print("Num annotations:", len(annotations))

embedding_model = EmbeddingModel.from_registry(MLX_EMBDEDDING_MODEL)

title_embeddings = embedding_model.encode(titles).tolist()
annotation_embeddings = embedding_model.encode(annotations).tolist()

all_embeddings = title_embeddings.copy()
all_embeddings.extend(annotation_embeddings)

all_text = titles.copy()
all_text.extend(annotations)

similarity_matrix = cosine_similarity(all_embeddings)

G = nx.to_networkx_graph(similarity_matrix)

def create_node_trace(G):
    node_x = []
    node_y = []
    node_text = []
    node_color = []

    for node, attr in G.nodes(data=True):
        x, y = attr['pos']  # Correctly access the position from the attribute dictionary
        node_x.append(x)
        node_y.append(y)
        node_text.append(attr.get('text', ''))
        node_color.append(attr.get('color', 'blue'))  # Default to 'blue' if no color is set

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color=node_color,
            size=16,
            line_width=0.5,
        ),
        text=node_text,
        visible=False
    )
    return node_trace

def create_edge_trace(G):
    edge_pos = []
    edge_color = []
    
    for edge in G.edges(data=True):
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_pos.append([[x0, x1, None], [y0, y1, None]])
        # Assign color based on node type
        if G.nodes[edge[0]].get("color", "orange") == "blue" or G.nodes[edge[1]].get("color", "orange") == "blue":
            edge_color.append('blue')
        else:
            edge_color.append("orange")

    edge_traces = []
    for i, pos in enumerate(edge_pos):
        trace = go.Scatter(
            x=pos[0], y=pos[1],
            line=dict(width=2, color=edge_color[i]),
            mode='lines',
            visible=False
        )
        edge_traces.append(trace)

    return edge_traces

def filter_similarity_matrix_at_step(square_matrix, step_value):
    # copy matrix
    aux = square_matrix.copy()
    
    # set as NaN all values equal to or below threshold value
    aux[aux <= step_value] = np.nan
    
    # return filtered matrix
    return aux

def get_interactive_slider_similarity_graph(square_matrix, slider_values, node_text=None, yaxisrange=None, xaxisrange=None):
    
    # Create figure with plotly
    fig = go.Figure()

    # key: slider value
    # value: list of traces to display for that slider value
    slider_dict = {}
    
    # total number of traces
    total_n_traces = 0
    
    # node positions on plot
    #node_pos = None

    # for each possible value in the slider, create and store traces (i.e., plots)
    for i, step_value in enumerate(slider_values):

        # update similarity matrix for the current step
        aux = filter_similarity_matrix_at_step(square_matrix, step_value)

        # create nx graph from sim matrix
        G = nx.to_networkx_graph(aux)
        
        # remove edges for 0 weight (NaN)
        G.remove_edges_from([(a, b) for a, b, attrs in G.edges(data=True) if np.isnan(attrs["weight"])])

        # assign node positions if None
        node_pos = nx.nx_pydot.graphviz_layout(G)

        # populate nodes with meta information
        for node in G.nodes(data=True):
            
            # node position
            node[1]['pos'] = node_pos[node[0]]

            # node text on hover if any is specified else is empty
            if node_text is not None:
                node[1]['text'] = node_text[node[0]]
                node[1]['color'] = "blue"
                if node[1]['text'] in titles:
                    node[1]['color'] = "orange"
            else:
                node[1]['text'] = ""
            
        # create edge taces (each edge is a trace, thus this is a list)
        edge_traces = create_edge_trace(G)
        
        # create node trace (a single trace for all nodes, thus it is not a list)
        node_trace = create_node_trace(G) 

        # store edge+node traces as single list for the current step value
        slider_dict[step_value] = edge_traces + [node_trace]
        
        # keep count of the total number of traces
        total_n_traces += len(slider_dict[step_value])

        # make sure that the first slider value is active for visualization
        if i == 0:
            for trace in slider_dict[step_value]:
                # make visible
                trace.visible = True

                
    # Create steps objects (one step per step_value)
    steps = []
    for step_value in slider_values:
        
        # count traces before adding new traces
        n_traces_before_adding_new = len(fig.data)
        
        # add new traces
        fig.add_traces(slider_dict[step_value])

        step = dict(
            # update figure when this step is active
            method="update",
            # make all traces invisible
            args=[{"visible": [False] * total_n_traces}],
            # label on the slider
            label=str(round(step_value, 3)),
        )

        # only toggle this step's traces visible, others remain invisible
        n_traces_for_step_value = len(slider_dict[step_value])
        for i in range(n_traces_before_adding_new, n_traces_before_adding_new + n_traces_for_step_value):
            step["args"][0]["visible"][i] = True
        
        # store step object in list of many steps
        steps.append(step)

    # create slider with list of step objects
    slider = [dict(
        active=0,
        steps=steps
    )]

    # add slider to figure and create layout
    fig.update_layout(
        sliders=slider,
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(range=xaxisrange, showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=yaxisrange, showgrid=False, zeroline=False, showticklabels=False),
        width=700, height=700,
    )

    return fig

# define slider steps (i.e., threshold values)
slider_steps = np.arange(0.7, 0.9, 0.1)
    
# get the slider figure
fig = get_interactive_slider_similarity_graph(
    similarity_matrix,
    slider_steps,
    node_text = all_text
)

# plot it
fig.show()