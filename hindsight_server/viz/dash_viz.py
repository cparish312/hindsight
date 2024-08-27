import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objects as go
import networkx as nx
import json

# from google_news_graph import navigate_down_google_news_graph, search_google_news_graph, initialize_google_news_graph
from screenshots_graph import navigate_down_google_news_graph, search_google_news_graph, initialize_google_news_graph

app = dash.Dash(__name__)

node_ids = list()

def create_graph_figure(networkx_graph):
    global node_ids
    pos = nx.spring_layout(networkx_graph)  # Position nodes using Spring layout

    edge_x = []
    edge_y = []
    for edge in networkx_graph.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])  # 'None' to prevent continuous lines
        edge_y.extend([y0, y1, None])
        # Couldn't get to work
        edge_width = edge[2].get('weight', 1)  * 10 

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color="gray"),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_ids = list()
    for node, attr in networkx_graph.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(attr.get("text", str(node)))
        node_color.append(attr.get("color", "orange")) 
        node_ids.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            showscale=True,
            # Node color and size settings can be adjusted as needed
            colorscale='YlGnBu',
            size=10,
            color=node_color,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            ),
            line_width=2))

    node_trace.text = node_text  # Hover text

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, t=0, r=0),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    
    return fig

initial_graph_height = 5
initial_graph = initialize_google_news_graph(height=initial_graph_height)
initial_figure = create_graph_figure(initial_graph)

app.layout = html.Div([
    dcc.Input(id='input-search', type='text', placeholder='Enter search term'),
    html.Button('Search', id='button-search'),
    dcc.Graph(id='output-graph', figure=initial_figure,  config={'staticPlot': False}),
    html.Button('Back', id='button-back'),
])


# Tried to seperate node click and search callbacks but node click wouldn't work
@app.callback(
    Output('output-graph', 'figure'),
    [Input('output-graph', 'clickData'),
     Input('button-search', 'n_clicks'),
     Input('button-back', 'n_clicks')],
    [State('input-search', 'value')],
    prevent_initial_call=True
)
def update_graph(clickData, n_clicks_search, n_clicks_back, value):
    global node_ids
    global initial_graph_height
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'output-graph' and clickData:
        node_index = clickData['points'][0]['pointIndex']
        node_id = node_ids[node_index]
        G = navigate_down_google_news_graph(node_id=node_id)
        return create_graph_figure(G)
    elif trigger_id == 'button-search' and value:
        G = search_google_news_graph(search_text=value)
        return create_graph_figure(G)
    elif trigger_id == 'button-back':
        print("Button back clicked")
        G = initialize_google_news_graph(height=initial_graph_height)
        return create_graph_figure(G)
    else:
        return dash.no_update

if __name__ == '__main__':
    app.run_server(debug=False)