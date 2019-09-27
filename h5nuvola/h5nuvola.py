"""
h5nuvola New WEB GUI
"""

import os
import urllib
import json

from flask import Flask, request, redirect, url_for, render_template

import h5py as h5

import numpy as np

import bokeh

from bokeh.plotting import figure
from bokeh.driving import count
from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn, Dropdown, NumberFormatter
from bokeh.embed import components, json_item
from bokeh.colors import RGB
from bokeh.sampledata.iris import flowers


###############################################
#
# Global variables 
#

fnfilter = lambda fn: True
dfilter = lambda d: True
extension_filter = ['.h5', '.hdf5'] # select desired file extensions to show

hf_dict = {} # dictionary object to store h5 file object, items, attributes and properties
hf_objects = []


###############################################
#
# Python auxiliar methods 
#

# python routine for remote browsing on file system
def get_files(d, fnfilter, dfilter, rel=True):
    d = os.path.expanduser(d)
    dirs = []
    fns = []
    for fn in sorted(os.listdir(d)):
        ffn = os.path.join(d, fn)
        if not rel:
            fn = ffn
        if os.path.isdir(ffn):
            if dfilter(ffn):
                dirs.append(fn)
        else:
            if fnfilter(ffn):
                if os.path.splitext(fn)[1] not in extension_filter:
                    pass
                else:
                    fns.append(fn)
    return fns, dirs

# read h5 file 
def read_h5(filename):
    hf = h5.File(filename, 'r')
    return hf

def hf_visit(name, obj):
    global hf_objects    
    hf_objects.append(obj)

def get_hf_items(items):
    l = []
    for item in items:
        attrs = []
        tp = ''
        children = None
        dtype = ''
        dshape = ''
        if item[1].attrs.keys() == []: # if there is no attributes
            pass
        else:            
            for key in item[1].attrs.keys():
                attrs.append([key, item[1].attrs[key]])
        if type(item[1]) == h5._hl.dataset.Dataset:
            if h5.check_dtype(vlen=item[1].dtype) == str:
                dtype = 'string'
            else:
                dtype = str(item[1].dtype)            
            dshape = str(list(item[1].shape))
            tp = 'dataset'
            children = False
        else:            
            tp = 'group'
            dtype = 'Group size'
            dshape = str(len(item[1].items()))
            if len(item[1].items()) == 0:
                children = False
            else:
                children = True
        l.append( [str(item[1].name), #0
                   tp, #1
                   attrs, #2
                   children, #3
                   dtype, #4
                   dshape] ) #5
    return l

def expand_tree(filepath, node):
    global hf_objects    
    with h5.File(filepath) as hf:
        hf_objects = []
        hf.visititems(hf_visit)        
        for obj in hf_objects:                        
            if str(obj.name) == node:                    
                if len(obj.items()) != 0:
                    hf_new_items = get_hf_items(obj.items())                    
                else:
                    hf_new_items = [[str(1)]]
        return hf_new_items

###############################################
#
# Bokeh plotting routines - raw, curve and image
#

# Define bokeh_tools for plotting interaction
def create_bokeh_tools():
    bokeh_tools = ["pan","wheel_zoom","box_zoom","reset","save","box_select"]
    hover = HoverTool(tooltips=[
                ("pixel_value", "@image{0.00}"),
                ("point_value", "$y{0.00}"),            
                ("(x,y)", "($x{0.},$y{0.})"),            
            ])
    bokeh_tools.append(hover)
    return bokeh_tools

