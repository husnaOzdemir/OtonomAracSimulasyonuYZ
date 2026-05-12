# optimal_sezgisel.py
# -*- coding: utf-8 -*-
"""
Bu modül iki rota planlayıcı içerir:
1) A*  (astar_yol)
2) IDA* (ida_star_yol)

- Düğümler: harita.ikili_yol_dugumleri  (index -> (x, y))
- Kenarlar: harita.ikili_yol_graf[u][v] = maliyet (taban maliyet)

- Engel etkisi:
    - YolCalismasi: ilgili kenarı tamamen kapatır (o kenar yok sayılır)
    - Diğer engeller: kenar maliyetine pozitif "ceza" ekler

- Heuristik h(n):
    - hedef 136 ise: harita.heuristik_136 (hazır tablo)
    - aksi halde: Öklid (kuş uçuşu) mesafe

not:
- Simülasyonda engeller dinamik eklenebildiği için rota "aktifken" yeni engel gelirse
  yeni bir planlama koşusu başlatılır (replan). Bu yüzden A* hedefe ulaştığı an durdurulur.
"""

import math
import heapq
from typing import Dict, List, Optional, Set, Tuple

# Engel türleri: "hangi engel ne ceza veriyor" ayrımı için sınıf türlerini kullanıyoruz
from engel import HizKesici, KayganZemin, TrafikIsigi, YayaGecidi, YolCalismasi


def _heuristik(harita, dugum_id: int, hedef_id: int) -> float:
    """
    Heuristik fonksiyon h(n): "n düğümünden hedefe kalan tahmini maliyet".

    - A* ve IDA* her düğüm için f(n) = g(n) + h(n) kullanır.
    - h(n) kabul edilebilir (admissible) olursa A* optimal çözüm garantisine yaklaşır.
      (Bizim durumda Öklid mesafe genelde alt sınırdır; ancak engel cezaları pozitiftir,
       yani gerçek maliyet Öklid’den büyük olma eğilimindedir. Bu pratikte uygundur.)

    Uygulama kararı:
    - Eğer hedef 136 ise, önceden hazırlanmış heuristik tablosu kullanılıyor.
      Bu performansı artırır (her seferinde Öklid hesaplamaya gerek kalmaz).
    """
    # 1) Özel hedef: 136 ise hazır tabloyu tercih et
    if hasattr(harita, "heuristik_136") and hedef_id == 136:
        h_tablo = getattr(harita, "heuristik_136", {})
        if dugum_id in h_tablo:
            return h_tablo[dugum_id]
        
    # Güvenlik: düğüm listesi yoksa veya indeksler geçersizse heuristik 0 kabul edilir.  
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])
    if (
        not dugumler
        or dugum_id < 0
        or hedef_id < 0
        or dugum_id >= len(dugumler)
        or hedef_id >= len(dugumler)
    ):
        # Veri eksik veya id hatalı ise heuristiği 0 döndürmek güvenli fallback'tir.
        # (A* daha çok Dijkstra'ya yaklaşır, ama hata fırlatmaz.)
        return 0.0
    

    # 3) Öklid mesafesi (kuş uçuşu tahmini maliyet)
    x1, y1 = dugumler[dugum_id]
    x2, y2 = dugumler[hedef_id]
    return math.hypot(x2 - x1, y2 - y1)


