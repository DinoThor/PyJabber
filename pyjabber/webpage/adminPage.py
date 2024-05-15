from aiohttp import web
from pyjabber.db.database import connection
import json
import aiohttp_cors

async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)

async def handleUser(request):
    data = {
        "users": [
            {"id": 1, "jid": "demo", "hash": 132131},
            {"id": 2, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131},
            {"id": 1, "jid": "demo", "hash": 132131},
            {"id": 2, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131},
            {"id": 3, "jid": "demo", "hash": 132131}
        ]
    }
    data = json.dumps(data)
    return web.Response(text=data)
app = web.Application()
app.add_routes([web.get('/', handle)])

cors = aiohttp_cors.setup(app)
resource = cors.add(app.router.add_resource("/api/users"))


async def serverInstance():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='localhost', port=9090)
    await site.start()