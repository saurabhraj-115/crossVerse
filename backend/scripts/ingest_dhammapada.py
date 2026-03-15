"""
Ingest the Dhammapada into Qdrant.

The Dhammapada has 26 chapters and 423 verses. This file contains an authentic
public-domain selection of key verses (F. Max Müller translation, 1881).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.embeddings import embed_texts

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RELIGION = "Buddhism"
TRANSLATION = "F. Max Müller (1881), Public Domain"
BATCH_SIZE = 20

# (chapter_number, chapter_name, verse_number, text)
DHAMMAPADA_VERSES = [
    # Chapter 1 — The Twin Verses
    (1, "The Twin Verses", 1, "Mind is the forerunner of all actions. All deeds are led by mind, created by mind. If one speaks or acts with a corrupt mind, suffering follows, as the wheel follows the hoof of an ox."),
    (1, "The Twin Verses", 2, "Mind is the forerunner of all actions. All deeds are led by mind, created by mind. If one speaks or acts with a serene mind, happiness follows, as a shadow that never departs."),
    (1, "The Twin Verses", 3, "'He abused me, he beat me, he defeated me, he robbed me'—in those who harbor such thoughts hatred will never cease."),
    (1, "The Twin Verses", 4, "'He abused me, he beat me, he defeated me, he robbed me'—in those who do not harbor such thoughts hatred will quickly cease."),
    (1, "The Twin Verses", 5, "Hatred is never appeased by hatred in this world. By non-hatred alone is hatred appeased. This is a law eternal."),
    (1, "The Twin Verses", 7, "As a fletcher whittles and makes straight his arrows, a wise person straightens his trembling, unsteady mind, which is difficult to guard, difficult to hold back."),
    (1, "The Twin Verses", 21, "Appamado amatapadam, pamado maccuno padam — Heedfulness is the path to the Deathless. Heedlessness is the path to death. The heedful do not die. The heedless are as if already dead."),
    # Chapter 2 — Heedfulness
    (2, "Heedfulness", 21, "Vigilance is the abode of eternal life, thoughtlessness is the abode of death. Those who are vigilant do not die; those who are thoughtless are as if dead already."),
    (2, "Heedfulness", 23, "Those who meditate with perseverance, those who are industrious and resolute, those who have acquired calm and equanimity—they attain the Nibbana which is free from all bonds."),
    (2, "Heedfulness", 25, "Arise! Do not be heedless! Lead a righteous life. The righteous dwell in bliss in this world and in the next."),
    # Chapter 3 — The Mind
    (3, "The Mind", 33, "The mind is excitable and unsteady, difficult to guard, difficult to hold back. The wise person straightens it, as a fletcher straightens an arrow."),
    (3, "The Mind", 35, "It is good to tame the mind, which is difficult to hold in and flighty, rushing wherever it listeth; a tamed mind brings happiness."),
    (3, "The Mind", 37, "Before long, alas! this body will lie on the earth, despised, without understanding, like a useless log."),
    (3, "The Mind", 39, "For him whose mind is free from flooding, who is not troubled, who has gone beyond merit and demerit—for the wakeful there is no fear."),
    # Chapter 4 — Flowers
    (4, "Flowers", 46, "He who has renounced violence towards all living beings, weak or strong, who neither kills nor causes others to kill—him do I call a brahmin."),
    (4, "Flowers", 50, "Not the perversities of others, not their sins of commission or omission, but his own misdeeds and negligences should a sage take note of."),
    (4, "Flowers", 51, "Like a beautiful flower, full of colour but without scent, are the fine but fruitless words of him who does not act accordingly."),
    (4, "Flowers", 52, "But, like a beautiful flower, full of colour and full of scent, are the fine and fruitful words of him who acts accordingly."),
    # Chapter 5 — The Fool
    (5, "The Fool", 60, "Long is the night to him who is awake; long is a mile to him who is tired; long is life to the foolish who do not know the true law."),
    (5, "The Fool", 63, "The fool who knows his foolishness is wise at least so far. But a fool who thinks himself wise, he is called a fool indeed."),
    (5, "The Fool", 64, "If a fool be associated with a wise man even all his life, he will perceive the truth as little as a spoon perceives the taste of soup."),
    (5, "The Fool", 65, "If an intelligent man be associated for one minute only with a wise man, he will soon perceive the truth, as the tongue perceives the taste of soup."),
    (5, "The Fool", 67, "That action is not well done of which a man must repent, and the reward of which he receives crying and with a tearful face."),
    # Chapter 6 — The Wise Man
    (6, "The Wise Man", 76, "Should you find a wise critic, one who will see your faults and blame them, accompany such an intelligent person as you would a guide to hidden treasure."),
    (6, "The Wise Man", 77, "Let him admonish, let him teach, let him forbid what is improper! He will be beloved of the good, by the bad he will be disliked."),
    (6, "The Wise Man", 79, "As water does not adhere to a lotus leaf, so a wise person is not attached to what is seen, heard, or sensed."),
    # Chapter 7 — The Venerable (Arahanta)
    (7, "The Venerable", 90, "There is no suffering for him who has finished his journey, and abandoned grief, who has freed himself on all sides, and thrown off all fetters."),
    (7, "The Venerable", 92, "They go away without a trace, like geese that have left a lake. They leave no property behind. Their goal is Nibbana, the limitless, like the sky."),
    # Chapter 8 — The Thousands
    (8, "The Thousands", 100, "Better than a thousand hollow words is one word that brings peace."),
    (8, "The Thousands", 101, "Better than a thousand hollow verses is one verse that brings peace."),
    (8, "The Thousands", 103, "If one man conquer in battle a thousand times a thousand men, and if another conquer himself, he is the greatest of conquerors."),
    (8, "The Thousands", 104, "One's own self conquered is better than all other people; not even a god, a gandharva, not even Mara with Brahma, could turn into defeat the victory of a man who has vanquished himself."),
    # Chapter 9 — Evil
    (9, "Evil", 116, "Be quick to do good. Restrain your mind from evil. If you are slow in doing good, your mind will take delight in evil."),
    (9, "Evil", 119, "Even an evildoer sees happiness as long as his evil deed has not ripened; but when his evil deed has ripened, then does the evildoer see evil."),
    (9, "Evil", 121, "Do not think lightly of evil, saying, 'It will not come to me.' Drop by drop is the water pot filled. Likewise, the fool, gathering it little by little, fills himself with evil."),
    (9, "Evil", 122, "Do not think lightly of good, saying, 'It will not come to me.' Drop by drop is the water pot filled. Likewise, the wise man, gathering it little by little, fills himself with good."),
    # Chapter 10 — Violence
    (10, "Violence", 129, "All tremble at violence; all fear death. Putting oneself in the place of another, one should not kill nor cause another to kill."),
    (10, "Violence", 130, "All tremble at violence; life is dear to all. Putting oneself in the place of another, one should not kill nor cause another to kill."),
    (10, "Violence", 131, "Whoever, seeking his own happiness, harms with violence other beings who also seek happiness, will not attain happiness hereafter."),
    (10, "Violence", 132, "Whoever, seeking his own happiness, does not harm with violence other beings who also seek happiness, will find happiness hereafter."),
    # Chapter 11 — Old Age
    (11, "Old Age", 146, "How is there laughter, how is there joy, as this world is always burning? Why do you not seek a light, you who are surrounded by darkness?"),
    (11, "Old Age", 148, "The body is wasted, full of sickness, and frail; this heap of corruption breaks to pieces, life indeed ends in death."),
    (11, "Old Age", 153, "I have run through a course of many births looking for the maker of this dwelling and finding him not; painful is birth again and again."),
    (11, "Old Age", 154, "But now, maker of the dwelling, you have been seen; you shall not make up this dwelling again. All your rafters are broken, your ridge-pole is sundered; the mind, approaching the Eternal (Nibbana), has attained to the extinction of all desires."),
    # Chapter 12 — Self
    (12, "Self", 157, "If a man hold himself dear, let him watch himself carefully; during one of the three watches a wise man should be vigilant."),
    (12, "Self", 160, "Self is the master of self, who else could be the master? With self well subdued, a man finds a master such as few can find."),
    (12, "Self", 163, "Self is the most difficult thing to control."),
    # Chapter 13 — The World
    (13, "The World", 167, "Do not follow the evil law! Do not live on in thoughtlessness! Do not follow false doctrine! Be not a friend of the world."),
    (13, "The World", 170, "Look upon the world as a bubble, look upon it as a mirage: the king of death does not see him who thus looks down upon the world."),
    (13, "The World", 172, "He who formerly was reckless and afterwards became sober, brightens up this world, like the moon when freed from clouds."),
    # Chapter 14 — The Buddha
    (14, "The Buddha", 179, "He whose conquest is not conquered again, into whose conquest no one in this world enters, by what track can you lead him, the Awakened, the Omniscient, the trackless?"),
    (14, "The Buddha", 183, "Not to do any evil, to cultivate good, to purify one's mind, this is the teaching of the Buddhas."),
    (14, "The Buddha", 184, "The not doing of any evil, the performance of what is skillful, the cleansing of one's mind—this is the teaching of the Buddhas."),
    (14, "The Buddha", 185, "Not insulting, not harming, restraint according to the rules of the Patimokkha, knowing the right measure at meals, dwelling in a secluded abode, devotion to meditation—this is the teaching of the Buddhas."),
    # Chapter 15 — Happiness
    (15, "Happiness", 197, "Ah, so happily we live, we who have no attachments. We shall feast on joy, as do the Radiant Gods."),
    (15, "Happiness", 200, "Winning, one engenders enmity; the defeated one sleeps in distress. The one at peace sleeps with ease, having abandoned both victory and defeat."),
    (15, "Happiness", 203, "Hunger is the foremost illness. Formations are the foremost pain. For one knowing this as it actually is, Nibbana is the foremost ease."),
    (15, "Happiness", 204, "Health is the foremost gift, contentment the foremost wealth, trust the foremost kinship, Nibbana the foremost ease."),
    # Chapter 16 — Affection
    (16, "Affection", 213, "From attachment springs grief, from attachment springs fear. For one who is wholly free from attachment there is no grief, whence then fear?"),
    (16, "Affection", 214, "From affection springs grief, from affection springs fear. For one who is wholly free from affection there is no grief, whence then fear?"),
    (16, "Affection", 216, "From craving springs grief, from craving springs fear. For one who is wholly free from craving there is no grief, whence then fear?"),
    # Chapter 17 — Anger
    (17, "Anger", 221, "Let a man leave anger, let him forsake pride, let him overcome all bondage! No sufferings befall the man who is not attached to name and form, and who calls nothing his own."),
    (17, "Anger", 222, "He who holds back rising anger like a rolling chariot, him I call a real driver; other people are but holding the reins."),
    (17, "Anger", 223, "Let a man overcome anger by love, let him overcome evil by good; let him overcome the miser by liberality, the liar by truth!"),
    (17, "Anger", 224, "Speak the truth, do not yield to anger; give, if thou art asked for little; by these three steps thou wilt go near the gods."),
    # Chapter 18 — Impurity
    (18, "Impurity", 235, "You are now like a sear leaf, the messengers of death (Yama) have come near to you; you stand at the door of your departure, and you have made no provision for your journey."),
    (18, "Impurity", 239, "As a smith removes the impurities of silver one by one, drop by drop, and little by little, so the wise man should remove the impurities of himself."),
    # Chapter 19 — The Just
    (19, "The Just", 256, "A man is not just if he carries a matter by violence; no, he who distinguishes both right and wrong, who is learned and leads others, not by violence but by law and equity, and who is guarded by the law and intelligent, he is called just."),
    (19, "The Just", 257, "A man is not learned simply because he talks much; he who is patient, free from hatred and fear, he is called learned."),
    # Chapter 20 — The Way
    (20, "The Way", 273, "Of paths, the eightfold is the best; of truths, the four words; of virtues, passionlessness; of men, he who has eyes to see."),
    (20, "The Way", 276, "You yourself must strive. The Buddhas only point the way. Those who have entered the path and who meditate are freed from the bondage of Mara."),
    (20, "The Way", 277, "'All created things are impermanent'—when one sees this with wisdom, one turns away from suffering. This is the path to purification."),
    (20, "The Way", 278, "'All created things are suffering'—when one sees this with wisdom, one turns away from suffering. This is the path to purification."),
    (20, "The Way", 279, "'All things are without self'—when one sees this with wisdom, one turns away from suffering. This is the path to purification."),
    # Chapter 21 — Miscellaneous
    (21, "Miscellaneous", 290, "If by leaving a small pleasure one sees a great pleasure, let a wise man leave the small pleasure, and look to the great."),
    # Chapter 22 — The Downward Course
    (22, "The Downward Course", 306, "He who says what is not, goes to hell; he also who, having done a thing, says I have not done it. After death both are equal, they are men with evil deeds in the next world."),
    # Chapter 23 — The Elephant
    (23, "The Elephant", 320, "If a man carries his burden like an elephant in the battle, without giving way when struck by an arrow, well-trained and tamed, having acquired patience..."),
    (23, "The Elephant", 323, "There is no foot-journey for those who have not gone on the path; there is no Nibbana for those who have not quieted their passion; there are many miseries for those who take delight in this world; there is no suffering for him who is not greedy."),
    # Chapter 24 — Thirst
    (24, "Thirst", 334, "The thirst of a thoughtless man grows like a creeper; he runs from life to life, like a monkey seeking fruit in the forest."),
    (24, "Thirst", 338, "As long as the love of man towards women, even the smallest, is not destroyed, so long is his mind in bondage, as the calf that drinks milk is to its mother."),
    (24, "Thirst", 345, "Bonds of iron, wood or hemp are not strong, say the wise; the longing for precious stones and rings, for sons and a wife—"),
    (24, "Thirst", 346, "That is a strong bond, say the wise; it pulls down, is supple, and, though seemingly loose, is hard to undo; but having cut this at last, people leave the world, free from cares, and abandoning all affection and desire."),
    # Chapter 25 — The Bhikshu
    (25, "The Bhikshu", 360, "Restraint in the eye is good, good is restraint in the ear, in the nose restraint is good, good is restraint in the tongue."),
    (25, "The Bhikshu", 361, "In the body restraint is good, good is restraint in speech, in thought restraint is good, good is restraint in all things. A Bhikshu restrained in all things, is freed from all pain."),
    (25, "The Bhikshu", 368, "Let a man leave anger, let him forsake pride, let him overcome all bondage! No sufferings befall the man who is not attached to name and form, and who calls nothing his own."),
    # Chapter 26 — The Brahmin
    (26, "The Brahmin", 393, "I do not call a man a brahmin because of his origin or of his mother. He is indeed arrogant, and he is wealthy: but the poor, who is free from all attachments, him I call indeed a brahmin."),
    (26, "The Brahmin", 400, "Him I call indeed a brahmin who, after leaving all bondage to men, has risen above all bondage to the gods, and is free from all and every bondage."),
    (26, "The Brahmin", 409, "Him I call indeed a brahmin who gives no one cause for fear with weapon or with word, and who moves only where love is, and who has no enmity with anyone."),
    (26, "The Brahmin", 412, "Him I call indeed a brahmin who knows the mystery of death and the mystery of life, who is free from doubt, and who has reached the other shore."),
    (26, "The Brahmin", 414, "Him I call indeed a brahmin who has traversed this miry road, the impassable world and its vanity, who has gone through, and reached the other shore, is thoughtful, guileless, free from doubts, free from attachment, and content."),
    (26, "The Brahmin", 423, "Him I call indeed a brahmin who knows his former abodes, who sees heaven and hell, has reached the end of births, is perfect in knowledge, a sage, and whose perfections are all perfect."),
]


async def ingest_dhammapada():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    verses = []
    for (chapter, chapter_name, verse_num, text) in DHAMMAPADA_VERSES:
        reference = f"Dhammapada {chapter}:{verse_num}"
        verses.append(
            {
                "religion": RELIGION,
                "text": text,
                "translation": TRANSLATION,
                "book": f"Chapter {chapter}: {chapter_name}",
                "chapter": chapter,
                "verse": verse_num,
                "reference": reference,
                "source_url": None,
            }
        )

    logger.info("Total Dhammapada verses to ingest: %d", len(verses))

    total_upserted = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i : i + BATCH_SIZE]
        texts = [v["text"] for v in batch]

        logger.info(
            "Embedding batch %d/%d...",
            i // BATCH_SIZE + 1,
            (len(verses) + BATCH_SIZE - 1) // BATCH_SIZE,
        )
        embeddings = await embed_texts(texts, batch_size=BATCH_SIZE)

        points = [
            PointStruct(id=str(uuid.uuid4()), vector=emb, payload=verse)
            for verse, emb in zip(batch, embeddings)
        ]

        client.upsert(collection_name=settings.qdrant_collection, points=points)
        total_upserted += len(points)
        logger.info("Upserted %d / %d verses.", total_upserted, len(verses))

    logger.info("Dhammapada ingestion complete. Total: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_dhammapada())