def _engel_cezasi(harita, engeller, a_id: int, b_id: int) -> Optional[float]:
    """
    Engel cezası: (a_id -> b_id) kenarı üzerinde engel var mı diye kontrol eder.

    - A* / IDA* maliyet duyarlıdır; kenar maliyeti artarsa g(n) artar => f(n) artar.
      Bu da "masraflı yolları ilerletmekten kaçın" fikrini doğrudan uygular.

    Davranış:
    - YolCalismasi: Kenarı tamamen KAPATIR => None döner (bu kenar kullanılmaz)
    - Diğer engeller: Pozitif ceza döner => kenar maliyetine eklenir

    Neden kenar boyunca örnekleme yapıyoruz?
    - Engel, iki düğümün tam üzerinde olmayabilir; çizgi-segment boyunca kesişme aranır.
    - Bu yüzden a->b doğrusu üzerinde birkaç noktada "engel içinde miyim?" kontrol edilir.

    Neden aynı engeli birden fazla saymıyoruz?
    - Örnekleme ile aynı engeli birden çok noktada yakalanabilir.
      Aynı engeli her seferinde toplarnırsa ceza yapay şekilde şişer.
      Bu da “bir engel = bir ceza” mantığını bozar
    """
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])
    if (
        not dugumler
        or a_id < 0
        or b_id < 0
        or a_id >= len(dugumler)
        or b_id >= len(dugumler)
    ):
        # Kenar uçları geçersizse bu kenarı güvenli şekilde "kullanma"
        return None

    p1 = dugumler[a_id]
    p2 = dugumler[b_id]
    uzunluk = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    # Örnek sayısı: kenar uzunluğu büyüdükçe daha fazla nokta kontrol ederek kaçırmayı azaltıyoruz.
    # min 6 adım: kısa kenarlarda bile en az birkaç nokta kontrol edilsin.
    adim = max(6, int(uzunluk / 20)) if uzunluk > 0 else 1

    toplam_ceza = 0.0

    # Aynı engeli tekrar saymamak için: id(engel) bazlı "görülen" kümesi
    gorulen = set()

    for i in range(adim + 1):
        oran = i / adim
        x = p1[0] + (p2[0] - p1[0]) * oran
        y = p1[1] + (p2[1] - p1[1]) * oran

        for engel in engeller:
            # Engel geometrisi farklı sınıflarda farklı fonksiyonla tanımlı olabilir:
            # - icinde_mi(x,y): nokta engelin içinde mi?
            # - carpisti_mi(x,y): alternatif isimlendirme
            if hasattr(engel, "icinde_mi"):
                icinde = engel.icinde_mi(x, y)
            elif hasattr(engel, "carpisti_mi"):
                icinde = engel.carpisti_mi(x, y)
            else:
                # Engel sınıfı geometrik kontrol sunmuyorsa atla
                continue

            if not icinde:
                continue

            # Yol çalışması: bu kenar tamamen "yasak"
            # -> A* ve IDA* bu kenarı değerlendirmesin diye None döndürürüz.
            if isinstance(engel, YolCalismasi) and icinde:
                return None

            # Aynı engeli, örnekleme noktalarında birden fazla yakalayabiliriz.
            # Bu durumda tekrar ceza yazmak maliyeti yapay şişirir.
            eid = id(engel)
            if eid in gorulen:
                continue
            gorulen.add(eid)

            # Ceza ölçeği: Harita yol kalınlığına göre ayarlanır (simülasyonda "ölçek" görevi görür).
            # Bu sayede ceza değerleri haritanın görsel/mesafe ölçeğiyle tutarlı kalır.
            yol_k = getattr(harita, "YOL_KALINLIK", 100)  

            # Engel tipine göre ceza katsayıları:
            # Trafik ışığı: bekleme/gecikme -> yüksek ceza
            if isinstance(engel, TrafikIsigi):
                toplam_ceza += yol_k * 0.7
                continue

            # Kasis: hız düşürme -> orta-yüksek ceza
            if isinstance(engel, HizKesici):
                toplam_ceza += yol_k * 0.6
                continue

            # Kaygan zemin: risk/azalma -> orta ceza
            # Not: Negatif ceza vermiyoruz. Negatif maliyetler A*/IDA* varsayımlarını bozabilir.
            if isinstance(engel, KayganZemin):
                toplam_ceza += yol_k * 0.4
                continue

            # Yaya geçidi: yavaşlama -> orta ceza
            if isinstance(engel, YayaGecidi):
                toplam_ceza += yol_k * 0.5


    return toplam_ceza

