"""gRPC adapter. Stubs are generated at build time:
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. simulation/grpc/sim.proto"""
from __future__ import annotations
import logging
import os
from concurrent import futures

import grpc                                    # grpcio (absolute import; this package is simulation.grpc)

from simulation.grpc import sim_pb2 as pb, sim_pb2_grpc as pbg
from simulation.grpc.service import SimService

log = logging.getLogger("sim")


def _snapshot_pb(aid, s):
    m = pb.Snapshot(aquarium_id=aid, tick=s["tick"], time=s["time"])
    for c in s["creatures"]:
        m.creatures.add(id=c["id"], species=c["sp"], x=c["x"], y=c["y"], vx=c["vx"], vy=c["vy"], heading=c["h"],
                        state=c["st"], energy=c["e"], hunger=c["hu"], health=c["hp"], size=c["sz"])
    for f in s["food"]:
        m.food.add(id=f["id"], kind=f["k"], x=f["x"], y=f["y"])
    for e in s.get("events", []):
        m.events.add(tick=e["tick"], kind=e["kind"], text=e["text"], creature_id=e["creature_id"])
    st = s["stats"]
    m.stats.CopyFrom(pb.SimStats(step_ms=st["step_ms"], decisions=st["decisions"],
                                 creatures=st["creatures"], food=st["food"]))
    return m


def _world_pb(aid, i):
    m = pb.WorldInfo(aquarium_id=aid, width=i["width"], height=i["height"], floor_y=i["floor_y"],
                     tick_rate=i["tick_rate"])
    for r in i["rocks"]:
        m.rocks.add(x=r["x"], y=r["y"], r=r["r"])
    for r in i["shelters"]:
        m.shelters.add(x=r["x"], y=r["y"], r=r["r"])
    for s in i["species"]:
        m.species.add(**s)
    return m


class Servicer(pbg.SimulationServicer):
    def __init__(self, svc=None):
        self.svc = svc or SimService()

    def _missing(self, ctx, aid):
        ctx.abort(grpc.StatusCode.NOT_FOUND, f"aquarium {aid!r} not found")

    def CreateWorld(self, req, ctx):
        return _world_pb(req.aquarium_id, self.svc.create_world(req.aquarium_id, req.seed, req.populate_default))

    def Step(self, req, ctx):
        s = self.svc.step(req.aquarium_id, req.ticks or 1)
        if s is None:
            self._missing(ctx, req.aquarium_id)
        return _snapshot_pb(req.aquarium_id, s)

    def GetSnapshot(self, req, ctx):
        s = self.svc.snapshot(req.aquarium_id)
        if s is None:
            self._missing(ctx, req.aquarium_id)
        return _snapshot_pb(req.aquarium_id, s)

    def AddFood(self, req, ctx):
        ok, msg, i = self.svc.add_food(req.aquarium_id, req.x, req.y, req.count, req.kind or "fish_food")
        return pb.CommandResult(ok=ok, message=msg, id=i)

    def AddCreature(self, req, ctx):
        ok, msg, i = self.svc.add_creature(req.aquarium_id, req.species, req.x or None, req.y or None)
        return pb.CommandResult(ok=ok, message=msg, id=i)

    def RemoveCreature(self, req, ctx):
        ok, msg, i = self.svc.remove_creature(req.aquarium_id, req.creature_id)
        return pb.CommandResult(ok=ok, message=msg, id=i)

    def DropWorld(self, req, ctx):
        return pb.CommandResult(ok=self.svc.drop_world(req.aquarium_id))

    def Inspect(self, req, ctx):
        d = self.svc.inspect(req.aquarium_id, req.creature_id)
        if d is None:
            return pb.CreatureDetail(found=False)
        m = pb.CreatureDetail(found=True, id=d["id"], name=d["name"], species=d["species"], age=d["age"],
                              health=d["health"], energy=d["energy"], hunger=d["hunger"], safety=d["safety"],
                              social=d["social"], personality=d["personality"], mood=d["mood"],
                              state=d["state"], goal=d["goal"], vision=d["vision"])
        m.genes.update(d["genes"])
        m.traits.update(d["traits"])
        for s in d["scores"]:
            m.scores.add(action=s["action"], score=s["score"])
        for e in d["memories"]:
            m.memories.add(**e)
        m.recent.extend(d["recent"])
        if d["target"]:
            m.has_target, m.target_x, m.target_y = True, d["target"][0], d["target"][1]
        return m


def serve(port=None):
    port = port or int(os.environ.get("SIM_PORT", "50051"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8),
                         options=[("grpc.max_send_message_length", 16 * 1024 * 1024)])
    pbg.add_SimulationServicer_to_server(Servicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    log.info("simulation service listening on :%d", port)
    return server
