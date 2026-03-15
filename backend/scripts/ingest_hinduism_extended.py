"""
Ingest extended Hindu scriptures into Qdrant.

Covers four additional sacred texts:
  - Principal Upanishads (Isha, Kena, Katha, Mundaka, Mandukya, Chandogya, Brihadaranyaka)
  - Yoga Sutras of Patanjali
  - Rigveda (selected hymns)
  - Mahabharata (key verses outside the Gita)

All translations are public domain.
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
BATCH_SIZE = 20

# (book, chapter_or_section, verse, text, translation_label)
VERSES = [

    # ── UPANISHADS ────────────────────────────────────────────────────────────

    # Isha Upanishad
    ("Isha Upanishad", 1, 1,  "Isha vasyam idam sarvam — All this, whatever moves on earth, is to be enveloped by the Lord.",                                      "Isha Upanishad (Max Müller, 1884)"),
    ("Isha Upanishad", 1, 2,  "One should not covet what belongs to others. By doing work without attachment, one may hope to live a hundred years.",               "Isha Upanishad (Max Müller, 1884)"),
    ("Isha Upanishad", 1, 6,  "He who sees all beings in his own Self and his own Self in all beings loses all fear.",                                              "Isha Upanishad (Max Müller, 1884)"),
    ("Isha Upanishad", 1, 7,  "When to a man who understands, the Self has become all things, what sorrow or what trouble can there be to him who once beheld that unity?", "Isha Upanishad (Max Müller, 1884)"),
    ("Isha Upanishad", 1, 15, "The face of truth is covered with a golden disc. Unveil it, O Pushan, so that I who love the truth may see it.",                    "Isha Upanishad (Max Müller, 1884)"),
    ("Isha Upanishad", 1, 18, "O Agni, lead us on to wealth by a good path, thou who knowest all the ways. Keep far from us crooked sin, and we shall offer thee the fullest praise.", "Isha Upanishad (Max Müller, 1884)"),

    # Kena Upanishad
    ("Kena Upanishad", 1, 1,  "By whom directed does the mind fly forth? By whom commanded does the first breath move? By whom is this speech impelled?",          "Kena Upanishad (S. Radhakrishnan, Public Domain)"),
    ("Kena Upanishad", 1, 3,  "It is not known by those who know it; it is known by those who do not know it.",                                                    "Kena Upanishad (S. Radhakrishnan, Public Domain)"),
    ("Kena Upanishad", 2, 4,  "Brahman is not that which is worshipped here. Do not be satisfied with this Brahman you know — know it better in its higher form.", "Kena Upanishad (S. Radhakrishnan, Public Domain)"),

    # Katha Upanishad
    ("Katha Upanishad", 1, 20, "Yama said: This secret about the soul — the ancient one — is not easily known; it is very subtle and hard to understand. Ask some other boon, O Nachiketa, do not press me; release me from this.",  "Katha Upanishad (Public Domain)"),
    ("Katha Upanishad", 1, 27, "The self-existent Lord pierced the senses to turn outward; therefore man looks outward, not inward into himself. Some wise man, however, with his eyes closed and wishing for immortality, saw the self behind.", "Katha Upanishad (Public Domain)"),
    ("Katha Upanishad", 1, 29, "The soul is not born; it does not die. It was not produced from anyone. Unborn, eternal, it is not slain though the body is slain.",   "Katha Upanishad (Public Domain)"),
    ("Katha Upanishad", 2, 23, "The Self cannot be gained by the Veda, nor by understanding, nor by much learning. He whom the Self chooses, by him the Self can be gained.",  "Katha Upanishad (Public Domain)"),
    ("Katha Upanishad", 3, 3,  "Know the Self as the lord of a chariot, the body as the chariot, the intellect as the charioteer, and the mind as the reins.",     "Katha Upanishad (Public Domain)"),
    ("Katha Upanishad", 3, 14, "The wise man who knows the Self as bodiless within the bodies, as unchanging among changing things — he, the great, the omnipresent Self — does not grieve.", "Katha Upanishad (Public Domain)"),

    # Mundaka Upanishad
    ("Mundaka Upanishad", 1, 6,  "Two kinds of knowledge must be known: the higher and the lower. Of these, the lower is the Rig Veda, the Yajur Veda, the Sama Veda, the Atharva Veda, phonetics, ceremonial, grammar, etymology, metre, and astronomy. The higher is that by which the Indestructible Brahman is apprehended.", "Mundaka Upanishad (Public Domain)"),
    ("Mundaka Upanishad", 2, 10, "Brahman is infinite, and the universe is infinite. The infinite proceeds from the infinite. Taking the infinitude of the infinite, it remains as the infinite alone.",                                "Mundaka Upanishad (Public Domain)"),
    ("Mundaka Upanishad", 3, 9,  "He who knows Brahman becomes Brahman.",                                                                                          "Mundaka Upanishad (Public Domain)"),
    ("Mundaka Upanishad", 3, 10, "Satyam eva jayate — Truth alone triumphs, not falsehood. By truth is laid the path leading to the gods, by which the sages whose desires are satisfied travel to where the supreme treasure of truth is.",  "Mundaka Upanishad (Public Domain)"),

    # Mandukya Upanishad
    ("Mandukya Upanishad", 1, 2,  "All this is, indeed, Brahman. This Self is Brahman. This same Self has four states of consciousness.",                           "Mandukya Upanishad (Public Domain)"),
    ("Mandukya Upanishad", 1, 7,  "The fourth — Turiya — is not that which cognizes the internal, nor that which cognizes the external, nor that which cognizes both, nor that which is a mass of cognition, nor that which is simple cognition, nor that which is insentient. It is unseen, unrelated, incomprehensible, uninferable, unthinkable, indescribable, the sole essence of self-consciousness, the negation of all phenomena — the peaceful, the auspicious, the non-dual. This is the Self; this has to be known.", "Mandukya Upanishad (Public Domain)"),

    # Chandogya Upanishad
    ("Chandogya Upanishad", 3, 14, "All this universe is Brahman. In tranquility, let one worship It as Tajjalan — that from which he came forth, as that into which he will be dissolved, as that in which he breathes.", "Chandogya Upanishad (Public Domain)"),
    ("Chandogya Upanishad", 6, 8,  "Tat tvam asi — That thou art. That which is the finest essence, this whole world has that as its soul. That is Reality. That is Atman. That art thou.",                                "Chandogya Upanishad (Public Domain)"),
    ("Chandogya Upanishad", 6, 12, "Bring me a fruit of that banyan tree. Here it is, revered sir. Break it. It is broken, revered sir. What do you see? These fine seeds, revered sir. Break one of them. It is broken, revered sir. What do you see there? Nothing, revered sir. My dear, that subtle essence which you do not perceive there — in that very essence stands the being of this great banyan tree. That is the True. That is the Self. That art thou.",                                               "Chandogya Upanishad (Public Domain)"),

    # Brihadaranyaka Upanishad
    ("Brihadaranyaka Upanishad", 1, 3,  "Asato ma sad gamaya — Lead me from untruth to truth. Tamaso ma jyotir gamaya — Lead me from darkness to light. Mrityor ma amritam gamaya — Lead me from death to immortality.",  "Brihadaranyaka Upanishad (Public Domain)"),
    ("Brihadaranyaka Upanishad", 2, 4,  "The Self, my dear Maitreyi, should be realized — should be heard of, reflected on, and meditated upon. When the Self is known, heard, reflected on, and meditated upon, all this is known.",  "Brihadaranyaka Upanishad (Public Domain)"),
    ("Brihadaranyaka Upanishad", 4, 4,  "A person is of the same nature as the objects of his desire. He comes to act in accordance with his desire. He becomes fit for attaining the object of his desire according to what he does.",  "Brihadaranyaka Upanishad (Public Domain)"),

    # ── YOGA SUTRAS OF PATANJALI ──────────────────────────────────────────────

    ("Yoga Sutras", 1, 1,  "Atha yoganushasanam — Now, the teachings of yoga.",                                                                                     "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 1, 2,  "Yogas chitta vritti nirodhah — Yoga is the cessation of the movements of the mind.",                                                    "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 1, 3,  "Tada drastuh svarupe avasthanam — Then the seer abides in his own true nature.",                                                        "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 1, 4,  "Vritti sarupyam itaratra — At other times, the seer identifies with the fluctuations of the mind.",                                     "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 1, 12, "Abhyasa vairagyabhyam tat nirodhah — The cessation of these fluctuations is achieved through practice and non-attachment.",              "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 1, 33, "Maitri karuna muditopeksanam sukha duhkha punyapunya visayanam bhavanatas citta prasadanam — The mind becomes clear and serene when it cultivates friendliness towards the happy, compassion for the suffering, joy for the virtuous, and equanimity towards the wicked.", "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 2, 29, "The eight limbs of yoga are: yama (restraints), niyama (observances), asana (posture), pranayama (breath control), pratyahara (sense withdrawal), dharana (concentration), dhyana (meditation), samadhi (absorption).",  "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 2, 30, "Ahimsa satya asteya brahmacharya aparigraha yamah — The restraints are non-violence, truthfulness, non-stealing, continence, and non-possessiveness.",  "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 2, 32, "Saucha santosa tapah svadhyaya isvara pranidhanani niyamah — The observances are purity, contentment, austerity, self-study, and surrender to the Lord.",  "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 2, 46, "Sthira sukham asanam — Posture should be steady and comfortable.",                                                                       "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 3, 16, "By samyama on the three transformations, knowledge of past and future.",                                                                  "Yoga Sutras of Patanjali (Public Domain)"),
    ("Yoga Sutras", 4, 1,  "The accomplishments may be attained through birth, herbs, mantra, austerity, or samadhi.",                                               "Yoga Sutras of Patanjali (Public Domain)"),

    # ── RIGVEDA ───────────────────────────────────────────────────────────────

    ("Rigveda", 1, 1,   "Agnim ile purohitam — I laud Agni, the chosen priest, god, minister of sacrifice, who pours treasure and dispels the night.",               "Rigveda (Griffith, 1896)"),
    ("Rigveda", 1, 89,  "A noble heart, and well-inclined thoughts come to us from every side. May the gods be with us for our gain and our protector at our calling.", "Rigveda (Griffith, 1896)"),
    ("Rigveda", 1, 164, "Ekam sat vipra bahudha vadanti — Truth is one; the sages speak of it differently. They call it Agni, Yama, Matarisvan.",                    "Rigveda (Griffith, 1896)"),
    ("Rigveda", 10, 90, "Purusa sukta — The Purusha has a thousand heads, a thousand eyes, a thousand feet. On every side pervading earth he fills a space ten fingers wide. All this is the Purusha's — whatever has been and whatever shall be.",  "Rigveda (Griffith, 1896)"),
    ("Rigveda", 10, 117,"The gods have not ordained hunger to be our death: even to the well-fed man death comes in varied shapes. The riches of the liberal never waste away, while he who will not give finds none to comfort him.",               "Rigveda (Griffith, 1896)"),
    ("Rigveda", 10, 129,"There was neither non-existence nor existence then; there was neither the realm of space nor the sky which is beyond. What stirred? Where? In whose protection? Was there water, bottomlessly deep?",                       "Rigveda — Nasadiya Sukta (Griffith, 1896)"),

    # ── MAHABHARATA ───────────────────────────────────────────────────────────

    ("Mahabharata", 1, 1,   "Vyasa said: Whatever is here is found elsewhere; what is not here is nowhere else. — The Mahabharata contains the totality of dharma.",   "Mahabharata (Public Domain)"),
    ("Mahabharata", 3, 313, "Ahimsa paramo dharma — Non-injury to living beings is the highest dharma. It is the highest self-control. It is the highest truth from which all dharma proceeds.",                                                  "Mahabharata, Vana Parva (Public Domain)"),
    ("Mahabharata", 5, 39,  "Do not do to others what you do not want done to yourself. This is the whole of dharma. Heed it well.",                                 "Mahabharata, Udyoga Parva (Public Domain)"),
    ("Mahabharata", 12, 110,"One should not impose on others what oneself dislikes. This is the essence of morality.",                                                "Mahabharata, Shanti Parva (Public Domain)"),
    ("Mahabharata", 12, 167,"Those who are free from pride and delusion, who have subdued the evil of attachment, who are ever engaged in welfare of all beings — they attain that undecaying state.",                                             "Mahabharata, Shanti Parva (Public Domain)"),
    ("Mahabharata", 12, 258,"A man of wisdom should regard all creatures as his own self. He should never act against the wish of another. The conduct of the righteous is a great purifier.",                                                     "Mahabharata, Shanti Parva (Public Domain)"),
    ("Mahabharata", 12, 301,"Contentment is the highest heaven. Contentment is the highest happiness. There is nothing higher than contentment.",                     "Mahabharata, Shanti Parva (Public Domain)"),
    ("Mahabharata", 13, 6,  "The highest gift is the gift of life. The highest wisdom is freedom from attachment. The highest happiness is seeing the divine in all beings.",  "Mahabharata, Anushasana Parva (Public Domain)"),
    ("Mahabharata", 13, 116,"Compassion for all creatures is the root of dharma.",                                                                                    "Mahabharata, Anushasana Parva (Public Domain)"),
]


async def ingest_hinduism_extended():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    verses = []
    for (book, chapter, verse_num, text, translation) in VERSES:
        reference = f"{book} {chapter}:{verse_num}"
        verses.append({
            "religion": RELIGION,
            "text": text,
            "translation": translation,
            "book": book,
            "chapter": chapter,
            "verse": verse_num,
            "reference": reference,
            "source_url": None,
        })

    logger.info("Total extended Hindu verses to ingest: %d", len(verses))

    total_upserted = 0
    for i in range(0, len(verses), BATCH_SIZE):
        batch = verses[i: i + BATCH_SIZE]
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

    logger.info("Extended Hinduism ingestion complete. Total: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_hinduism_extended())
