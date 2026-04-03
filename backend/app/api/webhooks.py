from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, WebhookConfig
from app.api.deps import get_current_user

router = APIRouter()


class WebhookCreate(BaseModel):
    platform: str  # "slack" or "discord"
    webhook_url: str
    tag_id: int | None = None
    enabled: bool = True


class WebhookUpdate(BaseModel):
    webhook_url: str | None = None
    tag_id: int | None = None
    enabled: bool | None = None


class WebhookResponse(BaseModel):
    id: int
    platform: str
    webhook_url: str
    tag_id: int | None
    enabled: bool


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.user_id == user.id).order_by(WebhookConfig.created_at.desc())
    )
    return [
        WebhookResponse(id=w.id, platform=w.platform, webhook_url=w.webhook_url, tag_id=w.tag_id, enabled=w.enabled)
        for w in result.scalars().all()
    ]


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.platform not in ("slack", "discord"):
        raise HTTPException(status_code=400, detail="Platform must be 'slack' or 'discord'")

    wh = WebhookConfig(
        user_id=user.id,
        platform=body.platform,
        webhook_url=body.webhook_url,
        tag_id=body.tag_id,
        enabled=body.enabled,
    )
    db.add(wh)
    await db.flush()
    return WebhookResponse(id=wh.id, platform=wh.platform, webhook_url=wh.webhook_url, tag_id=wh.tag_id, enabled=wh.enabled)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    body: WebhookUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.id == webhook_id, WebhookConfig.user_id == user.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if body.webhook_url is not None:
        wh.webhook_url = body.webhook_url
    if body.tag_id is not None:
        wh.tag_id = body.tag_id
    if body.enabled is not None:
        wh.enabled = body.enabled

    return WebhookResponse(id=wh.id, platform=wh.platform, webhook_url=wh.webhook_url, tag_id=wh.tag_id, enabled=wh.enabled)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.id == webhook_id, WebhookConfig.user_id == user.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(wh)
