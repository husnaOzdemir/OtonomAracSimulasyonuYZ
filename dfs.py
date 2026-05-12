# dfs.py
import math
from engel import YolCalismasi, YayaGecidi, HizKesici, KayganZemin, TrafikIsigi

HEDEF_ID = 136

# Engel maliyetleri
SABIT_MALIYETLER = {
    "KIRMIZI_ISIK": 7.0,
    "YAYA_GECIDI": 6.0,
    "HIZ_KESICI": 5.0,
    "KAYGAN_ZEMIN": 4.0,
}

# Engel cezası (aynı senin mevcut kodun)
def _engel_cezasi(harita, engeller, a, b):
    dugumler = harita.ikili_yol_dugumleri
    ax, ay = dugumler[a]
    bx, by = dugumler[b]

    gorulen = set()
    toplam = 0.0

    for i in range(20):
        t = i / 20.0
        x = ax*(1-t) + bx*t
        y = ay*(1-t) + by*t

        for e in engeller:

            # Yol çalışması → dal tamamen kapalı
            if isinstance(e, YolCalismasi) and e.icinde_mi(x, y):
                return None

            temas = False
            if hasattr(e, "carpisti_mi") and e.carpisti_mi(x, y):
                temas = True
            elif hasattr(e, "icinde_mi") and e.icinde_mi(x, y):
                temas = True

            if not temas:
                continue

            eid = id(e)
            if eid in gorulen:
                continue
            gorulen.add(eid)

            # Tip bazlı ceza
            if isinstance(e, TrafikIsigi):
                toplam += SABIT_MALIYETLER["KIRMIZI_ISIK"]
            elif isinstance(e, YayaGecidi):
                toplam += SABIT_MALIYETLER["YAYA_GECIDI"]
            elif isinstance(e, HizKesici):
                toplam += SABIT_MALIYETLER["HIZ_KESICI"]
            elif isinstance(e, KayganZemin):
                toplam += SABIT_MALIYETLER["KAYGAN_ZEMIN"]

    return toplam


# ============================================================
#  🔥 DFS — DAL BAZLI ERKEN BUDAMA (B MODELİ)
#  Engel maliyeti yüksekse DAL kesilir ama DFS çalışmaya devam eder
# ============================================================

def dfs_yol(harita, baslangic, engeller, yasakli=None):
    hedef = HEDEF_ID
    yasakli = yasakli or set()
    graf = harita.ikili_yol_graf

    ESIG = 17.0  # Senin belirlediğin kritik eşik

    stack = [(baslangic, [baslangic])]
    visited = set()

    while stack:
        dugum, yol = stack.pop()

        if dugum == hedef:
            return yol

        visited.add(dugum)

        for komsu in graf.get(dugum, []):
            if komsu in visited:
                continue

            kenar = tuple(sorted((dugum, komsu)))
            if kenar in yasakli:
                continue

            # 🔥 Bu kısım kritik: DAL BAZLI ERKEN BUDAMA
            ceza = _engel_cezasi(harita, engeller, dugum, komsu)

            if ceza is None:
                # yol çalışması → dal tamamen yasaklanır
                continue

            if ceza > ESIG:
                # Bu dal kapatılır ama DFS devam eder
                continue

            # Engel düşükse DFS derine inmeye devam eder
            stack.append((komsu, yol + [komsu]))

    return []
