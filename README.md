# Bakthat SyncSever

Draft of a synchronization server for [bakthat](http://docs.bakthat.io).

Requirements:

- [MongoDB](http://www.mongodb.org/)
- [Flask](http://flask.pocoo.org/)

Be careful, you should use ssl (even with a self signed cert) and run it whith something like [gunicorn](http://gunicorn.org/).

## Setting up

### Server side

You should run it with a proxy like gunicorn.

    $ pip install -r requirements.txt
    $ python server.py
     * Running on http://0.0.0.0:2405/
     * Restarting with reloader

### Client side

Assuming bakthat is already installed.

**Change LOGIN and PASSWORD** on top of server.py, you can also change the port a the end (**2405 by default**).

Edit ~/.bakthat.yml for each client.

    sync:
      auto: false
      url: http://yourserver:2405
      username: login
      password: password

Now you can run on each client.

    $ bakthat sync

That's it.