=============================================
Moksha Tutorial:  Live Graph of User Activity
=============================================

.. note:: You can find the source for this tutorial `on github
   <http://github.com/mokshaproject/moksha-pyramid-activity-graph>`_.

Today I'll be showing you how to add a websocket-powered
`d3 <http://d3js.org/>`_ graph of user activity to a
`pyramid <http://www.pylonsproject.org/>`_ app using `moksha
<http://mokshaproject.net>`_.

Bootstrapping
-------------

.. note:: Bootstrapping here is *almost* exactly the same as in
   the `Hello World
   <http://moksha.readthedocs.org/en/latest/main/tutorials/Pyramid/>`_
   tutorial.  So if you've gone through that, this should be simple.

   The exception is the new addition of a ``tw2.d3`` dependency.

Set up a virtualenv and install Moksha and Pyramid (install
`virtualenvwrapper
<http://pypi.python.org/pypi/virtualenvwrapper>`_ if you haven't already).

.. code-block:: bash

    $ mkvirtualenv tutorial
    $ pip install pyramid
    $ pip install moksha.wsgi moksha.hub

    $ # tw2.d3 for our frontend component.
    $ pip install tw2.d3

    $ # Also, install weberror for kicks.
    $ pip install weberror

Use ``pcreate`` to setup a Pyramid scaffold, install dependencies,
and verify that its working.  I like the ``alchemy`` scaffold, so we'll use that
one.  Its kind of silly, though:  we won't be using a database or sqlalchemy at
all for this tutorial.

.. code-block:: bash

    $ pcreate -t alchemy tutorial
    $ cd tutorial/
    $ rm production.ini  # moksha-hub gets confused when this is present.
    $ python setup.py develop
    $ initialize_tutorial_db development.ini
    $ pserve --reload development.ini

Visit http://localhost:6543 to check it out.  Success.

Enable ToscaWidgets2 and Moksha Middlewares
-------------------------------------------

.. note:: Enabling the middleware here is also identical to the `Hello World
   <http://moksha.readthedocs.org/en/latest/main/tutorials/Pyramid/>`_
   tutorial.

Moksha is framework-agnostic, meaning that you can use it with `TurboGears2
<http://moksha.readthedocs.org/en/latest/main/tutorials/TurboGears2/>`_,
`Pyramid <http://moksha.readthedocs.org/en/latest/main/tutorials/Pyramid>`_, or
`Flask <http://moksha.readthedocs.org/en/latest/main/tutorials/Flask>`_.  It
integrates with apps written against those frameworks by way of a layer of WSGI
middleware you need to install.  Moksha is pretty highly-dependent on
`ToscaWidgets2 <http://toscawidgets.org>_` which has its own middleware layer.
You'll need to enable both, and in a particular order!

Go and edit ``development.ini``.  There should be a section at the top named
``[app:main]``.  Change that to ``[app:tutorial]``.  Then, just above the
``[server:main]`` section add the following three blocks::

    [pipeline:main]
    pipeline =
        egg:WebError#evalerror
        tw2
        moksha
        tutorial

    [filter:tw2]
    use = egg:tw2.core#middleware

    [filter:moksha]
    use = egg:moksha.wsgi#middleware

You now have three new pieces of WSGI middleware floating under your pyramid
app.  Neat!  Restart pserve and check http://localhost:6543 to make sure
its not crashing.

Provide some configuration for Moksha
-------------------------------------

.. warning:: This is where things begin to diverge from the `Hello World
   <http://moksha.readthedocs.org/en/latest/main/tutorials/Pyramid/>`_
   tutorial.

We're going to configure moksha to communicate with `zeromq
<http://www.zeromq.org>`_ and `WebSocket <http://websocket.org>`_.  As an aside,
one of Moksha's goals is to provide an abstraction over different messaging
transports.  It can speak zeromq, AMQP, and STOMP on the backend, and WebSocket
or COMET emulated-AMQP and/or STOMP on the frontend.

We need to configure a number of things:

 - Your app needs to know how to talk to the ``moksha-hub`` with zeromq.
 - Your clients need to know where to find their websocket server (its housed
   inside the ``moksha-hub``).

Edit ``development.ini`` and add the following lines in the ``[app:tutorial]``
section.  Do it just under the ``sqlalchemy.url`` line::

    ##moksha.domain = live.example.com
    moksha.domain = localhost

    moksha.notifications = True
    moksha.socket.notify = True

    moksha.livesocket = True
    moksha.livesocket.backend = websocket
    #moksha.livesocket.reconnect_interval = 5000
    moksha.livesocket.websocket.port = 9998

    zmq_enabled = True
    #zmq_strict = True
    zmq_publish_endpoints = tcp://*:3001
    zmq_subscribe_endpoints = tcp://127.0.0.1:3000,tcp://127.0.0.1:3001

Also, add a new ``hub-config.ini`` file with the following (nearly identical) content.
Notice that the only real different is the value of ``zmq_publish_endpoints``::

    [app:tutorial]
    ##moksha.domain = live.example.com
    moksha.domain = localhost

    moksha.livesocket = True
    moksha.livesocket.backend = websocket
    moksha.livesocket.websocket.port = 9998

    zmq_enabled = True
    #zmq_strict = True
    zmq_publish_endpoints = tcp://*:3000
    zmq_subscribe_endpoints = tcp://127.0.0.1:3000,tcp://127.0.0.1:3001

Emitting events when users make requests
----------------------------------------

This is the one tiny little nugget of "business logic" we're going to add.  When
a user anywhere makes a `Request` on our app, we want to emit a message that can
then be viewed in graphs by other users.  Pretty simple: we'll just emit a
message on a topic we hardcode that has an empty ``dict`` for its body.

Add a new file, ``tutorial/events.py`` with the following content:

.. code-block:: python

   from pyramid.events import NewRequest
   from pyramid.events import subscriber

   from moksha.hub.hub import MokshaHub

   hub = None

   def hub_factory(config):
       global hub
       if not hub:
           hub = MokshaHub(config)
       return hub

   @subscriber(NewRequest)
   def emit_message(event):
       """ For every request made of our app, emit a message to the moksha-hub.
       Given the config from the tutorial, this will go out on port 3001.
       """

       hub = hub_factory(event.request.registry.settings)
       hub.send_message(topic="tutorial.newrequest", message={})

Combining components to make a live widget
------------------------------------------

With those messages now being emitted to the ``"tutorial.newrequest"`` topic, we
can construct a frontend widget with ToscaWidgets2 that listens to that topic
(using a Moksha LiveWidget mixin).  When a message is received on the client the
javascript contained in ``onmessage`` will be executed (and passed a json object
of the message body).  We'll ignore that since its empty, and just increment a
counter provided by ``tw2.d3``.

Add a new file ``tutorial/widgets.py`` with the following content:

.. code-block:: python

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

Rendering Moksha Frontend Components
------------------------------------

With our widget defined, we'll need to expose it to our chameleon template and
render it.  Instead of doing this per-view like you might normally, we're going
to flex Pyramid's events system some more and inject it (and the requisite
``moksha_socket`` widget) on every page.

