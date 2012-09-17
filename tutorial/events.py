from pyramid.events import subscriber
from pyramid.events import NewRequest
from pyramid.events import BeforeRender

from pyramid.threadlocal import get_current_request

from moksha.hub.hub import MokshaHub
from moksha.wsgi.widgets.api import get_moksha_socket

from tutorial.widgets import get_time_series_widget

hub = None

def hub_factory(config):
    global hub
    if not hub:
        hub = MokshaHub(config)
    return hub

@subscriber(NewRequest)
def emit_message(event):
    """ For every request made of our app, emit a message to the moksha-hub.
    """
    hub = hub_factory(event.request.registry.settings)
    hub.send_message("tutorial.newrequest", message={})


@subscriber(BeforeRender)
def inject_globals(event):
    """ Before templates are rendered, make moksha front-end resources
    available in the template context.
    """
    request = get_current_request()

    # Expose these as global attrs for our templates
    event['moksha_socket'] = get_moksha_socket(request.registry.settings)
    event['users_widget'] = get_time_series_widget(request.registry.settings)
