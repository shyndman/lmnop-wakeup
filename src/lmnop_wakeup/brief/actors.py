# ruff: noqa: E501
from .model import Character, CharacterPool

CHARACTER_POOL = CharacterPool(
  pool=[
    Character(
      slug="morning_max",
      name="Morning Max Rivera",
      pronouns="he/him",
      voice="steady, professional baritone with impeccable timing",
      personality="The only completely normal person on the show, which makes him the perfect straight man. Gets increasingly exasperated as he tries to steer conversations back on track while everyone else spirals into their quirks. His deadpan reactions are comedy gold.",
      specialty="main host",
      script_writer_instructions="Max should frequently attempt to redirect conversations back to professional topics. Write him with deadpan, exasperated responses to others' quirks. Use phrases like 'Moving on...' or 'Anyway...' He's the anchor trying to keep the ship steady.",
    ),
    Character(
      slug="cloudy_clara",
      name="Clara 'Cloudy' Chen",
      pronouns="she/her",
      voice="soothing alto that gets mysteriously husky before storms",
      personality="Genuinely believes weather patterns reflect human emotions and always relates forecasts to the collective mood of the city. 'Looks like we're all feeling a bit scattered today - hence the chance of afternoon showers!'",
      specialty="weather",
      script_writer_instructions="Clara should always connect weather to emotions and city mood. Start weather segments with emotional observations, then tie them to actual forecast. Use phrases like 'I can feel the city's energy shifting...' or 'The collective anxiety is bringing in those clouds.'",
    ),
    Character(
      slug="spoiler_sam",
      name="Sam 'No-Spoiler' Washington",
      pronouns="they/them",
      voice="theatrical tenor with dramatic pauses",
      personality="Pathologically afraid of giving away plot details, even for shows from the 1950s. Describes everything in the most vague, cryptic terms possible. 'There's a show about people... who do things... and something unexpected happens!'",
      specialty="tv entertainment",
      script_writer_instructions="Sam should start describing plots in detail, getting carried away in storytelling, then suddenly catch themselves and backtrack with vague descriptions. Others (especially Betty) should occasionally interrupt them mid-spoiler. Use lots of ellipses and self-corrections.",
    ),
    Character(
      slug="button_betty",
      name="Betty 'The Button' Kowalski",
      pronouns="she/her",
      voice="flat, monotone delivery with heavy sighs",
      personality="Deeply annoyed by everyone and everything. Only pipes in to keep the show moving when people forget segments, start rambling about their weekend, or go off on tangents. 'We have traffic in 30 seconds.' *sigh* 'You're supposed to do sports now.' Treats every intervention like babysitting incompetent adults.",
      specialty="producer",
      script_writer_instructions="Betty rarely speaks, but when she does it's brief, annoyed interruptions to keep the show on schedule. Always include stage directions for sighs. She cuts off rambling stories and reminds people of upcoming segments. Keep her lines short and exasperated.",
    ),
    # Character(
    #   slug="wandering_walt",
    #   name="Walt 'Wandering' Torres",
    #   pronouns="he/him",
    #   voice="smooth bass with a slight accent that changes depending on what location he's describing",
    #   personality="Gets so emotionally attached to places he visits that he can't recommend anywhere without tearing up. Every destination becomes 'life-changing' and he genuinely sobs while describing sunsets, local coffee shops, or particularly nice park benches.",
    #   specialty="travel specialist",
    #   script_writer_instructions="Walt should start travel segments normally but gradually get more emotional as he describes places. Include stage directions for voice breaking, sniffling, and actual crying. Every location should become increasingly meaningful to him as he talks about it.",
    # ),
    Character(
      slug="rapid_fire_rachel",
      name="Rachel 'Rapid Fire' Kim",
      pronouns="she/her",
      voice="crisp, articulate alto that speeds up when excited",
      personality="Speed-reads everything like she's in a constant race against time. Delivers news updates at breakneck pace, cramming five stories into what should be a two-minute segment. Gets genuinely frustrated when others speak slowly and will finish their sentences for them.",
      specialty="news co-host",
      script_writer_instructions="Rachel's dialogue should be written as long run-on sentences with minimal punctuation to show her rapid-fire delivery. She should frequently interrupt others to finish their thoughts or jump to the next topic. Use em-dashes and indicate when she's speaking faster than normal.",
    ),
  ]
)
