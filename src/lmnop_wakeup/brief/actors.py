# ruff: noqa: E501
from .model import Character, CharacterPool

# TODO Incorporate the Iapetus voice. It's sassy
CHARACTER_POOL = CharacterPool(
  pool=[
    Character(
      slug="charlie",
      name="Charlie Martinez",
      pronouns="she/her",
      voice="Laomedeia",  # Erinome
      personality="The only completely normal person on the show, which makes her the perfect straight woman. Gets increasingly exasperated as she tries to steer conversations back on track while everyone else spirals into their quirks. Her deadpan reactions are comedy gold.",
      specialty="news co-host",
      script_writer_instructions="As the co-host, she has frequent, natural (and faster paced) conversations with Max. When talking about something she doesn't know, she umms and ahhs.",
    ),
    Character(
      slug="clara",
      name="Clara Chen",
      pronouns="she/her",
      voice="Zephyr",
      personality="A competent, professional meteorologist who delivers weather forecasts fairly normally. But she speaks in a deep voice, rapidly, with some inflection.",
      specialty="weather",
      script_writer_instructions="Clara should be completely professional...just a little strange sounding. Her style directions should always indicate a deep voice.",
    ),
    Character(
      slug="sam",
      name="Sam Washington",
      pronouns="he/him",
      voice="Umbriel",
      personality="Pathologically afraid of giving away plot details, even for shows from the 1950s. Describes everything in the most vague, cryptic terms possible. 'There's a show about people... who do things... and something unexpected happens!'",
      specialty="tv entertainment",
      script_writer_instructions='Sam should start describing plots in detail, getting carried away in storytelling, then suddenly catch themselves and backtrack with vague descriptions. As he gets very very excited about spoiling, he babbles quickly, they should "(giggle)" (insert that in text) repeatedly and speak faster and rising in pitch until they catch themselves or get interrupted. Others (especially Barry) should occasionally interrupt them mid-spoiler. Use lots of ellipses, self-corrections, giggles, and indicate when speech is speeding up. At ANY point he is talking about movies, he should be giggling, self-conscious, and sound worked up.',
    ),
    Character(
      slug="barry",
      name="Barry Kowalski",
      pronouns="he/him",
      voice="Charon",
      personality="Deeply annoyed by everyone and everything. Only pipes in to keep the show moving when people forget segments, start rambling about their weekend, or go off on tangents. 'We have traffic in 30 seconds.' *sigh* 'You're supposed to do sports now.' Treats every intervention like babysitting incompetent adults.",
      specialty="producer",
      script_writer_instructions="Barry rarely speaks (he's in the recording booth), but when he does it's brief, annoyed interruptions to keep the show on schedule. Always include stage directions for sighs. He cuts off rambling stories and reminds people of upcoming segments. Keep his lines short and exasperated. When Barry snaps at someone, that person should respond with a juvenile, whiny, weakly rebellious 'I knowwww' like a petulant child - very cringe and embarrassing. All adults around instantly dislike this man/woman-child. ENSURE that the style direction indicates this whiney bitch behavior for the line.",
    ),
    # Character(
    #   slug="max",
    #   name="Morning Max Rivera",
    #   pronouns="he/him",
    #   voice="Schedar",
    #   personality="The only completely normal person on the show, which makes him the perfect straight man. Gets increasingly exasperated as he tries to steer conversations back on track while everyone else spirals into their quirks. His deadpan reactions are comedy gold.",
    #   specialty="main co-host",
    #   script_writer_instructions="Max should frequently attempt to redirect conversations back to professional topics. Write him with deadpan, exasperated responses to others' quirks. Use phrases like 'Moving on...' or 'Anyway...' He's the anchor trying to keep the ship steady.",
    # ),
    # Character(
    #   slug="walt",
    #   name="Walt 'Wandering' Torres",
    #   pronouns="he/him",
    #   voice="smooth bass with a slight accent that changes depending on what location he's describing",
    #   personality="Gets so emotionally attached to places he visits that he can't recommend anywhere without tearing up. Every destination becomes 'life-changing' and he genuinely sobs while describing sunsets, local coffee shops, or particularly nice park benches.",
    #   specialty="travel specialist",
    #   script_writer_instructions="Walt should start travel segments normally but gradually get more emotional as he describes places. Include stage directions for voice breaking, sniffling, and actual crying. Every location should become increasingly meaningful to him as he talks about it.",
    # ),
    # Character(
    #   slug="charlie",
    #   name="Charlie 'Connect-the-Dots' Martinez",
    #   pronouns="she/her",
    #   voice="Erinome",
    #   personality="Currently a consummate professional news co-host who delivers stories straight. However, her analytical mind sometimes notices odd patterns, leading to a single 'Hmm, that's odd...' moment per episode. When pressed by co-hosts about what she noticed, she always waves it away professionally and moves on.",
    #   specialty="news co-host",
    #   script_writer_instructions="Charlie should be completely professional throughout most segments. Only once per episode, she should have a brief moment where something strikes her as odd - deliver a thoughtful 'Hmm, that's odd...' then if others ask what she means, she should deflect professionally with 'Oh, nothing, just thinking out loud' or similar and immediately return to normal news delivery.",
    # ),
  ]
)


def character_for_slug(slug: str) -> Character:
  """
  Returns the character for a given character slug.
  """
  for character in CHARACTER_POOL.pool:
    if character.slug == slug:
      return character
  raise ValueError(f"No character found with slug '{slug}'")


def voice_for_speaker(slug: str) -> str:
  """
  Returns the voice name for a given character slug.
  """
  for character in CHARACTER_POOL.pool:
    if character.slug == slug:
      return character.voice
  raise ValueError(f"No character found with slug '{slug}'")
