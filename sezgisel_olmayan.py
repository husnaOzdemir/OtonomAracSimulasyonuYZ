import heapq, math
from collections import deque
from engel import YolCalismasi, HizKesici, KayganZemin, YayaGecidi, TrafikIsigi


def _engel_cezasi(harita, engeller, a_id, b_id, taban):
    """
    taban = yol agirligi (her iki düğüm arasındaki bağlantılara atanmış maliyetler)
    engel varsa => taban * (1 + engel katsayisi)
    yol calismasi varsa => None
    """
    dugumler = harita.ikili_yol_dugumleri

    gx1, gy1 = dugumler[a_id]
    gx2, gy2 = dugumler[b_id]

    # Kenar taramasi grid biriminde; carpisma testi icin piksele ceviriyoruz
    uzunluk = math.hypot(gx2 - gx1, gy2 - gy1)
    adim = max(6, int(uzunluk * 2))

    # Engel katsayilari (taban maliyet * (1 + katsayi))
    agirliklar = {
        YolCalismasi: None,  # None => kenar kapali
        HizKesici: 0.5,
        KayganZemin: 0.4,
        YayaGecidi: 0.6,
        TrafikIsigi: 0.7,
    }

    gorulen = set()
    toplam = 0.0

    for i in range(adim + 1):
        t = i / adim
        x = gx1 + (gx2 - gx1) * t
        y = gy1 + (gy2 - gy1) * t
        px, py = harita.grid_to_pixel(x, y)  # carpisma testi icin pixel

        for engel in engeller:
            carpma_fn = getattr(engel, "carpisti_mi", None)
            icinde_fn = getattr(engel, "icinde_mi", None)

            carpti = False
            if callable(carpma_fn):
                try:
                    carpti = carpma_fn(px, py)
                except Exception:
                    carpti = False

            if not carpti and callable(icinde_fn):
                try:
                    carpti = icinde_fn(px, py)
                except Exception:
                    carpti = False

            if not carpti:
                continue

            if isinstance(engel, YolCalismasi):
                return None

            for cls, k in agirliklar.items():
                if k is None:
                    continue
                if isinstance(engel, cls) and id(engel) not in gorulen:
                    toplam += k
                    gorulen.add(id(engel))
                    break
    return taban * (1 + toplam)

# -----------------------------
#   KOMSU LISTESI
def _komsu_listesi(graf, node):
    komsular = graf.get(node, {})
    if isinstance(komsular, dict):
        return komsular.items()
    return [(k, None) for k in komsular] 


def bfs_yol(harita, baslangic_id, hedef_id, engeller, yasakli_kenarlar=None):
    yasakli_kenarlar = yasakli_kenarlar or set()
    graf = getattr(harita, "ikili_yol_graf", {})
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])

    best_steps = {baslangic_id: 0}       # en az adım sayısı
    best_cost = {baslangic_id: 0.0}      # aynı adımda en düşük maliyet
    kuyruk = deque([(baslangic_id, [baslangic_id], 0.0, 0)])  # node, path, cost, steps

    while kuyruk:
        node, yol, cost, steps = kuyruk.popleft()

        # Daha kötü (daha çok adım) veya aynı adımda daha pahalı durumları ele
        if steps > best_steps[node]:
            continue
        if steps == best_steps[node] and cost > best_cost[node] + 1e-9:
            continue

        if node == hedef_id:
            return yol

        for komsu, km in _komsu_listesi(graf, node):
            if komsu >= len(dugumler):
                continue
            kenar = tuple(sorted((node, komsu)))
            if kenar in yasakli_kenarlar:
                continue

            # taban kenar maliyeti (grafta varsa onu kullan, yoksa euklidian)
            if km is not None:
                taban = km
            else:
                ax, ay = dugumler[node]; bx, by = dugumler[komsu]
                taban = math.hypot(bx - ax, by - ay)

            kenar_m = _engel_cezasi(harita, engeller, node, komsu, taban)
            if kenar_m is None:  # kapalı kenar
                continue

            yeni_steps = steps + 1
            yeni_cost = cost + kenar_m

            iyilesti_mi = (
                (komsu not in best_steps) or
                (yeni_steps < best_steps[komsu]) or
                (yeni_steps == best_steps[komsu] and yeni_cost < best_cost[komsu] - 1e-9)
            )
            if iyilesti_mi:
                best_steps[komsu] = yeni_steps
                best_cost[komsu] = yeni_cost
                kuyruk.append((komsu, yol + [komsu], yeni_cost, yeni_steps))

    return []



def ucs_yol(harita, baslangic_id, hedef_id, engeller, yasakli_kenarlar=None):
    yasakli_kenarlar = yasakli_kenarlar or set()
    if baslangic_id == hedef_id:
        return [baslangic_id]

    graf = getattr(harita, "ikili_yol_graf", {})
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])

    def kenar_maliyeti(a, b, komsu_maliyet):
        if komsu_maliyet is not None:
            taban = komsu_maliyet
        else:
            ax, ay = dugumler[a]
            bx, by = dugumler[b]
            taban = math.hypot(bx - ax, by - ay)

        ceza = _engel_cezasi(harita, engeller, a, b, taban)
        return ceza  # None olabilir

    en_iyi = {}
    pq = [(0.0, baslangic_id, [baslangic_id])]

    while pq:
        maliyet, node, path = heapq.heappop(pq)

        if node in en_iyi and maliyet >= en_iyi[node]:
            continue
        en_iyi[node] = maliyet

        if node == hedef_id:
            return path

        for komsu, km in _komsu_listesi(graf, node):
            if komsu >= len(dugumler):
                continue

            kenar = tuple(sorted((node, komsu)))
            if kenar in yasakli_kenarlar:
                continue

            km2 = kenar_maliyeti(node, komsu, km)
            if km2 is None:
                continue  # kapali yol

            yeni = maliyet + km2

            if komsu not in en_iyi or yeni < en_iyi[komsu]:
                heapq.heappush(pq, (yeni, komsu, path + [komsu]))

    return []