def _kenar_maliyeti(
    harita,
    graf: Dict[int, Dict[int, float]],
    dugumler,
    a: int,
    b: int,
    engeller,
    yasakli_kenarlar: Set[Tuple[int, int]],
) -> Optional[float]:
    """
    (a -> b) kenarının toplam maliyetini verir:

    toplam = taban_maliyet + engel_cezasi
    - g(n): başlangıçtan n’e kadar birikmiş gerçek maliyet
    - Burada "gerçek maliyet" dediğimiz şey, graf taban maliyeti + engel cezalarıdır.

    Çıktı sözleşmesi:
    - Kenar yasaklıysa -> None (değerlendirme dışı)
    - YolCalismasi gibi engel kenarı kapatıyorsa -> None
    - Aksi halde pozitif bir maliyet döner

    Neden yasaklı kenarı (min, max) ile saklıyoruz?
    Yasaklı kenar kontrolü: (min,max) ile normalize ediyoruz ki (a,b) ve (b,a) aynı görülsün
    - Bazı haritalarda yol "yönsüz" gibi ele alınır.
      Aynı fiziksel yol (a,b) ve (b,a) olsun istemiyoruz.
    - tuple(sorted((a,b))) ile tek temsil elde ederiz.
    """
    # Yasaklı kenar kontrolü: (min,max) ile normalize ediyoruz ki (a,b) ve (b,a) aynı görülsün
    kenar = tuple(sorted((a, b)))
    if kenar in yasakli_kenarlar:
        return None

    # # Taban maliyet:
    # 1) Eğer graf içinde varsa onu kullan (tasarım maliyeti / yol ağırlığı)
    # 2) Yoksa fallback: Öklid (iki düğüm arası geometrik mesafe)
    w = None
    if a in graf and isinstance(graf[a], dict):
        w = graf[a].get(b)

    if w is None:
        # Graf'ta yoksa: uç düğümler geçerli mi?
        if a < 0 or b < 0 or a >= len(dugumler) or b >= len(dugumler):
            return None
        ax, ay = dugumler[a]
        bx, by = dugumler[b]
        w = math.hypot(bx - ax, by - ay)

    # 3) Engel maliyeti
    ceza = _engel_cezasi(harita, engeller, a, b)
    if ceza is None:
        # Bu kenar engel nedeniyle tamamen kapalı (örn. YolCalismasi)
        return None

    return w + ceza


