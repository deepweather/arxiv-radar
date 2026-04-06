"""Seed system account and curated collections on first deployment.

Fully idempotent — safe to run on every worker startup.
"""

import json
import logging
import uuid
from datetime import timezone

import arxiv
import bcrypt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Collection, CollectionPaper, Paper

logger = logging.getLogger(__name__)

SEED_USER_EMAIL = "team@arxivradar.com"

SEED_COLLECTIONS = [
    {
        "name": "AI All-Time Bangers",
        "description": "The most influential and widely-cited AI/ML papers of all time.",
        "paper_ids": [
            "1706.03762",   # Attention Is All You Need
            "1810.04805",   # BERT
            "2005.14165",   # GPT-3
            "1512.03385",   # ResNet
            "1406.2661",    # GANs
            "1412.6980",    # Adam Optimizer
            "1502.03167",   # Batch Normalization
            "1207.0580",    # Dropout
            "1301.3781",    # Word2Vec
            "1409.4842",    # GoogLeNet / Inception
            "1505.04597",   # U-Net
            "1409.1556",    # VGGNet
            "1506.02640",   # YOLO
            "2006.11239",   # DDPM (Denoising Diffusion)
            "2010.11929",   # Vision Transformer (ViT)
            "2112.10752",   # Latent Diffusion / Stable Diffusion
            "1312.5602",    # DQN (Playing Atari)
            "1707.06347",   # PPO
            "2201.11903",   # Chain-of-Thought Prompting
            "2203.02155",   # InstructGPT / RLHF
            "2205.14135",   # FlashAttention
            "2106.09685",   # LoRA
            "2302.13971",   # LLaMA
            "1701.06538",   # Mixture of Experts (Shazeer)
            "1611.01578",   # Neural Architecture Search
        ],
    },
    {
        "name": "JEPA - Joint Embedding Predictive Architectures",
        "description": "Papers on Joint Embedding Predictive Architectures (JEPA) and the path towards autonomous machine intelligence.",
        "paper_ids": [
            "2306.02572",   # Intro to Latent Variable EBMs / H-JEPA (Dawid & LeCun)
            "2301.08243",   # I-JEPA: Images
            "2404.08471",   # V-JEPA: Video
            "2506.09985",   # V-JEPA 2: Understanding, Prediction and Planning
            "2307.12698",   # MC-JEPA: Motion and Content (Bardes, Ponce, LeCun)
            "2410.03755",   # D-JEPA: Denoising with JEPA
            "2509.14252",   # LLM-JEPA: Large Language Models Meet JEPA
            "2512.10942",   # VL-JEPA: Vision-Language JEPA
            "2601.14354",   # VJEPA: Variational JEPA as Probabilistic World Models
            "2309.16014",   # Graph-JEPA: Graph-level Representation Learning
            "2507.02915",   # Audio-JEPA: Audio Representation Learning
        ],
    },
    {
        "name": "Schmidhuber Invented Everything",
        "description": "A curated tour of Juergen Schmidhuber's work and the papers where he argues he had the idea first.",
        "paper_ids": [
            "1404.7828",    # Deep Learning in Neural Networks: An Overview
            "1505.00387",   # Training Very Deep Networks (Highway Networks)
            "1202.2745",    # Multi-Column DNN for Image Classification
            "1503.04069",   # LSTM: A Search Space Odyssey
            "1511.09249",   # On Learning to Think
            "0812.4360",    # Driven by Compression Progress (Curiosity, Creativity)
            "2212.11279",   # Annotated History of Modern AI and Deep Learning
            "1803.10122",   # World Models (Ha & Schmidhuber)
            "2005.05744",   # Deep Learning: Our Miraculous Year 1990-1991
            "2202.05780",   # A Modern Self-Referential Weight Matrix (Kirsch & Schmidhuber)
        ],
    },
    {
        "name": "Awesome AI Weather Models",
        "description": "The papers behind the AI revolution in weather forecasting — from FourCastNet to GenCast.",
        "paper_ids": [
            "2202.11214",   # FourCastNet (NVIDIA)
            "2211.02556",   # Pangu-Weather (Huawei)
            "2212.12794",   # GraphCast (DeepMind)
            "2301.10343",   # ClimaX: Foundation Model for Weather and Climate
            "2306.12873",   # FuXi: 15-day Global Weather Forecast
            "2311.07222",   # NeuralGCM (Google)
            "2312.03876",   # Stormer: Scaling Transformers for Weather
            "2312.15796",   # GenCast: Diffusion-based Ensemble Forecasting (DeepMind)
            "2405.13063",   # Aurora: Foundation Model for Earth System (Microsoft)
            "2406.01465",   # AIFS: ECMWF's Data-Driven Forecasting System
            "2503.22235",   # WeatherMesh-3: Operational Global Forecasting (WindBorne)
            "2410.15076",   # EPT-1.5: Earth Physics Transformer (Jua)
            "2507.09703",   # EPT-2: Earth Physics Transformer (Jua)
            "2602.11893",   # Universal Diffusion-Based Probabilistic Downscaling (Jua)
        ],
    },
]

