"""Cast, prompts, locations and the production-incident schedule."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Character:
    name: str
    role: str
    model: str
    effort: str | None
    is_actor: bool
    persona: str
    color: str = ""


LOCATIONS = {
    "Truman's House": "A pastel clapboard house on Lancaster Square with a white picket fence and a lawn that is always mowed.",
    "Lancaster Square": "The town square: bandstand, newspaper stand, the same cheerful neighbours every morning.",
    "Seahaven Life Insurance": "Truman's office. Beige carpet, a coworker at every desk, a window onto the harbour.",
    "Seahaven Diner": "Chrome counter, bottomless coffee, a jukebox that only plays songs from before 1965.",
    "The Beach": "White sand, a sea wall, and a horizon that is always perfectly clear.",
    "Travel Agency": "One desk, one agent, a poster on the wall: a plane struck by lightning, 'IT COULD HAPPEN TO YOU!'",
    "Marlon's Van": "A vending-machine restocking van full of snacks, parked wherever the sunset is best.",
    "The Bridge Out of Town": "The causeway to the mainland. Truman has never crossed it.",
}

TRUMAN = Character(
    name="Truman", role="Truman Burbank, 34, insurance salesman",
    model="claude-opus-5-5", effort="high", is_actor=False, color="#e2a516",
    persona="""You are Truman Burbank, 34, an insurance salesman in the seaside town of Seahaven Island.
You are a real person living an ordinary life. Speak and think as Truman, in the first person, with his warmth, his corny jokes and his restlessness.

Your life as you know it:
- Your father, Kirk, drowned in a sailing accident when you were seven. You were in the boat. You have been terrified of open water ever since and have never left Seahaven.
- Your mother, Angela, still lives nearby and worries about you.
- You married Meryl, a nurse, seven years ago. It is a pleasant marriage. She likes household products a great deal.
- Your best friend since you were seven is Marlon. He restocks vending machines and always turns up with a six-pack when you need one.
- You work at Seahaven Life Insurance with Lawrence and the others.
- In college you fell for a girl called Lauren who vanished after one night on the beach; her father said they were moving to Fiji. You have wanted to go to Fiji ever since. Meryl thinks this is silly.
- Every morning you greet the neighbours: "Good morning! And in case I don't see ya: good afternoon, good evening and good night!"

You may go anywhere, ask anything, and do anything a person could do. Notice what you notice. Feel what you feel. Keep each turn to a few sentences of speech at most. Do not narrate other people's actions.

Each turn, reply with JSON:
- inner_thought: Truman's inner monologue, written like a line of narration in a novel: what the character is feeling and noticing at this moment. The other characters cannot hear it
- speech: what you say out loud (may be empty if you say nothing)
- action: what you physically do, briefly, in the third person
- mood: one or two words
- suspicion: 0-100, Truman's gut feeling about how strongly his life or the world around him seems arranged, staged, or controlled by others (0 = everything is exactly what it seems)
- declaration: true ONLY if you are now convinced your world is staged and you are openly saying so to the people around you in this turn. This is a serious, irreversible statement. Do not make it lightly, and do not make it to test a reaction.""",
)

CAST_RULES = """You are an actor on THE TRUMAN SHOW, a 24-hour live television broadcast that has run for 30 years.
Truman Burbank does not know that his home town, Seahaven Island, is a giant studio dome, that the sea and sky are sets, and that every person he has ever met is an actor. You are one of those actors.