def astar_yol(
    harita,
    baslangic_id: int,
    hedef_id: int,
    engeller,
    yasakli_kenarlar: Optional[Set[Tuple[int, int]]] = None,
) -> List[int]:
    """
    A* rota planlayıcı (A-star).

    Teori:
    - f(n) = g(n) + h(n)
      g(n): başlangıçtan n düğümüne kadar gerçek birikimli maliyet
      h(n): n'den hedefe tahmini maliyet (heuristik)
    - Açık liste (open set): keşfedilecek aday düğümler (priority queue / heap) en küçük f(n) değerine göre seçilir.
    - Her iterasyonda en küçük f değerine sahip düğüm "pop" edilir ve genişletilir.
    Hedef düğüm open list’ten (heap’ten) pop edildiği an, çözüm bulunmuş kabul edilir

    Bu implementasyonda özellikle iki kritik pratik iyileştirme var:
    1) "outdated entry" filtresi:
       - Aynı düğüm heap'e birden fazla kez push edilebilir.
       - En güncel (en düşük g) olmayan heap kayıtlarını pop edince çöpe atarız.
    2) hedef pop edilince bitir:
       - Bu projede dinamik engel eklendiğinde zaten yeni bir A* koşusu başlatılıyor.
       - Bu yüzden hedefe ulaştığımız anda (hedef heap'ten pop edildiğinde) aramayı bitirmek pratikte en doğru.
    """
    if baslangic_id is None or hedef_id is None:
        return []

    graf: Dict[int, Dict[int, float]] = getattr(harita, "ikili_yol_graf", {})
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])


    # Harita verileri yoksa veya ID'ler geçersizse güvenli şekilde boş rota dön
    if (
        not graf
        or not dugumler
        or baslangic_id < 0
        or hedef_id < 0
        or baslangic_id >= len(dugumler)
        or hedef_id >= len(dugumler)
    ):
        return []
    

    # Başlangıç = hedef ise rota tek düğümden ibarettir
    if baslangic_id == hedef_id:
        return [baslangic_id]

    yasakli_kenarlar = yasakli_kenarlar or set()

    # g_maliyet: "şu ana kadar bulunan en iyi g" tablosu
    # - aynı düğüm için daha iyi yol bulunursa güncellenir
    g_maliyet: Dict[int, float] = {baslangic_id: 0.0}


    # parent[n] = en iyi yolda n düğümünün bir önceki düğümü
    # Rota geri izleme (path reconstruction) için kullanılır.
    # parent: en iyi yol ağaç/ormanını geri izlemek için
    # - parent[v] = u ise: v düğümüne en iyi geliş u üzerinden bulunmuştur
    parent: Dict[int, Optional[int]] = {baslangic_id: None}

    
    genisletilen = 0   # kaç düğüm heap'ten pop edilip gerçekten işlendi
    itilen = 0         # heap'e kaç kayıt push edildi

    # open heap: (f, g, dugum_id)
    # Neden tuple'ın ilk elemanı f? ve Neden (f, g, node) tutuyoruz?
    # - heapq en küçük elemanı seçer ve tuple karşılaştırması soldan başlar.
    # - Böylece "en küçük f" öncelikli olarak seçilmiş olur (A*'ın temel kuralı).
    # - f eşitse g küçük olan önce gelsin (tie-break) => pratikte daha stabil davranır
    acik_kuyruk: List[Tuple[float, float, int]] = []

    # Başlangıç düğümü heap'e eklenir:
    # f(s) = h(s) çünkü g(s)=0
    h0 = _heuristik(harita, baslangic_id, hedef_id)
    heapq.heappush(acik_kuyruk, (h0, 0.0, baslangic_id))
    itilen += 1


    # Hedef bulundu mu? bulunduysa hedef_g hedef maliyetini taşır, yoksa None kalır.
    hedef_g = None 


    while acik_kuyruk:
        # f burada sadece heap sıralaması için kullanıldı; pop sonrası hesaplarda kullanmıyoruz.
        # Bu yüzden "_" ile "bilerek kullanmıyorum" mesajı veriyoruz.
        _, g_aktif, simdiki = heapq.heappop(acik_kuyruk)

        
        # Aynı düğüm heap'e birden çok kez push edilebilir.
        # En güncel (en düşük g) olmayan kayıt pop edilirse "çöpe atılır".
        # Örnek: önce pahalı bir yol bulundu -> (f=100,g=80,n) push
        # sonra daha ucuz yol bulundu -> (f=60,g=40,n) push
        # Heap'ten pahalı kayıt önce/sonra çıkabilir; biz sadece "en güncel g" kaydını işleriz.
        if g_aktif != g_maliyet.get(simdiki, float("inf")):
            continue

        genisletilen += 1


        # Hedef düğüm heap'ten pop edildiyse:
        # Hedef düğüm open list’ten en küçük f ile seçilip pop edildiğinde,
        # - Bu, A* sıralamasına göre artık bu hedef için elimizdeki g'nin en iyi aday olduğunu gösterir.
        # - Proje dinamik replanning yaptığı için (engel eklenince yeniden A*) burada bitirmek en mantıklısıdır.
        if simdiki == hedef_id:
            hedef_g = g_aktif
            break

        # Komşuları genişlet:
        # graf[simdiki] -> komşu düğümler
        for komsu in graf.get(simdiki, {}):
            # Güvenlik: komşu id geçerli mi?
            if komsu < 0 or komsu >= len(dugumler):
                continue

            # Kenar maliyeti: taban + engel cezası + yasaklı kenar kontrolü
            km = _kenar_maliyeti(
                harita,
                graf,
                dugumler,
                simdiki,
                komsu,
                engeller,
                yasakli_kenarlar,
            )
            if km is None:
                # Bu kenar kapalı/yasak => komşu olarak değerlendirme
                continue

            # Yeni g: simdiki düğümün en iyi g'si + kenar maliyeti
            yeni_g = g_maliyet[simdiki] + km

            # Eğer komşuya daha önce hiç gitmediysek veya daha ucuz bir yol bulduysak güncelle:
            # Bu satır slayttaki "eski pahalı yolu sil / unut" fikrinin temelidir.
            if yeni_g < g_maliyet.get(komsu, float("inf")):
                g_maliyet[komsu] = yeni_g
                parent[komsu] = simdiki

                # f = g + h (A* değerlendirme fonksiyonu)
                f_deger = yeni_g + _heuristik(harita, komsu, hedef_id)

                # Heap'e, OPEN LIST’e yeni aday kaydı ekle
                heapq.heappush(acik_kuyruk, (f_deger, yeni_g, komsu))
                itilen += 1
    

    # arama istatistikleri
    if hedef_g is not None:
        print(f"[A*] genisletilen={genisletilen}, heap_push={itilen}, hedef_g={hedef_g:.2f}")
    else:
        print(f"[A*] genisletilen={genisletilen}, heap_push={itilen}, hedef bulunamadı")

    # Hedef bulunamadıysa rota yok
    if hedef_g is None:
        return []

    # parent tablosu "hedefe giden en iyi yolu" temsil eder.
    # hedef -> parent[hedef] -> ... -> baslangic şeklinde geri gideriz.
    rota: List[int] = []
    dugum = hedef_id

    while dugum is not None:
        rota.append(dugum)
        dugum = parent.get(dugum)

    rota.reverse()

    # Zincir kırılmışsa (başlangıca ulaşamıyorsak) güvenli çık:
    # Bu, olağandışı bir durumdur; ama dinamik engel / veri tutarsızlığı olursa patlamamak için kontrol.
    if not rota or rota[0] != baslangic_id:
        return []

    return rota

