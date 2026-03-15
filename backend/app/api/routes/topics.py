from fastapi import APIRouter
from app.models.schemas import TopicsResponse, TopicCategory

router = APIRouter()

TOPICS = TopicsResponse(
    categories=[
        TopicCategory(
            name="Universal Themes",
            topics=["Love", "Compassion", "Forgiveness", "Gratitude", "Hope"],
        ),
        TopicCategory(
            name="Life & Death",
            topics=["Afterlife", "Death", "Rebirth", "Resurrection", "Soul"],
        ),
        TopicCategory(
            name="Ethics & Morality",
            topics=["Sin", "Virtue", "Justice", "Honesty", "Charity"],
        ),
        TopicCategory(
            name="Society",
            topics=["War", "Peace", "Women", "Marriage", "Family"],
        ),
        TopicCategory(
            name="Wealth & Material",
            topics=["Money", "Greed", "Poverty", "Generosity", "Fasting"],
        ),
        TopicCategory(
            name="Spirituality",
            topics=["Prayer", "Meditation", "God", "Faith", "Worship"],
        ),
        TopicCategory(
            name="Human Nature",
            topics=["Pride", "Anger", "Fear", "Desire", "Ego"],
        ),
    ]
)


@router.get("/topics", response_model=TopicsResponse, summary="Get available discussion topics")
async def get_topics() -> TopicsResponse:
    """Return a curated list of topics organized by category."""
    return TOPICS
