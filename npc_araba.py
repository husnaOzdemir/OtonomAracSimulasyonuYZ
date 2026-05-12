import pygame, math, random, heapq
# <--- YENİ EKLENDİ: Engel türlerini tanımak için import
from engel import TrafikIsigi, YayaGecidi, HizKesici, KayganZemin, YolCalismasi

class NPCArac(pygame.sprite.Sprite):
    def __init__(self, harita, x, y, genislik, yukseklik, resim_yolu=None, yedek_renk=(0, 0, 255), engeller_ref=None, npc_ref=None):
        super().__init__()
        self.h = harita
        self.x = x
        self.y = y
        self.get_engeller = engeller_ref if engeller_ref else (lambda: [])
        self.get_npcs = npc_ref if npc_ref else (lambda: [])
        try:
            if resim_yolu:
                img = pygame.image.load(resim_yolu).convert_alpha()
                self.orijinal_gorsel = pygame.transform.scale(img, (genislik, yukseklik))
            else:
                raise pygame.error("no-image")
        except pygame.error:
            self.orijinal_gorsel = pygame.Surface([genislik, yukseklik], pygame.SRCALPHA)
            self.orijinal_gorsel.fill(yedek_renk)
            pygame.draw.polygon(self.orijinal_gorsel, (255, 255, 255), [(genislik, yukseklik / 2), (genislik * 0.8, yukseklik * 0.2), (genislik * 0.8, yukseklik * 0.8)])
        self.image = self.orijinal_gorsel
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.aci = 0
        
        # <--- GÜNCELLENDİ: Hız durumları
        self.maks_hiz = random.uniform(1.2, 1.8)
        self.normal_maks_hiz = self.maks_hiz
        # !<--- DÜZELTME: Kaygan zemin hızı %50 değil, %20 (1.2) daha mantıklı
        self.kaygan_maks_hiz = self.normal_maks_hiz * 1.2 # Kayganken %20 daha hızlı
        self.kasis_hizi = self.normal_maks_hiz * 0.5 # Kasiste daha yavaş
        self.hiz = self.normal_maks_hiz
        self.yasakli_kenarlar = set()
        self.cimen_yasakli_kenarlar = set()
        
        # <--- YENİ EKLENDİ: Durum değişkenleri
        self.isikta_bekliyor = False
        self.yaya_bekliyor = False
        self.is_on_kasis = False
        self.is_on_kaygan_zemin = False
        
        # <--- YENİ EKLENDİ: Düğüm tabanlı rastgele hareket
        self.hedef_dugum_id = None  # Şu anki hedef düğüm ID'si
        self.serit_tercihi = random.choice(["sag", "sol"])
        self.aktif_patika = []
        self.aktif_adim = 0
        self.onceki_dugum_id = None
        self.dugum_tol = 8
        self.durma_sayaci = 0
        

    def _en_yakin_dugumu_bul(self, x, y):
        """Verilen koordinata en yakın düğümü bulur"""
        if not hasattr(self.h, 'ikili_yol_dugumleri') or not self.h.ikili_yol_dugumleri:
            return None
        
        en_yakin_id = None
        en_yakin_mesafe = float('inf')
        
        for dugum_id, dugum_pos in enumerate(self.h.ikili_yol_dugumleri):
            dx = dugum_pos[0] - x
            dy = dugum_pos[1] - y
            mesafe = math.sqrt(dx*dx + dy*dy)
            if mesafe < en_yakin_mesafe:
                en_yakin_mesafe = mesafe
                en_yakin_id = dugum_id
        
        return en_yakin_id

    def _norm_vektor(self, a_id, b_id):
        if a_id is None or b_id is None:
            return (0.0, 0.0)
        if a_id >= len(self.h.ikili_yol_dugumleri) or b_id >= len(self.h.ikili_yol_dugumleri):
            return (0.0, 0.0)
        ax, ay = self.h.ikili_yol_dugumleri[a_id]
        bx, by = self.h.ikili_yol_dugumleri[b_id]
        vx, vy = bx - ax, by - ay
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return (0.0, 0.0)
        return (vx / uzunluk, vy / uzunluk)

    def _kenar_id(self, a_id, b_id):
        return tuple(sorted((a_id, b_id)))

    def _engel_kenari_kapatiyor(self, p1, p2, engel):
        if not isinstance(engel, YolCalismasi):
            return False
        uzunluk = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        adim = max(6, int(uzunluk / 12)) if uzunluk else 1
        for i in range(adim + 1):
            oran = i / adim
            x = p1[0] + (p2[0] - p1[0]) * oran
            y = p1[1] + (p2[1] - p1[1]) * oran
            if engel.carpisti_mi(x, y):
                return True
        return False

    def _yol_calismasi_kenarlari(self):
        yasak = set()
        calisma_engelleri = [e for e in self.get_engeller() if isinstance(e, YolCalismasi)]
        if not calisma_engelleri:
            return yasak
        graf = getattr(self.h, 'ikili_yol_graf', {})
        dugumler = getattr(self.h, 'ikili_yol_dugumleri', [])
        for a_id, komsular in graf.items():
            for b_id in komsular:
                if a_id >= len(dugumler) or b_id >= len(dugumler):
                    continue
                kenar = self._kenar_id(a_id, b_id)
                if kenar in yasak:
                    continue
                p1, p2 = dugumler[a_id], dugumler[b_id]
                for engel in calisma_engelleri:
                    if self._engel_kenari_kapatiyor(p1, p2, engel):
                        yasak.add(kenar)
                        break
        return yasak

    def _nokta_cimen_mi(self, x, y):
        if not getattr(self.h, "ekran", None):
            return False
        try:
            renk = self.h.ekran.get_at((int(x), int(y)))
            return self._renk_cimen_mi(renk)
        except Exception:
            return False

    def _kenar_cimen_kesiyor_mu(self, a_id, b_id):
        dugumler = getattr(self.h, 'ikili_yol_dugumleri', [])
        if (a_id is None or b_id is None or
            a_id >= len(dugumler) or b_id >= len(dugumler)):
            return False
        p1, p2 = dugumler[a_id], dugumler[b_id]
        uzunluk = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if uzunluk == 0:
            return self._nokta_cimen_mi(p1[0], p1[1])
        adim = max(8, int(uzunluk / 12))
        for i in range(adim + 1):
            oran = i / adim
            x = p1[0] + (p2[0] - p1[0]) * oran
            y = p1[1] + (p2[1] - p1[1]) * oran
            if self._nokta_cimen_mi(x, y):
                return True
        return False

    def _hat_uzerinde_engel_var(self, engel, baslangic, bitis):
        uzunluk = math.hypot(bitis[0] - baslangic[0], bitis[1] - baslangic[1])
        adim = max(6, int(uzunluk / 15)) if uzunluk else 1
        for i in range(adim + 1):
            oran = i / adim
            x = baslangic[0] + (bitis[0] - baslangic[0]) * oran
            y = baslangic[1] + (bitis[1] - baslangic[1]) * oran
            if hasattr(engel, 'icinde_mi') and engel.icinde_mi(x, y):
                return True
            if engel.carpisti_mi(x, y):
                return True
        return False

    def _ana_araba_tam_ondami(self):
        """Ana arabayla mesafeyi ve yönü göz önüne alarak yakınlığı kontrol eder."""
        ana = getattr(self, 'ana_araba', None)
        if ana is None:
            return False
        dx = ana.x - self.x
        dy = ana.y - self.y
        mesafe = math.hypot(dx, dy)
        if mesafe == 0:
            return True
        safe_gap = max(self.orijinal_gorsel.get_width(), self.orijinal_gorsel.get_height()) * 2.2
        if mesafe >= safe_gap:
            return False
        radyan = math.radians(self.aci)
        ileri = (math.cos(radyan), -math.sin(radyan))
        yon_to_ana = (dx / mesafe, dy / mesafe)
        dot = ileri[0] * yon_to_ana[0] + ileri[1] * yon_to_ana[1]
        return dot > 0.15

    def _on_ucu_koor(self):
        """Arabanın ön ucunun (tampon) piksel koordinatı."""
        radyan = math.radians(self.aci)
        uzunluk = self.orijinal_gorsel.get_width()
        return (
            self.x + math.cos(radyan) * (uzunluk / 2),
            self.y - math.sin(radyan) * (uzunluk / 2),
        )

    def _orientation(self, a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def _on_segment(self, a, b, c):
        return (
            min(a[0], b[0]) - 1e-3 <= c[0] <= max(a[0], b[0]) + 1e-3 and
            min(a[1], b[1]) - 1e-3 <= c[1] <= max(a[1], b[1]) + 1e-3
        )

    def _segmentler_kesisiyor_mu(self, p1, p2, q1, q2):
        if p1 is None or p2 is None or q1 is None or q2 is None:
            return False
        if p1 == p2 or q1 == q2:
            return False
        o1 = self._orientation(p1, p2, q1)
        o2 = self._orientation(p1, p2, q2)
        o3 = self._orientation(q1, q2, p1)
        o4 = self._orientation(q1, q2, p2)
        eps = 1e-3
        def is_zero(val):
            return abs(val) < eps
        if is_zero(o1) and self._on_segment(p1, p2, q1):
            return True
        if is_zero(o2) and self._on_segment(p1, p2, q2):
            return True
        if is_zero(o3) and self._on_segment(q1, q2, p1):
            return True
        if is_zero(o4) and self._on_segment(q1, q2, p2):
            return True
        return (not is_zero(o1) and not is_zero(o2) and (o1 > 0) != (o2 > 0)) and \
               (not is_zero(o3) and not is_zero(o4) and (o3 > 0) != (o4 > 0))

    def _trafik_isigi_yolu_uzerinde(self, isik, curr_pos, next_pos):
        if not hasattr(isik, "stop_line_p1") or not hasattr(isik, "stop_line_p2"):
            return False
        return self._segmentler_kesisiyor_mu(curr_pos, next_pos, isik.stop_line_p1, isik.stop_line_p2)

    def _kirmizi_stop_gerekli(self, isik, on_x, on_y):
        """
        Kırmızı ışıkta gerçekten durmamız gerekip gerekmediğini hesaplar.
        Arabanın ön ucu stop çizgisini geçtiyse durmaz.
        """
        if not hasattr(isik, "stop_line_p1") or not hasattr(isik, "stop_line_p2"):
            return True

        p1 = isik.stop_line_p1
        p2 = isik.stop_line_p2
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        tol = self.h.YOL_KALINLIK * 0.8
        radyan = math.radians(self.aci)
        vx = math.cos(radyan)
        vy = -math.sin(radyan)

        # Stop çizgisi yönünü doğru okuyarak, tampon çizgiyi geçtiyse durma.
        is_horizontal = abs(dy) < abs(dx)
        if is_horizontal:
            line_y = p1[1]
            if vy < 0 and on_y <= line_y:
                return False
            if vy > 0 and on_y >= line_y:
                return False
            return abs(on_y - line_y) <= tol

        line_x = p1[0]
        if vx > 0 and on_x >= line_x:
            return False
        if vx < 0 and on_x <= line_x:
            return False
        return abs(on_x - line_x) <= tol

    def _donus_yonu(self, prev_id, curr_id, next_id):
        vin = self._norm_vektor(prev_id, curr_id)
        vout = self._norm_vektor(curr_id, next_id)
        dot = vin[0] * vout[0] + vin[1] * vout[1]
        cross = vin[0] * vout[1] - vin[1] * vout[0]
        if dot < 0.2:
            return "geri"
        if abs(cross) < 0.1:
            return "duz"
        return "sag" if cross < 0 else "sol"

    def _serit_kurali_uygun(self, prev_id, curr_id, next_id):
        if prev_id is None:
            return True
        yon = self._donus_yonu(prev_id, curr_id, next_id)
        if yon == "geri":
            return False
        if self.serit_tercihi == "sag" and yon == "sol":
            return False
        if self.serit_tercihi == "sol" and yon == "sag":
            return False
        return True

    def _donus_cezasi(self, prev_id, curr_id, next_id):
        if prev_id is None:
            return 0
        vin = self._norm_vektor(prev_id, curr_id)
        vout = self._norm_vektor(curr_id, next_id)
        dot = max(-1.0, min(1.0, vin[0] * vout[0] + vin[1] * vout[1]))
        return (1 - max(dot, 0)) * 25
    
    def _heuristik_dugum(self, dugum_id, hedef_id):
        # 1) Özel: hedef 136 ve txt'ten gelen hazır değer
        h_dict = getattr(self.h, "heuristik_136", None)
        if h_dict is not None and hedef_id == 136 and dugum_id in h_dict:
            return h_dict[dugum_id]

        # 2) Genel: ikili_yol_dugumleri üzerinden kuş uçuşu
        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        if (not dugumler or
            dugum_id >= len(dugumler) or
            hedef_id >= len(dugumler)):
            return 0.0

        x1, y1 = dugumler[dugum_id]
        x2, y2 = dugumler[hedef_id]
        return math.hypot(x2 - x1, y2 - y1)


    def _kisa_yol_hesapla(self, baslangic_id, hedef_id, serit_kuralini_kullan=True, yasakli_kenarlar=None):
        if baslangic_id is None or hedef_id is None or baslangic_id == hedef_id:
            return []
        if not hasattr(self.h, 'ikili_yol_graf') or not self.h.ikili_yol_graf:
            return []
        graf = self.h.ikili_yol_graf
        dugumler = self.h.ikili_yol_dugumleri
        yasakli_kenarlar = yasakli_kenarlar or set()
        kuyruk = []
        bas_state = (None, baslangic_id)
        heapq.heappush(kuyruk, (0, bas_state))
        en_iyi = {bas_state: 0}
        ebeveyn = {}

        while kuyruk:
            maliyet, state = heapq.heappop(kuyruk)
            prev, node = state
            if maliyet > en_iyi.get(state, float('inf')):
                continue

            if node == hedef_id and prev is not None:
                rota = [node]
                cur = state
                while cur in ebeveyn:
                    onceki_state = ebeveyn[cur]
                    onceki_dugum = cur[0]
                    if onceki_dugum is not None:
                        rota.append(onceki_dugum)
                    cur = onceki_state
                rota.reverse()
                return rota

            for komsu, kenar_maliyet in graf.get(node, {}).items():
                if komsu >= len(dugumler):
                    continue
                if self._kenar_id(node, komsu) in yasakli_kenarlar:
                    continue
                if serit_kuralini_kullan and not self._serit_kurali_uygun(prev, node, komsu):
                    continue
                donus_cezasi = self._donus_cezasi(prev, node, komsu)
                yeni_maliyet = maliyet + kenar_maliyet + donus_cezasi
                yeni_state = (node, komsu)
                if yeni_maliyet < en_iyi.get(yeni_state, float('inf')):
                    en_iyi[yeni_state] = yeni_maliyet
                    ebeveyn[yeni_state] = state
                    heapq.heappush(kuyruk, (yeni_maliyet, yeni_state))
        return []

    def _rastgele_uzak_dugum(self, baslangic_id, min_px):
        dugumler = getattr(self.h, 'ikili_yol_dugumleri', [])
        if not dugumler:
            return None
        bas_x, bas_y = dugumler[baslangic_id]
        adaylar = []
        for idx, (dx, dy) in enumerate(dugumler):
            if idx == baslangic_id:
                continue
            mesafe = math.hypot(dx - bas_x, dy - bas_y)
            if mesafe >= min_px:
                adaylar.append((mesafe, idx))
        if not adaylar:
            return None
        adaylar.sort(key=lambda t: t[0], reverse=True)
        secim_havuzu = [i for _, i in adaylar[:max(6, len(adaylar) // 3)]]
        return random.choice(secim_havuzu) if secim_havuzu else None

    def _rota_hazirla(self):
        if not hasattr(self.h, 'ikili_yol_dugumleri') or not self.h.ikili_yol_dugumleri:
            return
        self.serit_tercihi = random.choice(["sag", "sol"])
        if not hasattr(self, "cimen_yasakli_kenarlar"):
            self.cimen_yasakli_kenarlar = set()
        self.yasakli_kenarlar = self._yol_calismasi_kenarlari().union(self.cimen_yasakli_kenarlar)
        baslangic_id = self._en_yakin_dugumu_bul(self.x, self.y)
        if baslangic_id is None:
            return
        hedef_id = self._rastgele_uzak_dugum(baslangic_id, max(self.h.HUCRE * 3, 150))
        if hedef_id is None:
            return
        rota = self._kisa_yol_hesapla(baslangic_id, hedef_id, serit_kuralini_kullan=True, yasakli_kenarlar=self.yasakli_kenarlar)
        if not rota:
            rota = self._kisa_yol_hesapla(baslangic_id, hedef_id, serit_kuralini_kullan=False, yasakli_kenarlar=self.yasakli_kenarlar)
        if rota and len(rota) > 1:
            self.aktif_patika = rota
            self.aktif_adim = 1
            self.hedef_dugum_id = rota[1]
            self.onceki_dugum_id = rota[0]
        else:
            self.aktif_patika = []
            self.hedef_dugum_id = None
            self.aktif_adim = 0

    def _rota_ilerlet(self):
        if self.hedef_dugum_id is None or not self.aktif_patika:
            return
        if self.hedef_dugum_id >= len(self.h.ikili_yol_dugumleri):
            self.hedef_dugum_id = None
            self.aktif_patika = []
            self.aktif_adim = 0
            return
        hedef_x, hedef_y = self.h.ikili_yol_dugumleri[self.hedef_dugum_id]
        mesafe = math.hypot(hedef_x - self.x, hedef_y - self.y)
        if mesafe < self.dugum_tol:
            self.aktif_adim += 1
            if self.aktif_adim < len(self.aktif_patika):
                self.onceki_dugum_id = self.aktif_patika[self.aktif_adim - 1]
                self.hedef_dugum_id = self.aktif_patika[self.aktif_adim]
            else:
                self.onceki_dugum_id = self.hedef_dugum_id
                self.hedef_dugum_id = None
                self.aktif_patika = []
                self.aktif_adim = 0
                self._rota_hazirla()

    def _aci_hedefe_yonlendir(self):
        if self.hedef_dugum_id is None or self.hedef_dugum_id >= len(self.h.ikili_yol_dugumleri):
            return
        hedef_x, hedef_y = self.h.ikili_yol_dugumleri[self.hedef_dugum_id]
        dx = hedef_x - self.x
        dy = hedef_y - self.y
        hedef_aci = -math.degrees(math.atan2(dy, dx))
        aci_farki = hedef_aci - self.aci
        while aci_farki > 180:
            aci_farki -= 360
        while aci_farki < -180:
            aci_farki += 360
        donus_hizi = 3
        if abs(aci_farki) > donus_hizi:
            self.aci += donus_hizi if aci_farki > 0 else -donus_hizi
        else:
            self.aci = hedef_aci
        self.aci %= 360

    # npc_araba.py dosyasında, NPCArac sınıfı içinde

    def _sag_dugumu_tercih_et(self, mevcut_dugum_id, komsu_dugum_id):
        """
        Aracın o anki hareket yönüne göre, komşu düğümün "sağda" olup olmadığını kontrol eder.
        Böylece araç, çift şeritli yollarda rastgele değil, sağ şeridi takip etmeye eğilimli olur.
        """
        if mevcut_dugum_id is None or komsu_dugum_id is None:
            return False
        
        if mevcut_dugum_id >= len(self.h.ikili_yol_dugumleri) or komsu_dugum_id >= len(self.h.ikili_yol_dugumleri):
            return False
        
        pos_mevcut = self.h.ikili_yol_dugumleri[mevcut_dugum_id]
        pos_komsu = self.h.ikili_yol_dugumleri[komsu_dugum_id]
        
        # 1. Mevcut pozisyondan komşu pozisyona olan yön vektörü
        vec_mevcut_komsu = (pos_komsu[0] - pos_mevcut[0], pos_komsu[1] - pos_mevcut[1])
        
        # 2. Aracın o anki hareket yön vektörünü hesapla
        radyan = math.radians(self.aci)
        vec_arac_yon = (math.cos(radyan), -math.sin(radyan)) # Y ekseni tersine çevrildi
        
        # 3. İç çarpım (Dot product) ile iki vektörün paralellik/diklik durumunu kontrol et
        # Bu kontrol, komşu düğümün aracın hareket yönünde mi, yoksa zıt yönde mi olduğunu belirler.
        dot_product = vec_arac_yon[0] * vec_mevcut_komsu[0] + vec_arac_yon[1] * vec_mevcut_komsu[1]
        
        if dot_product < 0.35: # 0.35 değeri, çok yanlara ve geriye doğru giden düğümleri engeller.
            return False

       # 2. SAĞ ŞERİT KONTROLÜ (Cross product)
        # Negatif = sağ, Pozitif = sol.
        cross_product = vec_arac_yon[0] * vec_mevcut_komsu[1] - vec_arac_yon[1] * vec_mevcut_komsu[0]
        
        # Sağdaki düğümleri (negatif) veya tam önündeki düğümleri (sıfıra yakın) tercih et.
        # Toleransı 30'da tutarak sağa kayışı zorlar.
        return cross_product <= 30
   
    def _rastgele_hedef_dugum_sec(self, mevcut_dugum_id):
        # ... (Başlangıçtaki kontroller aynı)

        komsular = list(self.h.ikili_yol_graf[mevcut_dugum_id].keys())
        if not komsular:
            return None
        
        # Düz giden veya sağdaki düğümleri filtrele
        tercih_edilen_dugumler = [k for k in komsular 
                                if k < len(self.h.ikili_yol_dugumleri) and 
                                self._sag_dugumu_tercih_et(mevcut_dugum_id, k)]
        
        # Tercih edilen düğümler varsa:
        if tercih_edilen_dugumler:
            # Gerçek trafik simülasyonu için rastgelelik yerine kesinlik kullanılır.
            return random.choice(tercih_edilen_dugumler) # Rastgeleliği kaldırdık, bulunanlardan birini seç.
        else:
            # Çıkmaz sokak vb. durumlar için tüm komşulardan seçim.
            return random.choice(komsular)

    def get_sensor_distances(self):
            """
            OPTİMİZE EDİLDİ: Sensör mesafelerini hesaplar: (sol30, on, sag30)
            Artık get_at() ve çim kontrolü kullanmıyor, sadece engel/NPC/ana araba çarpışma kontrolü yapıyor.
            Bu sayede performans çok daha iyi.
            """
            sensor_acilari = [-15, 0, 15] 
            dists = []
            max_mesafe = 100
            
            # Arabanın ön ucunu hesapla
            radyan = math.radians(self.aci)
            araba_uzunlugu = self.orijinal_gorsel.get_width()
            on_uc_x = self.x + math.cos(radyan) * (araba_uzunlugu / 2)
            on_uc_y = self.y - math.sin(radyan) * (araba_uzunlugu / 2)
            
            for aci_deg in sensor_acilari:
                toplam_aci_rad = math.radians(self.aci - aci_deg)
                bu_sens_max = max_mesafe if aci_deg == 0 else 50
                carpti_mi = False
                uzaklik = 0
                for u in range(0, bu_sens_max, 3): 
                    x = int(on_uc_x + math.cos(toplam_aci_rad) * u)
                    y = int(on_uc_y - math.sin(toplam_aci_rad) * u)
                    if not (0 <= x < self.h.GENISLIK and 0 <= y < self.h.YUKSEKLIK):
                        uzaklik = u
                        break
                    
                    # OPTİMİZE EDİLDİ: get_at() ve çim kontrolü kaldırıldı
                    # Artık sadece engel sprite'ları, NPC'ler ve ana araba ile çarpışma kontrolü yapılıyor
                    
                    # Engel kontrolü
                    for engel in self.get_engeller():
                        if engel.carpisti_mi(x, y):
                            if isinstance(engel, TrafikIsigi):
                                is_red = getattr(engel, 'durum', None) == "kirmizi"
                                if is_red:
                                    carpti_mi = True
                                    if aci_deg == 0: self.isikta_bekliyor = True
                            elif isinstance(engel, YayaGecidi):
                                is_active = getattr(engel, 'yayalar_aktif_mi', False)
                                if is_active:
                                    carpti_mi = True
                                    if aci_deg == 0: self.yaya_bekliyor = True
                            elif isinstance(engel, YolCalismasi):
                                carpti_mi = True 
                            elif isinstance(engel, (HizKesici, KayganZemin)):
                                carpti_mi = False  # Hız kesici ve kaygan zemin engel değil
                            elif not isinstance(engel, (HizKesici, KayganZemin, TrafikIsigi, YayaGecidi)):
                                carpti_mi = True 
                            if carpti_mi:
                                break
                    
                    if not carpti_mi:
                        # NPC çarpışma kontrolü
                        for npc in self.get_npcs():
                            if npc is self:
                                continue
                            if npc.rect.collidepoint(x, y):
                                carpti_mi = True
                                break
                        
                        # Ana araba çarpışma kontrolü
                        if hasattr(self, 'ana_araba') and self.ana_araba is not None:
                            ana_rect = self.ana_araba.rect.inflate(48, 48)
                            if ana_rect.collidepoint(x, y):
                                carpti_mi = True
                    
                    if carpti_mi:
                        uzaklik = u
                        break
                else:
                    uzaklik = bu_sens_max
                dists.append(uzaklik)
            return tuple(dists) 


    def guncelle(self):
        # Sadece düğümden düğüme, yolun tam ortasında ilerle
        if not (hasattr(self.h, 'ikili_yol_dugumleri') and self.h.ikili_yol_dugumleri):
            return
        self.yasakli_kenarlar = self._yol_calismasi_kenarlari().union(self.cimen_yasakli_kenarlar)
        if not self.aktif_patika or self.hedef_dugum_id is None:
            self._rota_hazirla()
        # Hedef düğüm yoksa bekle
        if self.hedef_dugum_id is None or self.aktif_adim >= len(self.aktif_patika):
            return
        curr_id = self.aktif_patika[self.aktif_adim - 1]
        next_id = self.aktif_patika[self.aktif_adim]
        curr_pos = self.h.ikili_yol_dugumleri[curr_id]
        next_pos = self.h.ikili_yol_dugumleri[next_id]
        kenar = self._kenar_id(curr_id, next_id)
        on_uc_x, on_uc_y = self._on_ucu_koor()

        if kenar not in self.cimen_yasakli_kenarlar and self._kenar_cimen_kesiyor_mu(curr_id, next_id):
            self.cimen_yasakli_kenarlar.add(kenar)
            self.yasakli_kenarlar.add(kenar)

        if kenar in self.yasakli_kenarlar:
            self._rota_hazirla()
            if self.hedef_dugum_id is None or self.aktif_adim >= len(self.aktif_patika):
                return
            curr_id = self.aktif_patika[self.aktif_adim - 1]
            next_id = self.aktif_patika[self.aktif_adim]
            curr_pos = self.h.ikili_yol_dugumleri[curr_id]
            next_pos = self.h.ikili_yol_dugumleri[next_id]
            kenar = self._kenar_id(curr_id, next_id)
            if kenar in self.yasakli_kenarlar or self._kenar_cimen_kesiyor_mu(curr_id, next_id):
                self.cimen_yasakli_kenarlar.add(kenar)
                return

        if self._nokta_cimen_mi(self.x, self.y):
            self.x, self.y = curr_pos
            self.aci = -math.degrees(math.atan2(next_pos[1] - curr_pos[1], next_pos[0] - curr_pos[0]))
        # Engel kontrolü (trafik ışığı, yaya geçidi, yol çalışması, hız kesici, kaygan zemin)
        engeller = self.get_engeller()
        durmali = False
        hiz_carpan = 1.0
        engel_bekliyor = False
        adim_sayisi = max(8, int(math.hypot(next_pos[0] - self.x, next_pos[1] - self.y) / 20))
        ilerleme_noktalari = [
            (self.x + (next_pos[0] - self.x) * (i / adim_sayisi), self.y + (next_pos[1] - self.y) * (i / adim_sayisi))
            for i in range(adim_sayisi + 1)
        ]
        for engel in engeller:
            if isinstance(engel, TrafikIsigi) and getattr(engel, "durum", None) == "kirmizi":
                if not self._trafik_isigi_yolu_uzerinde(engel, curr_pos, next_pos):
                    continue
                if not self._kirmizi_stop_gerekli(engel, on_uc_x, on_uc_y):
                    continue
                durmali = True
                engel_bekliyor = True
                break
            # Yaya geçidi kontrolü
            elif isinstance(engel, YayaGecidi):
                if engel.yayalar_aktif_mi and any(engel.carpisti_mi(px, py) for px, py in ilerleme_noktalari):
                    durmali = True
                    engel_bekliyor = True
                    break
            # Yol çalışması kontrolü
            elif isinstance(engel, YolCalismasi):
                if self._hat_uzerinde_engel_var(engel, (self.x, self.y), next_pos):
                    self._rota_hazirla()
                    return
            # Hız kesici kontrolü
            elif isinstance(engel, HizKesici):
                if self._hat_uzerinde_engel_var(engel, (self.x, self.y), next_pos):
                    hiz_carpan = min(hiz_carpan, self.kasis_hizi / self.normal_maks_hiz)
            # Kaygan zemin kontrolü
            elif isinstance(engel, KayganZemin):
                if engel.icinde_mi(self.x, self.y):
                    hiz_carpan = max(hiz_carpan, self.kaygan_maks_hiz / self.normal_maks_hiz)
        
        # Sensör mesafesine göre hız kontrolü (0 dereceli sensör)
        sensor_mesafeleri = self.get_sensor_distances()
        on_sensor_mesafe = sensor_mesafeleri[1] if len(sensor_mesafeleri) > 1 else 150  # 0 dereceli sensör (index 1)
        
        if on_sensor_mesafe <= 20:
            # Mesafe 5 veya daha azsa dur
            durmali = True
        elif on_sensor_mesafe <= 30:
            # Mesafe 15 veya daha azsa hızı 1/5 oranında düşür
            hiz_carpan = min(hiz_carpan, 0.2)
        if self._ana_araba_tam_ondami():
            ana = getattr(self, "ana_araba", None)
            ana_hareketli = ana is not None and getattr(ana, "hiz", 0) > 0.05
            if ana_hareketli:
                durmali = False
                hiz_carpan = min(hiz_carpan, 0.6)
            else:
                durmali = True
                hiz_carpan = min(hiz_carpan, 0.25)
        # Bekleme kancas\u0131: uzun bekleme sonras\u0131nda k\u0131tl\u0131klar\u0131 azaltmak i\u00e7in yavas ilerle
        if durmali:
            self.durma_sayaci += 1
        else:
            self.durma_sayaci = 0
        if durmali and not engel_bekliyor and self.durma_sayaci >= 45:
            durmali = False
            hiz_carpan = min(hiz_carpan, 0.35)
        # Mesafe > 15 ise default hız (hiz_carpan = 1.0 zaten)
        
        # Eğer durması gerekiyorsa hareket etme
        if durmali:
            self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
            self.rect = self.image.get_rect(center=(self.x, self.y))
            return
        # Doğrusal interpolasyon ile ilerle
        yol_vektoru = (next_pos[0] - curr_pos[0], next_pos[1] - curr_pos[1])
        yol_uzunlugu = math.hypot(yol_vektoru[0], yol_vektoru[1])
        if yol_uzunlugu == 0:
            self.aktif_adim += 1
            if self.aktif_adim < len(self.aktif_patika):
                self.hedef_dugum_id = self.aktif_patika[self.aktif_adim]
            return
        ilerleme_orani = ((self.x - curr_pos[0]) * yol_vektoru[0] + (self.y - curr_pos[1]) * yol_vektoru[1]) / (yol_uzunlugu ** 2)
        ilerleme_orani = max(0.0, min(1.0, ilerleme_orani))
        hedef_hiz = self.normal_maks_hiz * hiz_carpan
        if hiz_carpan > 1.0:
            hedef_hiz = min(hedef_hiz, self.kaygan_maks_hiz)
        hiz = hedef_hiz
        yeni_oran = ilerleme_orani + (hiz / yol_uzunlugu)
        if yeni_oran >= 1.0:
            self.x, self.y = next_pos
            self.aktif_adim += 1
            if self.aktif_adim < len(self.aktif_patika):
                self.hedef_dugum_id = self.aktif_patika[self.aktif_adim]
            else:
                self.hedef_dugum_id = None
            self.aci = -math.degrees(math.atan2(next_pos[1] - curr_pos[1], next_pos[0] - curr_pos[0]))
        else:
            self.x = curr_pos[0] + yol_vektoru[0] * yeni_oran
            self.y = curr_pos[1] + yol_vektoru[1] * yeni_oran
            self.aci = -math.degrees(math.atan2(next_pos[1] - curr_pos[1], next_pos[0] - curr_pos[0]))
        self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def _renk_cimen_mi(self, renk, tolerans=18):
        # Toleranslı çim/yeşil alan tespiti
        if len(renk) < 3:
            return False
        c_r, c_g, c_b = self.h.CIMEN[:3]
        r_r, r_g, r_b = renk[0], renk[1], renk[2]
        return (
            abs(c_r - r_r) <= tolerans and
            abs(c_g - r_g) <= tolerans and
            abs(c_b - r_b) <= tolerans 
        )

    def sensorleri_ciz(self):
            """
            OPTİMİZE EDİLDİ: Sensör çizgilerini çizer.
            Artık get_at() kullanmıyor, sadece get_sensor_distances()'ten aldığı mesafeleri çiziyor.
            Bu sayede performans çok daha iyi.
            """
            ekran = self.h.ekran
            sensor_acilari = [-15, 0, 15]
            alpha_değeri = 100 
            
            # Arabanın ön ucunu hesapla
            radyan = math.radians(self.aci)
            araba_uzunlugu = self.orijinal_gorsel.get_width()
            on_uc_x = self.x + math.cos(radyan) * (araba_uzunlugu / 2)
            on_uc_y = self.y - math.sin(radyan) * (araba_uzunlugu / 2)
            
            # OPTİMİZE EDİLDİ: get_sensor_distances()'ten mesafeleri al, tekrar hesaplama yapma
            sensor_mesafeleri = self.get_sensor_distances()
            
            for idx, aci_deg in enumerate(sensor_acilari):
                # get_sensor_distances()'ten alınan mesafeyi kullan
                default_mesafe = 120 if aci_deg == 0 else 50
                uzaklik = sensor_mesafeleri[idx] if idx < len(sensor_mesafeleri) else default_mesafe
                
                toplam_aci = math.radians(self.aci - aci_deg)
                
                # Mesafeye göre renk belirle
                if uzaklik < 40:
                    renk_cizgi_base = (255, 0, 0)  # Kırmızı - çok yakın
                elif uzaklik < 80:
                    renk_cizgi_base = (255, 255, 0)  # Sarı - yakın
                else:
                    renk_cizgi_base = (0, 255, 0)  # Yeşil - güvenli
                
                renk_cizgi_silik = tuple(min(255, int(c * (alpha_değeri / 255))) for c in renk_cizgi_base[:3])
                
                # Sensör çizgisinin bitiş noktasını hesapla
                x_bitis = int(on_uc_x + math.cos(toplam_aci) * uzaklik)
                y_bitis = int(on_uc_y - math.sin(toplam_aci) * uzaklik)
                
                # Çizgiyi ve bitiş noktasını çiz
                pygame.draw.line(ekran, renk_cizgi_silik, (on_uc_x, on_uc_y), (x_bitis, y_bitis), 1)
                pygame.draw.circle(ekran, renk_cizgi_silik, (x_bitis, y_bitis), 3)
        
    def ciz(self):
            self.h.ekran.blit(self.image, self.rect)
            # self.sensorleri_ciz()  # OPTİMİZE EDİLDİ: Sensörler gizlendi (performans için)


#! <--- DÜZELTME 4: ENGEL ÜZERİNDE BAŞLAMAYI ENGELLEYEN FONKSİYON
def npc_arac_uret(harita, araba_uzunluk, araba_genislik, ana_x, ana_y, engeller_ref=None, npc_ref=None, ana_araba=None):
    # --- YENİ: NPC'ler bir düğümün tam üstünde doğacak ---
    npcs = []
    tum_engeller = engeller_ref() if engeller_ref else []
    dugumler = getattr(harita, 'ikili_yol_dugumleri', [])
    if not dugumler:
        return npcs
    kullanilan_dugumler = set()
    deneme_limit = 100  # sonsuz döngüye girmemek için
    # Ana arabanın konumundan minimum mesafe (piksel cinsinden)
    min_mesafe_ana_arabadan = max(araba_uzunluk * 3, 200)  # En az 3 araba uzunluğu veya 200 piksel
    i = 0
    while len(npcs) < 4 and deneme_limit > 0:
        # Her seferinde rastgele bir düğüm seç
        secilebilirler = [idx for idx in range(len(dugumler)) if idx not in kullanilan_dugumler]
        if not secilebilirler:
            # Eğer tüm düğümler denendiyse, tekrar başa dön (ama sonsuz döngüye girmesin)
            secilebilirler = list(range(len(dugumler)))
        dugum_id = random.choice(secilebilirler)
        x, y = dugumler[dugum_id]
        is_guvenli = True
        
        # Ana arabanın konumundan yeterince uzak mı kontrol et
        mesafe_ana_arabadan = math.hypot(x - ana_x, y - ana_y)
        if mesafe_ana_arabadan < min_mesafe_ana_arabadan:
            is_guvenli = False
        
        try:
            if harita.ekran and hasattr(harita, 'CIMEN'):
                renk = harita.ekran.get_at((int(x), int(y)))
                if abs(renk[0] - harita.CIMEN[0]) <= 18 and abs(renk[1] - harita.CIMEN[1]) <= 18 and abs(renk[2] - harita.CIMEN[2]) <= 18:
                    is_guvenli = False
        except Exception:
            pass
        for engel in tum_engeller:
            if isinstance(engel, (HizKesici, KayganZemin)):
                if hasattr(engel, 'icinde_mi') and engel.icinde_mi(x, y):
                    is_guvenli = False
                    break
            elif isinstance(engel, (YolCalismasi, YayaGecidi, TrafikIsigi)):
                if hasattr(engel, 'carpisti_mi') and engel.carpisti_mi(x, y):
                    is_guvenli = False
                    break
        if is_guvenli:
            renk = [random.randint(0, 255) for _ in range(3)]
            resim_yolu = f"araba{i+1}.png"
            npc = NPCArac(harita, x, y, araba_uzunluk, araba_genislik, resim_yolu=resim_yolu, yedek_renk=tuple(renk), engeller_ref=engeller_ref, npc_ref=npc_ref)
            npc.aci = random.uniform(0, 360)
            npc.ana_araba = ana_araba
            npcs.append(npc)
            kullanilan_dugumler.add(dugum_id)
            i += 1
        deneme_limit -= 1
    # Eğer hala 4'e ulaşamadıysa, ana arabanın konumundan uzak düğümlerden seç (garanti 4 olsun)
    while len(npcs) < 4:
        # Ana arabanın konumundan yeterince uzak düğümleri bul
        uzak_dugumler = []
        for idx, (dx, dy) in enumerate(dugumler):
            mesafe = math.hypot(dx - ana_x, dy - ana_y)
            if mesafe >= min_mesafe_ana_arabadan and idx not in kullanilan_dugumler:
                uzak_dugumler.append(idx)
        
        if not uzak_dugumler:
            # Eğer hiç uzak düğüm yoksa, en uzak olanı seç
            en_uzak_id = 0
            en_uzak_mesafe = 0
            for idx, (dx, dy) in enumerate(dugumler):
                mesafe = math.hypot(dx - ana_x, dy - ana_y)
                if mesafe > en_uzak_mesafe:
                    en_uzak_mesafe = mesafe
                    en_uzak_id = idx
            dugum_id = en_uzak_id
        else:
            dugum_id = random.choice(uzak_dugumler)
        
        x, y = dugumler[dugum_id]
        renk = [random.randint(0, 255) for _ in range(3)]
        resim_yolu = f"araba{i+1}.png"
        npc = NPCArac(harita, x, y, araba_uzunluk, araba_genislik, resim_yolu=resim_yolu, yedek_renk=tuple(renk), engeller_ref=engeller_ref, npc_ref=npc_ref)
        npc.aci = random.uniform(0, 360)
        npc.ana_araba = ana_araba
        npcs.append(npc)
        kullanilan_dugumler.add(dugum_id)
        i += 1
    return npcs


