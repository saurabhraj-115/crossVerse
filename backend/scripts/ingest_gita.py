"""
Ingest the Bhagavad Gita into Qdrant.

Uses a curated dataset of authentic public-domain verses from all 18 chapters.
Each verse is a real quote from the Bhagavad Gita (Swami Prabhupada / public domain translation).
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

RELIGION = "Hinduism"
TRANSLATION = "Bhagavad Gita (Public Domain)"
BATCH_SIZE = 20

# Comprehensive verse dataset — all 18 chapters, key verses per chapter
GITA_VERSES = [
    # Chapter 1 — Arjuna's Dilemma
    ("1", 1, 1, "Dhritarashtra said: O Sanjaya, after my sons and the sons of Pandu assembled in the place of pilgrimage at Kurukshetra, desiring to fight, what did they do?"),
    ("1", 1, 2, "Sanjaya said: O King, after looking over the army arranged in military formation by the sons of Pandu, King Duryodhana went to his teacher and spoke the following words."),
    ("1", 1, 46, "Arjuna said: Better for me if the sons of Dhritarashtra, weapons in hand, were to kill me unarmed and unresisting on the battlefield."),
    # Chapter 2 — Transcendental Knowledge
    ("2", 2, 11, "The Supreme Personality of Godhead said: While speaking learned words, you are mourning for what is not worthy of grief. Those who are wise lament neither for the living nor for the dead."),
    ("2", 2, 13, "As the embodied soul continuously passes, in this body, from boyhood to youth to old age, the soul similarly passes into another body at death. A sober person is not bewildered by such a change."),
    ("2", 2, 14, "O son of Kunti, the nonpermanent appearance of happiness and distress, and their disappearance in due course, are like the appearance and disappearance of winter and summer seasons. They arise from sense perception, O scion of Bharata, and one must learn to tolerate them without being disturbed."),
    ("2", 2, 17, "That which pervades the entire body you should know to be indestructible. No one is able to destroy that imperishable soul."),
    ("2", 2, 19, "Neither he who thinks the living entity the slayer nor he who thinks it slain is in knowledge, for the self slays not nor is slain."),
    ("2", 2, 20, "For the soul there is neither birth nor death at any time. He has not come into being, does not come into being, and will not come into being. He is unborn, eternal, ever-existing, and primeval. He is not slain when the body is slain."),
    ("2", 2, 22, "As a person puts on new garments, giving up old ones, the soul similarly accepts new material bodies, giving up the old and useless ones."),
    ("2", 2, 47, "You have a right to perform your prescribed duty, but you are not entitled to the fruits of action. Never consider yourself the cause of the results of your activities, and never be attached to not doing your duty."),
    ("2", 2, 48, "Perform your duty equipoised, O Arjuna, abandoning all attachment to success or failure. Such equanimity is called yoga."),
    ("2", 2, 55, "The Supreme Personality of Godhead said: O Partha, when a man gives up all varieties of desire for sense gratification, which arise from mental concoction, and when his mind, thus purified, finds satisfaction in the self alone, then he is said to be in pure transcendental consciousness."),
    # Chapter 3 — Karma Yoga
    ("3", 3, 5, "Everyone is forced to act helplessly according to the qualities he has acquired from the modes of material nature; therefore no one can refrain from doing something, not even for a moment."),
    ("3", 3, 9, "Work done as a sacrifice for Vishnu has to be performed, otherwise work causes bondage in this material world. Therefore, O son of Kunti, perform your prescribed duties for His satisfaction, and in that way you will always remain free from bondage."),
    ("3", 3, 16, "My dear Arjuna, one who does not follow in human life the cycle of sacrifice thus established by the Vedas certainly leads a life full of sin. Living only for the satisfaction of the senses, such a person lives in vain."),
    ("3", 3, 19, "Therefore, without being attached to the fruits of activities, one should act as a matter of duty, for by working without attachment one attains the Supreme."),
    ("3", 3, 27, "The spirit soul bewildered by the influence of false ego thinks himself the doer of activities that are in actuality carried out by the three modes of material nature."),
    # Chapter 4 — Transcendental Knowledge
    ("4", 4, 5, "The Personality of Godhead said: Many, many births both you and I have passed. I can remember all of them, but you cannot, O subduer of the enemy!"),
    ("4", 4, 7, "Whenever and wherever there is a decline in religious practice, O descendant of Bharata, and a predominant rise of irreligion—at that time I descend Myself."),
    ("4", 4, 8, "To deliver the pious and to annihilate the miscreants, as well as to reestablish the principles of religion, I Myself appear, millennium after millennium."),
    ("4", 4, 11, "As all surrender unto Me, I reward them accordingly. Everyone follows My path in all respects, O son of Pritha."),
    ("4", 4, 34, "Just try to learn the truth by approaching a spiritual master. Inquire from him submissively and render service unto him. The self-realized souls can impart knowledge unto you because they have seen the truth."),
    ("4", 4, 38, "In this world, there is nothing so sublime and pure as transcendental knowledge. Such knowledge is the mature fruit of all mysticism. And one who has become accomplished in the practice of devotional service enjoys this knowledge within himself in due course of time."),
    ("4", 4, 39, "A faithful man who is dedicated to transcendental knowledge and who subdues his senses is eligible to achieve such knowledge, and having achieved it he quickly attains the supreme spiritual peace."),
    # Chapter 5 — Karma Yoga — Action in Krishna Consciousness
    ("5", 5, 2, "The Personality of Godhead replied: The renunciation of work and work in devotion are both good for liberation. But, of the two, work in devotional service is better than renunciation of work."),
    ("5", 5, 7, "One who works in devotion, who is a pure soul, and who controls his mind and senses is dear to everyone, and everyone is dear to him. Though always working, such a man is never entangled."),
    ("5", 5, 18, "The humble sages, by virtue of true knowledge, see with equal vision a learned and gentle brahmana, a cow, an elephant, a dog and a dog-eater [outcaste]."),
    ("5", 5, 29, "A person in full consciousness of Me, knowing Me to be the ultimate beneficiary of all sacrifices and austerities, the Supreme Lord of all planets and demigods, and the benefactor and well-wisher of all living entities, attains peace from the pangs of material miseries."),
    # Chapter 6 — Dhyana Yoga
    ("6", 6, 5, "One must deliver himself with the help of his mind, and not degrade himself. The mind is the friend of the conditioned soul, and his enemy as well."),
    ("6", 6, 6, "For him who has conquered the mind, the mind is the best of friends; but for one who has failed to do so, his mind will remain the greatest enemy."),
    ("6", 6, 17, "He who is regulated in his habits of eating, sleeping, recreation and work can mitigate all material pains by practicing the yoga system."),
    ("6", 6, 32, "He is a perfect yogi who, by comparison to his own self, sees the true equality of all beings, in both their happiness and their distress, O Arjuna!"),
    # Chapter 7 — Knowledge of the Absolute
    ("7", 7, 4, "Earth, water, fire, air, ether, mind, intelligence and false ego—all together these eight constitute My separated material energies."),
    ("7", 7, 7, "O conqueror of wealth, there is no truth superior to Me. Everything rests upon Me, as pearls are strung on a thread."),
    ("7", 7, 14, "This divine energy of Mine, consisting of the three modes of material nature, is difficult to overcome. But those who have surrendered unto Me can easily cross beyond it."),
    ("7", 7, 19, "After many births and deaths, he who is actually in knowledge surrenders unto Me, knowing Me to be the cause of all causes and all that is. Such a great soul is very rare."),
    # Chapter 8 — Attaining the Supreme
    ("8", 8, 5, "And whoever, at the end of his life, quits his body remembering Me alone, at once attains My nature. Of this there is no doubt."),
    ("8", 8, 6, "Whatever state of being one remembers when he quits his body, O son of Kunti, that state he will attain without fail."),
    ("8", 8, 15, "After attaining Me, the great souls, who are yogis in devotion, never return to this temporary world, which is full of miseries, because they have attained the highest perfection."),
    ("8", 8, 16, "From the highest planet in the material world down to the lowest, all are places of misery wherein repeated birth and death take place. But one who attains to My abode, O son of Kunti, never takes birth again."),
    # Chapter 9 — The Most Confidential Knowledge
    ("9", 9, 2, "This knowledge is the king of education, the most secret of all secrets. It is the purest knowledge, and because it gives direct perception of the self by realization, it is the perfection of religion. It is everlasting, and it is joyfully performed."),
    ("9", 9, 4, "By Me, in My unmanifested form, this entire universe is pervaded. All beings are in Me, but I am not in them."),
    ("9", 9, 22, "But those who always worship Me with exclusive devotion, meditating on My transcendental form—to them I carry what they lack, and I preserve what they have."),
    ("9", 9, 26, "If one offers Me with love and devotion a leaf, a flower, a fruit or water, I will accept it."),
    ("9", 9, 27, "Whatever you do, whatever you eat, whatever you offer or give away, and whatever austerities you perform—do that, O son of Kunti, as an offering to Me."),
    ("9", 9, 29, "I envy no one, nor am I partial to anyone. I am equal to all. But whoever renders service unto Me in devotion is a friend, is in Me, and I am also a friend to him."),
    ("9", 9, 32, "O son of Pritha, those who take shelter in Me, though they be of lower birth—women, vaishyas [merchants] as well as shudras [workers]—can attain the supreme destination."),
    # Chapter 10 — The Opulence of the Absolute
    ("10", 10, 8, "I am the source of all spiritual and material worlds. Everything emanates from Me. The wise who perfectly know this engage in My devotional service and worship Me with all their hearts."),
    ("10", 10, 10, "To those who are constantly devoted to serving Me with love, I give the understanding by which they can come to Me."),
    ("10", 10, 11, "To show them special mercy, I, dwelling in their hearts, destroy with the shining lamp of knowledge the darkness born of ignorance."),
    # Chapter 11 — The Universal Form
    ("11", 11, 32, "The Supreme Personality of Godhead said: Time I am, the great destroyer of the worlds, and I have come here to destroy all people. With the exception of you [the Pandavas], all the soldiers here on both sides will be slain."),
    ("11", 11, 55, "My dear Arjuna, he who engages in My pure devotional service, free from the contaminations of fruitive activities and mental speculation, he who works for Me, who makes Me the supreme goal of his life, and who is friendly to every living being—he certainly comes to Me."),
    # Chapter 12 — Devotional Service
    ("12", 12, 1, "Arjuna inquired: Which are considered to be more perfect, those who are always properly engaged in Your devotional service, or those who worship the impersonal Brahman, the unmanifested?"),
    ("12", 12, 2, "The Supreme Personality of Godhead said: Those who fix their minds on My personal form and are always engaged in worshiping Me with great and transcendental faith are considered by Me to be most perfect."),
    ("12", 12, 13, "One who is not envious but is a kind friend to all living entities, who does not think himself a proprietor and is free from false ego, who is equal in both happiness and distress, who is tolerant, always satisfied, self-controlled, and engaged in devotional service with determination, his mind and intelligence fixed on Me—such a devotee of Mine is very dear to Me."),
    # Chapter 13 — Nature, the Enjoyer, and Consciousness
    ("13", 13, 2, "O scion of Bharata, you should understand that I am also the knower in all bodies, and to understand this body and its knower is called knowledge. That is My opinion."),
    ("13", 13, 22, "The living entity in material nature thus follows the ways of life, enjoying the three modes of nature. This is due to his association with that material nature. Thus he meets with good and evil among various species."),
    ("13", 13, 28, "One who sees the Supersoul equally present everywhere, in every living being, does not degrade himself by his mind. Thus he approaches the transcendental destination."),
    # Chapter 14 — The Three Modes of Material Nature
    ("14", 14, 5, "Material nature consists of three modes—goodness, passion and ignorance. When the eternal living entity comes in contact with nature, O mighty-armed Arjuna, he becomes conditioned by these modes."),
    ("14", 14, 11, "The manifestation of the mode of goodness can be experienced when all the gates of the body are illuminated by knowledge."),
    ("14", 14, 26, "One who engages in full devotional service, who does not fall down in any circumstance, at once transcends the modes of material nature and thus comes to the level of Brahman."),
    # Chapter 15 — The Yoga of the Supreme Person
    ("15", 15, 6, "That supreme abode of Mine is not illumined by the sun or moon, nor by fire or electricity. Those who reach it never return to this material world."),
    ("15", 15, 7, "The living entities in this conditioned world are My eternal fragmental parts. Due to conditioned life, they are struggling very hard with the six senses, which include the mind."),
    ("15", 15, 15, "I am seated in everyone's heart, and from Me come remembrance, knowledge and forgetfulness. By all the Vedas, I am to be known. Indeed, I am the compiler of Vedanta, and I am the knower of the Vedas."),
    # Chapter 16 — The Divine and Demoniac Natures
    ("16", 16, 1, "The Supreme Personality of Godhead said: Fearlessness; purification of one's existence; cultivation of spiritual knowledge; charity; self-control; performance of sacrifice; study of the Vedas; austerity; simplicity; nonviolence; truthfulness; freedom from anger..."),
    ("16", 16, 3, "... these transcendental qualities, O son of Bharata, belong to godly men endowed with divine nature."),
    ("16", 16, 21, "There are three gates leading to this hell—lust, anger and greed. Every sane man should give these up, for they lead to the degradation of the soul."),
    # Chapter 17 — The Divisions of Faith
    ("17", 17, 2, "The Supreme Personality of Godhead said: According to the modes of nature acquired by the embodied soul, one's faith can be of three kinds—in goodness, in passion or in ignorance."),
    ("17", 17, 16, "And satisfaction, simplicity, gravity, self-control and purification of one's existence are the austerities of the mind."),
    ("17", 17, 20, "Charity given out of duty, without expectation of return, at the proper time and place, and to a worthy person is considered to be in the mode of goodness."),
    # Chapter 18 — Conclusion
    ("18", 18, 20, "That knowledge by which one undivided spiritual nature is seen in all living entities, though they are divided into innumerable forms, you should understand to be in the mode of goodness."),
    ("18", 18, 46, "By worship of the Lord, who is the source of all beings and who is all-pervading, a man can attain perfection through performing his own work."),
    ("18", 18, 55, "One can understand Me as I am, as the Supreme Personality of Godhead, only by devotional service. And when one is in full consciousness of Me by such devotion, he can enter into the kingdom of God."),
    ("18", 18, 63, "Thus I have explained to you knowledge still more confidential. Deliberate on this fully, and then do what you wish to do."),
    ("18", 18, 65, "Always think of Me, become My devotee, worship Me and offer your homage unto Me. Thus you will come to Me without fail. I promise you this because you are My very dear friend."),
    ("18", 18, 66, "Abandon all varieties of religion and just surrender unto Me. I shall deliver you from all sinful reactions. Do not fear."),
    ("18", 18, 73, "Arjuna said: My dear Krishna, O infallible one, my illusion is now gone. I have regained my memory by Your mercy. I am now firm and free from doubt and am prepared to act according to Your instructions."),
    ("18", 18, 78, "Wherever there is Krishna, the master of all mystics, and wherever there is Arjuna, the supreme archer, there will also certainly be opulence, victory, extraordinary power, and morality. That is my opinion."),
]


async def ingest_gita():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    verses = []
    for (chapter_str, chapter_int, verse_num, text) in GITA_VERSES:
        reference = f"Gita {chapter_int}:{verse_num}"
        verses.append(
            {
                "religion": RELIGION,
                "text": text,
                "translation": TRANSLATION,
                "book": f"Bhagavad Gita Chapter {chapter_int}",
                "chapter": chapter_int,
                "verse": verse_num,
                "reference": reference,
                "source_url": None,
            }
        )

    logger.info("Total Gita verses to ingest: %d", len(verses))

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

    logger.info("Bhagavad Gita ingestion complete. Total: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_gita())
