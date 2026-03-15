"""
Ingest the Torah/Tanakh into Qdrant.

Covers key passages from all three sections of the Tanakh:
  - Torah (Five Books of Moses): Genesis, Exodus, Leviticus, Numbers, Deuteronomy
  - Nevi'im (Prophets): Isaiah, Jeremiah, Ezekiel, Amos, Micah, Zechariah
  - Ketuvim (Writings): Psalms, Proverbs, Ecclesiastes, Job, Ruth, Song of Songs

All texts are from public-domain translations (JPS 1917 / KJV Old Testament).
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

RELIGION = "Judaism"
TRANSLATION = "Tanakh (JPS 1917 / Public Domain)"
BATCH_SIZE = 20

# (book, chapter, verse, text)
TORAH_VERSES = [
    # ── GENESIS (Bereshit) ──────────────────────────────────────────────────
    ("Genesis", 1, 1, "In the beginning God created the heaven and the earth."),
    ("Genesis", 1, 27, "So God created man in His own image, in the image of God created He him; male and female created He them."),
    ("Genesis", 1, 31, "And God saw every thing that He had made, and, behold, it was very good."),
    ("Genesis", 2, 7, "And the LORD God formed man of the dust of the ground, and breathed into his nostrils the breath of life; and man became a living soul."),
    ("Genesis", 2, 24, "Therefore shall a man leave his father and his mother, and shall cleave unto his wife: and they shall be one flesh."),
    ("Genesis", 4, 9, "And the LORD said unto Cain, Where is Abel thy brother? And he said, I know not: Am I my brother's keeper?"),
    ("Genesis", 12, 1, "Now the LORD had said unto Abram, Get thee out of thy country, and from thy kindred, and from thy father's house, unto a land that I will show thee."),
    ("Genesis", 12, 2, "And I will make of thee a great nation, and I will bless thee, and make thy name great; and thou shalt be a blessing."),
    ("Genesis", 15, 6, "And he believed in the LORD; and He counted it to him for righteousness."),
    ("Genesis", 17, 7, "And I will establish My covenant between Me and thee and thy seed after thee in their generations for an everlasting covenant, to be a God unto thee, and to thy seed after thee."),
    ("Genesis", 22, 12, "And He said, Lay not thine hand upon the lad, neither do thou any thing unto him: for now I know that thou fearest God, seeing thou hast not withheld thy son, thine only son from Me."),
    ("Genesis", 28, 16, "And Jacob awaked out of his sleep, and he said, Surely the LORD is in this place; and I knew it not."),
    ("Genesis", 32, 28, "And He said, Thy name shall be called no more Jacob, but Israel: for as a prince hast thou power with God and with men, and hast prevailed."),
    ("Genesis", 50, 20, "But as for you, ye thought evil against me; but God meant it unto good, to bring to pass, as it is this day, to save much people alive."),

    # ── EXODUS (Shemot) ─────────────────────────────────────────────────────
    ("Exodus", 3, 14, "And God said unto Moses, I AM THAT I AM: and He said, Thus shalt thou say unto the children of Israel, I AM hath sent me unto you."),
    ("Exodus", 6, 7, "And I will take you to Me for a people, and I will be to you a God: and ye shall know that I am the LORD your God, which bringeth you out from under the burdens of the Egyptians."),
    ("Exodus", 19, 5, "Now therefore, if ye will obey My voice indeed, and keep My covenant, then ye shall be a peculiar treasure unto Me above all people: for all the earth is Mine."),
    ("Exodus", 19, 6, "And ye shall be unto Me a kingdom of priests, and a holy nation. These are the words which thou shalt speak unto the children of Israel."),
    ("Exodus", 20, 2, "I am the LORD thy God, which have brought thee out of the land of Egypt, out of the house of bondage. Thou shalt have no other gods before Me."),
    ("Exodus", 20, 8, "Remember the sabbath day, to keep it holy."),
    ("Exodus", 20, 12, "Honour thy father and thy mother: that thy days may be long upon the land which the LORD thy God giveth thee."),
    ("Exodus", 20, 13, "Thou shalt not murder."),
    ("Exodus", 20, 14, "Thou shalt not commit adultery."),
    ("Exodus", 20, 15, "Thou shalt not steal."),
    ("Exodus", 20, 16, "Thou shalt not bear false witness against thy neighbour."),
    ("Exodus", 33, 19, "And He said, I will make all My goodness pass before thee, and I will proclaim the name of the LORD before thee; and will be gracious to whom I will be gracious, and will show mercy on whom I will show mercy."),
    ("Exodus", 34, 6, "And the LORD passed by before him, and proclaimed, The LORD, The LORD God, merciful and gracious, longsuffering, and abundant in goodness and truth."),

    # ── LEVITICUS (Vayikra) ─────────────────────────────────────────────────
    ("Leviticus", 19, 2, "Speak unto all the congregation of the children of Israel, and say unto them, Ye shall be holy: for I the LORD your God am holy."),
    ("Leviticus", 19, 18, "Thou shalt not avenge, nor bear any grudge against the children of thy people, but thou shalt love thy neighbour as thyself: I am the LORD."),
    ("Leviticus", 19, 34, "But the stranger that dwelleth with you shall be unto you as one born among you, and thou shalt love him as thyself; for ye were strangers in the land of Egypt."),
    ("Leviticus", 26, 12, "And I will walk among you, and will be your God, and ye shall be My people."),

    # ── NUMBERS (Bamidbar) ──────────────────────────────────────────────────
    ("Numbers", 6, 24, "The LORD bless thee, and keep thee."),
    ("Numbers", 6, 25, "The LORD make His face shine upon thee, and be gracious unto thee."),
    ("Numbers", 6, 26, "The LORD lift up His countenance upon thee, and give thee peace."),

    # ── DEUTERONOMY (Devarim) ────────────────────────────────────────────────
    ("Deuteronomy", 6, 4, "Hear, O Israel: The LORD our God is one LORD."),
    ("Deuteronomy", 6, 5, "And thou shalt love the LORD thy God with all thine heart, and with all thy soul, and with all thy might."),
    ("Deuteronomy", 6, 6, "And these words, which I command thee this day, shall be in thine heart."),
    ("Deuteronomy", 6, 7, "And thou shalt teach them diligently unto thy children, and shalt talk of them when thou sittest in thine house, and when thou walkest by the way, and when thou liest down, and when thou risest up."),
    ("Deuteronomy", 10, 12, "And now, Israel, what doth the LORD thy God require of thee, but to fear the LORD thy God, to walk in all His ways, and to love Him, and to serve the LORD thy God with all thy heart and with all thy soul."),
    ("Deuteronomy", 16, 20, "Justice, justice shalt thou pursue, that thou mayest live, and inherit the land which the LORD thy God giveth thee."),
    ("Deuteronomy", 30, 14, "But the word is very nigh unto thee, in thy mouth, and in thy heart, that thou mayest do it."),
    ("Deuteronomy", 30, 19, "I call heaven and earth to record this day against you, that I have set before you life and death, blessing and cursing: therefore choose life, that both thou and thy seed may live."),

    # ── ISAIAH (Yeshayahu) ───────────────────────────────────────────────────
    ("Isaiah", 1, 17, "Learn to do well; seek judgment, relieve the oppressed, judge the fatherless, plead for the widow."),
    ("Isaiah", 2, 4, "And He shall judge among the nations, and shall rebuke many people: and they shall beat their swords into plowshares, and their spears into pruninghooks: nation shall not lift up sword against nation, neither shall they learn war any more."),
    ("Isaiah", 6, 3, "And one cried unto another, and said, Holy, holy, holy, is the LORD of hosts: the whole earth is full of His glory."),
    ("Isaiah", 40, 28, "Hast thou not known? hast thou not heard, that the everlasting God, the LORD, the Creator of the ends of the earth, fainteth not, neither is weary? there is no searching of His understanding."),
    ("Isaiah", 40, 29, "He giveth power to the faint; and to them that have no might He increaseth strength."),
    ("Isaiah", 40, 31, "But they that wait upon the LORD shall renew their strength; they shall mount up with wings as eagles; they shall run, and not be weary; and they shall walk, and not faint."),
    ("Isaiah", 41, 10, "Fear thou not; for I am with thee: be not dismayed; for I am thy God: I will strengthen thee; yea, I will help thee; yea, I will uphold thee with the right hand of My righteousness."),
    ("Isaiah", 43, 1, "But now thus saith the LORD that created thee, O Jacob, and He that formed thee, O Israel, Fear not: for I have redeemed thee, I have called thee by thy name; thou art Mine."),
    ("Isaiah", 55, 8, "For My thoughts are not your thoughts, neither are your ways My ways, saith the LORD."),
    ("Isaiah", 61, 1, "The Spirit of the Lord GOD is upon me; because the LORD hath anointed me to preach good tidings unto the meek; He hath sent me to bind up the brokenhearted, to proclaim liberty to the captives, and the opening of the prison to them that are bound."),

    # ── JEREMIAH (Yirmiyahu) ─────────────────────────────────────────────────
    ("Jeremiah", 29, 11, "For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end."),
    ("Jeremiah", 31, 3, "The LORD hath appeared of old unto me, saying, Yea, I have loved thee with an everlasting love: therefore with lovingkindness have I drawn thee."),
    ("Jeremiah", 31, 33, "But this shall be the covenant that I will make with the house of Israel; After those days, saith the LORD, I will put My law in their inward parts, and write it in their hearts; and will be their God, and they shall be My people."),

    # ── EZEKIEL (Yechezkel) ─────────────────────────────────────────────────
    ("Ezekiel", 18, 4, "Behold, all souls are Mine; as the soul of the father, so also the soul of the son is Mine: the soul that sinneth, it shall die."),
    ("Ezekiel", 36, 26, "A new heart also will I give you, and a new spirit will I put within you: and I will take away the stony heart out of your flesh, and I will give you an heart of flesh."),

    # ── MICAH ────────────────────────────────────────────────────────────────
    ("Micah", 6, 8, "He hath showed thee, O man, what is good; and what doth the LORD require of thee, but to do justly, and to love mercy, and to walk humbly with thy God?"),

    # ── ZECHARIAH ────────────────────────────────────────────────────────────
    ("Zechariah", 4, 6, "Then he answered and spake unto me, saying, This is the word of the LORD unto Zerubbabel, saying, Not by might, nor by power, but by My spirit, saith the LORD of hosts."),

    # ── PSALMS (Tehillim) ────────────────────────────────────────────────────
    ("Psalms", 1, 1, "Blessed is the man that walketh not in the counsel of the ungodly, nor standeth in the way of sinners, nor sitteth in the seat of the scornful."),
    ("Psalms", 1, 2, "But his delight is in the law of the LORD; and in His law doth he meditate day and night."),
    ("Psalms", 19, 7, "The law of the LORD is perfect, converting the soul: the testimony of the LORD is sure, making wise the simple."),
    ("Psalms", 19, 14, "Let the words of my mouth, and the meditation of my heart, be acceptable in Thy sight, O LORD, my strength, and my redeemer."),
    ("Psalms", 22, 1, "My God, my God, why hast Thou forsaken me? why art Thou so far from helping me, and from the words of my roaring?"),
    ("Psalms", 23, 1, "The LORD is my shepherd; I shall not want."),
    ("Psalms", 23, 4, "Yea, though I walk through the valley of the shadow of death, I will fear no evil: for Thou art with me; Thy rod and Thy staff they comfort me."),
    ("Psalms", 27, 1, "The LORD is my light and my salvation; whom shall I fear? the LORD is the strength of my life; of whom shall I be afraid?"),
    ("Psalms", 34, 8, "O taste and see that the LORD is good: blessed is the man that trusteth in Him."),
    ("Psalms", 37, 4, "Delight thyself also in the LORD; and He shall give thee the desires of thine heart."),
    ("Psalms", 46, 10, "Be still, and know that I am God: I will be exalted among the heathen, I will be exalted in the earth."),
    ("Psalms", 91, 1, "He that dwelleth in the secret place of the most High shall abide under the shadow of the Almighty."),
    ("Psalms", 100, 3, "Know ye that the LORD He is God: it is He that hath made us, and not we ourselves; we are His people, and the sheep of His pasture."),
    ("Psalms", 118, 24, "This is the day which the LORD hath made; we will rejoice and be glad in it."),
    ("Psalms", 119, 105, "Thy word is a lamp unto my feet, and a light unto my path."),
    ("Psalms", 121, 1, "I will lift up mine eyes unto the hills, from whence cometh my help."),
    ("Psalms", 121, 2, "My help cometh from the LORD, which made heaven and earth."),
    ("Psalms", 139, 7, "Whither shall I go from Thy spirit? or whither shall I flee from Thy presence?"),
    ("Psalms", 139, 14, "I will praise Thee; for I am fearfully and wonderfully made: marvellous are Thy works; and that my soul knoweth right well."),
    ("Psalms", 145, 18, "The LORD is nigh unto all them that call upon Him, to all that call upon Him in truth."),

    # ── PROVERBS (Mishlei) ───────────────────────────────────────────────────
    ("Proverbs", 1, 7, "The fear of the LORD is the beginning of knowledge: but fools despise wisdom and instruction."),
    ("Proverbs", 3, 5, "Trust in the LORD with all thine heart; and lean not unto thine own understanding."),
    ("Proverbs", 3, 6, "In all thy ways acknowledge Him, and He shall direct thy paths."),
    ("Proverbs", 4, 23, "Keep thy heart with all diligence; for out of it are the issues of life."),
    ("Proverbs", 10, 12, "Hatred stirreth up strifes: but love covereth all sins."),
    ("Proverbs", 11, 2, "When pride cometh, then cometh shame: but with the lowly is wisdom."),
    ("Proverbs", 12, 17, "An honest witness tells the truth, but a false witness tells lies."),
    ("Proverbs", 14, 34, "Righteousness exalteth a nation: but sin is a reproach to any people."),
    ("Proverbs", 16, 18, "Pride goeth before destruction, and an haughty spirit before a fall."),
    ("Proverbs", 22, 6, "Train up a child in the way he should go: and when he is old, he will not depart from it."),
    ("Proverbs", 31, 10, "Who can find a virtuous woman? for her price is far above rubies."),

    # ── ECCLESIASTES (Kohelet) ───────────────────────────────────────────────
    ("Ecclesiastes", 1, 2, "Vanity of vanities, saith the Preacher, vanity of vanities; all is vanity."),
    ("Ecclesiastes", 3, 1, "To every thing there is a season, and a time to every purpose under the heaven."),
    ("Ecclesiastes", 3, 11, "He hath made every thing beautiful in His time: also He hath set the world in their heart, so that no man can find out the work that God maketh from the beginning to the end."),
    ("Ecclesiastes", 12, 13, "Let us hear the conclusion of the whole matter: Fear God, and keep His commandments: for this is the whole duty of man."),

    # ── JOB (Iyov) ───────────────────────────────────────────────────────────
    ("Job", 1, 21, "Naked came I out of my mother's womb, and naked shall I return thither: the LORD gave, and the LORD hath taken away; blessed be the name of the LORD."),
    ("Job", 38, 4, "Where wast thou when I laid the foundations of the earth? declare, if thou hast understanding."),
    ("Job", 42, 5, "I have heard of Thee by the hearing of the ear: but now mine eye seeth Thee."),

    # ── RUTH ─────────────────────────────────────────────────────────────────
    ("Ruth", 1, 16, "And Ruth said, Intreat me not to leave thee, or to return from following after thee: for whither thou goest, I will go; and where thou lodgest, I will lodge: thy people shall be my people, and thy God my God."),

    # ── SONG OF SONGS (Shir HaShirim) ────────────────────────────────────────
    ("Song of Songs", 2, 4, "He brought me to the banqueting house, and his banner over me was love."),
    ("Song of Songs", 8, 6, "Set me as a seal upon thine heart, as a seal upon thine arm: for love is strong as death; jealousy is cruel as the grave."),
]


async def ingest_torah():
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    verses = []
    for (book, chapter, verse_num, text) in TORAH_VERSES:
        reference = f"{book} {chapter}:{verse_num}"
        verses.append(
            {
                "religion": RELIGION,
                "text": text,
                "translation": TRANSLATION,
                "book": book,
                "chapter": chapter,
                "verse": verse_num,
                "reference": reference,
                "source_url": None,
            }
        )

    logger.info("Total Torah/Tanakh verses to ingest: %d", len(verses))

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

    logger.info("Torah/Tanakh ingestion complete. Total: %d", total_upserted)


if __name__ == "__main__":
    asyncio.run(ingest_torah())
