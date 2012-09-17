from tw2.d3 import TimeSeriesChart
from moksha.wsgi.widgets.api.live import LiveWidget


class UsersChart(TimeSeriesChart, LiveWidget):
    id = 'users-chart'
    topic = "tutorial.newrequest"
    onmessage = """
    tw2.store['${id}'].value++;
    """

    width = 800
    height = 150

    # Keep this many data points
    n = 200
    # Initialize to n zeros
    data = [0] * n


def get_time_series_widget(config):
    return UsersChart(
        backend=config.get('moksha.livesocket.backend', 'websocket')
    )
