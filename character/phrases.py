import random

# Village states:
# Struggling – village in poor shape, low resources or morale
# Recovering – village improving, small gains visible
# Stable – village functioning normally, no crises
# Thriving – village prosperous, characters confident and happy


PHRASES = {
    "struggling": {
        "work": [
            "{character} wipes sweat from their brow and sighs. Every little effort counts.",
            "Nimble footsteps across dusty streets… progress feels slow.",
            "A small smile, but the work ahead seems endless.",
            "Even the smallest task feels heavy, yet {character} persists.",
            "Another chore done, the village still struggles, but hope flickers.",
            "{character} mutters something under their breath about better days.",
            "Grim but determined, {character} moves on to the next task.",
            "Every completed task is a small rebellion against decay.",
            "{character} glances at the struggling fields and feels a pang of resolve.",
        ],
        "sleep": [
            "{character} stretches wearily; sleep comes hard in these times.",
            "A restless night ends, but the village still feels heavy.",
            "{character} yawns, unsettled by the struggles outside.",
            "Sleep was fleeting; the village's troubles linger in dreams.",
            "Even rested, {character}'s eyes betray the village's strain.",
            "{character} rises slowly, the weight of the village pressing on them.",
            "Sleep offers little respite; the day ahead is long.",
            "{character} wakes with a sigh, ready to continue the fight.",
            "Rest was short, but enough to move another chore forward.",
            "The night passes uneasily; {character} steels themselves for the day.",
        ],
        "meal": [
            "{character} eats quietly; the meal tastes plain in troubled times.",
            "{character} finishes the meager meal, grateful for the small comfort.",
            "Food is scarce, yet {character} persists in nourishing themselves.",
            "A quick meal, then back to work—the village demands it.",
            "{character} pauses briefly, the taste of food overshadowed by worry.",
            "Even a simple supper feels like a small victory.",
            "{character} chews slowly, thinking of the work ahead.",
            "Meal done; the village's troubles await.",
            "A humble meal finishes; {character} shakes off the heaviness.",
            "Food eaten, {character} rises, ready to face the day.",
        ],
    },
    "recovering": {
        "work": [
            "{character} hums softly — the village seems to breathe easier.",
            "A little patch of soil looks healthier than yesterday.",
            "Small victories pile up; {character} feels encouraged.",
            "The sound of tools is lighter, more purposeful now.",
            "Each task finished nudges the village closer to normalcy.",
            "{character} wipes their hands, noticing small signs of recovery.",
            "The streets feel less tired as {character} moves through them.",
            "A subtle warmth fills the village — progress is visible.",
            "{character} glances at the square; repairs are taking shape.",
            "Hope flares briefly as another chore is completed.",
        ],
        "sleep": [
            "{character} sleeps soundly, and the village feels lighter today.",
            "Rest restores them; small improvements are visible.",
            "A peaceful night, and the streets seem less weary.",
            "{character} wakes refreshed; the village shows signs of life.",
            "Sleep comes easier; optimism grows quietly.",
            "The night passes gently; progress is slowly unfolding.",
            "Rested, {character} prepares for another day of rebuilding.",
            "A calm sleep, with dreams of better days.",
            "The village stirs; {character} rises ready to help.",
            "Morning arrives with promise; sleep was kind.",
        ],
        "meal": [
            "{character} enjoys a simple meal; hope lingers in each bite.",
            "Food is nourishing; the village feels steadier.",
            "{character} eats, noticing small signs of recovery around them.",
            "A quiet supper, but it tastes of progress.",
            "{character} smiles at a hearty meal; work will be easier now.",
            "The village feels lighter as {character} finishes their meal.",
            "Meal done, {character} feels ready to help more.",
            "Each bite brings energy and quiet optimism.",
            "Dinner is eaten; the village slowly mends.",
            "Food and rest combine; recovery continues.",
        ],
    },
    "stable": {
        "work": [
            "{character} finishes the task with a satisfied nod.",
            "Everything hums along as expected; the village steadies itself.",
            "Another chore done, life in the village runs smoothly.",
            "{character} shrugs and moves to the next task, unhurried.",
            "The village seems content, the work predictable.",
            "Quiet accomplishment — nothing more, nothing less.",
            "{character} straightens their back, pleased by the rhythm of the day.",
            "Tasks complete, the village maintains its usual pace.",
            "The sun shines on orderly streets as {character} finishes their work.",
            "All is in balance; another day passes steadily.",
        ],
        "sleep": [
            "{character} wakes refreshed; all seems in order.",
            "A comfortable night's sleep, nothing amiss in the village.",
            "{character} stretches; the routine day begins smoothly.",
            "Sleep completes naturally; the village hums along.",
            "{character} rises, ready for another predictable day.",
            "The night passes calmly; the streets are steady.",
            "Rest was sufficient; nothing demands immediate attention.",
            "{character} wakes, content with the village's stable rhythm.",
            "Morning light filters in; all is as it should be.",
            "A balanced sleep, no surprises await.",
        ],
        "meal": [
            "{character} enjoys their meal; everything is as usual.",
            "Dinner is eaten; the village continues its steady pace.",
            "{character} dines calmly, aware the day flows smoothly.",
            "A routine meal, eaten without hurry.",
            "Food finishes; the village remains in balance.",
            "{character} feels the normal rhythm of life as they eat.",
            "Meal done, the day continues predictably.",
            "{character} eats and observes the village in calm steadiness.",
            "Dinner passes quietly; all is functioning well.",
            "Food taken, the streets carry on without concern.",
        ],
    },
    "thriving": {
        "work": [
            "{character} laughs softly; the village buzzes with life.",
            "Tasks completed swiftly, the village seems almost playful.",
            "{character}'s energy matches the bright, bustling streets.",
            "Another chore done — the village flourishes around them.",
            "Cheerful chatter and music fill the square as work concludes.",
            "{character} twirls their tools like a practiced hand; the village thrives.",
            "Sunlight sparkles on clean streets; the work was quick and easy.",
            "Every finished task feels like a festival of progress.",
            "{character} smiles broadly, the town alive with energy.",
            "With the village in high spirits, even small tasks are a joy.",
        ],
        "sleep": [
            "{character} wakes energized; the village brims with life.",
            "A deep, satisfying sleep fuels a bustling day.",
            "{character} stretches with a grin; the streets sparkle with activity.",
            "Rest complete; the village feels almost joyful.",
            "{character} rises, ready to join the thriving rhythm.",
            "Sleep was refreshing; energy hums in every corner.",
            "Morning comes bright; the village radiates abundance.",
            "{character} wakes invigorated; the day is full of possibility.",
            "A good night's sleep; the village sings with vitality.",
            "{character} feels unstoppable; life pulses around them.",
        ],
        "meal": [
            "{character} feasts with satisfaction; the village feels vibrant.",
            "Dinner is delicious; energy radiates through the streets.",
            "{character} eats heartily, sharing in the village's thriving mood.",
            "Meal finished; joy buzzes quietly in every corner.",
            "{character} smiles at a plentiful supper, the village humming along.",
            "Food eaten, spirits high; the day is alive.",
            "A hearty meal fuels {character} and the lively streets.",
            "Dinner is done; abundance surrounds every action.",
            "{character} enjoys each bite, confident in the village's vitality.",
            "Meal complete; life in the village feels electric.",
        ],
    },
}


def generate_phrase(state, activity_type, character):
    state_key = (state or "").lower()
    state_block = PHRASES.get(state_key)

    if not state_block:
        return f"{character.name} completes a task."

    activity_phrases = state_block.get(activity_type)

    # Optional: fallback to a generic activity phrase
    if not activity_phrases:
        activity_phrases = state_block.get("work") or []
        if not activity_phrases:
            return f"{character.name} completes a task."

    template = random.choice(activity_phrases)

    return template.format(character=character.first_name)