def bokeh_table(filepath, node):
    with h5.File(filepath) as hf:
        data = hf[node][()]
    if type(data) == str:        
        table = dict(x=[data])
        columns = [
            TableColumn( field='x', title='0', width=400, sortable=False )
        ]
        width=400
        height=200
        table_source = ColumnDataSource(table)
        data_table = DataTable(source=table_source, columns=columns,                            
                            fit_columns=False, sizing_mode="scale_width",
                            width=width, height=height,
                            selectable=True, sortable=False)

        return [data_table]                

    else:
        if data.ndim == 0:                         
            table = dict( x=[data] )
            columns = [
                TableColumn( field='x', title='0', width=100,
                            sortable=False, formatter=NumberFormatter(format="0,0.0000000000") )
            ]
            width=200
            height=200
            table_source = ColumnDataSource(table)
            data_table = DataTable(source=table_source, columns=columns,                            
                                fit_columns=False, sizing_mode="scale_width",
                                width=width, height=height,
                                selectable=True, sortable=False)

            return [data_table]
       
        elif data.ndim == 1:            
            table = dict( x=data.tolist() )
            columns = [
                TableColumn( field='x', title='0', width=100,
                            sortable=False, formatter=NumberFormatter(format="0,0.0000000000") )
            ]
            width=200
            height=800
            table_source = ColumnDataSource(table)
            data_table = DataTable(source=table_source, columns=columns,                            
                                fit_columns=False, sizing_mode="scale_width",
                                width=width, height=height,
                                selectable=True, sortable=False)
            
            return [data_table]
        
        elif data.ndim == 2:            
            table = {}
            i = 0
            columns = []
            for column in data.transpose():
                table.update({str(i):column})
                columns.append( TableColumn( field=str(i), title=str(i), width=100,
                                            sortable=False, formatter=NumberFormatter(format="0,0.0000000000") ) )
                i = i + 1
            width=800
            height=800
            table_source = ColumnDataSource(table)            
            data_table = DataTable(source=table_source, columns=columns,                            
                                fit_columns=False, sizing_mode="scale_width",                                   
                                selectable=True, sortable=False, editable=False)
            
            return [data_table]

        elif data.ndim == 3:
            pass
            

def bokeh_plot(filepath, node):
    with h5.File(filepath) as hf:
        data = hf[node][()]
    if data.ndim == 0:        
        bokeh_tools = create_bokeh_tools()
        y=[data]
        x=[0]
        source = ColumnDataSource(data=dict(x=x, y=y))
        plot = figure(title=node.split('/')[-1], toolbar_location="above",
                    sizing_mode="scale_width", tools=bokeh_tools)
        plot.line('x', 'y', source=source, legend=node.split('/')[-1],
                line_width=3, line_alpha=0.6, line_color=RGB(0,158,234))
        plot.circle('x', 'y', source=source, fill_color="white", size=10)
        
        return [plot]        

    elif data.ndim == 1:        
        bokeh_tools = create_bokeh_tools()
        y = data
        x = np.arange(data.shape[0])

        source = ColumnDataSource(data=dict(x=x, y=y))
        
        plot = figure(title=node.split('/')[-1], toolbar_location="above",
                    sizing_mode="scale_width", tools=bokeh_tools)
        plot.line('x', 'y', source=source, legend=node.split('/')[-1],
                line_width=3, line_alpha=0.6, line_color=RGB(0,158,234))
        plot.circle('x', 'y', source=source, fill_color="white", size=10)

        return [plot]

    elif data.ndim == 2:                
        plots = []
        i = 0
        for p in data:
            bokeh_tools = create_bokeh_tools()
            y = p
            x = np.arange(p.shape[0])

            source = ColumnDataSource(data=dict(x=x, y=y))

            p = figure(title=node.split('/')[-1], toolbar_location="above",
                    sizing_mode="scale_width", tools=bokeh_tools)
            p.line('x', 'y', source=source, legend=node.split('/')[-1],
                line_width=3, line_alpha=0.6, line_color=RGB(0,158,234))
            p.circle('x', 'y', source=source, fill_color="white", size=10)
            plots.append(p)            
            i += 1
        
        return plots

    elif data.ndim == 3:
        pass
        # Try plotly 3D scatter, 3D isosurface, 

def bokeh_image(filepath, node):
    with h5.File(filepath) as hf:
        data = hf[node][()]
    if data.ndim == 2:
        bokeh_tools = create_bokeh_tools()
        plot = figure(title=node.split('/')[-1], toolbar_location="above",
                        sizing_mode="scale_width", tools=bokeh_tools,
                        x_range=(0,data.shape[0]), y_range=(0,data.shape[1]))
        plot.image(image=[data], x=0, y=0, dw=data.shape[0], dh=data.shape[1])

        return [plot]
    
    elif data.ndim == 3:
        pass
        # Try plotly 3d surface, 3d volume  
    


###############################################
#
# Flask app config 
#

app = Flask(__name__)
app.secret_key = 'some super secret key here'



