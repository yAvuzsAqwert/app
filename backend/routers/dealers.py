"""Bayi (firma + ülke) kartları — her bayinin projeleri, cirosu ve açık bakiyesi."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from lib.auth import current_user
from lib.db import db
from lib.permissions import require, user_permissions
from models.schemas import STAGE_LABELS, STAGES, DealerCard, Project, StageCount

router = APIRouter(tags=["dealers"])


def _aware(doc: dict) -> dict:
    for key in ("created_at", "updated_at"):
        value = doc.get(key)
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


def _build_cards(projects: List[Project]) -> List[DealerCard]:
    groups: dict[str, List[Project]] = defaultdict(list)
    for p in projects:
        firma = (p.firma or "Belirtilmemiş").strip()
        ulke = (p.ulke or "—").strip()
        groups[f"{firma}|{ulke}"].append(p)

    cards: List[DealerCard] = []
    for key, group in groups.items():
        firma, ulke = key.split("|", 1)
        ciro = round(sum(p.muhasebe.transfer_dahil_toplam_satis for p in group), 2)
        tahsilat = round(sum(p.muhasebe.toplam_tahsilat for p in group), 2)
        net_kar = round(sum(p.muhasebe.net_kar for p in group), 2)
        # A dealer can hold projects in several currencies; label the mixed case explicitly.
        currencies = {p.para_birimi for p in group if p.para_birimi}
        asama = [
            StageCount(
                durum=s,
                label=STAGE_LABELS[s],
                adet=len([p for p in group if p.durum == s]),
                tutar=round(
                    sum(p.muhasebe.transfer_dahil_toplam_satis for p in group if p.durum == s), 2
                ),
            )
            for s in STAGES
            if any(p.durum == s for p in group)
        ]
        cards.append(
            DealerCard(
                anahtar=key,
                firma=firma,
                ulke=ulke,
                musteriler=sorted({p.musteri for p in group if p.musteri}),
                proje_adet=len(group),
                aktif_adet=len([p for p in group if not p.arsiv]),
                arsiv_adet=len([p for p in group if p.arsiv]),
                para_birimi=currencies.pop() if len(currencies) == 1 else "KARMA",
                ciro=ciro,
                tahsilat=tahsilat,
                acik_bakiye=round(sum(p.muhasebe.kalan_bakiye for p in group), 2),
                net_kar=net_kar,
                kar_yuzdesi=round(net_kar / ciro * 100, 2) if ciro else 0.0,
                son_proje_tarihi=max((p.proje_tarihi for p in group if p.proje_tarihi), default=""),
                asama_dagilimi=asama,
                projeler=sorted(group, key=lambda p: p.proje_tarihi or "", reverse=True),
            )
        )
    return sorted(cards, key=lambda c: c.ciro, reverse=True)


@router.get("/dealers", response_model=List[DealerCard])
async def list_dealers(user: dict = Depends(require("bayi:goruntule", "muhasebe:goruntule"))):
    docs = await db.projects.find().to_list(1000)
    return _build_cards([Project(**_aware(d)) for d in docs])


@router.get("/dealers/{anahtar}", response_model=DealerCard)
async def get_dealer(
    anahtar: str, user: dict = Depends(require("bayi:goruntule", "muhasebe:goruntule"))
):
    docs = await db.projects.find().to_list(1000)
    for card in _build_cards([Project(**_aware(d)) for d in docs]):
        if card.anahtar == anahtar:
            return card
    raise HTTPException(status_code=404, detail="Bayi bulunamadı")
