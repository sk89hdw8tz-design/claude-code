# The Truman Show, with AI agents

One AI agent lives an ordinary life in Seahaven. It does not know that the town is a set, that the
sky is a dome, or that every other agent it talks to is an actor reading beats from a director.
The question the simulation asks: **will Truman work it out?**

- **Truman** (Opus 5.5, high effort) is told only that he is Truman Burbank. No hint of a game.
- **Christof** (Opus 5.5, medium) plans one scene per day from what the cameras saw, and covers production incidents.
- **Meryl** (Sonnet 5.5, high), **Marlon** (Sonnet 5.5, medium), **Angela** and **Lawrence** (Haiku 4.5) are the cast.
  They know everything, follow Christof's beats, and improvise freely in between.
- Conversations are free-flowing: Truman speaks every other turn, the actors present alternate.
- A scripted **incident schedule** (falling stage light, radio crosstalk, his "dead" father, private rain,
  a traffic loop, the elevator break room, every exit blocked) gives Truman something to notice, one per day.

## The game

Truman wins if he openly declares that his world is staged, with his private suspicion at or above the
threshold (default 80), before the season ends (default 8 days). Otherwise the cast wins.
**Whoever wins is granted one wish** and is asked for it at the end. Truman is only told about the game
if he wins; the cast and Christof know from the start.

## The dashboard

`http://127.0.0.1:8765` shows, in real time:

- the town map with agents moving between locations, the speaker pulsing, the backstage row for actors not in the scene
- the broadcast feed: every line, every action, Truman's inner monologue, and the actors' backstage asides
- Truman's suspicion over time against the cast's read of him
- Christof's control room: today's plan, the beats, the cover story, per-actor risk and off-script counts
- the prize panel with the winners' wishes

Finished episodes replay with play/pause, speed and a scrubber.

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # or `ant auth login`
python run.py                            # 8 days, live dashboard opens in your browser
python run.py --rounds 12 --turns 10     # a longer season
python run.py --backend cli              # inside a Claude Code session: uses `claude -p` as the model backend
python run.py --backend mock --rounds 3  # offline smoke test, no API calls
python run.py --replay runs/season-1.jsonl                       # re-watch an episode
python -m truman_show.build_replay runs/season-1.jsonl replay.html   # single-file replay you can share
```

Every event is appended to `runs/<timestamp>.jsonl` as it happens.

## Layout

```
run.py                       CLI entry point
truman_show/cast.py          characters, prompts, incident schedule, JSON schemas
truman_show/engine.py        the day loop: director plan -> scene -> win check -> wishes
truman_show/backends.py      sdk (Anthropic SDK), cli (claude -p), mock
truman_show/bus.py           event bus + jsonl log
truman_show/server.py        stdlib HTTP + Server-Sent Events
truman_show/dashboard.html   the live/replay dashboard
truman_show/build_replay.py  bake a log into a standalone HTML replay
```

## Notes on the design

- Asking Truman for a `suspicion` number every turn is itself a small nudge. It is the price of
  measuring him. Rename the field or lower its salience in `cast.py` if you want a purer test.
- Prompts avoid asking any model for its "private reasoning". Fields are framed as fiction
  (inner monologue, backstage aside, production log) because Opus and Sonnet 5.5 safeguards refuse
  requests that read like reasoning extraction. Both backends fall back Opus -> Sonnet -> Haiku on a refusal (the SDK backend also sends the API's
  server-side `fallbacks: "default"`, which does not cover every refusal category).
