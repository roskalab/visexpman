# -*- coding: utf-8 -*-
import numpy
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

def generate_table(dataframe):
    return html.Table(
    # Header
    [html.Tr([html.Th(col) for col in range(dataframe.shape[1])])] +
    # Body
    [html.Tr([
    html.Td(round(dataframe[i][col],3)) for col in range(dataframe.shape[1])
    ]) for i in range(dataframe.shape[0])]
)

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.c

app = dash.Dash(__name__)#, external_stylesheets=external_stylesheets)
app.pagen='pp'
app.layout = html.Div(children=[
#        html.Title(children='Title'),
#        generate_table(dataframe),
        dcc.Location(id='url', refresh=False),
        dcc.Link('Navigate to "/"', href='/'),
        html.Br(),
        dcc.Link('Navigate to "/page-2"', href='/page-2'),
        html.Div(id='page-content'),
        html.H1(children='Jobs'),
        html.Div(id='live-update-text'),
        html.Div(children='''
                TBD.
        '''),
        dcc.Interval(
                id='interval-component',
                interval=20*1000, # in milliseconds
                n_intervals=0
        )
    ])

@app.callback(Output('live-update-text', 'children'),
                        [Input('interval-component', 'n_intervals')])
def update(n):
    if app.pagen=='/':
        nrows=5
        app.title='TITLE'
    else:
        nrows=10
        app.title='TITLE2'
    return generate_table(numpy.random.random((nrows,3)))
    
@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    app.pagen=pathname
    return html.Div([
        html.H3('You are on page {}'.format(pathname)),
    ])

if __name__ == '__main__':
    app.run_server(debug=True, port=2000)