Go back to ``tutorial/events.py`` and add the following new handler:

.. code-block:: python

    from pyramid.events import BeforeRender
    from pyramid.threadlocal import get_current_request

    from moksha.wsgi.widgets.api import get_moksha_socket

    from tutorial.widgets import get_time_series_widget


    @subscriber(BeforeRender)
    def inject_globals(event):
        """ Before templates are rendered, make moksha front-end resources
        available in the template context.
        """
        request = get_current_request()

        # Expose these as global attrs for our templates
        event['users_widget'] = get_time_series_widget(request.registry.settings)
        event['moksha_socket'] = get_moksha_socket(request.registry.settings)

And lastly, go edit ``tutorial/templates/mytemplate.pt`` so that it displays
``users_widget`` and ``moksha_socket`` on the page::

    <div id="bottom">
      <div class="bottom">
        <div tal:content="structure users_widget.display()"></div>
        <div tal:content="structure moksha_socket.display()"></div>
      </div>
    </div>

Running the Hub alongside pserve
--------------------------------

When the ``moksha-hub`` process starts up, it will begin handling your
messages.  It also houses a small websocket server that the ``moksha_socket``
will try to connect back to.

Open up *two* terminals and activate your virtualenv in both with ``workon
tutorial``.  In one of them, run::

    $ moksha-hub -v hub-config.ini

And in the other run::

    $ pserve --reload development.ini

Now open up *two* browsers, (say.. one chrome, the other firefox) and visit
http://localhost:6543/ in both.  In one of them, reload the page over and over
again.. you should see the graph in the other one "spike" showing a count of all
the requests issued.
