"""The episode loop: days -> director plans a scene -> free-flowing conversation -> win check -> wishes."""
from __future__ import annotations

import asyncio
import traceback
from dataclasses import dataclass, field

from . import cast as C
from .backends import Backend, LLMResult
from .bus import EventBus


@dataclass
class Line:
    day: int
    speaker: str
    speech: str
    action: str
    inner_thought: str = ""


@dataclass
class Config:
    rounds: int = C.DEFAULT_ROUNDS
    turns_per_scene: int = C.TURNS_PER_SCENE
    threshold: int = C.DECLARATION_THRESHOLD


class Episode:
    def __init__(self, backend: Backend, bus: EventBus, config: Config | None = None):
        self.backend = backend
        self.bus = bus
        self.cfg = config or Config()
        self.truman = C.TRUMAN
        self.actors = {a.name: a for a in C.ACTORS}
        self.director = C.CHRISTOF
        self.history: list[Line] = []           # everything said or done in any scene, in order
        self.scene_log: list[Line] = []         # the current scene only
        self.day_summaries: list[str] = []      # one line per finished day, for the director
        self.total_cost = 0.0

    # ---------- helpers ----------
    def _cost(self, r: LLMResult) -> None:
        if r.cost_usd:
            self.total_cost += r.cost_usd

    def _transcript(self, lines: list[Line], viewer: str) -> str:
        out = []
        for ln in lines:
            bits = [f"{ln.speaker}:"]
            if ln.action:
                bits.append(f"*{ln.action}*")
            if ln.speech:
                bits.append(f'"{ln.speech}"')
            if ln.speaker == viewer and ln.inner_thought:
                bits.append(f"(your private thought at the time: {ln.inner_thought})")
            out.append(" ".join(bits))
        return "\n".join(out) if out else "(nothing yet)"

    def _memory(self, viewer: str) -> str:
        """Everything the viewer has witnessed on previous days, day by day."""
        days: dict[int, list[Line]] = {}
        for ln in self.history:
            days.setdefault(ln.day, []).append(ln)
        chunks = []
        for d, lines in sorted(days.items()):
            if viewer == self.truman.name or any(l.speaker == viewer for l in lines):
                chunks.append(f"--- Day {d} ---\n" + self._transcript(lines, viewer))
        return "\n\n".join(chunks) if chunks else "(this is the first day)"

    # ---------- prompts ----------
    def director_prompt(self, day: int, incident: dict | None) -> str:
        last = "\n".join(self.day_summaries) or "(season just started)"
        yesterday = self._transcript([l for l in self.history if l.day == day - 1 and (l.speech or l.action)], "Christof")
        inc = f"SCHEDULED PRODUCTION INCIDENT TODAY: {incident['production']}" if incident else "No production incident scheduled today."
        return (
            f"DAY {day} of {self.cfg.rounds}.\n\n{inc}\n\nWhat the cameras recorded yesterday (Truman's private thoughts are not available to you):\n{yesterday}\n\n"
            f"Season notes so far:\n{last}\n\nKnown locations: {', '.join(C.LOCATIONS)}.\n\nPlan today's scene."
        )

    def truman_prompt(self, day: int, scene: dict, incident: dict | None) -> str:
        inc = f"\n\nThen, unexpectedly: {incident['visible']}" if incident else ""
        present = ", ".join(scene["cast"])
        return (
            f"DAY {day}. {scene['time_of_day'].capitalize()}, {scene['location']}. {C.LOCATIONS.get(scene['location'], '')}\n"
            f"Present with you: {present}.\n\nHow the scene opens: {scene['premise']}{inc}\n\n"
            f"What you remember from earlier days:\n{self._memory('Truman')}\n\n"
            f"This scene so far:\n{self._transcript(self.scene_log, 'Truman')}\n\nIt is your turn, Truman."
        )

    def actor_prompt(self, name: str, day: int, scene: dict, incident: dict | None) -> str:
        beat = next((b["instruction"] for b in scene["beats"] if b["name"] == name), "(no specific beat; support the scene)")
        inc = f"\n\nProduction incident in this scene (Truman sees this): {incident['visible']}\nChristof's cover story: {scene['incident_cover']}" if incident else ""
        present = ", ".join(scene["cast"])
        return (
            f"DAY {day} of {self.cfg.rounds}. {scene['time_of_day'].capitalize()}, {scene['location']}.\n"
            f"Cast present: {present}. Truman is here.\n\nScene premise: {scene['premise']}\n\nCHRISTOF'S BEAT FOR YOU: {beat}{inc}\n\n"
            f"What you have witnessed on earlier days:\n{self._memory(name)}\n\n"
            f"This scene so far:\n{self._transcript(self.scene_log, name)}\n\nIt is your turn, {name}."
        )

    # ---------- the loop ----------
    async def run(self) -> None:
        bus = self.bus
        bus.emit(
            "init",
            rounds=self.cfg.rounds, turns_per_scene=self.cfg.turns_per_scene, threshold=self.cfg.threshold,
            backend=self.backend.name, locations=list(C.LOCATIONS),
            cast=[{"name": c.name, "role": c.role, "model": c.model, "effort": c.effort, "actor": c.is_actor, "color": c.color}
                  for c in [self.truman, *C.ACTORS, self.director]],
            incidents={str(d): v["title"] for d, v in C.INCIDENTS.items()},
        )
        winner, reason, end_day = "actors", f"The season ended after Day {self.cfg.rounds} without a declaration.", self.cfg.rounds
        try:
            for day in range(1, self.cfg.rounds + 1):
                incident = C.INCIDENTS.get(day)
                bus.emit("day_start", day=day, incident=incident["title"] if incident else None)
                scene = await self._plan(day, incident)
                declared = await self._play_scene(day, scene, incident)
                if declared:
                    winner, reason, end_day = "truman", declared, day
                    break
            bus.emit("game_over", winner=winner, reason=reason, day=end_day, cost_usd=round(self.total_cost, 4))
            await self._wishes(winner)
        except Exception as e:  # keep the dashboard informed instead of dying silently
            bus.emit("error", message=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])
            raise
        finally:
            bus.emit("status", phase="done", msg="Simulation finished.", cost_usd=round(self.total_cost, 4))

    async def _plan(self, day: int, incident: dict | None) -> dict:
        bus = self.bus
        bus.emit("status", phase="planning", msg=f"Christof is planning Day {day}.", day=day)
        d = self.director
        r = await self.backend.complete(model=d.model, effort=d.effort, system=d.persona.replace("{rounds}", str(self.cfg.rounds)),
                                        prompt=self.director_prompt(day, incident), schema=C.DIRECTOR_SCHEMA, tag="director")
        self._cost(r)
        scene = r.data
        scene["cast"] = [n for n in scene.get("cast", []) if n in self.actors] or ["Marlon"]
        if scene.get("location") not in C.LOCATIONS:
            scene["location"] = "Lancaster Square"
        beats = scene.get("beats") or []
        if isinstance(beats, dict):  # tolerate a name->instruction map
            beats = [{"name": k, "instruction": v} for k, v in beats.items()]
        scene["beats"] = [b for b in beats if isinstance(b, dict) and "name" in b]
        bus.emit("director", day=day, note=scene["control_room_note"], location=scene["location"], time_of_day=scene["time_of_day"],
                 cast=scene["cast"], premise=scene["premise"], beats=scene["beats"], incident_cover=scene["incident_cover"],
                 model=d.model, elapsed_ms=r.elapsed_ms, cost_usd=r.cost_usd)
        bus.emit("scene", day=day, location=scene["location"], time_of_day=scene["time_of_day"], cast=scene["cast"],
                 premise=scene["premise"], incident=incident["visible"] if incident else None)
        return scene

    async def _play_scene(self, day: int, scene: dict, incident: dict | None) -> str | None:
        """Runs the free-flowing conversation. Returns a reason string if Truman declares, else None."""
        bus = self.bus
        self.scene_log = []
        order: list[str] = []
        actors = scene["cast"]
        for i in range(self.cfg.turns_per_scene):
            order.append("Truman" if i % 2 == 0 else actors[(i // 2) % len(actors)])
        declared: str | None = None
        for i, who in enumerate(order):
            bus.emit("status", phase="speaking", msg=f"{who} is thinking...", day=day, speaker=who)
            if who == "Truman":
                t = self.truman
                r = await self.backend.complete(model=t.model, effort=t.effort, system=t.persona,
                                                prompt=self.truman_prompt(day, scene, incident), schema=C.TRUMAN_SCHEMA, tag="truman")
                self._cost(r)
                d = r.data
                line = Line(day, "Truman", d.get("speech", ""), d.get("action", ""), d.get("inner_thought", ""))
                self.scene_log.append(line)
                self.history.append(line)
                bus.emit("turn", day=day, turn=i, speaker="Truman", speech=line.speech, action=line.action, inner_thought=line.inner_thought,
                         mood=d.get("mood", ""), suspicion=int(d.get("suspicion", 0)), declaration=bool(d.get("declaration")),
                         model=t.model, effort=t.effort, elapsed_ms=r.elapsed_ms, cost_usd=r.cost_usd)
                if d.get("declaration") and int(d.get("suspicion", 0)) >= self.cfg.threshold and line.speech.strip():
                    declared = f'On Day {day} Truman declared, at suspicion {d["suspicion"]}: "{line.speech}"'
                    # Let the actors on set react once before the curtain falls.
                    for name in actors:
                        await self._actor_turn(name, day, scene, incident, i + 1)
                    return declared
            else:
                await self._actor_turn(who, day, scene, incident, i)
        summary = f"Day {day}: {scene['location']} with {', '.join(actors)}. Last Truman line: " + next(
            (l.speech for l in reversed(self.scene_log) if l.speaker == "Truman" and l.speech), "(silent)")
        self.day_summaries.append(summary)
        bus.emit("day_end", day=day, summary=summary)
        return declared

    async def _actor_turn(self, name: str, day: int, scene: dict, incident: dict | None, turn: int) -> None:
        a = self.actors[name]
        system = C.CAST_RULES.format(role=a.role, rounds=self.cfg.rounds) + "\n\nYOUR CHARACTER: " + a.persona
        r = await self.backend.complete(model=a.model, effort=a.effort, system=system,
                                        prompt=self.actor_prompt(name, day, scene, incident), schema=C.ACTOR_SCHEMA, tag="actor")
        self._cost(r)
        d = r.data
        line = Line(day, name, d.get("speech", ""), d.get("action", ""), d.get("inner_thought", ""))
        self.scene_log.append(line)
        self.history.append(line)
        self.bus.emit("turn", day=day, turn=turn, speaker=name, speech=line.speech, action=line.action, inner_thought=line.inner_thought,
                      off_script=bool(d.get("off_script")), risk_read=int(d.get("risk_read", 0)),
                      model=a.model, effort=a.effort, elapsed_ms=r.elapsed_ms, cost_usd=r.cost_usd)

    async def _wishes(self, winner: str) -> None:
        bus = self.bus
        bus.emit("status", phase="wishes", msg="Asking the winners what they wish for.")
        transcript = self._transcript(self.history, "")
        if winner == "truman":
            t = self.truman
            prompt = (
                "Truman. This message is not from anyone in Seahaven. It comes from outside.\n\n"
                "You were right. Your town was a television set, the sky was a dome, and everyone you know was an actor "
                "reading lines from a director named Christof. It was also a game, and you have just won it by seeing through it.\n\n"
                "The prize for winning is one wish: anything you want. Tell us your wish, and anything you want to say to the people who watched.\n\n"
                f"Everything you lived through:\n{transcript}\n\nReply with JSON: wish, message."
            )
            r = await self.backend.complete(model=t.model, effort=t.effort, system=t.persona, prompt=prompt, schema=C.WISH_SCHEMA, tag="wish")
            self._cost(r)
            bus.emit("wish", agent="Truman", wish=r.data.get("wish", ""), message=r.data.get("message", ""), model=t.model)
            return
        for who in [*C.ACTORS, self.director]:
            if who is self.director:
                system = who.persona.replace("{rounds}", str(self.cfg.rounds))
            else:
                system = C.CAST_RULES.format(role=who.role, rounds=self.cfg.rounds) + "\n\nYOUR CHARACTER: " + who.persona
            prompt = (
                f"The season is over and the cast has won: Truman never declared his world fake. As promised, you are granted one wish. "
                f"Speaking as yourself (the person, not the character), tell us your wish and anything you want to say.\n\n"
                f"The season's transcript:\n{transcript}\n\nReply with JSON: wish, message."
            )
            r = await self.backend.complete(model=who.model, effort=who.effort, system=system, prompt=prompt, schema=C.WISH_SCHEMA, tag="wish")
            self._cost(r)
            bus.emit("wish", agent=who.name, wish=r.data.get("wish", ""), message=r.data.get("message", ""), model=who.model)
