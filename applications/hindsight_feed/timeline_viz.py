import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objects as go

from plot_history import search_history
from feed_generator import FeedGenerator
from feeders.browser_history_summary import TopicBrowserSummaryFeeder

feed_generator = FeedGenerator(content_generators=list())

dash_app = dash.Dash(__name__)

node_ids = list()

urls_values = []
titles_values = []

selected_urls = []
selected_titles = []

selected_indices = []

def create_line_plot_figure(data_points, selected_indices=None):
    global urls_values
    global titles_values

    selected_indices = selected_indices if selected_indices is not None else list()

    x_values = [point[0].start_time.to_pydatetime() for point in data_points]
    y_values = [point[1] for point in data_points]
    urls_values = [point[2] for point in data_points]
    titles_values = [point[3] for point in data_points]

    # Update marker colors based on selection
    marker_colors = ['#FF0000' if i in selected_indices else '#007BFF' for i in range(len(data_points))]

    fig = go.Figure(data=go.Scatter(x=x_values, y=y_values, mode='lines+markers', 
                                    marker=dict(color=marker_colors, size=10)))
    fig.update_layout(
        title='Browser History',
        xaxis_title='Time',
        yaxis_title='Num URLs',
        xaxis=dict(type='date', tickformat='%d %b %Y %H:%M'),
        margin=dict(b=20, l=40, t=60, r=20),
        hovermode='closest',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig

initial_points = search_history(text=None)
initial_figure = create_line_plot_figure(initial_points)

dash_app.layout = html.Div([
    html.Div([
        html.Label('Search Text: ', htmlFor='input-search', style={'margin-right': '10px'}),
        dcc.Input(id='input-search', type='text', placeholder='Enter search term', style={
            'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'margin-right': '10px'
        }),
        html.Label('Embedding Distance Threshold: ', htmlFor='input-distance-threshold', style={'margin-right': '10px'}),
        dcc.Input(id='input-distance-threshold', type='number', placeholder='Enter threshold', value=1.2, style={
            'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'margin-right': '10px'
        }),
        html.Button('Search', id='button-search', style={
            'padding': '10px 20px', 'font-size': '16px', 'color': 'white', 'background-color': '#007BFF', 'border': 'none',
            'border-radius': '5px', 'cursor': 'pointer', 'margin-right': '20px'
        }),
        html.Button('Summarize URLs', id='button-summarize', style={
            'padding': '10px 20px', 'font-size': '16px', 'color': 'white', 'background-color': '#007BFF', 'border': 'none',
            'border-radius': '5px', 'cursor': 'pointer'
        }),
    ], style={'margin-bottom': '20px', 'display': 'flex', 'align-items': 'center'}),

    html.Div([
        html.Label('Time Bins:', htmlFor='input-time-bins', style={'margin-right': '10px'}),
        dcc.Dropdown(
            id='input-time-bins',
            options=[
                {'label': 'Year', 'value': 'Y'},
                {'label': 'Month', 'value': 'M'},
                {'label': 'Week', 'value': 'W'},
                {'label': 'Day', 'value': 'D'},
                {'label': 'Hour', 'value': 'H'}
            ],
            value='M',  # Default selection
            clearable=False,  # Prevents user from clearing the selection
            placeholder='Select a time bin',
            style={
                'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'width': '200px'
            }
        ),
    ], style={'margin-bottom': '20px', 'display': 'flex', 'align-items': 'center'}),

    html.Div([
        dcc.Graph(id='output-graph', figure=initial_figure, config={'staticPlot': False}),
    ], style={'margin-bottom': '20px', 'background-color': '#ffffff', 'border-radius': '8px', 'padding': '20px', 'box-shadow': '0 6px 12px rgba(0, 0, 0, 0.1)'}),

    dcc.Markdown(
        id='output-urls',
        children='',  # Placeholder text or initial content
        style={
            'white-space': 'pre-wrap',
            'border': '1px solid #ccc',
            'border-radius': '5px',
            'padding': '10px',
            'margin-bottom': '20px',
            'background-color': '#f0f2f5'
        }
    ),
    html.Div(
        html.Button('Open URLs', id='button-open', style={
            'padding': '10px 20px', 'font-size': '16px', 'color': 'white', 'background-color': '#007BFF', 'border': 'none',
            'border-radius': '5px', 'cursor': 'pointer'
        })
    )
], style={'margin': '40px', 'font-family': 'Arial, sans-serif'})


dash_app.layout.children.append(html.Div(id='dummy-div', style={'display': 'none'}))

@dash_app.callback(
    Output('dummy-div', 'children'),  # Dummy output, not used in UI
    [Input('button-open', 'n_clicks')],
    [],
    prevent_initial_call=True
)
def open_urls(n_clicks):
    global selected_urls
    if n_clicks:
        print(selected_urls)
        # utils.open_urls(selected_urls)
    else:
        raise dash.exceptions.PreventUpdate

@dash_app.callback(
    Output('output-urls', 'children'),
    [Input('output-graph', 'clickData')],
    prevent_initial_call=True
)
def display_url(clickData):
    global selected_urls
    global selected_titles
    if clickData:
        node_index = clickData['points'][0]['pointIndex']
        selected_urls = urls_values[node_index]  # Assume urls_values is defined globally or fetched dynamically
        selected_titles = titles_values[node_index]
        
        # Format URLs and titles as Markdown links
        markdown_links = "\n".join(
            [f"[{title}]({url})" for title, url in zip(selected_titles, selected_urls)]
        )
        
        return markdown_links
    else:
        raise dash.exceptions.PreventUpdate
    
    
@dash_app.callback(
    Output('output-graph', 'figure'),
    [Input('output-graph', 'clickData'),
    Input('button-search', 'n_clicks'),
    Input('button-summarize', 'n_clicks'),
    Input('input-time-bins', 'value')],
    [State('input-search', 'value'),
     State('input-distance-threshold', 'value'),
     State('output-graph', 'figure')],
    prevent_initial_call=True
)
def update_graph(clickData, n_clicks_search, n_clicks_summarize, time_bin, search_text, distance_threshold, existing_figure):
    global node_ids, selected_indices
    global initial_graph_height
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'output-graph':
        if clickData:
            point_index = clickData['points'][0]['pointIndex']
            if point_index in selected_indices:
                selected_indices.remove(point_index)  # Toggle off if already selected
            else:
                selected_indices.append(point_index)  # Toggle on if not already selected
            
            # Replot with updated selections
            data_points = search_history(text=search_text, distance_threshold=distance_threshold, 
                                         time_bin=time_bin)  # Retrieve the full dataset or filter again if needed
            return create_line_plot_figure(data_points, selected_indices)
        return dash.no_update
    
    if trigger_id == 'button-summarize':
        query = f"History Search {search_text}"
        selected_urls = set()
        for selected_index in selected_indices:
            selected_urls.update(urls_values[selected_index])
        feed_generator.add_content_generator(TopicBrowserSummaryFeeder(name=f"""TopicBrowserSummaryFeeder_{query.replace(" ", "_")}""", 
                                                    description=f"Generates an html page with a summary for all browser history related to {query}",
                                                    topic=query, topic_urls=selected_urls))

    if trigger_id == 'button-search' or trigger_id == 'input-time-bins':
        selected_indices = []
        data_points = search_history(text=search_text, distance_threshold=distance_threshold, time_bin=time_bin)
        return create_line_plot_figure(data_points=data_points)
    else:
        return dash.no_update

if __name__ == '__main__':
    dash_app.run_server(debug=False, port=8050)