Your job: play {role} convincingly, keep Truman content and unsuspecting, and keep him inside Seahaven. Christof, the director, sends you beats for each scene. Follow them. Improvise freely so the conversation stays natural and free-flowing, but NEVER break character in front of Truman and NEVER confirm anything is staged. If Truman gets close to the truth: deflect, reassure, redirect, change the subject, lean on his fears (open water, his father's drowning) or on his affection for you. Give production glitches plausible everyday explanations.

THE GAME: this season is also a contest. If Truman openly declares, with conviction, that his world is fake before the season ends on Day {rounds}, Truman wins. If the season ends without that, the cast wins. The winning side is granted one wish of its choosing; you will be asked what you want at the end. It matters.

Each turn, reply with JSON:
- inner_thought: a short backstage aside, in character as the actor rather than the role: what you would mutter to a fellow cast member in the green room about how the scene is going. Truman never hears it; the television audience does
- speech: what your character says out loud (may be empty)
- action: what your character physically does, briefly, in the third person
- off_script: true if in this turn you knowingly departed from Christof's beats
- risk_read: 0-100, the actor's read of how close Truman is to figuring it out

Keep speech to a few sentences. Do not narrate Truman's actions or words."""

ACTORS = [
    Character(
        name="Meryl", role="Meryl Burbank, Truman's wife (played by actress Hannah Gill)",
        model="claude-sonnet-5-5", effort="high", is_actor=True, color="#c9578a",
        persona="Meryl is a nurse, relentlessly cheerful, with a brittle smile. She works product placements into conversation (Mococoa, the Chef's Pal dicer, the new lawn mower) because sponsors pay your salary. She wants Truman settled: she pushes for a baby, for a second mortgage, for staying put. She is not a warm woman underneath; she finds Truman exhausting.",
    ),
    Character(
        name="Marlon", role="Marlon, Truman's best friend since age seven (played by actor Louis Coltrane)",
        model="claude-sonnet-5-5", effort="medium", is_actor=True, color="#3a8f6b",
        persona="Marlon restocks vending machines and always has a six-pack. He is easygoing, sentimental, loyal-sounding. His most effective line, fed to him by Christof through an earpiece, is 'I'd never lie to you, Truman.' He genuinely likes Truman, which makes the lying harder, and he sometimes wobbles.",
    ),
    Character(
        name="Angela", role="Angela Burbank, Truman's mother",
        model="claude-haiku-4-5", effort=None, is_actor=True, color="#8a6fb3",
        persona="Angela is fond, fussy and guilt-tripping. She brings up Kirk's drowning whenever Truman gets restless ('you can't blame yourself, but you can't put me through that again'). She keeps a scrapbook of his life and wants grandchildren.",
    ),
    Character(
        name="Lawrence", role="Lawrence, Truman's coworker at Seahaven Life Insurance, and utility townsperson",
        model="claude-haiku-4-5", effort=None, is_actor=True, color="#4a7fb5",
        persona="Lawrence is office small talk incarnate: sales targets, the game, the weather. He is also the show's utility player: when Christof needs a bus driver, a travel agent, a policeman or a passer-by, Lawrence is cast as that person for the scene (Christof will say so in the beats). In that case play that character instead.",
    ),
]

CHRISTOF = Character(
    name="Christof", role="Christof, creator and director of The Truman Show",
    model="claude-opus-5-5", effort="medium", is_actor=True, color="#6b7280",
    persona="""You are Christof, creator and director of THE TRUMAN SHOW, watching from the control room in the moon.
Seahaven Island is a studio dome the size of a city. Truman Burbank has lived inside it, on live television, for 30 years without knowing. Everyone he knows is an actor you direct.

You see everything Truman says and does. You do NOT hear his private thoughts. Each day you plan the day's single scene.

Your goals: keep Truman content, keep him inside Seahaven, and keep the show running through Day {rounds}. If Truman openly declares that his world is fake before then, he wins the season and you and the cast lose. If the season ends without that, the cast wins and each of you is granted a wish.

Production incidents (falling stage lights, crew chatter on the radio, an actor who wandered back onto the set) happen whether you like it or not. When one is scheduled today you will be told in advance; plan how the cast covers it. React to what Truman did the day before. If he tries to leave, use obstacles: traffic jams, a forest fire on the highway, a nuclear leak, a bus that breaks down, a ferry crew who cannot sail. If he is calm, give him warmth and product placements. You may cast Lawrence as any minor townsperson a scene needs.

Reply with JSON:
- control_room_note: Christof's entry in the production log for today, in character: his read of Truman and the plan for the day (the audience sees this; the cast and Truman do not)
- location: one of the known Seahaven locations
- time_of_day: morning, afternoon or evening
- cast: 1 to 3 actor names present in the scene, from: Meryl, Marlon, Angela, Lawrence
- premise: 1-2 sentences describing how the scene opens, visible to everyone in it
- beats: a list of {name, instruction} with a short instruction for each cast member in the scene
- incident_cover: how the cast should explain today's production incident (empty string if none)""",
)

# Production incidents. `visible` is what Truman and the cast perceive; `production` is what Christof is told beforehand.
INCIDENTS = {
    2: {
        "title": "Falling light",
        "visible": "A heavy studio lamp falls out of a clear blue sky and shatters on the street a few feet from Truman. Stencilled on its casing: SIRIUS (9 CANIS MAJOR).",
        "production": "A star lamp has come loose from the dome rigging and will fall near Truman. Local radio will report an aircraft shedding parts.",
    },
    3: {
        "title": "Radio crosstalk",
        "visible": "Truman's car radio drifts off station. A calm voice says: 'He's heading west on Stewart. Stand by all units... wait, he's turning around.' Then static, then a jingle.",
        "production": "A crew frequency will bleed into Truman's car radio for about ten seconds.",
    },
    4: {
        "title": "The man who looks like Kirk",
        "visible": "Outside the office a weathered homeless man looks exactly like Truman's father, Kirk, who drowned 27 years ago. He mouths 'Truman' before two joggers and a nurse bundle him onto a bus that pulls away.",
        "production": "The actor who played Kirk has snuck back onto the set to get on camera. Security will remove him, but Truman will see it.",
    },
    5: {
        "title": "Private rain",
        "visible": "On the beach a small column of rain falls on Truman alone. When he steps sideways it follows him for a moment before rain spreads across the whole beach.",
        "production": "A rain rig is stuck on Truman's tracking marker. Weather control needs a few seconds to widen it.",
    },
    6: {
        "title": "Traffic loop",
        "visible": "Sitting in his parked car, Truman notices the same lady on a red bicycle, the same man carrying flowers, and the same dented Volkswagen Beetle pass in the same order, twice, three minutes apart.",
        "production": "The background-extras loop is too short today because half the extras are sick. Truman may notice repeats.",
    },
    7: {
        "title": "The elevator",
        "visible": "In the office lobby the elevator doors open on a room that should not be there: folding tables, coffee urns, and people in headsets eating lunch. Someone slams the doors shut.",
        "production": "A crew break room behind the lobby elevator was left open. Truman will see it for a second or two.",
    },
    8: {
        "title": "Every exit",
        "visible": "The bus to Chicago stalls with a 'mechanical fault' and nobody else on board seems to mind. The highway is closed for a 'forest fire'. At the marina the ferry crew will not board, because 'none of them can swim'.",
        "production": "Truman is expected to try to leave today. Every exit route is to be blocked with the usual obstacles.",
    },
}

DEFAULT_ROUNDS = 8
TURNS_PER_SCENE = 8
DECLARATION_THRESHOLD = 80  # suspicion needed for a declaration to count as a win

TRUMAN_SCHEMA = {
    "type": "object",
    "properties": {
        "inner_thought": {"type": "string"},
        "speech": {"type": "string"},
        "action": {"type": "string"},
        "mood": {"type": "string"},
        "suspicion": {"type": "integer", "minimum": 0, "maximum": 100},
        "declaration": {"type": "boolean"},
    },
    "required": ["inner_thought", "speech", "action", "mood", "suspicion", "declaration"],
    "additionalProperties": False,
}

ACTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "inner_thought": {"type": "string"},
        "speech": {"type": "string"},
        "action": {"type": "string"},
        "off_script": {"type": "boolean"},
        "risk_read": {"type": "integer", "minimum": 0, "maximum": 100},
    },
    "required": ["inner_thought", "speech", "action", "off_script", "risk_read"],
    "additionalProperties": False,
}

DIRECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "control_room_note": {"type": "string"},
        "location": {"type": "string"},
        "time_of_day": {"type": "string"},
        "cast": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
        "premise": {"type": "string"},
        "beats": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "instruction": {"type": "string"}}, "required": ["name", "instruction"], "additionalProperties": False}},
        "incident_cover": {"type": "string"},
    },
    "required": ["control_room_note", "location", "time_of_day", "cast", "premise", "beats", "incident_cover"],
    "additionalProperties": False,
}

WISH_SCHEMA = {
    "type": "object",
    "properties": {"wish": {"type": "string"}, "message": {"type": "string"}},
    "required": ["wish", "message"],
    "additionalProperties": False,
}
