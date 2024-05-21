import hashlib
import json
import os

from aiohttp import web
from contextlib import closing
from loguru import logger
from pyjabber.db.database import connection


async def handleUser(request):
    with closing(connection()) as con:
        res = con.execute("SELECT id, jid FROM credentials")
        res = res.fetchall()

    users = [{"id": i, "jid": v} for i, v in res]
    return web.Response(text=json.dumps(users))

async def handleDelete(request):
    try:
        user_id = int(request.match_info['id'])

        with closing(connection()) as con:
            res = con.execute("SELECT id FROM credentials")
            res = res.fetchall()

            if user_id not in [r[0] for r in res]:
                return web.json_response({"status": "error", "message": "User not found"}, status=404)
            
            con.execute("DELETE FROM credentials WHERE id = ?", (user_id, ))
            con.commit()

        logger.info(f"User with ID {user_id} deleted")
        return web.json_response({"status": "success", "message": "User deleted"}, status=200)

    except ValueError:
        return web.json_response({"status": "error", "message": "Invalid user ID"}, status=400)
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e)
        }
        return web.json_response(error_response, status=500)

async def handleRegister(request):
    try:
        data = await request.json()

        with closing(connection()) as con:
            res = con.execute("SELECT jid FROM credentials")
            res = res.fetchall()

        if any(r[0] == data["jid"] for r in res):
            raise Exception("JID already in use")

        hash_pwd = hashlib.sha256(data["pwd"].encode()).hexdigest()

        with closing(connection()) as con:
            con.execute("INSERT INTO credentials (jid, hash_pwd) VALUES (?, ?)",
                        (data["jid"], hash_pwd))
            con.commit()

        response_data = {
            "status": "success",
            "message": "OK",
            "received_data": data
        }

        logger.info(f"User with jid {data['jid']} created")
        return web.json_response(response_data, status=200)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e)
        }
        return web.json_response(error_response, status=500)

async def handle(request):
    return web.FileResponse(os.getcwd() + '/pyjabber/webpage/build/index.html')