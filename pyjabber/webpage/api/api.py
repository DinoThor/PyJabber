import hashlib
import json

from aiohttp import web
from loguru import logger
from sqlalchemy import select, delete, insert

from pyjabber.db.database import DB
from pyjabber.db.model import Model


async def handleUser(_):
    with DB.connection() as con:
        query = select(Model.Credentials.c.id, Model.Credentials.c.jid)
        res = con.execute(query).fetchall()

    users = [{"id": i, "jid": v} for i, v in res]
    return web.Response(text=json.dumps(users))


async def handleRoster(request):
    try:
        user_id = int(request.match_info['id'])

        with DB.connection() as con:
            user_jid = con.execute(
                select(Model.Credentials.c.jid).where(Model.Credentials.c.id == user_id)
            ).fetchone()[0]

            if not user_jid:
                return web.json_response({"status": "error", "message": "User not found"}, status=404)

            roster = con.execute(
                select(Model.Roster.c.roster_item).where(Model.Roster.c.jid.like(f"{user_jid}%"))
            ).fetchall()

            response = [{"item": r[0]} for r in roster]

        return web.Response(text=json.dumps(response))

    except ValueError:
        return web.json_response({"status": "error", "message": "Invalid user ID"}, status=400)
    except Exception as e:
        logger.error(e)
        error_response = {
            "status": "error",
            "message": str(e)
        }
        return web.json_response(error_response, status=500)


async def handleDelete(request):
    try:
        user_id = int(request.match_info['id'])

        with DB.connection() as con:
            res = con.execute(
                select(Model.Credentials.c.id)
            ).fetchall()

            if user_id not in [r[0] for r in res]:
                return web.json_response({"status": "error", "message": "User not found"}, status=404)

            user_jid = con.execute(
                select(Model.Credentials.c.jid).where(Model.Credentials.c.id == user_id)
            ).fetchone()[0]

            con.execute(
                delete(Model.Credentials).where(Model.Credentials.c.id == user_id)
            )
            con.execute(
                delete(Model.Roster).where(Model.Roster.c.jid.like(f"{user_jid}%"))
            )
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

        with DB.connection() as con:
            res = con.execute(
                select(Model.Credentials.c.jid)
            ).fetchall()

        if any(r[0] == data["jid"] for r in res):
            raise Exception("JID already in use")

        hash_pwd = hashlib.sha256(data["pwd"].encode()).hexdigest()

        with DB.connection() as con:
            con.execute(
                insert(Model.Credentials).values({
                    'jid': data['jid'],
                    'hash_pwd': hash_pwd
                })
            )
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
