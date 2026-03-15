"""
Ingest key passages from the Guru Granth Sahib into Qdrant.

The Guru Granth Sahib is the eternal Guru of the Sikhs, comprising 1430 pages (Ang).
This file contains a curated selection of key shabads (hymns) from the public domain
English translations covering the major theological themes.
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

RELIGION = "Sikhism"
TRANSLATION = "Guru Granth Sahib (English Translation, Public Domain)"
BATCH_SIZE = 20

# (ang_page, author, reference_label, text)
GGS_VERSES = [
    # Japji Sahib — Guru Nanak Dev Ji (Ang 1–8)
    (1, "Guru Nanak Dev Ji", "GGS 1:1", "Ik Onkar Satnam Kartapurkh Nirbhau Nirvair Akalmurat Ajuni Saibhang Gurprasad — One Universal Creator God. The Name is Truth. Creative Being Personified. No Fear. No Hatred. Image of the Undying. Beyond Birth. Self-Existent. By Guru's Grace."),
    (1, "Guru Nanak Dev Ji", "GGS 1:2", "Aad sach, jugaad sach, hai bhi sach, Nanak hosi bhi sach — True in the Primal Beginning. True throughout the ages. True here and now. O Nanak, forever and ever True."),
    (1, "Guru Nanak Dev Ji", "GGS 1:3", "Sochai soch na hovaee je sochi lakh vaar — By thinking, He cannot be reduced to thought, even by thinking hundreds of thousands of times. By remaining silent, inner silence is not obtained, even by remaining lovingly absorbed deep within."),
    (1, "Guru Nanak Dev Ji", "GGS 1:4", "Hukam rajai chalna Nanak likhia naal — O Nanak, it is written that you shall obey the Hukam of His Command, and walk in the Way of His Will."),
    (2, "Guru Nanak Dev Ji", "GGS 2:1", "Hukami hovant aakaar hukam na kahia jaee. Hukami hovant jeea hukam milai vadeeyaaee. — By His Command, bodies are created; His Command cannot be described. By His Command, souls come into being; by His Command, glory and greatness are obtained."),
    (3, "Guru Nanak Dev Ji", "GGS 3:1", "Gavai ko taakat tan hove. Gavai ko dat jaane neesaan. Gavai ko gun vadiaeeaan chaar. Gavai ko vidya vikham vichaar. — Some sing of His Power—who has that Power? Some sing of His Gifts, and know His Sign and Insignia. Some sing of His Glorious Virtues, Greatness and Beauty. Some sing of knowledge obtained of Him, through difficult philosophical studies."),
    (4, "Guru Nanak Dev Ji", "GGS 4:1", "Sacha sahib sach naye. Bhakhia bhau apaar. Aakhahi manghahi dehi dehi. Dat kare dataar. — True is the Master, True is His Name—speak it with infinite love. People beg and pray, 'Give to us, give to us'; the Great Giver gives His Gifts."),
    (5, "Guru Nanak Dev Ji", "GGS 5:1", "Thapya na jaaye kita na hoye. Aapay aap niranjan soye. — He cannot be established, He cannot be created. He Himself is Immaculate and Pure."),
    (6, "Guru Nanak Dev Ji", "GGS 6:1", "Tithai surt na chalai man budhi. Surt surat suratay budhi budhi. — There, the intuitive consciousness of the mind and intellect do not reach; awareness is focused on awareness, intellect on intellect."),
    (7, "Guru Nanak Dev Ji", "GGS 7:1", "Asa mahl pahilaa — Some are givers, some are beggars. Such is His Wondrous Play."),
    (8, "Guru Nanak Dev Ji", "GGS 8:1", "Nanak naam chardi kala. Tere bhane sarbat da bhala. — O Nanak, through the Name, there is eternal bliss. May everyone prosper by Your Will."),
    # Raag Gauree — Guru Arjan Dev Ji (Ang 294+)
    (294, "Guru Arjan Dev Ji", "GGS 294:1", "Sukh saagar hari naam hai. Hari bhagtan ko dee-o. — The Lord's Name is the ocean of peace. This has been given to the Lord's devotees."),
    (295, "Guru Arjan Dev Ji", "GGS 295:1", "Har ka naam sukhdaata jeeo. — The Name of the Lord is the giver of peace, O dear soul."),
    # Raag Aasaa — Guru Nanak Dev Ji (Ang 347+)
    (347, "Guru Nanak Dev Ji", "GGS 347:1", "Ik doo jibhau lakh hohe lakh hohe lakh vees. Lakh lakh gerhaa aakheeahi ik naam jagdees. — If I had 100,000 tongues, and these were then multiplied twenty times more, with each tongue, I would repeat, hundreds of thousands of times, the Name of the One Lord of the Universe."),
    (349, "Guru Nanak Dev Ji", "GGS 349:1", "Neevan so gal uchee. Neechai neem jhukee nadir nisaan. — Humility is higher than all. Under the neem tree, the humble one stands in the Shelter of the Lord's Grace."),
    # Raag Gujri — Guru Nanak Dev Ji (Ang 489+)
    (489, "Guru Nanak Dev Ji", "GGS 489:1", "Tum thakur tum peh ardaas. Jeeo pind sabh teri raas. — You are our Lord and Master; to You, I offer this prayer. This body and soul are all Your property."),
    # Raag Sorath — Guru Arjan Dev Ji (Ang 617+)
    (617, "Guru Arjan Dev Ji", "GGS 617:1", "Har simrat sukh paavehi santo. Dukh dard bhram katat santo. — Meditating in remembrance on the Lord, peace is found, O Saints. Pain, disease and doubt are dispelled, O Saints."),
    # Raag Dhanasree — Guru Arjan Dev Ji (Ang 670+)
    (670, "Guru Arjan Dev Ji", "GGS 670:1", "Toon mera pita toon hai mera maata. Toon mera bandap toon mera brata. — You are my Father, and You are my Mother. You are my Relative, and You are my Brother."),
    (671, "Guru Arjan Dev Ji", "GGS 671:1", "Jis ke sir upar toon swami. So dukhi kaahay re mami. — One who has You as his Lord and Master above his head—why would that person feel any sorrow?"),
    # Raag Bihaagraa — Guru Nanak Dev Ji (Ang 555+)
    (555, "Guru Nanak Dev Ji", "GGS 555:1", "Maanas kee jaat sabhay ekay pahchanbo — Recognize the human race as one."),
    # Sukhmani Sahib — Guru Arjan Dev Ji (Ang 262–296)
    (262, "Guru Arjan Dev Ji", "GGS 262:1", "Simro simro simro har soye. Har simrat aghaa naas hoye. — Remember, remember, remember God in meditation. Remembering God in meditation, sins are erased."),
    (263, "Guru Arjan Dev Ji", "GGS 263:1", "Sukhmani sukh amrit prabh naam. Bhagat janaa kai man bisraam. — Sukhmani: Peace of mind, the nectar of God's Name. The minds of the devotees abide in a state of rest."),
    (270, "Guru Arjan Dev Ji", "GGS 270:1", "Jo maango thaakur apne tay. Soee soee devai. — Whatever I ask of my Lord and Master, He gives that to me."),
    (275, "Guru Arjan Dev Ji", "GGS 275:1", "Mitar pyaaray noo haal mureedaa da kehna. — Tell the state of the disciples to our dear Friend."),
    (276, "Guru Arjan Dev Ji", "GGS 276:1", "Sabh te vadda satgur naanak. Jin kal raakhi meri. — The greatest of all is Guru Nanak; He has preserved my honor through this Dark Age of Kali Yuga."),
    # Raag Basant — Guru Nanak Dev Ji (Ang 1168+)
    (1168, "Guru Nanak Dev Ji", "GGS 1168:1", "Vahu vahu baani nirankaar hae. Tis jevad avar na koee. — Waaho! Waaho! Wondrous is the Word of the Formless Lord. There is none other like Him."),
    # Shaloks — Guru Nanak Dev Ji
    (1410, "Guru Nanak Dev Ji", "GGS 1410:1", "Pavan guru paanee pita. Mata dharat mahat. — Air is the Guru, water is the Father, and the great earth is the Mother."),
    (1412, "Guru Nanak Dev Ji", "GGS 1412:1", "Ek noor tay sabh jag upajiya kaun bhalay ko manday — From the One Light, the entire universe welled up. So who is good, and who is bad?"),
    # Mundaavanee — Guru Arjan Dev Ji (Ang 1429)
    (1429, "Guru Arjan Dev Ji", "GGS 1429:1", "Thal vich tin vastu payo sat santokh vicharo. Amrit naam thakur ka peeo jis ka sabhas adharo. — Upon this Plate, three things have been placed: Truth, Contentment and Contemplation. The Ambrosial Nectar of the Naam, the Name of our Lord and Master, has been placed upon it as well; it is the Support of all."),
    # Mool Mantar (fundamental statement of faith)
    (1, "Guru Nanak Dev Ji", "GGS Mool Mantar", "Ik Onkar — There is One God. He is the supreme truth. He, the creator, is without fear and without hate. He, the omnipresent, pervades the universe. He is not born, nor does He die to be born again. By His grace shalt thou worship Him."),
    # Anand Sahib — Guru Amar Das Ji (Ang 917)
    (917, "Guru Amar Das Ji", "GGS 917:1", "Anand bhiya mere maay sathguroo mai paaya. — I am in ecstasy, O my mother, for I have found my True Guru."),
    (918, "Guru Amar Das Ji", "GGS 918:1", "Aavahu sant janahu. Mil gavo mera prabh neetaa. — Come, O Saints; join together and sing the praises of my God forever."),
    # Shabad on equality
    (83, "Guru Nanak Dev Ji", "GGS 83:1", "Neech jaat nirgun mairi. Kaho Nanak tin sang behi — I am of low social class, without virtue. O Nanak, say that I sit in the company of such humble ones."),
    # Shabad on service (seva)
    (26, "Guru Nanak Dev Ji", "GGS 26:1", "Ghar ghar andar dharamsaal. Hovai keertan sadaa visaal. — Within each and every home, within each and every heart, this infinite Light shines. May the Kirtan of His Praises be sung continuously, forever."),
    # Shabad on forgiveness
    (624, "Guru Arjan Dev Ji", "GGS 624:1", "Avar dosh na deyjai. Aapnaa aap pehchaanai. — Do not blame anyone else; look within your own self instead."),
    # Shabad on death
    (78, "Guru Nanak Dev Ji", "GGS 78:1", "Jo aaya so chalsi sabb koee aai jaaiye — Whoever has come will depart; all must rise and leave."),
    (79, "Guru Nanak Dev Ji", "GGS 79:1", "Nanak ik vajeer hai jis da ant na paar — O Nanak, He is the One Vizier; He has no end or limitation."),
]


async def ingest_guru_granth():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    verses = []
    for (ang, author, reference, text) in GGS_VERSES:
        verses.append(
            {
                "religion": RELIGION,
                "text": text,
                "translation": TRANSLATION,
                "book": f"Ang {ang} — {author}",
                "chapter": ang,
                "verse": None,
                "reference": reference,
                "source_url": None,
            }
        )

    logger.info("Total GGS passages to ingest: %d", len(verses))

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
        logger.info("Upserted %d / %d passages.", total_upserted, len(verses))

    logger.info("Guru Granth Sahib ingestion complete. Total: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_guru_granth())
