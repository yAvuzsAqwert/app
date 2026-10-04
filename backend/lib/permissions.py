"""Rol tabanlı yetkilendirme — tek organizasyon, tek karar fonksiyonu.

Roller `roles` koleksiyonunda tutulur ve ekrandan düzenlenebilir; `admin` rolü
daima tüm yetkilere sahiptir (kilitli). Yetki kontrolü yalnızca sunucuda yapılır:
kullanıcının rolü her istekte veritabanından okunur, token/istemciden değil.
"""

from fastapi import Depends, HTTPException

from lib.auth import current_user
from lib.db import db

# Yetki kodu -> ekranda görünen etiket
PERMISSIONS: dict[str, str] = {
    "proje:goruntule": "Projeleri görüntüle",
    "proje:ekle": "Proje ekle",
    "proje:duzenle": "Proje bilgilerini düzenle",
    "proje:sil": "Proje sil / arşivle",
    "asama:degistir": "Süreç aşamasını değiştir",
    "kalem:yonet": "Ürün kalemlerini yönet",
    "sandik:yonet": "Sandık / sevkiyat kayıtlarını yönet",
    "muhasebe:goruntule": "Muhasebe ve tahsilatı görüntüle",
    "muhasebe:duzenle": "Muhasebe ve tahsilatı düzenle",
    "evrak:goruntule": "Evrakları görüntüle / indir",
    "evrak:yukle": "Evrak yükle",
    "evrak:sil": "Evrak sil",
    "proforma:olustur": "Proforma PDF / etiket oluştur",
    "revizyon:yonet": "Revizyon kaydet / sil",
    "rapor:goruntule": "Raporları görüntüle",
    "rapor:disaari": "Rapor / ekstre Excel indir",
    "bayi:goruntule": "Bayi kartlarını görüntüle",
    "portal:yonet": "Bayi portal hesaplarını yönet",
    "tanim:yonet": "Tanım listelerini yönet",
    "kur:yonet": "Döviz kurlarını güncelle",
    "kullanici:yonet": "Kullanıcı ve yetkileri yönet",
}

ALL_PERMISSIONS = list(PERMISSIONS)

# Hazır roller — kurulumda tohumlanır, sonrasında (admin hariç) düzenlenebilir.
ROLE_DEFAULTS: dict[str, tuple[str, list[str]]] = {
    "admin": ("Yönetici (Admin)", ALL_PERMISSIONS),
    "satis": (
        "Satış",
        [
            "proje:goruntule",
            "proje:ekle",
            "proje:duzenle",
            "asama:degistir",
            "kalem:yonet",
            "muhasebe:goruntule",
            "evrak:goruntule",
            "evrak:yukle",
            "proforma:olustur",
            "revizyon:yonet",
            "rapor:goruntule",
            "rapor:disaari",
            "bayi:goruntule",
        ],
    ),
    "uretim": (
        "Üretim / Lojistik",
        [
            "proje:goruntule",
            "proje:duzenle",
            "asama:degistir",
            "kalem:yonet",
            "sandik:yonet",
            "evrak:goruntule",
            "evrak:yukle",
            "proforma:olustur",
            "rapor:goruntule",
        ],
    ),
    "muhasebe": (
        "Muhasebe",
        [
            "proje:goruntule",
            "muhasebe:goruntule",
            "muhasebe:duzenle",
            "rapor:goruntule",
            "rapor:disaari",
            "bayi:goruntule",
            "kur:yonet",
            "evrak:goruntule",
            "evrak:yukle",
        ],
    ),
    "izleyici": (
        "Sadece Görüntüleme",
        ["proje:goruntule", "rapor:goruntule"],
    ),
}

DEFAULT_ROLE = "satis"


async def ensure_role_defaults() -> None:
    """Hazır rolleri tohumlar; var olan rol yetkilerine dokunmaz."""
    for kod, (label, yetkiler) in ROLE_DEFAULTS.items():
        mevcut = await db.roles.find_one({"kod": kod})
        if not mevcut:
            await db.roles.insert_one(
                {"kod": kod, "label": label, "yetkiler": yetkiler, "sistem": kod == "admin"}
            )
    # admin rolü her zaman tam yetkili kalır
    await db.roles.update_one(
        {"kod": "admin"}, {"$set": {"yetkiler": ALL_PERMISSIONS, "sistem": True}}
    )
    # rolü olmayan kullanıcılara varsayılan rol
    await db.users.update_many({"rol": {"$exists": False}}, {"$set": {"rol": DEFAULT_ROLE}})


async def permissions_of(rol: str) -> list[str]:
    if rol == "admin":
        return ALL_PERMISSIONS
    role = await db.roles.find_one({"kod": rol})
    return list(role.get("yetkiler", [])) if role else []


async def user_permissions(user: dict) -> list[str]:
    return await permissions_of(user.get("rol", DEFAULT_ROLE))


def require(*actions: str):
    """Route bağımlılığı: yetki yoksa 403 — varsayılan reddet."""

    async def dependency(user: dict = Depends(current_user)) -> dict:
        yetkiler = await user_permissions(user)
        eksik = [a for a in actions if a not in yetkiler]
        if eksik:
            etiket = PERMISSIONS.get(eksik[0], eksik[0])
            raise HTTPException(status_code=403, detail=f"Bu işlem için yetkiniz yok: {etiket}")
        return user

    return dependency
