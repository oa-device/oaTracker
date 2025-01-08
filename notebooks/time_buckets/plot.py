from bokeh.colors import RGB
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates



import pandas as pd
import numpy as np
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool
from bokeh.plotting import figure, show

dark_theme_colors = [
    (0.12, 0.47, 0.71),  # Dark Blue
    (0.17, 0.63, 0.17),  # Dark Green
    (0.84, 0.15, 0.16),  # Dark Red
    (0.58, 0.40, 0.74),  # Purple
    (0.55, 0.34, 0.29),  # Brown
    (0.89, 0.47, 0.76),  # Pink
    (0.50, 0.50, 0.50),  # Gray
    (0.74, 0.74, 0.13),  # Olive
    (0.09, 0.75, 0.81),  # Teal
    (0.80, 0.40, 0.00),  # Dark Orange
]


def plot(data, zones, name, bucket_size_minutes):
    # Convert to a Pandas DataFrame
    df = pd.DataFrame(data)
    # Set dark mode for the plot
    plt.style.use('dark_background')

    # Create the plot
    plt.figure(figsize=(14, 6))

    # Plot the categories of visits
    i = 0
    for zone in zones:
        plt.plot(df['time_bucket'], df[f'{zone}_{name}'], label=f'{zone} {name}', marker='o', linestyle='-', color=dark_theme_colors[i], markersize=8)
        i+=1

    # Customize the plot
    plt.title(f'{name} per {bucket_size_minutes} minutes', fontsize=14, color='white')
    plt.xlabel('Time', fontsize=12, color='white')
    plt.ylabel(name, fontsize=12, color='white')


    # Set the format for the x-axis to display full time bucket
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))

    # Make sure all time buckets are visible on the x-axis
    plt.xticks(df['time_bucket'], rotation=45, fontsize=10, color='white', ha='right')  # Display full time_bucket strings
    plt.yticks(fontsize=10, color='white')

    # Add gridlines for clarity
    plt.grid(True, linestyle='--', alpha=0.5)

    # Add legend
    plt.legend(loc='upper left', fontsize=10, shadow=True)

    # Adjust layout to ensure everything fits (including rotated x-ticks)
    plt.tight_layout()

    # Show the plot
    plt.show()


from bokeh.models import HoverTool, WheelZoomTool

def plot2(data, zones, name, bucket_size_minutes):

    df = pd.DataFrame(data)

    # Convert 'time_bucket' to datetime
    df["time_bucket"] = pd.to_datetime(df["time_bucket"])

    # Extract dates and prepare data for Bokeh
    dates = np.array(df["time_bucket"], dtype=np.datetime64)

    # Main plot
    hover = HoverTool(tooltips=[
        ("value", "@data")
    ])
    
    p = figure(title=f'{name} per {bucket_size_minutes} minutes',height=700, width=1200, tools=[hover, "xpan", "wheel_zoom"], toolbar_location=None,
            x_axis_type="datetime",
            background_fill_color="#efefef", 
            x_range=(dates[0], dates[-1]), x_axis_location="below")

    sources: list[ColumnDataSource] = []
    # Plot the categories of visits
    i = 0
    for zone in zones:
        source = ColumnDataSource(data=dict(date=dates, data=df[f'{zone}_{name}']))
        (r,g,b) = dark_theme_colors[i]
        color=RGB(r*255,g*255,b*255)
        p.line('date', 'data', source=source, color=color, legend_label=f'{zone} {name}')
        p.scatter('date', 'data', source=source, fill_color="white", size=8, color=color)
        sources.append(source)
        i+=1

    p.yaxis.axis_label = name

    # Range selector
    select = figure(title="Drag the middle and edges of the selection box to change the range above",
                    height=130, width=1200, y_range=p.y_range,
                    x_axis_type="datetime", y_axis_type=None,
                    tools="", toolbar_location=None, background_fill_color="#efefef")

    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_color = "navy"
    range_tool.overlay.fill_alpha = 0.2

    select.ygrid.grid_line_color = None
    select.add_tools(range_tool)
    select.add_tools("wheel_zoom")

    from bokeh.models import DatetimeTickFormatter

    # Customize the x-axis formatter to display full datetime strings
    p.xaxis.formatter = DatetimeTickFormatter(
        seconds="%Y-%m-%d %H:%M:%S",
        minsec="%Y-%m-%d %H:%M:%S",
        minutes="%Y-%m-%d %H:%M:%S",
        hours="%Y-%m-%d %H:%M:%S",
        days="%Y-%m-%d %H:%M:%S",
        months="%Y-%m-%d %H:%M:%S",
        years="%Y-%m-%d %H:%M:%S"
    )

    # Adjust the range selector similarly
    select.xaxis.formatter = DatetimeTickFormatter(
        seconds="%Y-%m-%d %H:%M:%S",
        minsec="%Y-%m-%d %H:%M:%S",
        minutes="%Y-%m-%d %H:%M:%S",
        hours="%Y-%m-%d %H:%M:%S",
        days="%Y-%m-%d %H:%M:%S",
        months="%Y-%m-%d %H:%M:%S",
        years="%Y-%m-%d %H:%M:%S"
    )

    # Rotate labels to prevent overlap
    p.xaxis.major_label_orientation = 0.785  # Rotate ~45 degrees
    select.xaxis.major_label_orientation = 0.785  # Rotate labels to avoid overlap

    # Adjust the number of ticks to maximize visibility
    p.xgrid.grid_line_color = None  # Optional: Remove grid lines for a cleaner view

    # Let Bokeh automatically manage the tick intervals
    p.xaxis.ticker.desired_num_ticks = len(dates)
    select.xaxis.ticker.desired_num_ticks = len(dates)

    # Display the plots
    show(column(p,select))