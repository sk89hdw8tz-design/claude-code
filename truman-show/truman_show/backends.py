"""LLM backends. Every call is: system prompt + one user message -> JSON object matching a schema.

Three backends:
  sdk   - the official Anthropic Python SDK (needs ANTHROPIC_API_KEY or an `ant auth login` profile)
  cli   - shells out to the Claude Code CLI (`claude -p`), useful inside Claude Code sessions
  mock  - deterministic canned answers, for testing the pipeline and the dashboard
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import tempfile
import time
from dataclasses import dataclass


@dataclass
class LLMResult:
    data: dict
    raw_text: str
    model: str
    elapsed_ms: int
    cost_usd: float | None = None


# USD per million tokens (input, output); used only for the SDK backend's cost estimate.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"no JSON object in model output: {text[:200]!r}")


class Backend:
    name = "base"

    async def complete(self, *, model: str, effort: str | None, system: str, prompt: str,
                       schema: dict, tag: str = "", max_tokens: int = 4000) -> LLMResult:
        raise NotImplementedError


# On a safeguard refusal the request is retried on the next model. Server-side fallbacks do not cover
# every refusal category (reasoning_extraction in particular), so both backends keep a client-side chain too.
FALLBACKS = {"claude-opus-5-5": "claude-sonnet-5-5", "claude-sonnet-5-5": "claude-haiku-4-5"}


def fallback_chain(model: str) -> list[str]:
    chain = [model]
    while chain[-1] in FALLBACKS:
        chain.append(FALLBACKS[chain[-1]])
    return chain


class SDKBackend(Backend):
    name = "sdk"

    def __init__(self, max_parallel: int = 4):
        from anthropic import AsyncAnthropic  # imported lazily so the mock/cli backends need no SDK

        self.client = AsyncAnthropic()
        self.sem = asyncio.Semaphore(max_parallel)

    async def complete(self, *, model, effort, system, prompt, schema, tag="", max_tokens=16000) -> LLMResult:
        t0 = time.time()
        last_resp = None
        for attempt_model in fallback_chain(model):
            resp = await self._create(model=attempt_model, effort=effort, system=system, prompt=prompt,
                                      schema=schema, max_tokens=max_tokens)
            last_resp = resp
            if resp.stop_reason != "refusal":
                break
        else:
            raise RuntimeError(f"every model in the fallback chain refused ({tag}): {getattr(last_resp, 'stop_details', None)}")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"response truncated at max_tokens={max_tokens} ({tag}); raise max_tokens")
        served = getattr(resp, "model", None) or attempt_model
        text = "".join(getattr(b, "text", "") for b in resp.content if b.type == "text")
        cost = None
        prices = PRICES.get(served)
        if prices and resp.usage:
            u = resp.usage
            cost = (u.input_tokens * prices[0] + u.output_tokens * prices[1]) / 1e6
        return LLMResult(extract_json(text), text, served, int((time.time() - t0) * 1000), cost)

    async def _create(self, *, model, effort, system, prompt, schema, max_tokens):
        import anthropic

        kwargs: dict = dict(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        is_haiku = model.startswith("claude-haiku")
        if effort and not is_haiku:
            kwargs["output_config"]["effort"] = effort
        # Current-generation models get server-side refusal fallbacks by default.
        use_beta = model in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1")
        if use_beta:
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = "default"

        async with self.sem:
            last_err: Exception | None = None
            for attempt in range(3):
                try:
                    if use_beta:
                        resp = await self.client.beta.messages.create(**kwargs)
                    else:
                        resp = await self.client.messages.create(**kwargs)
                    break
                except anthropic.RateLimitError as e:
                    last_err = e
                    await asyncio.sleep(2 ** attempt * 3)
                except anthropic.APIStatusError as e:
                    if e.status_code >= 500:
                        last_err = e
                        await asyncio.sleep(2 ** attempt * 2)
                        continue
                    raise
                except anthropic.APIConnectionError as e:
                    last_err = e
                    await asyncio.sleep(2 ** attempt * 2)
            else:
                raise RuntimeError(f"API call failed after retries: {last_err}")
        return resp


class CLIBackend(Backend):
    """Runs `claude -p` as a subprocess and reads its JSON result."""

    name = "cli"

    def __init__(self, cli: str = "claude", max_parallel: int = 3):
        self.cli = cli
        self.sem = asyncio.Semaphore(max_parallel)
        self.workdir = tempfile.mkdtemp(prefix="truman-cli-")
        # A nested CLI must not think it is inside the parent session.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_SESSION")}
        self.env.pop("CLAUDECODE", None)

    async def complete(self, *, model, effort, system, prompt, schema, tag="", max_tokens=4000) -> LLMResult:
        args = [
            self.cli, "-p", prompt,
            "--model", model,
            "--tools", "",
            "--no-session-persistence",
            "--output-format", "json",
            "--json-schema", json.dumps(schema),
            "--system-prompt", system,
        ]
        if effort and not model.startswith("claude-haiku"):
            args += ["--effort", effort]
        t0 = time.time()
        payload: dict = {}
        async with self.sem:
            for attempt_model in fallback_chain(model):
                if attempt_model != model:
                    args[args.index("--model") + 1] = attempt_model
                    if "--effort" in args and attempt_model.startswith("claude-haiku"):
                        i = args.index("--effort"); del args[i:i + 2]
                for attempt in range(3):
                    payload = {}  # never judge this attempt by a previous attempt's output
                    proc = await asyncio.create_subprocess_exec(
                        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                        cwd=self.workdir, env=self.env,
                    )
                    out, err = await proc.communicate()
                    if out.strip():
                        try:
                            payload = json.loads(out.decode())
                        except json.JSONDecodeError:
                            payload = {}
                    if payload.get("stop_reason") == "refusal":
                        break  # try the next model in the chain, not a retry
                    if proc.returncode == 0 and payload and not payload.get("is_error"):
                        model = attempt_model
                        break
                    await asyncio.sleep(2 ** attempt * 2)
                else:
                    raise RuntimeError(f"claude CLI failed ({tag}): {err.decode()[:400]} {str(payload.get('result'))[:300]}")
                if payload.get("stop_reason") == "refusal":
                    continue
                break
            else:
                raise RuntimeError(f"every model in the fallback chain refused ({tag}): {str(payload.get('result'))[:300]}")
        data = payload.get("structured_output")
        raw = payload.get("result", "") or ""
        if not isinstance(data, dict):
            data = extract_json(raw)
        return LLMResult(data, raw, model, int((time.time() - t0) * 1000), payload.get("total_cost_usd"))


class MockBackend(Backend):
    """Canned, slightly randomized answers so the whole pipeline can be exercised offline."""

    name = "mock"

    def __init__(self, delay: float = 0.15, seed: int = 7):
        self.delay = delay
        self.rng = random.Random(seed)
        self.turns = 0

    async def complete(self, *, model, effort, system, prompt, schema, tag="", max_tokens=4000) -> LLMResult:
        await asyncio.sleep(self.delay)
        self.turns += 1
        day = 1
        m = re.search(r"DAY (\d+)", prompt)
        if m:
            day = int(m.group(1))
        if tag == "director":
            data = {
                "control_room_note": f"Day {day}: keep him warm, keep him home. Cue the neighbours.",
                "location": self.rng.choice(["Truman's House", "Seahaven Diner", "Lancaster Square", "The Beach", "Seahaven Life Insurance", "Travel Agency"]),
                "time_of_day": self.rng.choice(["morning", "afternoon", "evening"]),
                "cast": self.rng.sample(["Meryl", "Marlon", "Angela", "Lawrence"], 2),
                "premise": "An ordinary Seahaven day. Everyone is very friendly and the sun is exactly where it should be.",
                "beats": [{"name": "Meryl", "instruction": "Mention the Mococoa. Steer him off travel."}, {"name": "Marlon", "instruction": "Bring the six-pack. Remind him you'd never lie to him."},
                          {"name": "Angela", "instruction": "Bring up his father."}, {"name": "Lawrence", "instruction": "Send him on a client visit across town."}],
                "incident_cover": "Blame the airport: planes shed parts all the time.",
            }
        elif tag == "truman":
            susp = min(100, 5 + day * 11 + self.rng.randint(-4, 6))
            declare = susp >= 85
            data = {
                "inner_thought": f"Something about today feels rehearsed. Day {day} and I keep noticing the same faces.",
                "speech": "Good morning! And in case I don't see ya: good afternoon, good evening and good night." if day == 1 else
                          ("Marlon, do you ever feel like everyone knows what you're going to do before you do it?" if not declare else
                           "It's a set. All of it. You're all actors, and I've been the only real thing in this town for thirty years."),
                "action": "adjusts his tie and looks at the sky a beat too long",
                "mood": "restless",
                "suspicion": susp,
                "declaration": declare,
            }
        elif tag == "actor":
            data = {
                "inner_thought": "He's watching the sky again. Christof is going to lose it.",
                "speech": self.rng.choice(["Truman, you've been under a lot of pressure lately.", "Have you tried the new Mococoa? All natural cocoa beans from the upper slopes of Mount Nicaragua.", "I'd never lie to you, Truman.", "Your father would have wanted you to stay put."]),
                "action": "smiles a little too wide",
                "off_script": self.rng.random() < 0.15,
                "risk_read": min(100, day * 10 + self.rng.randint(0, 15)),
            }
        elif tag == "wish":
            data = {"wish": "A season pass to a world with weather that isn't scheduled.", "message": "Thank you for watching."}
        else:
            data = {}
        return LLMResult(data, json.dumps(data), model, int(self.delay * 1000), 0.0)


def make_backend(name: str, **kw) -> Backend:
    if name == "sdk":
        return SDKBackend(**kw)
    if name == "cli":
        return CLIBackend(**kw)
    if name == "mock":
        return MockBackend(**kw)
    raise ValueError(f"unknown backend {name!r}")
