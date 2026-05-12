import pygame
import sys
import math
import json
import os
from typing import List, Optional, Callable
import csv 
from io import StringIO 
import random
from sezgisel_olmayan import _engel_cezasi as _engel_cezasi_legacy
from optimal_sezgisel import _kenar_maliyeti as _kenar_maliyeti_opt
from greedy import _engel_cezasi_greedy
from dfs import _engel_cezasi as _engel_cezasi_dfs
from harita import Harita
from araba import Araba as HaritaAraba
from npc_araba import npc_arac_uret, NPCArac
from engel import (
    Engel,
    YayaGecidi,
    YolCalismasi,
    HizKesici,
    TrafikIsigi,
    KayganZemin,
    en_yakin_duz_segmente_projeksiyon,
    engel_uzunlugunu_degistir,
    engel_dondur_90,
    
)

class Game:

    # Simülasyon Paneli
    def __init__(self, genislik: int = 1500, yukseklik: int = 700):
        
        # --- DEBUG ÖZELLİĞİ ---
        self.debug = False
        print("--- DEBUG MODU ---")
        print("Düğüm ekleme/görme aracını açmak için 'D' tuşuna basın.")
        print("Debug modu açılırken panel/engel tıklaması çalışmaz.")
        print("-" * 20)
        
        # Maliyetleri çizmek için font tanımlama
        try:
            pygame.font.init()
            self.cost_font = pygame.font.Font(None, 24)
        except:
            self.cost_font = None


        # Manuel düğüm yönetimi için gerekli attribute'lar
        self.dugum_dosya_yolu = "manuel_dugumler.json"
        self.manuel_dugumler: List[tuple] = []
        self.manuel_baglantilar: List[tuple] = []
        self.dugum_ekleme_modu = False
        self.secili_dugum_id: Optional[int] = None

        self.harita = Harita(genislik, yukseklik)
        
        # Kaydedilmiş düğümleri yükle (harita oluşturulduktan sonra)
        self._manuel_dugumleri_yukle()
        
        # MALİYET ENTEGRASYONU: Yönlü maliyet atamasını yap
        if len(self.manuel_dugumler) > 0:
            self._maliyetleri_yukle() 
        
        self.engeller: List[Engel] = []
        self.npcs: List[NPCArac] = []
        self.secili_engel: Optional[Engel] = None
        self.surukleniyor = False
        self.suruklenen_yeni_isik: Optional[TrafikIsigi] = None
        self.algoritma_opsiyonlari: List[str] = [
            "BFS",       # 1
            "UCS",       # 2
            "A*",        # 3
            "IDA*",      # 4
            "Greedy",    # 5
            "DFS"        # 6 
]

        self.secili_algoritma: Optional[str] = None
        self.algoritma_btnleri: List[pygame.Rect] = []
        self.algoritma_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.algoritma_basla_ms: Optional[int] = None
        self.algoritma_bitis_ms: Optional[int] = None
        
        self.dinamik_maliyet = 0.0
        self.onceki_dugum = None

        self._katedilen_yol: List[tuple[int, int]] = []


        # Başlangıç düğümleri: A, B, C
        self.mumkun_baslangiclar = [4, 78, 98]
        self.baslangic_etiketleri = ["A", "B", "C"]
        self.secili_baslangic_index: int = 0   # varsayılan A noktası
        self.baslangic_btnleri: List[pygame.Rect] = []

        # Seçili başlangıç düğümüne göre arabayı konumlandır
        dugumler = getattr(self.harita, "ikili_yol_dugumleri", [])
        if dugumler and self.mumkun_baslangiclar:
            bas_id = self.mumkun_baslangiclar[self.secili_baslangic_index]
            if 0 <= bas_id < len(dugumler):
                baslangic_x, baslangic_y = dugumler[bas_id]
            else:
                baslangic_x = self.harita.GENISLIK // 2
                baslangic_y = self.harita.YUKSEKLIK // 2
        else:
            baslangic_x = self.harita.GENISLIK // 2
            baslangic_y = self.harita.YUKSEKLIK // 2

        def get_engeller() -> List[Engel]:
            return self.engeller

        def get_npcs() -> List[NPCArac]:
            return self.npcs

        araba_uzunluk = int(self.harita.YOL_KALINLIK * 0.7)
        araba_genislik = int(self.harita.YOL_KALINLIK * 0.35)
        # baslangic_x, baslangic_y = self.harita.kose(2, 2)
        
        self.araba = HaritaAraba(
            self.harita,
            get_engeller,
            get_npcs,
            baslangic_x,
            baslangic_y,
            araba_uzunluk,
            araba_genislik,
            gorsel_yolu="mainaraba.png",
            algoritma_getir=lambda: self.secili_algoritma,
        )
        self.araba.onceki_dugum_id = None 

        self._ek_engelleri_baslat()
        
        self.harita.ekran.fill(self.harita.CIMEN)
        for yol in self.harita.yollar:
            self.harita.yol_ciz(yol)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_1, self.harita.KAVSAK_YARICAP)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_2, self.harita.KAVSAK_YARICAP)
        self._cimen_kenarlarini_filtrele()
        
        self.npcs = npc_arac_uret(
            self.harita,
            araba_uzunluk,
            araba_genislik,
            self.araba.x,
            self.araba.y,
            get_engeller,
            get_npcs,
            ana_araba=self.araba,
        )

        # Sonuç panelindeki hız slider'ı için başlangıç değerleri
        self.hiz_slider_baseline_hiz = max(0.1, getattr(self.araba, "normal_maks_hiz", 1.0))
        self.hiz_slider_baseline_ivme = getattr(self.araba, "normal_ivme", 0.12)
        self.hiz_slider_min = max(0.15, self.hiz_slider_baseline_hiz * 0.25)
        self.hiz_slider_max = self.hiz_slider_baseline_hiz
        self.hiz_slider_deger = self.hiz_slider_baseline_hiz
        self.hiz_slider_rect: Optional[pygame.Rect] = None
        self.hiz_slider_thumb_rect: Optional[pygame.Rect] = None
        self.hiz_slider_dragging = False
        if self.hiz_slider_min > self.hiz_slider_max:
            self.hiz_slider_min = max(0.1, self.hiz_slider_max * 0.5)
        self._ana_araba_hizini_ayarla(self.hiz_slider_deger)
        
    # Default olarak haritaya konumlanmış engeller
    def _ek_engelleri_baslat(self):
        yol_k = self.harita.YOL_KALINLIK
        self.engeller.append(YayaGecidi(self.harita, self.harita.kose(4, 10), self.harita.kose(6, 10), int(yol_k * 0.8)))
        self.engeller.append(YayaGecidi(self.harita, self.harita.kose(6, 5), self.harita.kose(3, 1), int(yol_k * 0.8)))
        self.engeller.append(YayaGecidi(self.harita, self.harita.kose(15, 10), self.harita.kose(15, 12), int(yol_k * 0.8)))
        self.engeller.append(YolCalismasi(self.harita, self.harita.kose(10, 5), self.harita.kose(10, 7), int(yol_k * 0.8)))
        self.engeller.append(HizKesici(self.harita, self.harita.kose(8, 10), self.harita.kose(9, 10), int(yol_k * 0.8)))
        self.engeller.append(HizKesici(self.harita, self.harita.kose(11, 4), self.harita.kose(12, 4), int(yol_k * 0.8)))
        self.engeller.append(TrafikIsigi(self.harita, c=5, r=6, yon='yatay', kirmizi_sure_sn=3, yesil_sure_sn=2, sari_sure_sn=1))
        self.engeller.append(TrafikIsigi(self.harita, c=9, r=2, yon='yatay', kirmizi_sure_sn=3, yesil_sure_sn=2, sari_sure_sn=1))
        self.engeller.append(TrafikIsigi(self.harita, c=15, r=8, yon='yatay', kirmizi_sure_sn=3, yesil_sure_sn=2, sari_sure_sn=1))
        self.engeller.append(KayganZemin(self.harita, self.harita.kose(11, 10), self.harita.kose(15, 10), int(yol_k * 0.75)))
        self.engeller.append(KayganZemin(self.harita, self.harita.kose(17, 5), self.harita.kose(17, 7), int(yol_k * 0.75)))

    def _araba_baslangica_konumla(self):
        """Seçili başlangıç noktasına (A/B/C) arabayı yerleştirip durumunu sıfırlar."""
        dugumler = getattr(self.harita, "ikili_yol_dugumleri", [])
        if not (dugumler and self.mumkun_baslangiclar):
            return

        if 0 <= self.secili_baslangic_index < len(self.mumkun_baslangiclar):
            bas_id = self.mumkun_baslangiclar[self.secili_baslangic_index]
        else:
            bas_id = self.mumkun_baslangiclar[0]

        if not (0 <= bas_id < len(dugumler)):
            return

        bx, by = dugumler[bas_id]
        self.araba.x, self.araba.y = bx, by
        self.araba.onceki_dugum_id = bas_id
        self.araba.aktif_patika = [bas_id]
        self.araba.aktif_adim = 0
        self.araba.hedef_dugum_id = None

        if self.araba.hedef_global_id < len(dugumler):
            hx, hy = dugumler[self.araba.hedef_global_id]
            dx, dy = hx - bx, hy - by
            if dx != 0 or dy != 0:
                self.araba.aci = -math.degrees(math.atan2(dy, dx))

        self.araba.image = self.araba.orijinal_gorsel
        self.araba.rect = self.araba.image.get_rect(center=(self.araba.x, self.araba.y))

    def _yeni_cizgisel_engel(self, cls: Callable, mx: int, my: int, hedef_uzunluk_px: int) -> Optional[Engel]:
        sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
        if sonuc is None:
            return None
        p1, p2, (px, py), _t, ux, uy = sonuc
        yarim = hedef_uzunluk_px / 2
        a = (px - ux * yarim, py - uy * yarim)
        b = (px + ux * yarim, py + uy * yarim)
        return cls(self.harita, a, b, int(self.harita.YOL_KALINLIK * 0.75))
    
    def _yeni_yaya_gecidi(self, mx: int, my: int, hedef_uzunluk_px: int) -> Optional[Engel]: 
        sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
        if sonuc is None:
            return None
        p1, p2, (px, py), _t, ux, uy = sonuc
        yarim = hedef_uzunluk_px / 2
        a = (px - yarim, py)
        b = (px + yarim, py)
        return YayaGecidi(self.harita, a, b, int(self.harita.YOL_KALINLIK * 0.75))

    def _engel_secimi(self, mx: int, my: int):
        yakin_engel = None
        yakin_mesafe = float('inf')
        for engel in self.engeller:
            if hasattr(engel, '_proj_ve_mesafe'):
                t, dik, uzunluk = engel._proj_ve_mesafe(mx, my)
                if 0 <= t <= uzunluk and dik <= max(getattr(engel, 'genislik', 0) / 2, 20):
                    if dik < yakin_mesafe:
                        yakin_mesafe = dik
                        yakin_engel = engel
            elif isinstance(engel, TrafikIsigi):
                dist = math.hypot(engel.pixel_pos[0] - mx, engel.pixel_pos[1] - my)
                if dist < self.harita.HUCRE * 1.2 and dist < yakin_mesafe:
                    yakin_mesafe = dist
                    yakin_engel = engel
        self.secili_engel = yakin_engel
        self.surukleniyor = self.secili_engel is not None

    def _baslangic_tiklama(self, pos) -> bool:
        """Algoritma panelinin içindeki A/B/C başlangıç butonları için tıklama kontrolü."""
        mx, my = pos
        if not self.algoritma_panel_rect.collidepoint((mx, my)):
            return False

        for idx, rect in enumerate(getattr(self, "baslangic_btnleri", [])):
            if rect.collidepoint((mx, my)):
                self.secili_baslangic_index = idx
                if self.algoritma_basla_ms is None:
                    self._araba_baslangica_konumla()
                # Sadece seçim değişecek; rota, algoritma seçildiğinde çizilecek.
                return True

        return False


    def _algoritma_tiklama(self, pos) -> bool:
        """Algoritma panelinde tiklama varsa secimi gunceller.
        Arac rota uzerindeyken de algoritma degistirilebilir.
        """
        mx, my = pos
        if not self.algoritma_panel_rect.collidepoint((mx, my)):
            return False

        for idx, rect in enumerate(self.algoritma_btnleri):
            if rect.collidepoint((mx, my)):
                self.secili_algoritma = self.algoritma_opsiyonlari[idx]
                bastan_baslat = getattr(self.araba, "hedefe_ulasti", False) or self.algoritma_basla_ms is None

                # Yolu sadece yeni bir kosuya baslarken temizle; rota degisimi yaparken gecmisi koru
                if bastan_baslat:
                    self._katedilen_yolu_temizle()
                    if hasattr(self, "araba"):
                        self.araba.katedilen_patika = []

                # Maliyet ve zaman sayaclarini sadece yeni kosuya girerken sifirla
                if bastan_baslat:
                    self.dinamik_maliyet = 0.0
                    self.onceki_dugum = None
                self.algoritma_bitis_ms = None

                # Ilk baslatma ya da hedefe ulastiktan sonra yeniden konumlandir
                if bastan_baslat:
                    self._araba_baslangica_konumla()

                # Yeni algoritmayla mevcut konumdan rota olustur
                if hasattr(self, "araba") and hasattr(self.araba, "rota_yenile"):
                    # bastan_baslat degilse adim sayaci korunur
                    self.araba.rota_yenile(keep_steps=not bastan_baslat)

                # Sureyi her algoritma degisiminde sifirla
                self.algoritma_basla_ms = pygame.time.get_ticks()

                return True
        return False

    def _kasis_etkisi(self):
        radyan = math.radians(self.araba.aci)
        kontrol_noktasi_mesafesi = self.araba.orijinal_gorsel.get_width() / 2 * 0.8
        sapma_x = kontrol_noktasi_mesafesi * math.cos(radyan)
        sapma_y = -kontrol_noktasi_mesafesi * math.sin(radyan)
        bx = self.araba.x + sapma_x
        by = self.araba.y + sapma_y
        for engel in self.engeller:
            if isinstance(engel, HizKesici) and engel.icinde_mi(bx, by):
                self.araba.hiz *= engel.carpma_orani
                break
 
    def _manuel_dugumleri_yukle(self):
        """
        Kaydedilmiş manuel düğümleri ve bağlantıları JSON dosyasından yükler.
        """
        # Başlangıç değerlerini ayarla
        if not hasattr(self, 'manuel_dugumler'):
            self.manuel_dugumler = []
        if not hasattr(self, 'manuel_baglantilar'):
            self.manuel_baglantilar = []
            
        if not os.path.exists(self.dugum_dosya_yolu):
            print(f"[!] Kayıt dosyası bulunamadı: {self.dugum_dosya_yolu}")
            print("  Yeni düğümler ekleyebilirsiniz.")
            return
        
        try:
            with open(self.dugum_dosya_yolu, 'r', encoding='utf-8') as f:
                veri = json.load(f)
            
            # Düğumleri yükle
            if "dugumler" in veri:
                self.manuel_dugumler = [(float(x), float(y)) for x, y in veri["dugumler"]]
            
            # Bağlantıları yükle (Görsel çizim için tutulur)
            if "baglantilar" in veri:
                self.manuel_baglantilar = [(int(id1), int(id2)) for id1, id2 in veri["baglantilar"]]
            
            # Yüklenen düğümleri graf'a da ekle
            if len(self.manuel_dugumler) > 0:
                if hasattr(self.harita, 'ikili_yol_dugumleri') and hasattr(self.harita, 'ikili_yol_graf'):
                    baslangic_id = len(self.harita.ikili_yol_dugumleri)
                    
                    # Düğumleri ekle
                    for x, y in self.manuel_dugumler:
                        self.harita.ikili_yol_dugumleri.append((x, y))
                    
                    # Graf'a yeni düğümleri ekle (Boş kenar sözlüğü ile)
                    for i in range(len(self.manuel_dugumler)):
                        dugum_id = baslangic_id + i
                        if dugum_id not in self.harita.ikili_yol_graf:
                            self.harita.ikili_yol_graf[dugum_id] = {}
                    
                    print("=" * 50)
                    print("[*] KAYDEDİLMİŞ DÜĞÜMLER YÜKLENDİ!")
                    print("=" * 50)
                    print(f"  [+] {len(self.manuel_dugumler)} düğüm yüklendi")
                    print(f"  [+] {len(self.manuel_baglantilar)} bağlantı yüklendi (Görsel amaçlı)")
                    print(f"  - Dosya: {self.dugum_dosya_yolu}")
                    print("=" * 50)
        except Exception as e:
            print(f"[!] HATA: Düğumler dosyadan yüklenemedi: {e}")
            print("  Yeni düğümler ekleyebilirsiniz.")

        self._graf_baglantilarini_duzgunlestir()

    # MALİYETLERİ YÜKLEME METODU
    def _maliyetleri_yukle(self):
        """
        Google Sheets'ten alınan son maliyet listesini kullanarak
        yönlü kenarları ve maliyetleri harita grafiğine (ikili_yol_graf) atar.
        """
        # Sizin sağladığınız Kaynak/Hedef/Maliyet listesinin TAMAMI
        maliyet_verisi_str = """
Kaynak Düğüm,Hedef Düğüm,Maliyet (weight)
0,2,5.0
2,4,4.0
4,7,1.5
4,39,7.0
5,4,1.6
5,3,3.0
3,1,3.4
1,0,1.0
39,41,1.0
41,43,7.0
43,45,1.0
43,46,4.0
46,47,1.0
47,45,4.0
45,44,1.5
44,42,1.0
44,62,3.0
42,40,7.0
41,40,1.5
40,54,3.0
40,38,1.0
38,39,1.5
38,7,7.0
7,6,1.6
6,5,1.5
7,8,3.0
62,63,1.5
63,61,1.0
61,60,1.5
60,42,3.0
60,62,1.0
42,43,1.5
45,44,1.5
62,63,1.5
58,60,3.0
72,61,4.0
61,59,3.0
58,59,1.5
56,58,1.0
57,56,1.5
59,57,1.0
57,55,3.0
54,56,3.0
54,55,1.5
52,54,1.0
52,38,3.0
59,70,4.0
68,57,4.0
55,141,2.0
55,53,1.0
53,52,1.5
50,52,3.0
48,50,1.0
49,48,1.5
50,51,1.5
53,51,3.0
140,53,2.0
51,66,4.0
51,49,1.0
64,49,4.0
49,11,3.0
8,48,3.0
8,11,1.5
11,10,1.6
10,9,1.5
9,6,3.0
9,8,1.6
13,10,4.0
11,12,4.0
12,64,3.0
12,15,1.5
13,12,1.6
16,13,4.0
18,16,7.0
15,14,1.6
14,17,3.0
17,19,4.0
19,20,3.0
20,22,1.6
22,23,1.5
15,22,4.0
14,13,1.5
20,14,4.0
64,66,1.0
66,67,1.5
65,64,1.5
65,15,3.0
67,65,1.0
66,140,3.0
140,141,1.0
141,68,3.0
68,70,1.0
76,65,4.0
67,78,4.0
73,72,1.5
70,71,1.5
59,70,4.0
70,72,3.0
72,74,1.0
74,75,1.5
75,73,1.0
73,71,3.0
71,69,1.0
69,138,3.0
138,139,1.0
139,67,3.0
69,68,1.5
68,69,1.5
72,61,4.0
63,74,4.0
145,96,3.0
75,90,4
90,91,1.5
91,102,4
102,103,1.5
103,118,4
118,119,1.5
119,130,3
130,131,1.5
131,137,3
137,136,1
136,129,3
131,129,1
129,128,1.5
128,130,1
128,117,3
117,116,1.5
119,117,1
116,118,1
116,101,4
101,100,1.5
100,102,1
103,101,1
100,89,4
89,88,1.5
88,90,1
91,89,1
88,73,4
71,86,4
86,88,3
86,87,1.5
87,98,4
98,99,1.5
99,114,4
114,115,1.5
115,126,3
126,127,1.5
129,127,3
126,128,3
117,115,3
114,116,3
101,99,3
98,100,3
89,87,3
127,125,1
125,124,1.5
124,126,1
124,113,3
115,113,1
113,112,1.5
112,97,4
112,114,1
99,97,1
96,98,1
97,96,1.5
96,85,4
85,84,1.5
84,69,4
84,86,1
87,85,1
138,82,2
82,84,3
82,83,1.5
85,83,3
83,145,2
145,96,3
97,143,3
143,142,1
142,95,3
80,139,2
80,82,1
81,80,1.5
83,81,1
78,80,3
81,79,3
78,79,1.5
144,81,2
144,145,1
94,144,3
79,94,4
94,95,1.5
95,106,4
106,108,3
108,110,1
108,142,2
143,110,2
110,112,3
113,111,3
110,111,1.5
111,109,1
109,108,1.5
109,107,3
111,122,3
122,124,3
125,123,3
122,123,1.5
123,133,3
133,134,4
134,135,1
135,132,5
132,121,4
123,121,1
121,120,1.5
120,122,1
120,109,3
23,25,4
104,106,1
106,107,1.5
107,105,1
105,104,1.5
104,93,4
95,93,1
93,92,1.5
92,94,1
92,77,4
79,77,1
76,78,1
22,76,3
77,76,1.5
77,23,3
23,21,1.6
21,20,1.5
21,18,4
28,92,3
93,26,3
25,26,1.5
25, 92,3
26,27,1.6
27,24,1.5
24,25,1.6
24,21,4
26,29,4
29,104,3
105,30,3
29,30,1.5
30,31,1.6
31,28,1.5
28,29,1.6
28,27,4
30,33,3
33,34,1.5
32,31,3
32,33,1.6
35,32,1.5
34,35,1.6
34,36,3.5
36,37,1.6
37,35,3.5
33,120,7
121,34,7
"""
        
        baslangic_id = len(self.harita.ikili_yol_dugumleri) - len(self.manuel_dugumler)
        
        csv_reader = csv.reader(StringIO(maliyet_verisi_str))
        next(csv_reader) # Başlık satırını atla
        
        eklenen_kenar_sayisi = 0
        for row in csv_reader:
            if len(row) < 3 or not row[0].strip().isdigit():
                continue
            try:
                dugum1_id = int(row[0].strip())
                dugum2_id = int(row[1].strip())
                cost = float(row[2].strip())
                
                gercek_id1 = baslangic_id + dugum1_id
                gercek_id2 = baslangic_id + dugum2_id
                
                if dugum1_id < len(self.manuel_dugumler) and dugum2_id < len(self.manuel_dugumler):
                    if gercek_id1 not in self.harita.ikili_yol_graf:
                         self.harita.ikili_yol_graf[gercek_id1] = {}
                         
                    self.harita.ikili_yol_graf[gercek_id1][gercek_id2] = cost
                    eklenen_kenar_sayisi += 1
                    
            except ValueError:
                continue

        print("[*] YÖNLÜ MALİYETLER GRAFİĞE BAŞARIYLA YÜKLENDİ!")
        print(f"  - Toplam {eklenen_kenar_sayisi} yönlü kenar atandı (Sağ şerit kuralı ile belirlenen).")
        self._graf_baglantilarini_duzgunlestir()



    def _graf_baglantilarini_duzgunlestir(self):
        '''Keep only allowed connections between nodes.

        - Non-manual edges are restricted to axis-aligned (horizontal/vertical) pairs.
        - Manual nodes follow the adjacency defined in manuel_baglantilar; any edge that
          is not listed is removed even if diagonal.
        '''
        dugumler = getattr(self.harita, "ikili_yol_dugumleri", []) or []
        graf = getattr(self.harita, "ikili_yol_graf", {})
        tolerance = max(4.0, getattr(self.harita, "HUCRE", 50) * 0.15)
        manuel_count = len(getattr(self, "manuel_dugumler", []))
        manuel_start = len(dugumler) - manuel_count if manuel_count else len(dugumler)
        manuel_allowed = set()
        if manuel_count and hasattr(self, "manuel_baglantilar"):
            for id1, id2 in self.manuel_baglantilar:
                if not (0 <= id1 < manuel_count and 0 <= id2 < manuel_count):
                    continue
                global_a = manuel_start + id1
                global_b = manuel_start + id2
                if global_a >= len(dugumler) or global_b >= len(dugumler):
                    continue
                manuel_allowed.add((global_a, global_b))
                manuel_allowed.add((global_b, global_a))

        for kaynak, komsular in list(graf.items()):
            if not isinstance(komsular, dict):
                continue
            if not (0 <= kaynak < len(dugumler)):
                continue
            ax, ay = dugumler[kaynak]
            for hedef in list(komsular.keys()):
                if not (0 <= hedef < len(dugumler)):
                    continue
                # Manual node pair: keep only allowed adjacency
                if kaynak >= manuel_start and hedef >= manuel_start:
                    if (kaynak, hedef) not in manuel_allowed:
                        del komsular[hedef]
                    continue
                # Any edge touching manual nodes is assumed intentional
                if kaynak >= manuel_start or hedef >= manuel_start:
                    continue
                bx, by = dugumler[hedef]
                dx = abs(ax - bx)
                dy = abs(ay - by)
                if dx > tolerance and dy > tolerance:
                    del komsular[hedef]

    def _renk_cimen_mi(self, renk, tolerans: int = 18) -> bool:
        if len(renk) < 3:
            return False
        c_r, c_g, c_b = self.harita.CIMEN[:3]
        return (
            abs(c_r - renk[0]) <= tolerans and
            abs(c_g - renk[1]) <= tolerans and
            abs(c_b - renk[2]) <= tolerans
        )

    def _kenar_cimen_kesiyor_mu(self, a_id: int, b_id: int) -> bool:
        """Bir kenar�n herhangi bir noktas�n�n �im renklere denk gelip gelmedi�ini tarar."""
        dugumler = getattr(self.harita, "ikili_yol_dugumleri", [])
        if (not dugumler or
            a_id >= len(dugumler) or
            b_id >= len(dugumler)):
            return False

        p1 = dugumler[a_id]
        p2 = dugumler[b_id]
        uzunluk = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if uzunluk == 0:
            try:
                renk = self.harita.ekran.get_at((int(p1[0]), int(p1[1])))
                return self._renk_cimen_mi(renk)
            except Exception:
                return False

        adim = max(10, int(uzunluk / 20))
        for i in range(adim + 1):
            oran = i / adim
            x = p1[0] + (p2[0] - p1[0]) * oran
            y = p1[1] + (p2[1] - p1[1]) * oran
            try:
                renk = self.harita.ekran.get_at((int(x), int(y)))
            except Exception:
                continue
            if self._renk_cimen_mi(renk):
                return True
        return False

    def _cimen_kenarlarini_filtrele(self):
        graf = getattr(self.harita, "ikili_yol_graf", {})
        silinen = 0
        yasak = set()

        for a, komsular in list(graf.items()):
            for b in list(komsular.keys()):
                if self._kenar_cimen_kesiyor_mu(a, b):
                    graf[a].pop(b, None)
                    yasak.add(tuple(sorted((a, b))))
                    silinen += 1

        if yasak and hasattr(self, "araba") and hasattr(self.araba, "cimen_yasakli_kenarlar"):
            self.araba.cimen_yasakli_kenarlar.update(yasak)

        if silinen:
            print(f"[CIMEN] Yol d���n� kesen {silinen} kenar grafikten kald�r�ld�.")

    def _kaygan_zemin_etkisi(self):
        if not hasattr(self.araba, 'kaygan_zemin_uzerinde'):
             self.araba.kaygan_zemin_uzerinde = False
            
        self.araba.kaygan_zemin_uzerinde = False
        for engel in self.engeller:
            if isinstance(engel, KayganZemin):
                if engel.icinde_mi(self.araba.x, self.araba.y):
                    self.araba.kaygan_zemin_uzerinde = True
                    break

    # MALİYETLERİ HARİTA ÜZERİNE ÇİZME
    def _maliyetleri_ciz(self):
        """Debug modunda manuel düğümler arasındaki maliyetleri (ağırlıkları) çizer."""
        if not self.cost_font:
            return
            
        graf = self.harita.ikili_yol_graf
        dugumler = self.harita.ikili_yol_dugumleri
        
        # Manuel düğümlerin başlangıç ID'si (ızgara düğümlerinin bitişinden başlar)
        manuel_node_start_id = len(self.harita.ikili_yol_graf) - len(self.manuel_dugumler)
        
        for dugum1_id, komsular in graf.items():
            # Sadece manuel düğümden başlayan kenarları kontrol et
            if dugum1_id >= manuel_node_start_id:
                for dugum2_id, cost in komsular.items():
                    # Hedef de manuel düğüm olmalı (kendi aralarındaki bağlantılar)
                    if dugum2_id >= manuel_node_start_id:
                        
                        # ID'lerin geçerli olup olmadığını kontrol et
                        if dugum1_id < len(dugumler) and dugum2_id < len(dugumler):
                            
                            x1, y1 = dugumler[dugum1_id]
                            x2, y2 = dugumler[dugum2_id]
                            
                            # Orta noktayı hesapla (çizim konumu)
                            center_x = (x1 + x2) / 2
                            center_y = (y1 + y2) / 2
                            
                            # Metni hazırla (Beyaz metin, siyah arka plan)
                            cost_text_surface = self.cost_font.render(f"{cost:.1f}", True, (255, 255, 255), (0, 0, 0))
                            
                            # Metni çiz (Orta noktaya hizala)
                            self.harita.ekran.blit(cost_text_surface, 
                                                (center_x - cost_text_surface.get_width() / 2, 
                                                 center_y - cost_text_surface.get_height() / 2))


    # -------------------------------------------------------------------
    # --- handle_event metodu ---
    # -------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        # --- DEBUG MODUNU AÇMA/KAPAMA ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d: # 'D' tuşuna basıldığında
                self.debug = not self.debug # Modu tersine çevir
                print(f"DEBUG MODU: {'AÇIK' if self.debug else 'KAPALI'}")
                return # Başka bir işlem yapma

        # --- MOUSE BUTTON DOWN EVENT ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            if self._hiz_slider_tiklama(mx, my):
                return
            if self._baslangic_tiklama((mx, my)):
                return
            if self._algoritma_tiklama((mx, my)):
                return
            
            # --- NORMAL TIKLAMA (DEBUG KAPALIYKEN) ---
            if not self.debug:
                if self.harita.ok_rect and self.harita.ok_rect.collidepoint((mx, my)):
                    self.harita.kutu_acik = not self.harita.kutu_acik
                    return
                
                if self.harita.kutu_acik:
                    # --- SAYFA GEÇİŞ KONTROLLERİ ---
                    if self.harita.BTN_PAGE_LEFT and self.harita.BTN_PAGE_LEFT.collidepoint((mx, my)):
                        self.harita.panel_sayfa = max(0, self.harita.panel_sayfa - 1)
                        return
                    
                    # --- 2. SAYFA KODU (SAĞ OK) ---
                    if self.harita.BTN_PAGE_RIGHT and self.harita.BTN_PAGE_RIGHT.collidepoint((mx, my)):
                        self.harita.panel_sayfa += 1 # Sayfayı bir arttır
                        return

                    # --- Buton tıklamaları ---
                    if self.harita.BTN_ADD_YAYA and self.harita.BTN_ADD_YAYA.collidepoint((mx, my)):
                        e = self._yeni_yaya_gecidi(mx, my, int(self.harita.HUCRE * 2))
                        if e:
                            self.engeller.append(e); self.secili_engel = e
                        return
                    if self.harita.BTN_ADD_CALISMA and self.harita.BTN_ADD_CALISMA.collidepoint((mx, my)):
                        e = self._yeni_cizgisel_engel(YolCalismasi, mx, my, int(self.harita.HUCRE * 2))
                        if e:
                            self.engeller.append(e); self.secili_engel = e
                        return
                    if self.harita.BTN_ADD_KASIS and self.harita.BTN_ADD_KASIS.collidepoint((mx, my)):
                        e = self._yeni_cizgisel_engel(HizKesici, mx, my, int(self.harita.HUCRE * 1.5))
                        if e:
                            self.engeller.append(e); self.secili_engel = e
                        return
                    if self.harita.BTN_ADD_BUZLU and self.harita.BTN_ADD_BUZLU.collidepoint((mx, my)):
                        e = self._yeni_cizgisel_engel(KayganZemin, mx, my, int(self.harita.HUCRE * 2))
                        if e:
                            self.engeller.append(e); self.secili_engel = e
                        return
                    if self.harita.BTN_ADD_ISIK and self.harita.BTN_ADD_ISIK.collidepoint((mx, my)):
                        yeni_isik = TrafikIsigi(self.harita, c=0, r=0, yon='dikey')
                        yeni_isik.surukleniyor_ilk = True
                        yeni_isik.pixel_pos = (mx, my)
                        yeni_isik.gorsel_konumunu_guncelle()
                        self.suruklenen_yeni_isik = yeni_isik
                        self.engeller.append(yeni_isik)
                        return
                    if self.harita.BTN_DELETE and self.harita.BTN_DELETE.collidepoint((mx, my)):
                        if self.secili_engel in self.engeller:
                            self.engeller.remove(self.secili_engel)
                            self.secili_engel = None
                            self.surukleniyor = False
                        return
                    if self.harita.BTN_ROTATE and self.harita.BTN_ROTATE.collidepoint((mx, my)):
                        if self.secili_engel:
                            engel_dondur_90(self.harita, self.secili_engel)
                        return
                    if self.harita.BTN_LONGER and self.harita.BTN_LONGER.collidepoint((mx, my)):
                        if self.secili_engel:
                            engel_uzunlugunu_degistir(self.harita, self.secili_engel, +int(self.harita.HUCRE * 0.5))
                        return
                    if self.harita.BTN_SHORTER and self.harita.BTN_SHORTER.collidepoint((mx, my)):
                        if self.secili_engel:
                            engel_uzunlugunu_degistir(self.harita, self.secili_engel, -int(self.harita.HUCRE * 0.5))
                        return
                
                self._engel_secimi(mx, my)

        # --- MOUSE BUTTON UP EVENT ---
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # SÜRÜKLEME BİTİŞİ
            self.surukleniyor = False
            self.hiz_slider_dragging = False 
            # Yeni ışık sürükleniyorsa konumlandırmayı tamamla
            if self.suruklenen_yeni_isik is not None:
                mx, my = pygame.mouse.get_pos()
                sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
                # Konum geçerliyse ışığı yerleştir
                # Aksi halde sil
                if sonuc:
                    p1, p2, (px, py), _t, ux, uy = sonuc
                    yon = 'dikey' if abs(uy) > abs(ux) else 'yatay'
                    c = round((px - self.harita.KENAR_BOSLUK - self.harita.OFFSET_X) / self.harita.HUCRE)
                    r = round((py - self.harita.KENAR_BOSLUK - self.harita.OFFSET_Y) / self.harita.HUCRE)
                    self.suruklenen_yeni_isik.c, self.suruklenen_yeni_isik.r = c, r
                    self.suruklenen_yeni_isik.yon = yon
                    self.suruklenen_yeni_isik.pixel_pos = self.harita.kose(c, r)
                    self.suruklenen_yeni_isik.surukleniyor_ilk = False
                    self.suruklenen_yeni_isik.gorsel_konumunu_guncelle()
                else:
                    if self.suruklenen_yeni_isik in self.engeller:
                        self.engeller.remove(self.suruklenen_yeni_isik)
                self.suruklenen_yeni_isik = None

        # --- MOUSE MOTION EVENT ---
        if event.type == pygame.MOUSEMOTION:
            # SÜRÜKLEME İŞLEMİ
            # Hiz slider sürükleniyorsa öncelikli işlem o olsun
            if self.hiz_slider_dragging:
                mx, my = pygame.mouse.get_pos()
                self._hiz_slider_deger_ayarla(mx)
                return
            if self.surukleniyor and self.secili_engel is not None:
                mx, my = pygame.mouse.get_pos()
                if isinstance(self.secili_engel, TrafikIsigi):
                    sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
                    if sonuc:
                        p1, p2, (px, py), _t, ux, uy = sonuc
                        yon = 'dikey' if abs(uy) > abs(ux) else 'yatay'
                        c = round((px - self.harita.KENAR_BOSLUK - self.harita.OFFSET_X) / self.harita.HUCRE)
                        r = round((py - self.harita.KENAR_BOSLUK - self.harita.OFFSET_Y) / self.harita.HUCRE)
                        self.secili_engel.c = c
                        self.secili_engel.r = r
                        self.secili_engel.yon = yon
                        self.secili_engel.pixel_pos = self.harita.kose(c, r)
                        self.secili_engel.gorsel_konumunu_guncelle()
                else:
                    sonuc = en_yakin_duz_segmente_projeksiyon(self.harita, mx, my)
                    if sonuc:
                        p1, p2, (px, py), _t, ux, uy = sonuc
                        if isinstance(self.secili_engel, YayaGecidi):
                            yaya_gecidi_uzunlugu = self.harita.YOL_KALINLIK
                            yarim = yaya_gecidi_uzunlugu / 2
                            dik_ux = -uy
                            dik_uy = ux
                            gecici_p1 = (px + dik_ux * yarim, py + dik_uy * yarim)
                            gecici_p2 = (px - dik_ux * yarim, py - dik_uy * yarim)
                            self.secili_engel.p1 = gecici_p1
                            self.secili_engel.p2 = gecici_p2
                            self.secili_engel._yol_yonune_dik_yerlestir(gecici_p1, gecici_p2)
                        else:
                            uzunluk = math.hypot(self.secili_engel.p2[0] - self.secili_engel.p1[0], self.secili_engel.p2[1] - self.secili_engel.p1[1])
                            yarim = uzunluk / 2
                            self.secili_engel.p1 = (px - ux * yarim, py - uy * yarim)
                            self.secili_engel.p2 = (px + ux * yarim, py + uy * yarim)
            elif self.suruklenen_yeni_isik is not None:
                mx, my = pygame.mouse.get_pos()
                self.suruklenen_yeni_isik.pixel_pos = (mx, my)
                self.suruklenen_yeni_isik.gorsel_konumunu_guncelle()

    # -------------------------------------------------------------------
    def update(self):
        # Ana araç rota ile otomatik gidiyor
        self.araba.guncelle()

        # Algoritma bitiş zamanını kaydet
        if getattr(self.araba, "hedefe_ulasti", False) and self.algoritma_bitis_ms is None:
            self.algoritma_bitis_ms = pygame.time.get_ticks()

        # Fiziksel etkiler (kasis, kaygan zemin vs.)
        self._kasis_etkisi()
        self._kaygan_zemin_etkisi()
        self._katedilen_yolu_guncelle()
        
        # DİNAMİK MALİYET TOPLAMA
        # Artık düğümü haritadan değil, doğrudan arabadan alıyoruz
        aktif_dugum = getattr(self.araba, "onceki_dugum_id", None)

        # Eğer aktif düğüm mevcutsa ve önceki düğüm farklıysa maliyeti ekle
        if aktif_dugum is not None:
            if self.onceki_dugum is None:  
                # İlk kez düğüme giriyorsa
                self.onceki_dugum = aktif_dugum
            elif aktif_dugum != self.onceki_dugum:        
                # Başka bir düğüme geçtiyse, aradaki yolun maliyetini ekle
                graf = self.harita.ikili_yol_graf
                # Kenar maliyetini al
                dugumler = self.harita.ikili_yol_dugumleri

                # taban maliyet (grafta varsa al, yoksa öklid)
                w = None               
                if self.onceki_dugum in graf and aktif_dugum in graf[self.onceki_dugum]:
                    w = graf[self.onceki_dugum][aktif_dugum] 
                else:
                    # fallback: öklid (nadir; yönlü kenar yoksa)
                    if 0 <= self.onceki_dugum < len(dugumler) and 0 <= aktif_dugum < len(dugumler):
                        ax, ay = dugumler[self.onceki_dugum]
                        bx, by = dugumler[aktif_dugum]
                        w = math.hypot(bx - ax, by - ay)
                    else:
                        w = 0.0

                # --- Algoritmaya göre maliyet hesabı ---
                if self.secili_algoritma in ("A*", "IDA*"):
                    yasakli = getattr(self.araba, "cimen_yasakli_kenarlar", set())

                    km = _kenar_maliyeti_opt(
                        self.harita,
                        graf,
                        dugumler,
                        self.onceki_dugum,
                        aktif_dugum,
                        self.engeller,
                        yasakli
                    )

                    # km None ise (yol çalışması vb.) araç geçtiyse en azından tabanı yaz
                    if km is None:
                        km = w

                    self.dinamik_maliyet += km

                else:
                    # DFS ve Greedy için ilgili engel + yol maliyeti mantığını kullan
                    if self.secili_algoritma == "DFS":
                        yol_maliyeti = w
                        engel_maliyeti = _engel_cezasi_dfs(
                            self.harita,
                            self.engeller,
                            self.onceki_dugum,
                            aktif_dugum,
                        )
                        if engel_maliyeti is None:
                            engel_maliyeti = 0.0
                        self.dinamik_maliyet += yol_maliyeti + engel_maliyeti
                    elif self.secili_algoritma == "Greedy":
                        yol_maliyeti = w
                        engel_maliyeti = _engel_cezasi_greedy(
                            self.harita,
                            self.engeller,
                            self.onceki_dugum,
                            aktif_dugum,
                        )
                        if engel_maliyeti is None:
                            engel_maliyeti = 0.0
                        self.dinamik_maliyet += yol_maliyeti + engel_maliyeti
                    else:
                        # Engel cezasını da ekle
                        kenar_m = _engel_cezasi_legacy(
                            self.harita,
                            self.engeller,
                            self.onceki_dugum,
                            aktif_dugum,
                            w,
                        )
                        # Eğer ceza hesaplanamadıysa, normal maliyeti kullan
                        if kenar_m is None:
                            kenar_m = w    
                        # Toplam dinamik maliyete ekle
                        self.dinamik_maliyet += kenar_m

                self.onceki_dugum = aktif_dugum

        # NPC araçları güncelle
        for npc in self.npcs:
            npc.guncelle()

        # Trafik ışıkları ve yaya geçitlerini güncelle
        for e in self.engeller:
            if isinstance(e, TrafikIsigi):
                e.guncelle()
            elif isinstance(e, YayaGecidi):
                e.update()


    def _katedilen_yolu_temizle(self):
        self._katedilen_yol = []

    def _katedilen_yolu_guncelle(self):
        if self.secili_algoritma is None or not hasattr(self.araba, "x"):
            return
        pos = (int(round(self.araba.x)), int(round(self.araba.y)))
        if not self._katedilen_yol:
            self._katedilen_yol.append(pos)
            return
        last = self._katedilen_yol[-1]
        if math.hypot(pos[0] - last[0], pos[1] - last[1]) >= 6:
            self._katedilen_yol.append(pos)

    def _katedilen_yolu_ciz(self):
        if len(self._katedilen_yol) < 2:
            return
        pygame.draw.lines(self.harita.ekran, (0, 90, 255), False, self._katedilen_yol, 4)


    # -------------------------------------------------------------------
    # --- draw metodu (Maliyet çizim çağrısı eklendi) ---
    # -------------------------------------------------------------------
    def draw(self):
        self.harita.ekran.fill(self.harita.CIMEN)
        for yol in self.harita.yollar:
            self.harita.yol_ciz(yol)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_1, self.harita.KAVSAK_YARICAP)
        self.harita.doner_kavsak_ciz(self.harita.KAVSAK_MERKEZ_2, self.harita.KAVSAK_YARICAP)
        self._katedilen_yolu_ciz()
                # Kırmızı ile işaretlenen yerlere dekor görselleri
        self.harita.dekor_ciz()


        # --- DEBUG KODU BAŞLANGIÇ ---
        if self.debug:
            try:
                # 1. YENİ EKLENTİ: Maliyetleri çiz
                self._maliyetleri_ciz() 
                
                # 2. Izgara ve Manuel Düğumleri çiz (Görsel Yardımcı)
                dugum_yaricap = 5
                # Başlangıç ID'si (Hata olmaması için ikili_yol_dugumleri uzunluğu kullanılır)
                manuel_node_start_id = len(self.harita.ikili_yol_dugumleri) - len(self.manuel_dugumler)
                
                # Tüm düğümleri çiz
                for i, (x, y) in enumerate(self.harita.ikili_yol_dugumleri):
                    color = (255, 0, 0) if i < manuel_node_start_id else (0, 0, 255) # Izgara kırmızı, manuel mavi
                    pygame.draw.circle(self.harita.ekran, color, (int(x), int(y)), dugum_yaricap)
                    
                    # Düğüm ID'lerini de yaz
                    text_surface = self.cost_font.render(str(i - manuel_node_start_id) if i >= manuel_node_start_id else str(i), True, (0, 0, 0))
                    self.harita.ekran.blit(text_surface, (x + dugum_yaricap + 2, y - text_surface.get_height() / 2))
                    
                # 3. Manuel Bağlantıları çiz (Sarı çizgiler)
                for id1, id2 in self.manuel_baglantilar:
                    gercek_id1 = manuel_node_start_id + id1
                    gercek_id2 = manuel_node_start_id + id2
                    if gercek_id1 < len(self.harita.ikili_yol_dugumleri) and gercek_id2 < len(self.harita.ikili_yol_dugumleri):
                        p1 = self.harita.ikili_yol_dugumleri[gercek_id1]
                        p2 = self.harita.ikili_yol_dugumleri[gercek_id2]
                        pygame.draw.line(self.harita.ekran, (255, 255, 0), p1, p2, 1)

            except Exception:
                pass
        # --- DEBUG KODU BİTTİ ---

        # Engelleri çiz
        for e in self.engeller:
            e.ciz()
            if e is self.secili_engel:
                try:
                    if hasattr(e, 'p1'):
                        pygame.draw.line(self.harita.ekran, (0, 255, 255), e.p1, e.p2, 3)
                        pygame.draw.circle(self.harita.ekran, (0, 255, 255), (int(e.p1[0]), int(e.p1[1])), 6, 2)
                        pygame.draw.circle(self.harita.ekran, (0, 255, 255), (int(e.p2[0]), int(e.p2[1])), 6, 2)
                    else:
                        pygame.draw.circle(self.harita.ekran, (0, 255, 255), e.pixel_pos, 10, 3)
                except Exception:
                    pass
                
        # NPC araçlarını çiz
        for npc in self.npcs:
            if not hasattr(npc, 'ana_araba') or npc.ana_araba is None:
                npc.ana_araba = self.araba
            npc.ciz()
            
        # Ana aracın rotasını mavi çizgiyle göster
        self._rota_ciz()
        self.araba.ciz()
        self._hiz_slider_harita_ustu_ciz()
        self._algoritma_paneli_ciz()
        self._sonuc_paneli_ciz()
        self.harita.panel_ciz()
        pygame.display.flip()

    def _rota_ciz(self):
        """
        Ana aracın rotasını mavi çizgiyle çizer.

        - Öncelik: araba.aktif_patika (algoritmanın ürettiği güncel rota)
        - Eğer o boşsa: araba.son_patika (en son bilinen rota)
        - Sadece ikili_yol_graf içinde tanımlı, gerçek yol kenarları çizilir.
        - Araç ilerlese bile rota listesi kısaltılmadığı için çizgi kaybolmaz.
        """
        # 1) Hangi rota kullanılacak?
        rota = list(getattr(self.araba, "aktif_patika", []))
        if not rota:
            rota = list(getattr(self.araba, "son_patika", []))

        dugumler = getattr(self.harita, "ikili_yol_dugumleri", [])
        graf = getattr(self.harita, "ikili_yol_graf", {})

        if not rota or len(rota) < 2 or not dugumler:
            return

        # 2) Her kenarı düğümlere ve grafa göre çiz
        for a, b in zip(rota, rota[1:]):
            # Düğüm indexleri geçerli mi?
            if not (0 <= a < len(dugumler) and 0 <= b < len(dugumler)):
                continue

            # Graf yapısı dict-of-dict veya liste olabilir
            komsular = graf.get(a, {})
            if isinstance(komsular, dict):
                if b not in komsular:
                    # Bu iki düğüm arasında graf'ta kenar yok → yolu dışına taşmasın diye çizmiyoruz
                    continue
            elif isinstance(komsular, (list, tuple, set)):
                if b not in komsular:
                    continue
            # başka türse (boş vs.) direkt çizmeye geçiyoruz

            ax, ay = dugumler[a]
            bx, by = dugumler[b]

            pygame.draw.line(self.harita.ekran, (0, 0, 255), (ax, ay), (bx, by), 4)

    def _algoritma_paneli_ciz(self):
        """Sağ alt mini panelde algoritma ve başlangıç noktası butonlarını çizer."""
        w, h = 260, 220  # Panel boyutu
        margin = 12
        x = self.harita.GENISLIK - w - margin
        y = self.harita.YUKSEKLIK - h - margin
        self.algoritma_panel_rect = pygame.Rect(x, y, w, h)

        # Panel arka planı
        pygame.draw.rect(self.harita.ekran, (245, 245, 245),
                         self.algoritma_panel_rect, border_radius=8)
        pygame.draw.rect(self.harita.ekran, (90, 90, 90),
                         self.algoritma_panel_rect, 2, border_radius=8)

        baslik_font = self.cost_font or pygame.font.Font(None, 22)
        yazi_font = self.cost_font or pygame.font.Font(None, 20)

        # ---- ALGORTIMA BAŞLIĞI ----
        baslik = baslik_font.render("Algoritma", True, (30, 30, 30))
        self.harita.ekran.blit(baslik, (x + 12, y + 10))

        # ---- 2 SÜTUNLU ALGORİTMA BUTONLARI ----
        sutun_sayisi = 2
        btn_h = 32
        btn_y0 = y + 40
        gap = 8
        btn_w = (w - 24 - gap) // sutun_sayisi  # 2 buton + aradaki boşluk

        # Algoritma butonları
        self.algoritma_btnleri = []
        for idx, isim in enumerate(self.algoritma_opsiyonlari):
            satir = idx // sutun_sayisi    # 0,1,2,...
            sutun = idx % sutun_sayisi     # 0 veya 1
            
            # Buton pozisyonu
            btn_x = x + 12 + sutun * (btn_w + gap)
            btn_y = btn_y0 + satir * (btn_h + gap)

            rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            aktif = isim == self.secili_algoritma

            pygame.draw.rect(
                self.harita.ekran,
                (220, 230, 255) if aktif else (255, 255, 255),
                rect,
                border_radius=6,
            )
            pygame.draw.rect(
                self.harita.ekran,
                (40, 80, 180) if aktif else (120, 120, 120),
                rect,
                2,
                border_radius=6,
            )
            yazi = yazi_font.render(isim, True, (20, 20, 20))
            self.harita.ekran.blit(yazi, yazi.get_rect(center=rect.center))
            self.algoritma_btnleri.append(rect)

        # Kaç satır algoritma butonu olduğunu bul
        satir_sayisi = (len(self.algoritma_opsiyonlari) + sutun_sayisi - 1) // sutun_sayisi
        algoritma_alt_y = btn_y0 + satir_sayisi * (btn_h + gap) + 4

        # ---- BAŞLANGIÇ NOKTASI A / B / C ----
        baslik2 = baslik_font.render("Başlangıç", True, (30, 30, 30))
        self.harita.ekran.blit(baslik2, (x + 12, algoritma_alt_y))

        self.baslangic_btnleri = []
        if self.baslangic_etiketleri:
            btn2_y = algoritma_alt_y + 26
            adet = len(self.baslangic_etiketleri)
            gap2 = 6
            btn2_w = (w - 24 - gap2 * (adet - 1)) // adet

            for idx, etiket in enumerate(self.baslangic_etiketleri):
                bx = x + 12 + idx * (btn2_w + gap2)
                rect = pygame.Rect(bx, btn2_y, btn2_w, btn_h)
                aktif = (idx == self.secili_baslangic_index)

                pygame.draw.rect(
                    self.harita.ekran,
                    (220, 255, 220) if aktif else (255, 255, 255),
                    rect,
                    border_radius=6,
                )
                pygame.draw.rect(
                    self.harita.ekran,
                    (40, 140, 40) if aktif else (120, 120, 120),
                    rect,
                    2,
                    border_radius=6,
                )
                yazi = yazi_font.render(etiket, True, (20, 20, 20))
                self.harita.ekran.blit(yazi, yazi.get_rect(center=rect.center))
                self.baslangic_btnleri.append(rect)
                
    # -------------------------------------------------------------------
    # --- HIZ SLIDER METOTLARI ---
    def _ana_araba_hizini_ayarla(self, yeni_maks_hiz: float):
        # Ana aracın hızını slider değerine göre ayarlar.
        if not getattr(self, "araba", None):
            return
        # Slider maksimum hızı pozitifse sınırla
        if self.hiz_slider_max > 0:
            hedef = max(self.hiz_slider_min, min(yeni_maks_hiz, self.hiz_slider_max)) # hedef hızı sınırla
        else:
            hedef = max(self.hiz_slider_min, yeni_maks_hiz) # sadece minimuma göre sınırla
        # Güncelle
        self.hiz_slider_deger = hedef
        self.araba.normal_maks_hiz = hedef
        self.araba.kaygan_maks_hiz = hedef * 1.2 # Kaygan zemin için biraz daha yüksek
        self.araba.kasis_hizi = hedef * 0.55 # Kasis hızı da ayarla
        # Hız değişimine göre ivmeyi de orantıla
        if self.hiz_slider_baseline_hiz > 0:
            oran = hedef / self.hiz_slider_baseline_hiz
            self.araba.normal_ivme = self.hiz_slider_baseline_ivme * oran
            self.araba.kaygan_ivme = self.araba.normal_ivme * 1.1
        # Eğer mevcut hız yeni maksimumdan yüksekse düşür
        if getattr(self.araba, "hiz", 0) > hedef:
            self.araba.hiz = hedef
 
    def _hiz_slider_deger_ayarla(self, mx: int):
        # Slider üzerindeki x pozisyonuna göre hızı ayarlar.
        if not self.hiz_slider_rect:
            return
        # Geçerli slider aralığını kontrol et
        if self.hiz_slider_rect.width <= 0 or self.hiz_slider_max <= self.hiz_slider_min:
            return
        sol = self.hiz_slider_rect.left
        sag = self.hiz_slider_rect.right
        # Pozisyonu sınırla
        mx = max(sol, min(mx, sag))
        oran = (mx - sol) / self.hiz_slider_rect.width
        hedef = self.hiz_slider_min + oran * (self.hiz_slider_max - self.hiz_slider_min)
        self._ana_araba_hizini_ayarla(hedef) # Hızı ayarla

    def _hiz_slider_tiklama(self, mx: int, my: int) -> bool:
        if self.hiz_slider_rect is None: # Slider mevcut değilse
            return False
        aktif_rect = self.hiz_slider_rect.inflate(0, 18) # Y ekseninde biraz genişlet
        thumb_rect = self.hiz_slider_thumb_rect.inflate(8, 8) if self.hiz_slider_thumb_rect else None # Thumb için de genişlet
         # Tıklama slider alanındaysa sürüklemeyi başlat
        if aktif_rect.collidepoint((mx, my)) or (thumb_rect and thumb_rect.collidepoint((mx, my))):
            self.hiz_slider_dragging = True 
            self._hiz_slider_deger_ayarla(mx)
            return True
        return False

    def _hiz_slider_harita_ustu_ciz(self):
        """Ana hiz slider'ini haritanin ust orta kismina cizer."""
        # Her karede hitbox'lari sifirla
        self.hiz_slider_rect = None
        self.hiz_slider_thumb_rect = None

        # Slider sadece algoritma basladiginda aktif olsun
        if not getattr(self, 'araba', None) or self.secili_algoritma is None or self.algoritma_basla_ms is None:
            self.hiz_slider_dragging = False
            return

        font = self.cost_font or pygame.font.Font(None, 20)

        kutu_genislik = 270
        padding = 12
        bar_h = 12
        merkez_x = (self.harita.GENISLIK - kutu_genislik) // 2
        x = min(self.harita.GENISLIK - kutu_genislik - 10, max(10, merkez_x + 80))
        y = 12

        baslik = font.render("Ana hiz limiti", True, (30, 30, 30))
        baslik_pos = (self.harita.GENISLIK // 2 - baslik.get_width() // 2, y + padding)

        bar_x = x + padding
        bar_y = baslik_pos[1] + baslik.get_height() + 6
        bar_w = kutu_genislik - padding * 2
        bar_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)

        min_txt = font.render(f"{self.hiz_slider_min:.2f}", True, (70, 70, 70))
        max_txt = font.render(f"{self.hiz_slider_max:.2f}", True, (70, 70, 70))
        deger_txt = font.render(f"Hiz: {self.hiz_slider_deger:.2f}", True, (30, 30, 30))

        deger_y = bar_rect.bottom + max(min_txt.get_height(), max_txt.get_height()) + 6
        kutu_yukseklik = (deger_y + deger_txt.get_height() + padding) - y
        kutu_rect = pygame.Rect(x, y, kutu_genislik, kutu_yukseklik)

        pygame.draw.rect(self.harita.ekran, (250, 250, 250), kutu_rect, border_radius=10)
        pygame.draw.rect(self.harita.ekran, (90, 90, 90), kutu_rect, 2, border_radius=10)

        pygame.draw.rect(self.harita.ekran, (235, 235, 235), bar_rect, border_radius=6)
        pygame.draw.rect(self.harita.ekran, (90, 90, 90), bar_rect, 2, border_radius=6)

        if self.hiz_slider_max > self.hiz_slider_min:
            oran = (self.hiz_slider_deger - self.hiz_slider_min) / (self.hiz_slider_max - self.hiz_slider_min)
        else:
            oran = 0.0
        oran = max(0.0, min(1.0, oran))
        thumb_x = bar_rect.left + int(bar_rect.width * oran)
        thumb_rect = pygame.Rect(thumb_x - 8, bar_rect.top - 4, 16, bar_rect.height + 8)
        pygame.draw.rect(self.harita.ekran, (70, 130, 200), thumb_rect, border_radius=6)
        pygame.draw.rect(self.harita.ekran, (40, 90, 160), thumb_rect, 2, border_radius=6)

        self.hiz_slider_rect = bar_rect
        self.hiz_slider_thumb_rect = thumb_rect

        self.harita.ekran.blit(baslik, baslik_pos)
        self.harita.ekran.blit(min_txt, (bar_rect.left, bar_rect.bottom + 4))
        self.harita.ekran.blit(max_txt, (bar_rect.right - max_txt.get_width(), bar_rect.bottom + 4))
        self.harita.ekran.blit(deger_txt, (self.harita.GENISLIK // 2 - deger_txt.get_width() // 2, deger_y))

    # -------------------------------------------------------------------
    # --- SONUÇ PANELİ ÇİZİMİ ---
    def _sonuc_paneli_ciz(self):
        """Hedefe ulasilsa da ulasilamasa da algoritma ilerlemesini gosteren kutu."""
        if not getattr(self, 'araba', None):
            self.hiz_slider_dragging = False
            return
        if self.secili_algoritma is None:
            self.hiz_slider_dragging = False
            return
        if self.algoritma_basla_ms is None:
            self.hiz_slider_dragging = False
            return
        font = self.cost_font or pygame.font.Font(None, 20)
        w, h = 260, 160
        gap = 8
        x = self.algoritma_panel_rect.left
        y = max(gap, self.algoritma_panel_rect.top - h - gap)
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.harita.ekran, (250, 250, 250), rect, border_radius=8)
        pygame.draw.rect(self.harita.ekran, (90, 90, 90), rect, 2, border_radius=8)

        baslik = font.render("Sonuc", True, (30, 30, 30))
        self.harita.ekran.blit(baslik, (x + 12, y + 10))

        hiz_txt = font.render(f"Hiz: {self.hiz_slider_deger:.2f}", True, (30, 30, 30))
        hiz_txt_y = y + 10 + baslik.get_height() + 8
        self.harita.ekran.blit(hiz_txt, (x + 12, hiz_txt_y))

        algo = self.secili_algoritma or '-'
        gidilen_dugumler = getattr(self.araba, 'katedilen_patika', []) or []
        mevcut_adim = max(len(gidilen_dugumler) - 1, 0)
        if self.algoritma_bitis_ms is not None:
            gecen_ms = self.algoritma_bitis_ms - self.algoritma_basla_ms
            durum = "Tamamlandi"
        else:
            gecen_ms = pygame.time.get_ticks() - self.algoritma_basla_ms
            durum = "Devam ediyor..."
        sure_sn = max(0.0, gecen_ms / 1000.0)

        info_y = hiz_txt_y + hiz_txt.get_height() + 12

        satirlar = [
            f"Algoritma: {algo}",
            f"Adim: {mevcut_adim}",
            f"Maliyet: {self.dinamik_maliyet:.1f}",
            f"Sure: {sure_sn:.1f} sn ({durum})",
        ]

        for i, yazi in enumerate(satirlar):
            surf = font.render(yazi, True, (30, 30, 30))
            self.harita.ekran.blit(surf, (x + 12, info_y + i * (surf.get_height() + 4)))
            
    # -------------------------------------------------------------------
    # --- run metodu ---
    def run(self):
        while True:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
            self.harita.saat_tik(60)

# -------------------------------------------------------------------
# --- DOSYANIN EN ALTI ---
# -------------------------------------------------------------------
if __name__ == "__main__":
    Game().run()
