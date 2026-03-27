import os
from aiohttp import web

from pyjabber.webpage.api import api

FILE_PATH = os.path.dirname(os.path.abspath(__file__))

def api_adminpage_app():
    app = web.Application()
    app.router.add_get('/users', api.handleUser)
    app.router.add_get('/roster/{id}', api.handleRoster)
    app.router.add_post('/createuser', api.handleRegister)
    app.router.add_delete('/users/{id}', api.handleDelete)

    return '/api', app

async def get_index(_):
    return web.FileResponse(os.path.join(FILE_PATH, 'build', 'index.html'))

def get_static():
    return os.path.join(FILE_PATH, 'build', 'static')
