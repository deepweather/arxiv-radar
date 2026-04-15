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
            "2509.13523",   # AERIS: Argonne Earth Systems Model (Swin Diffusion Transformer)
        ],
    },
    {
        "name": "World Models",
        "description": "From learning environment simulators to video generation as world simulation — the papers building digital twins of reality.",
        "paper_ids": [
            "1803.10122",   # World Models (Ha & Schmidhuber)
            "1912.01603",   # Dreamer: Learning Behaviors by Latent Imagination
            "2010.02193",   # DreamerV2: Mastering Atari with Discrete World Models
            "2301.04104",   # DreamerV3: Mastering Diverse Domains through World Models
            "2309.17080",   # GAIA-1: Generative World Model for Autonomous Driving
            "2310.06114",   # UniSim: Learning Interactive Real-World Simulators
            "2402.15391",   # Genie: Generative Interactive Environments
            "2406.09455",   # Pandora: General World Model with Natural Language Actions
            "2501.03575",   # NVIDIA Cosmos World Foundation Model Platform
            "2512.08931",   # Astra: General Interactive World Model
            "2603.19312",   # LeWorldModel: Stable End-to-End JEPA from Pixels
        ],
    },
    {
        "name": "Reasoning & Thinking Models",
        "description": "The chain-of-thought revolution — from prompting tricks to test-time compute scaling and dedicated reasoning models.",
        "paper_ids": [
            "2201.11903",   # Chain-of-Thought Prompting
            "2203.11171",   # Self-Consistency Improves Chain of Thought Reasoning
            "2305.10601",   # Tree of Thoughts: Deliberate Problem Solving
            "2305.20050",   # Let's Verify Step by Step (Process Reward Models)
            "2403.09629",   # Quiet-STaR: LMs Can Teach Themselves to Think
            "2408.03314",   # Scaling LLM Test-Time Compute Optimally
            "2501.12599",   # Kimi k1.5: Scaling Reinforcement Learning with LLMs
            "2501.12948",   # DeepSeek-R1: Incentivizing Reasoning via RL
            "2501.19393",   # s1: Simple Test-Time Scaling
            "2502.03387",   # LIMO: Less Is More for Reasoning
        ],
    },
    {
        "name": "Robotics & Embodied AI",
        "description": "Foundation models meet physical manipulation — from RT-1 to general-purpose robot policies.",
        "paper_ids": [
            "2212.06817",   # RT-1: Robotics Transformer for Real-World Control
            "2307.15818",   # RT-2: Vision-Language-Action Models
            "2401.12963",   # AutoRT: Large Scale Orchestration of Robotic Agents
            "2402.18294",   # Whole-body Humanoid Robot Locomotion with Human Reference
            "2405.12213",   # Octo: An Open-Source Generalist Robot Policy
            "2406.09246",   # OpenVLA: Open-Source Vision-Language-Action Model
            "2410.24164",   # pi0: Vision-Language-Action Flow Model
            "2412.03293",   # Diffusion-VLA: Scaling Robot Foundation Models
            "2504.16054",   # pi0.5: VLA with Open-World Generalization
            "2507.02029",   # RoboBrain 2.0
        ],
    },
    {
        "name": "AI for Math & Science",
        "description": "AI systems making real discoveries — solving olympiad problems, proving theorems, and rediscovering physical laws.",
        "paper_ids": [
            "2206.14858",   # Minerva: Solving Quantitative Reasoning Problems
            "2310.10631",   # Llemma: An Open Language Model for Mathematics
            "2405.14333",   # DeepSeek-Prover: Theorem Proving via Synthetic Data
            "2411.19744",   # FunSearch: Amplifying Human Performance (follow-up)
            "2502.03544",   # AlphaGeometry2: Gold-Medalist Olympiad Geometry
            "2502.15815",   # TPBench: AI Reasoning in Theoretical Physics
            "2504.01538",   # AI-Newton: Concept-Driven Physical Law Discovery
            "2511.02864",   # AlphaEvolve: Mathematical Exploration at Scale
            "2512.19799",   # PhysMaster: Autonomous AI Physicist
        ],
    },
    {
        "name": "AI Coding Agents",
        "description": "From autocomplete to autonomous software engineering — AI systems that write, debug, and ship code.",
        "paper_ids": [
            "2107.03374",   # Codex: Evaluating Large Language Models Trained on Code
            "2203.07814",   # AlphaCode: Competition-Level Code Generation
            "2305.06161",   # StarCoder: May the Source Be With You
            "2310.06770",   # SWE-bench: Resolving Real-World GitHub Issues
            "2404.05427",   # AutoCodeRover: Autonomous Program Improvement
            "2405.15793",   # SWE-agent: Agent-Computer Interfaces
            "2406.11931",   # DeepSeek-Coder-V2: Breaking the Closed-Source Barrier
            "2407.16741",   # OpenHands: Open Platform for AI Software Developers
            "2409.12186",   # Qwen2.5-Coder
            "2411.04905",   # OpenCoder: Open Cookbook for Code LLMs
            "2506.07636",   # SWE-Dev: Training and Inference Scaling for SWE Agents
        ],
    },
    {
        "name": "Deep Research Agents",
        "description": "AI agents that autonomously browse the web, research topics, and synthesize comprehensive reports.",
        "paper_ids": [
            "2112.09332",   # WebGPT: Browser-Assisted Question-Answering
            "2210.03629",   # ReAct: Synergizing Reasoning and Acting
            "2302.04761",   # Toolformer: LMs Can Teach Themselves to Use Tools
            "2305.16291",   # Voyager: Open-Ended Embodied Agent with LLMs
            "2311.12983",   # GAIA: Benchmark for General AI Assistants
            "2504.12516",   # BrowseComp: Benchmark for Browsing Agents
            "2509.13309",   # WebResearcher: Unbounded Reasoning in Long-Horizon Agents
            "2509.24107",   # Fathom-DeepResearch: Long Horizon Retrieval & Synthesis
            "2510.15862",   # Rethinking RL-Based Deep Research Agents
            "2601.19578",   # Yunque DeepResearch
        ],
    },
    {
        "name": "Video & Image Generation",
        "description": "The diffusion and flow matching revolution in visual content creation — from DDPM to modern video generators.",
        "paper_ids": [
            "2006.11239",   # DDPM: Denoising Diffusion Probabilistic Models
            "2112.10752",   # Latent Diffusion Models / Stable Diffusion
            "2204.06125",   # DALL-E 2: Hierarchical Text-Conditional Image Generation
            "2205.11487",   # Imagen: Photorealistic Text-to-Image Diffusion
            "2212.09748",   # DiT: Scalable Diffusion Models with Transformers
            "2307.01952",   # SDXL: Improving Latent Diffusion for High-Res
            "2311.15127",   # Stable Video Diffusion
            "2403.03206",   # Scaling Rectified Flow Transformers (FLUX)
            "2408.06072",   # CogVideoX: Text-to-Video Diffusion
            "2410.13720",   # Movie Gen: Media Foundation Models (Meta)
            "2503.20314",   # Wan: Open Large-Scale Video Generative Models
        ],
    },
    {
        "name": "Audio & Speech AI",
        "description": "Voice cloning, text-to-speech, and music generation — the audio frontier of generative AI.",
        "paper_ids": [
            "2005.00341",   # Jukebox: A Generative Model for Music
            "2209.03143",   # AudioLM: Language Modeling for Audio Generation
            "2212.04356",   # Whisper: Robust Speech Recognition via Large-Scale Supervision
            "2301.02111",   # VALL-E: Neural Codec Language Models for Zero-Shot TTS
            "2306.05284",   # MusicGen: Simple and Controllable Music Generation
            "2306.15687",   # Voicebox: Text-Guided Universal Speech Generation
            "2312.01479",   # OpenVoice: Versatile Instant Voice Cloning
            "2406.02430",   # Seed-TTS: High-Quality Versatile Speech Generation
            "2406.04904",   # XTTS: Massively Multilingual Zero-Shot TTS
            "2407.05407",   # CosyVoice: Scalable Multilingual Zero-Shot TTS
            "2409.00750",   # MaskGCT: Zero-Shot TTS with Masked Generative Codec
            "2410.06885",   # F5-TTS: Fluent and Faithful Speech with Flow Matching
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
