"""Focused browser packets only; no backend heartbeat may prolong human input."""
import asyncio
import json
import time
import uuid
from fastapi import WebSocketDisconnect
from websockets.asyncio.client import connect
from ..lab.native_lease import NativeLeases


class Controls:
    def __init__(self, lab):
        self.lab = lab
        self.connections = {}
        self.leases = NativeLeases()

    def require(self, session):
        connection = self.connections.get(session["session_id"])
        if connection is None or time.monotonic()-connection["last_packet"] > .7:
            raise PermissionError("Keep the control view focused before enabling or starting.")
        return connection

    async def open(self, socket, session):
        identifier = session["session_id"]
        if identifier in self.connections or any(item['robot_id'] == session['robot_id'] for item in self.connections.values()):
            await socket.close(code=4409, reason="Another browser owns this control connection")
            return
        await socket.accept()
        entry = {"last_packet": time.monotonic(), "native": None, "state": {}, "owner": None, "owned": False, 'robot_id': session['robot_id']}
        self.connections[identifier] = entry
        try:
            if session["robot_id"] != "so101":
                await self.mobile(socket, session, entry)
            else:
                await self.browser(socket, session, entry)
        except (WebSocketDisconnect, TimeoutError, OSError, ValueError):
            pass
        finally:
            self.connections.pop(identifier, None)
            await self.release(session, entry)

    async def mobile(self, socket, session, entry):
        robot = session["robot_id"]
        path = "/api/lab/control" if robot == "tank" else "/api/rosmaster/console/ws"
        async with connect("ws://127.0.0.1:8030"+path, origin="http://127.0.0.1:8030", max_size=4_000_000) as downstream:
            entry["native"] = downstream
            tasks = [asyncio.create_task(self.browser(socket, session, entry)),
                     asyncio.create_task(self.telemetry(socket, downstream, entry))]
            try:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def telemetry(self, socket, downstream, entry):
        async for raw in downstream:
            payload = json.loads(raw)
            entry["state"] = payload.get("status", payload)
            entry["owner"] = payload.get("owner")
            await socket.send_json({"kind": "native_status", "data": entry["state"], "owner": entry["owner"]})

    async def browser(self, socket, session, entry):
        while True:
            packet = await asyncio.wait_for(socket.receive_json(), timeout=1)
            if packet.get("kind") == "clear":
                await self.release(session, entry)
            elif packet.get("kind") in ("heartbeat", "key", "input", "native_action", "clear_inputs"):
                entry["last_packet"] = time.monotonic()
                self.leases.heartbeat(session["session_id"])
                await self.input(session, entry, packet)
            else:
                raise ValueError("Unsupported direct control packet")
            if session["robot_id"] == "so101":
                await socket.send_json({"kind": "browser_lease", "focused": True})

    async def input(self, session, entry, packet):
        downstream = entry["native"]
        if downstream is None:
            return
        if session["robot_id"] == "tank":
            if packet["kind"] in ("heartbeat", "key", "clear_inputs"):
                await downstream.send(json.dumps(packet))
        elif packet['kind'] == 'clear_inputs':
            await downstream.send(json.dumps({'drive':[0,0,0],'arm':[0,0,0],'pitch':0,'roll':0,'grip':0,'slow':True}))
        elif packet['kind'] == 'native_action':
            action = packet.get('action')
            if action not in ('arm_mode','leader','leader_off','mirror'):
                raise PermissionError('Unsupported direct native action')
            allowed = {key:packet[key] for key in ('action','mode','on') if key in packet}
            await downstream.send(json.dumps(allowed))
        elif packet["kind"] == "input":
            allowed = {key: packet[key] for key in ("drive", "arm", "pitch", "roll", "grip", "slow") if key in packet}
            await downstream.send(json.dumps(allowed))

    async def command(self, session, packet):
        entry = self.require(session)
        if entry["native"] is None:
            raise ValueError("Native mobile connection is unavailable")
        nonce = uuid.uuid4().hex
        self.lab.journal.profile('ros-operation:'+session['session_id'], {'nonce':nonce,'action':packet['action']})
        await entry["native"].send(json.dumps({**packet,'homebrain_request':nonce}))
        entry["owned"] = True
        started = time.monotonic()
        while time.monotonic()-started < 8:
            result = await self.lab.native.request('explorer','/api/lab/rosmaster/operations/'+nonce)
            if result['status'] == 'rejected':
                raise ValueError('Native ROSMASTER rejected '+packet['action']+': '+str(result['error']))
            if result['status'] == 'accepted':
                return result
            await asyncio.sleep(.15)
        raise OSError('Native ROSMASTER acknowledgement is unknown; reconcile operation '+nonce+' before retrying')

    async def release(self, session, entry):
        self.leases.revoke(session['session_id'])
        if not entry['owned']:
            return
        try:
            if session['robot_id'] == 'so101':
                await self.lab.stop_owned(session)
            elif entry['native']:
                if session['robot_id'] == 'tank':
                    await entry['native'].send(json.dumps({'kind':'clear'}))
                else:
                    await entry['native'].close()
        except Exception as error:
            self.lab.journal.event(session['session_id'], 'stop_unconfirmed', 0, {'message':str(error)})
        entry['owned'] = False

    async def record_permit(self, session, status, dataset):
        if status['recording'].get('active'):
            raise PermissionError('An existing native recording must be reconciled first')
        if status['teleoperation'].get('active'):
            native = await self.lab.native.request('studio', '/api/lab/lease')
            operation = (native.get('active') or {}).get('operation_id')
            if self.leases.entries.get(operation, {}).get('session_id') != session['session_id']:
                raise PermissionError('The active native controller belongs to another session')
        return self.permit(session, status['hardware_stop_generation'], dataset)

    def permit(self, session, generation, dataset=None):
        self.require(session)
        return self.leases.issue(session['session_id'], generation, dataset)

    async def observed(self, session):
        if session["robot_id"] == "tank":
            return await self.lab.native.request("explorer", "/api/lab/status")
        return await self.lab.native.request('explorer', '/api/lab/rosmaster/status')
