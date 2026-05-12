from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Set
import heapq
import math

from harita import Harita
from dfs import _engel_cezasi as dfs_engel_cezasi


# ============================================================
#  HEDEF DÜĞÜM
# ============================================================
HEDEF_ID = 136

# Engel toleransı (çok katı olmasın diye)
TOLERANS = 0.25


# ============================================================
#  HEURİSTİK (h)
# ============================================================
def _heuristik(harita: Harita, dugum_id: int) -> float:
    tablo = getattr(harita, "heuristik_136", None)

    # Heuristic dosyası varsa onu kullan
    if isinstance(tablo, dict) and dugum_id in tablo:
        return float(tablo[dugum_id])

    # Yedek: kuş uçuşu mesafe
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])
    if (
        isinstance(dugumler, list)
        and 0 <= dugum_id < len(dugumler)
        and 0 <= HEDEF_ID < len(dugumler)
    ):
        x1, y1 = dugumler[dugum_id]
        x2, y2 = dugumler[HEDEF_ID]
        return math.hypot(x2 - x1, y2 - y1)

    return float("inf")


# ============================================================
#  ENGEL CEZASI (DFS sabitlerinin 1/10'u)
# ============================================================
def _engel_cezasi_greedy(harita, engeller, a_id, b_id):
    ceza = dfs_engel_cezasi(harita, engeller, a_id, b_id)
    if ceza is None:
        return None  # Yol kapalı
    return float(ceza) / 10.0


# ============================================================
#  YARI-SAF, TOLERANSLI VE TOPLAM-BAZLI GREEDY
# ============================================================
def greedy_yol(
    harita: Harita,
    baslangic_id: int,
    engeller: List,
    yasakli_kenarlar: Optional[Set[Tuple[int, int]]] = None,
) -> List[int]:

    graf: Dict[int, Dict[int, float]] = getattr(harita, "ikili_yol_graf", {})
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])
    yasakli_kenarlar = yasakli_kenarlar or set()

    if baslangic_id == HEDEF_ID:
        return [baslangic_id]

    # PQ: artık h değil, TOPLAM (h + ceza) ile sıralıyoruz
    acik = []
    ilk_h = _heuristik(harita, baslangic_id)
    heapq.heappush(acik, (ilk_h, baslangic_id))

    parent = {baslangic_id: None}
    visited = set()

    max_gen = max(200, len(dugumler) * 3)
    gen = 0

    while acik and gen < max_gen:
        _, simdiki = heapq.heappop(acik)

        if simdiki in visited:
            continue

        visited.add(simdiki)
        gen += 1

        if simdiki == HEDEF_ID:
            break

        komsular = graf.get(simdiki, {})

        komsu_bilgi = []
        for komsu in komsular:
            if komsu in visited or komsu >= len(dugumler):
                continue

            kenar = tuple(sorted((simdiki, komsu)))
            if kenar in yasakli_kenarlar:
                continue

            h = _heuristik(harita, komsu)
            if h == float("inf"):
                continue

            ceza = _engel_cezasi_greedy(harita, engeller, simdiki, komsu)
            if ceza is None:
                continue

            toplam = h + ceza

            komsu_bilgi.append({
                "id": komsu,
                "h": h,
                "ceza": ceza,
                "toplam": toplam,
            })

        if not komsu_bilgi:
            continue

        # En düşük h
        min_h = min(k["h"] for k in komsu_bilgi)

        # ENGEL YÜZÜNDEN çok kötüleşen yolları ele
        filtre = [
            k for k in komsu_bilgi
            if not (k["ceza"] > 0 and k["toplam"] > min_h + TOLERANS)
        ]

        # Hepsi elendiyse → fallback
        if not filtre:
            filtre = [min(komsu_bilgi, key=lambda x: x["toplam"])]

        # TOPLAM (h + ceza) ile sıralanmış bir PQ’ya ekle
        for k in filtre:
            parent[k["id"]] = simdiki
            heapq.heappush(acik, (k["toplam"], k["id"]))

    # Hedef bulunmadıysa
    if HEDEF_ID not in visited:
        return []

    # ROTA YENİDEN OLUŞTURULUR
    rota = []
    cur = HEDEF_ID
    while cur is not None:
        rota.append(cur)
        cur = parent.get(cur)
    rota.reverse()

    return rota


# ============================================================
#  ROTALAMA
# ============================================================
def greedy_rotala(
    harita: Harita,
    baslangic_id: int,
    engeller: List,
    yasakli_kenarlar=None,
    mevcut_rota=None
):
    yeni = greedy_yol(harita, baslangic_id, engeller, yasakli_kenarlar)

    if not yeni or yeni[-1] != HEDEF_ID:
        return mevcut_rota or []

    return yeni