_UPSERT_PAPER_SQL = text("""
    INSERT INTO papers (id, title, summary, authors, categories, pdf_url, published_at, updated_at)
    VALUES (:id, :title, :summary, CAST(:authors AS jsonb), :categories, :pdf_url, :published_at, :updated_at)
    ON CONFLICT (id) DO NOTHING
""")


def _parse_arxiv_result(result: arxiv.Result) -> dict:
    """Parse an arxiv.Result into a dict matching the papers table schema."""
    arxiv_id = result.entry_id.split("/abs/")[-1]
    if "v" in arxiv_id:
        arxiv_id = arxiv_id.split("v")[0]

    return {
        "id": arxiv_id,
        "title": result.title.strip().replace("\n", " "),
        "summary": result.summary.strip().replace("\n", " "),
        "authors": json.dumps([{"name": a.name} for a in result.authors]),
        "categories": list(result.categories),
        "pdf_url": result.pdf_url,
        "published_at": result.published.replace(tzinfo=timezone.utc) if result.published.tzinfo is None else result.published,
        "updated_at": result.updated.replace(tzinfo=timezone.utc) if result.updated.tzinfo is None else result.updated,
    }


async def _ensure_paper_exists(db: AsyncSession, paper_id: str, arxiv_client: arxiv.Client) -> bool:
    """Check if paper exists in DB; if not, fetch from arXiv and insert. Returns True if paper is available."""
    result = await db.execute(select(Paper.id).where(Paper.id == paper_id))
    if result.scalar_one_or_none() is not None:
        return True

    try:
        search = arxiv.Search(id_list=[paper_id])
        api_result = next(arxiv_client.results(search), None)
        if api_result is None:
            logger.warning("Seed: paper %s not found on arXiv, skipping", paper_id)
            return False

        parsed = _parse_arxiv_result(api_result)
        await db.execute(_UPSERT_PAPER_SQL, parsed)
        logger.info("Seed: fetched paper %s — %s", paper_id, parsed["title"][:80])
        return True
    except Exception:
        logger.exception("Seed: failed to fetch paper %s from arXiv", paper_id)
        return False


async def run_seed(db: AsyncSession) -> dict:
    """Create the system user and seed collections idempotently. Returns a summary dict."""
    stats = {"user_created": False, "collections_created": 0, "papers_added": 0, "papers_fetched": 0}

    # 1. Ensure system user exists
    result = await db.execute(select(User).where(User.email == SEED_USER_EMAIL))
    user = result.scalar_one_or_none()

    if user is None:
        random_pw = uuid.uuid4().hex
        pw_hash = bcrypt.hashpw(random_pw.encode(), bcrypt.gensalt()).decode()
        user = User(
            email=SEED_USER_EMAIL,
            password_hash=pw_hash,
            is_email_verified=True,
        )
        db.add(user)
        await db.flush()
        stats["user_created"] = True
        logger.info("Seed: created system user %s (id=%s)", SEED_USER_EMAIL, user.id)
    else:
        logger.info("Seed: system user %s already exists (id=%s)", SEED_USER_EMAIL, user.id)

    # 2. Seed collections
    arxiv_client = arxiv.Client(page_size=10, delay_seconds=3.0, num_retries=3)

    for coll_def in SEED_COLLECTIONS:
        coll_result = await db.execute(
            select(Collection).where(
                Collection.user_id == user.id,
                Collection.name == coll_def["name"],
            )
        )
        coll = coll_result.scalar_one_or_none()

        if coll is None:
            coll = Collection(
                user_id=user.id,
                name=coll_def["name"],
                description=coll_def["description"],
                is_public=True,
            )
            db.add(coll)
            await db.flush()
            stats["collections_created"] += 1
            logger.info("Seed: created collection '%s' (id=%s)", coll.name, coll.id)
        else:
            logger.info("Seed: collection '%s' already exists", coll.name)

        # 3. Add papers to the collection
        for paper_id in coll_def["paper_ids"]:
            # Check if already linked
            link_result = await db.execute(
                select(CollectionPaper).where(
                    CollectionPaper.collection_id == coll.id,
                    CollectionPaper.paper_id == paper_id,
                )
            )
            if link_result.scalar_one_or_none() is not None:
                continue

            paper_existed = await db.execute(select(Paper.id).where(Paper.id == paper_id))
            already_in_db = paper_existed.scalar_one_or_none() is not None

            if await _ensure_paper_exists(db, paper_id, arxiv_client):
                db.add(CollectionPaper(collection_id=coll.id, paper_id=paper_id, note=""))
                stats["papers_added"] += 1
                if not already_in_db:
                    stats["papers_fetched"] += 1

    await db.commit()
    return stats