###############################################
#
# h5nuvola GUI - remote browser, H5 visualisation 
#

@app.route('/test')
def test():
    return "TEST"

# home page
@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template('h5nuvola-demo-gui.html')

# returns html content from jquery FileTree to be rendered in browser
@app.route('/remotebrowse', methods=['POST'])
def remotebrowse():
    r = []
    try:
        d = urllib.parse.unquote(request.form.get('dir', './'))
        fns, dirs = get_files(d, fnfilter, dfilter, rel=True)
        r = ['<ul class="jqueryFileTree" style="display: none;">']
        for f in dirs:
            ff = os.path.join(d, f)
            r.append('<li class="directory collapsed">' \
                    '<a href="#" rel="%s/">%s</a></li>' % (ff, f))
        for f in fns:
            ff = os.path.join(d, f)
            e = os.path.splitext(f)[1][1:]  # get .ext and remove dot            
            r.append('<li class="file ext_%s">' \
            '<a href="#" rel="%s">%s</a></li>' % (e, ff, f))
        r.append('</ul>')
    except Exception as E:
        r.append('Could not load directory: %s' % (str(E)))
    return ''.join(r)

# load h5 file, collect its items, properties and attributes
@app.route('/loadH5File', methods=['GET', 'POST'])
def loadH5File():
    global hf_dict, hf_objects
    filepath = str(request.form['filepath'])    
    if request.method == 'POST':
        try:
            hf = read_h5( filepath )            
        except IOError:
            print("IOError")
        
        if filepath not in hf_dict.keys():
            hf_dict[filepath] = {}    
            hf_name = str(hf.filename).split('/')[-1]
            hf_dict[filepath]['hf_name'] = hf_name
            hf_objects = []
            hf.visititems(hf_visit) # update hf_objects
            hf_dict[filepath]['hf_objects'] = hf_objects
            root_attrs=[]
            if hf.attrs.keys() == []: # if there is no attributes
                pass
            else:            
                for key in hf.attrs.keys():
                    root_attrs.append([key, hf.attrs[key]])
            hf_dict[filepath]['root_attrs'] = root_attrs      
            root_properties = [ hf_name, 'group', root_attrs, True, 'Group size', str(len(hf.items())) ]
            hf_dict[filepath]['root_properties'] = root_properties
            hf_root_items = get_hf_items(hf.items())
            hf_dict[filepath]['hf_root_items'] = hf_root_items
            hf_new_items = [[str(0)]]
            hf_dict[filepath]['hf_new_items'] = hf_new_items
            hf.close()    
            return json.dumps({'filepath':filepath,
                            'hf_name':hf_name,
                            'hf_root_items':hf_root_items,
                            'hf_new_items':hf_new_items,
                            'root_properties':root_properties
                            })
        else:
            return json.dumps({})

@app.route('/h5treeUpdate', methods=["POST"])
def jstreeUpdate():
    current_filepath = str(request.form['filepath'])
    node_selected = str(request.form['node'])       

    hf_new_items = expand_tree(current_filepath, node_selected)
    hf_dict[current_filepath]['hf_new_items'] = hf_new_items   

    return json.dumps({'filepath': current_filepath,
                       'hf_new_items':hf_new_items
                       })

@app.route('/raw', methods=["POST"])
def raw():
    if request.method == "POST":            
        current_filepath = str(request.form['filepath'])
        node_selected = str(request.form['node'])       

        tables = bokeh_table(current_filepath, node_selected)
        json_item_tables = [json_item(table) for table in tables]
        
        return json.dumps(json_item_tables)

@app.route('/curve', methods=["POST"])
def curve():
    if request.method == "POST":
        current_filepath = str(request.form['filepath'])
        node_selected = str(request.form['node'])

        plots = bokeh_plot(current_filepath, node_selected)
        json_item_plots = [json_item(plot) for plot in plots]

        return json.dumps(json_item_plots)

@app.route('/image', methods=["POST"])
def image():
    if request.method == "POST":
        current_filepath = str(request.form['filepath'])
        node_selected = str(request.form['node'])

        images = bokeh_image(current_filepath, node_selected)
        json_item_images = [json_item(image) for image in images]

        return json.dumps(json_item_images)

        
app.run(port=5000)