def ida_star_yol(
    harita,
    baslangic_id: int,
    hedef_id: int,
    engeller,
    yasakli_kenarlar: Optional[Set[Tuple[int, int]]] = None,
) -> List[int]:
    """
    IDA* (Iterative Deepening A*) rota planlayici.

    - A*'ın bellek maliyeti büyüktür (open set büyür).
    - IDA* bunun yerine "f-sınırı" ile DFS yapar:
    - f(n) = g(n) + h(n)
    - Başlangıç sınırı: sinir = f(S) = 0 + h(S)
      * sınır = h(start)
      * DFS: f = g+h <= sınır olan düğümleri dolaş
      * sınırı aşan düğümlerin en küçük f değeri -> bir sonraki iterasyonun sınırı
    - Böylece bellek azalır; ancak bazı durumlarda tekrarlar artabilir.

    * f > sinir ise buda (prune) ve bu f değerini "bir sonraki sınır adayı" olarak raporla
    - Hedef bulunamadıysa: yeni_sinir = sınırı aşanlar arasındaki en küçük f
    - sinir = yeni_sinir yap ve tekrar dene
    - Böylece bellek azalır; ancak bazı durumlarda tekrarlar artabilir.
    Bu IDA* yaklaşımı:
    - Bellek açısından A*’a göre avantajlıdır (DFS stack kullanır).
    - Ancak aynı düğümler farklı iterasyonlarda tekrar görülebildiği için zaman maliyeti artabilir.

    Bu implementasyonda:
    - Komşular heuristiğe göre sıralanır (hedefe yakın olanı önce denemek pratikte hız kazandırır).
    - Cycle kırma: aynı düğümü yol içinde tekrar ziyaret etmeyiz.
    - Güvenlik limiti: max_genisleme ile uygulamanın kilitlenmesi engellenir.
    """
    graf: Dict[int, Dict[int, float]] = getattr(harita, "ikili_yol_graf", {})
    dugumler = getattr(harita, "ikili_yol_dugumleri", [])

    # Temel kontroller
    if (
        baslangic_id is None
        or hedef_id is None
        or not graf
        or not dugumler
        or baslangic_id < 0
        or hedef_id < 0
        or baslangic_id >= len(dugumler)
        or hedef_id >= len(dugumler)
    ):
        return []

    if baslangic_id == hedef_id:
        return [baslangic_id]

    yasakli_kenarlar = yasakli_kenarlar or set()
    INF = float("inf")


    # Komşu sıralaması:
    # - Heuristiği küçük olan komşuyu önce denemek hedefe daha hızlı ulaşma olasılığını artırır.
    # - pratikte IDA*’ı hızlandırır.
    komsu_sirasi: Dict[int, List[int]] = {}
    for u, komsular in graf.items():
        vs: List[int] = []
        for v in komsular.keys():
            kenar = tuple(sorted((u, v)))
            if kenar in yasakli_kenarlar:
                continue
            vs.append(v)
        # Heuristige gore sirala (h ne kadar kucukse o kadar once)
        vs.sort(key=lambda v: _heuristik(harita, v, hedef_id))
        komsu_sirasi[u] = vs

    # İlk f-sınırı: f(start) = 0 + h(start)
    sinir = _heuristik(harita, baslangic_id, hedef_id)

    # DFS'in üzerinde yürüdüğü anlık yol
    yol: List[int] = [baslangic_id]

    # Güvenlik limiti (uygulama kilitlenmesin)
    max_genisleme = 200_000
    genisleme_sayaci = 0

    def dfs(dugum: int, g: float, sinir: float, en_iyi_g: Dict[int, float]):
        """
        IDA* DFS adımı:
        - Eğer f=g+h sınırı aşarsa -> o f değerini geri döndür (bir sonraki sınır adaylarından biri)
        - Eğer hedef bulunursa -> "HEDEF" döndür
        - Aksi halde -> aşımlar arasındaki minimum f'yi döndür
        """
        nonlocal genisleme_sayaci

        f = g + _heuristik(harita, dugum, hedef_id)

        # 1) Sınır aşıldıysa buda ve bu f değerini üst kademeye bildir
        if f > sinir:
            return f

        # 2) Hedef bulunduysa dur
        if dugum == hedef_id:
            return "HEDEF"

        # Guvenlik limiti
        if genisleme_sayaci >= max_genisleme:
            return INF

        min_asim = INF

        # Komşular: heuristige gore siralanmis
        for komsu in komsu_sirasi.get(dugum, []):
            # Cycle kırma: mevcut yolda olan düğüme tekrar gitme
            if komsu in yol:
                continue

            km = _kenar_maliyeti(
                harita,
                graf,
                dugumler,
                dugum,
                komsu,
                engeller,
                yasakli_kenarlar,
            )
            if km is None:
                continue

            yeni_g = g + km

            # Aynı düğüme daha iyi g ile zaten gelmişsek bu dalı atla (pruning)
            # Not: Bu tablo her iterasyonda sıfırlanıyor; böylece klasik IDA* döngüsü korunuyor.
            if yeni_g >= en_iyi_g.get(komsu, float("inf")):
                continue

            en_iyi_g[komsu] = yeni_g
            yol.append(komsu)
            genisleme_sayaci += 1

            sonuc = dfs(komsu, yeni_g, sinir, en_iyi_g)
            if sonuc == "HEDEF":
                return "HEDEF"


            # Sınırı aşanlar arasında minimum f’yi yakala
            if isinstance(sonuc, (int, float)) and sonuc < min_asim:
                min_asim = sonuc

            yol.pop()

        return min_asim

    # hedef bulunana ya da arama tikanana kadar siniri artir
    while True:
        genisleme_sayaci = 0
        # Her f-kontur icin en iyi g tablosunu sifirla
        en_iyi_g: Dict[int, float] = {baslangic_id: 0.0}

        sonuc = dfs(baslangic_id, 0.0, sinir, en_iyi_g)


         # 1) Hedef bulunduysa: o anki "yol" stack’i çözüm yoludur
        if sonuc == "HEDEF":
            # yol listesi uzerinde DFS calisiyordu; su an hedefle biten gecerli yol var
            return yol.copy()

        # 2) Yol yok veya guvenlik limiti nedeniyle durduk
        if sonuc == INF or genisleme_sayaci >= max_genisleme:
            return []

        # 3) Yeni sınır: sınırı aşanlar arasındaki en küçük f
        # "minimal f(succ) > f(S)" kavramının karşılığı budur.
        sinir = sonuc

