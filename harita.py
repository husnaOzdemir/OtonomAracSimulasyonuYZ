import pygame, math, os

class Harita:
    def __init__(self, genislik=1500, yukseklik=700):
        pygame.init()
        self.GENISLIK, self.YUKSEKLIK = genislik, yukseklik
        self.ekran = pygame.display.set_mode((self.GENISLIK, self.YUKSEKLIK))
        pygame.display.set_caption("Izgara Yolları — Hareketli Araç & Panel")
        self.saat = pygame.time.Clock()

        # Renkler ve stiller
        self.CIMEN = (188, 224, 186)
        self.ASFALT = (90, 90, 90)
        self.SERIT = (255, 255, 255)
        self.YOL_KALINLIK = int(min(self.GENISLIK, self.YUKSEKLIK) * 0.082)
        self.SERIT_KALINLIK = max(4, self.YOL_KALINLIK // 10)

        # Trafik ışığı renkleri
        self.STOP_LINE_RENK = (255, 0, 0)
        self.ISIK_KUTU = (30, 30, 30)
        self.KAPALI_KIRMIZI = (100, 0, 0)
        self.KAPALI_SARI = (100, 100, 0)
        self.KAPALI_YESIL = (0, 100, 0)
        self.ACIK_KIRMIZI = (255, 0, 0)
        self.ACIK_SARI = (255, 255, 0)
        self.ACIK_YESIL = (0, 255, 0)

        # Panel renkleri & font
        self.KUTU_BG = (240, 240, 240)
        self.KUTU_KENAR = (100, 100, 100)
        self.OK_RENK = (50, 50, 50)
        self.YAZI_RENK = (30, 30, 30)
        try:
            self.BASLIK_FONT = pygame.font.SysFont("Arial", 28, bold=True)
        except Exception:
            self.BASLIK_FONT = pygame.font.Font(None, 34)
        try:
            self.BUTON_FONT = pygame.font.SysFont("Arial", 18, bold=True)
        except Exception:
            self.BUTON_FONT = pygame.font.Font(None, 24)
        try:
            self.SENSOR_FONT = pygame.font.SysFont("Arial", 20, bold=True)
        except Exception:
            self.SENSOR_FONT = pygame.font.Font(None, 28)

        # Izgara
        self.SUTUN, self.SATIR = 20, 12
        self.KENAR_BOSLUK = int(min(self.GENISLIK / self.SUTUN, self.YUKSEKLIK / self.SATIR) * 0.3) if self.SUTUN > 0 and self.SATIR > 0 else 20
        self.HUCRE = min((self.GENISLIK - 2 * self.KENAR_BOSLUK) / self.SUTUN, (self.YUKSEKLIK - 2 * self.KENAR_BOSLUK) / self.SATIR) if self.SUTUN > 0 and self.SATIR > 0 else 50
        self.OFFSET_X = 80
        self.OFFSET_Y = 50
                # --- Özel dekor görselleri (kırmızı noktalar için) ---
        try:
            klasor = os.path.dirname(os.path.abspath(__file__))

            # Sol üstteki görsel
           # Sol üstteki görsel
            self.dekor_sol_img = pygame.image.load(
                os.path.join(klasor, "dekor_sol.png")
            ).convert_alpha()

            # *** BOYUT KÜÇÜLTME BURADA ***
            self.dekor_sol_img = pygame.transform.scale(self.dekor_sol_img, (100, 100))

            self.dekor_sol_rect = self.dekor_sol_img.get_rect()


            # Sağ alttaki görsel
            self.dekor_sag_img = pygame.image.load(
                os.path.join(klasor, "dekor_sag.png")
            ).convert_alpha()

            # *** BOYUT KÜÇÜLTME BURADA ***
            self.dekor_sag_img = pygame.transform.scale(self.dekor_sag_img, (100, 100))

            self.dekor_sag_rect = self.dekor_sag_img.get_rect()


            # ---- KONUM AYARI ----
            # Grid üzerinden yerleştirmek istiyorsan:
            # k(c, r) = o grid kavşağının piksel koordinatı
            k = self.kose

            # Buradaki (c, r) değerlerini kendine göre oynayabilirsin.
            # Örnek: sol üst kırmızı nokta
            x_sol, y_sol = k(2, 0)   # yaklaşık sol üst uzantı tarafı
            self.dekor_sol_rect.center = (x_sol + 0, y_sol + 40)

            # Örnek: sağ alt kırmızı nokta
            x_sag, y_sag = k(18, 10) # yaklaşık sağ alt yolun iç tarafı
            self.dekor_sag_rect.center = (x_sag + 72, y_sag - 80)

        except Exception as e:
            print("[DEKOR] Görseller yüklenemedi:", e)
            self.dekor_sol_img = None
            self.dekor_sag_img = None
                # --- Ağaç görseli yükleme ---
        try:
            self.agac_img = pygame.image.load(os.path.join(klasor, "agac.png")).convert_alpha()
            self.agac_img = pygame.transform.scale(self.agac_img, (100, 100))  # boyutu ayarlayabilirsin
        except:
            print("Ağaç görseli yüklenemedi!")
            self.agac_img = None

        # --- Ağaç konumları (üst yol kenarı için) ---
        # k(c, r) = grid düğümü → piksel
        k = self.kose
        self.agac_konumlari = [
            k(4, 0),
            k(20, 0),
            k(5.5, 0),
            k(12, 0),
            k(14, 0),
            k(16, 0),
            k(18, 0),
        ]
                # --- Sağ üst dekor görseli ---
                # --- Çocuk Oyun Parkı Görseli ---
        try:
            self.park_img = pygame.image.load(
                os.path.join(klasor, "oyunpark.png")
            ).convert_alpha()

            # Boyut ayarı (istersen büyüt/küçült)
            self.park_img = pygame.transform.scale(self.park_img, (160, 130))

            self.park_rect = self.park_img.get_rect()
        except:
            print("Oyun parkı yüklenemedi!")
            self.park_img = None
        # Çocuk parkı konumu (kırmızı nokta için)
        k = self.kose
        x, y = k(1, 6)

        # Konumu tam oturtmak için küçük kaydırmalar
        self.park_rect.center = (x - 50, y)
                # --- ÇARDAK GÖRSELİ (oyun parkının üstü ve altı için) ---
        try:
            self.cardak_img = pygame.image.load(
                os.path.join(klasor, "cardak.png")  # dosya adını sen ne koyduysan onu yaz
            ).convert_alpha()

            # Boyut ayarı – büyük/küçük gelirse burayı değiştir
            self.cardak_img = pygame.transform.scale(self.cardak_img, (140, 120))

            # Bir tane referans rect alalım
            cardak_rect = self.cardak_img.get_rect()
            cardak_genislik, cardak_yukseklik = cardak_rect.size

            # Parkın merkezini referans al
            park_x, park_y = self.park_rect.center

            # Üstteki çardak
            self.cardak_ust_rect = self.cardak_img.get_rect(
                center=(park_x, park_y - cardak_yukseklik - 10)
            )

            # Alttaki çardak
            self.cardak_alt_rect = self.cardak_img.get_rect(
                center=(park_x, park_y + cardak_yukseklik + 10)
            )

        except Exception as e:
            print("Çardak yüklenemedi:", e)
            self.cardak_img = None
            self.cardak_ust_rect = None
            self.cardak_alt_rect = None




        # Panel ayarları
        self.KUTU_GENISLIK = 200
        self.KUTU_YUKSEKLIK = 450
        yukari_kaydir = 80
        self.KUTU_Y = max(20, (self.YUKSEKLIK - self.KUTU_YUKSEKLIK) / 2 - yukari_kaydir)
        self.KUTU_X_ACIK = self.GENISLIK - self.KUTU_GENISLIK
        self.KUTU_X_KAPALI = self.GENISLIK
        self.OK_SEKME_GENISLIK = 20
        self.OK_SEKME_YUKSEKLIK = 80
        self.OK_SEKME_Y = (self.YUKSEKLIK - self.OK_SEKME_YUKSEKLIK) / 2
        self.kutu_acik = False
        self.ok_rect = pygame.Rect(0, 0, 0, 0)

        # Yollar (V1'den alındı - Kavşaklı olan)
        self.yollar = self._olustur_yollar()
        self.KAVSAK_MERKEZ_1 = self.kose(7, 6)
        self.KAVSAK_MERKEZ_2 = self.kose(13, 6)
        self.KAVSAK_YARICAP = int(self.HUCRE * 1.5)
        
        
        # --- BİRLEŞTİRME 2: ALGORİTMA GRAFI ---
        # (Bizim 'harita_GRAF.py' dosyamızdan alındı)
        self.graf = self._olustur_graf() 
        self.BASLANGIC_Dugum = (18, 2)  
        self.HEDEF_Dugum = (16, 10)
        # --- BİRLEŞTİRME 2 BİTTİ ---
        
        # --- İKİLİ YOL DÜĞÜMLERİ ---
        # Manuel eklenen düğümler için kullanılıyor
        self.ikili_yol_dugumleri = []
        self.ikili_yol_graf = {}
        # --- İKİLİ YOL DÜĞÜMLERİ BİTTİ ---
                # --- HEURİSTİK (dugum -> hedef 136 kuş uçuşu) ---
        self.heuristik_136 = self._heuristik_dosyasi_yukle("heuristik_136.txt")
        

        # Buton rect referansları (V2'den alındı - Gelişmiş olan)
        self.BTN_ADD_YAYA = None
        self.BTN_ADD_CALISMA = None
        self.BTN_ADD_KASIS = None
        self.BTN_ADD_ISIK = None
        self.BTN_ADD_BUZLU = None # Buzlu zemin butonu
        self.BTN_DELETE = None
        self.BTN_ROTATE = None
        self.BTN_LONGER = None
        self.BTN_SHORTER = None
        self.BTN_PAGE_LEFT = None  # Sayfa solu butonu
        self.BTN_PAGE_RIGHT = None # Sayfa sağı butonu
        self.panel_sayfa = 0

    def kose(self, c, r):
        return (
            self.KENAR_BOSLUK + self.OFFSET_X + c * self.HUCRE,
            self.KENAR_BOSLUK + self.OFFSET_Y + r * self.HUCRE,
        )

    # --- BİRLEŞTİRME 2: 'piksel_to_grid' FONKSİYONU EKLENDİ ---
    def piksel_to_grid(self, x, y):
        """
        (x, y) piksel koordinatını (c, r) grid koordinatına çevirir.
        """
        if self.HUCRE == 0:
            return (0, 0)
            
        c = (x - self.KENAR_BOSLUK - self.OFFSET_X) / self.HUCRE
        r = (y - self.KENAR_BOSLUK - self.OFFSET_Y) / self.HUCRE
        
        return (round(c), round(r))
    # --- BİRLEŞTİRME 2 BİTTİ ---

    def _olustur_yollar(self):
        # (Senin 'harita_NPC.py' dosyasından alındı, _olustur_graf ile uyumlu)
        k = self.kose
        yollars = [
            [k(2, 2), k(18, 2)],
            [k(2, 10), k(18, 10)],
            [k(4, 2), k(4, 10)],
            [k(10, 2), k(10, 10)],
            [k(16, 2), k(16, 10)],
            [k(4, 4), k(16, 4)],
            [k(4, 8), k(16, 8)],
            [k(18, 5), k(18, 8)],
            [k(16, 8), k(18, 8)],
            [k(2, 2), k(4, 2)],
            [k(2, 10), k(4, 10)],
            [k(7, 2), k(7, 0)],
            [k(10, 2), k(10, 0)],
            [k(7, 0), k(10, 0)],
            [k(2, 2), k(2, 10)],
            [k(18, 2), k(18, 10)],
            [k(2, 10), k(0, 10)],
            [k(18, 2), k(20, 2)],
            [k(18, 6), k(20, 6), k(20, 8)],
            [k(2, 2), k(0, 2), k(0, 0)],
            # --- Yeni eklenen yol segmentleri (eksik düğümler için) ---
            [k(4, 4), k(7, 4), k(10, 4), k(13, 4), k(16, 4)], # Orta yatay
            [k(4, 8), k(7, 8), k(10, 8), k(13, 8), k(16, 8)], # Alt yatay
            [k(14, 6), k(16, 6), k(18, 6)], # Sağ orta çıkıntı
            [k(18, 10), k(20, 10)], # Sağ alt çıkıntı
        ]
        # Orta yatay yolun bölünmüş kısımları (kavşaklar için)
        yollars.extend([
            [k(2, 6), k(4, 6), k(6, 6)], 
            [k(8, 6), k(10, 6), k(12, 6)],
            [k(14, 6), k(18, 6)],
        ])
        # Kavşak 1 (col 7) dikey yolların bölünmüş kısımları
        yollars.extend([
            [k(7, 2), k(7, 4), k(7, 5)],
            [k(7, 7), k(7, 8), k(7, 10)],
        ])
        # Kavşak 2 (col 13) dikey yolların bölünmüş kısımları
        yollars.extend([
            [k(13, 2), k(13, 4), k(13, 5)],
            [k(13, 7), k(13, 8), k(13, 10)],
        ])
        # Kavşak 1 döngü ve bağlantılar (köşeler ve dönüşler)
        yollars.extend([
            [k(6, 5), k(8, 5)],
            [k(8, 5), k(8, 7)],
            [k(8, 7), k(6, 7)],
            [k(6, 7), k(6, 5)],
            [k(6, 6), k(6, 5)],
            [k(6, 6), k(6, 7)],
            [k(8, 6), k(8, 5)],
            [k(8, 6), k(8, 7)],
            [k(7, 5), k(6, 5)],
            [k(7, 5), k(8, 5)],
            [k(7, 7), k(6, 7)],
            [k(7, 7), k(8, 7)],
        ])
        # Kavşak 2 döngü ve bağlantılar (köşeler ve dönüşler)
        yollars.extend([
            [k(12, 5), k(14, 5)],
            [k(14, 5), k(14, 7)],
            [k(14, 7), k(12, 7)],
            [k(12, 7), k(12, 5)],
            [k(12, 6), k(12, 5)],
            [k(12, 6), k(12, 7)],
            [k(14, 6), k(14, 5)],
            [k(14, 6), k(14, 7)],
            [k(13, 5), k(12, 5)],
            [k(13, 5), k(14, 5)],
            [k(13, 7), k(12, 7)],
            [k(13, 7), k(14, 7)],
        ])
        yollars.extend([
            [k(18, 10), k(20, 10)],
        ])
        return yollars

    # Çizim yardımcıları
    def yol_yuzeyi_ciz(self, noktalar, genislik, renk):
        pygame.draw.lines(self.ekran, renk, False, noktalar, genislik)
        yaricap = genislik // 2
        for x, y in noktalar:
            pygame.draw.circle(self.ekran, renk, (int(x), int(y)), yaricap)

    def kesikli_serit(self, noktalar, uzunluk=None, bosluk=None):
        if uzunluk is None:
            uzunluk = int(self.YOL_KALINLIK * 0.8)
        if bosluk is None:
            bosluk = int(self.YOL_KALINLIK * 0.6)
        aralik = uzunluk + bosluk
        for (x1, y1), (x2, y2) in zip(noktalar[:-1], noktalar[1:]):
            d = math.hypot(x2 - x1, y2 - y1)
            if d == 0:
                continue
            ux, uy = (x2 - x1) / d, (y2 - y1) / d
            t = 0
            while t < d:
                a = (x1 + ux * t, y1 + uy * t)
                b = (x1 + ux * min(t + uzunluk, d), y1 + uy * min(t + uzunluk, d))
                pygame.draw.line(self.ekran, self.SERIT, a, b, self.SERIT_KALINLIK)
                t += aralik

    def yol_ciz(self, noktalar):
        self.yol_yuzeyi_ciz(noktalar, self.YOL_KALINLIK, self.ASFALT)
        self.kesikli_serit(noktalar)

    def doner_kavsak_ciz(self, merkez, dis_yaricap):
        ic_yaricap = dis_yaricap - self.YOL_KALINLIK
        pygame.draw.circle(self.ekran, self.ASFALT, merkez, int(dis_yaricap))
        ada_yaricap = max(8, int(ic_yaricap * 0.99))
        pygame.draw.circle(self.ekran, self.CIMEN, merkez, ada_yaricap)
        orta = (dis_yaricap + ic_yaricap) / 2
        for a in range(0, 360, 34):
            a1 = math.radians(a)
            a2 = math.radians(a + 18)
            p1 = (merkez[0] + orta * math.cos(a1), merkez[1] + orta * math.sin(a1))
            p2 = (merkez[0] + orta * math.cos(a2), merkez[1] + orta * math.sin(a2))
            pygame.draw.line(self.ekran, self.SERIT, p1, p2, self.SERIT_KALINLIK)

    
    # --- BİRLEŞTİRME 2: 'olustur_graf' FONKSİYONU EKLENDİ ---
    def _olustur_graf(self):
    
        graf = {}
        
        kenarlar = [
            # ---------------------------
            # Üst Uzantı (Kuzey)
            # ---------------------------
            ((7, 0), (10, 0), 5),
            ((7, 0), (7, 2), 2),
            ((10, 0), (10, 2), 2),

            # ---------------------------
            # Üst Yatay Yol (Sağdan Sola)
            # ---------------------------
            ((18, 2), (16, 2), 3),
            ((16, 2), (13, 2), 5), # Yaya geçidi
            ((13, 2), (10, 2), 5), 
            ((10, 2), (7, 2), 2),
            ((7, 2), (4, 2), 2),
            ((4, 2), (2, 2), 3),
            ((2, 2), (0, 2), 4),
            ((0, 2), (0, 0), 6),

            # ---------------------------
            # Orta Yatay Yol (Sağdan Sola)
            # ---------------------------
            ((16, 4), (13, 4), 5),
            ((13, 4), (10, 4), 5),
            ((10, 4), (7, 4), 5),
            ((7, 4), (4, 4), 5),

            # ---------------------------
            # Alt Yatay Yol 1 (Sağdan Sola)
            # ---------------------------
            ((18, 8), (16, 8), 3),
            ((16, 8), (13, 8), 5),
            ((13, 8), (10, 8), 5),
            ((10, 8), (7, 8), 5),
            ((7, 8), (4, 8), 5),
            ((4, 8), (2, 8), 3),

            # ---------------------------
            # Alt Yatay Yol 2 (Sağdan Sola)
            # ---------------------------
            ((20, 10), (18, 10), 3),
            ((18, 10), (16, 10), 3),
            ((16, 10), (13, 10), 2), # Kaygan Zemin 
            ((13, 10), (10, 10), 2), # Kaygan Zemin 
            ((10, 10), (7, 10), 4),  # Kasis 
            ((7, 10), (4, 10), 4),  # Kasis 
            ((4, 10), (2, 10), 6),
            ((2, 10), (0, 10), 6),

            # ---------------------------
            # Sol Dikey Yollar (Yukarıdan Aşağı)
            # ---------------------------
            ((2, 2), (2, 6), 6),
            ((4, 2), (4, 4), 3),
            ((4, 4), (4, 6), 5), # Yaya geçidi
            ((4, 6), (4, 8), 3),
            ((4, 8), (4, 10), 3),
            
            ((2, 6), (4, 6), 3),
            ((2, 6), (2, 8), 3),
            ((2, 8), (2, 10), 3),

            # ---------------------------
            # Orta Dikey Yollar (Yukarıdan Aşağı)
            # ---------------------------
            ((7, 2), (7, 4), 3),
            ((7, 4), (7, 5), 8),   # Kırmızı Işık
            ((7, 7), (7, 8), 3),
            ((7, 8), (7, 10), 8),  # Kırmızı Işık

            ((10, 2), (10, 4), 3),
            ((10, 4), (10, 5), 2),
            ((10, 5), (10, 7), 10), # Yol Çalışması 
            ((10, 7), (10, 8), 2),
            ((10, 8), (10, 10), 3),

            ((13, 2), (13, 4), 3),
            ((13, 5), (13, 7), 1),
            ((13, 7), (13, 8), 3),
            ((13, 8), (13, 10), 8), # Kırmızı Işık

            # ---------------------------
            # Sağ Dikey Yollar (Yukarıdan Aşağı)
            # ---------------------------
            ((18, 2), (18, 5), 4), # Kasis
            ((18, 5), (18, 6), 2), # Kaygan Zemin
            ((18, 6), (18, 8), 3),
            ((18, 8), (18, 10), 3),
            
            ((16, 2), (16, 4), 3),
            ((16, 4), (16, 6), 3),
            ((16, 6), (16, 8), 5), # Yaya geçidi
            ((16, 8), (16, 10), 3),

            # ---------------------------
            # Sağ Orta Çıkıntı
            # ---------------------------
            ((16, 6), (18, 6), 3),
            ((18, 6), (20, 6), 3),
            ((20, 6), (20, 8), 6),
            ((18, 2), (20, 2), 6),

            # ---------------------------
            # Çift şerit geçişleri (çapraz eklentiler kaldırıldı)
            # ---------------------------
            ((4, 6), (6, 6), 2),
            ((6, 6), (8, 6), 3),
            ((8, 6), (10, 6), 2),

            ((10, 6), (12, 6), 2),
            ((12, 6), (14, 6), 3),
            ((14, 6), (16, 6), 2),
        ]
        
        # ---------------------------------------------------------------
        # Kenar listesini çift yönlü bir graf sözlüğüne dönüştür
        # ---------------------------------------------------------------
        for n1, n2, cost in kenarlar:
            if n1 not in graf:
                graf[n1] = {}
            graf[n1][n2] = cost
            
            if n2 not in graf:
                graf[n2] = {}
            graf[n2][n1] = cost

        # ---------------------------------------------------------------
        # Tüm Düğümleri Ekle (Komşusu olmasa bile)
        # ---------------------------------------------------------------
        
        tum_koordinatlar = [
            (2, 2), (18, 2), (2, 10), (18, 10), (4, 2), (4, 10), (10, 2), (10, 10),
            (16, 2), (16, 10), (4, 4), (16, 4), (4, 8), (16, 8), (18, 5), (18, 8),
            (7, 2), (7, 0), (10, 0), (0, 10), (20, 2), (18, 6), (20, 6), (20, 8),
            (0, 2), (0, 0), (2, 6), (6, 6), (8, 6), (12, 6), (14, 6), (7, 5), (7, 7),
            (13, 2), (13, 5), (13, 7), (6, 5), (8, 5), (8, 7), (6, 7), (12, 5), (14, 5),
            (14, 7), (12, 7)
        ]
        
        tum_koordinatlar.extend([
            (2, 8), (13, 4), (7, 4), (10, 6), (10, 8), 
            (20, 10), (16, 6), (4, 6), (10, 5), (10, 7)
        ]) 

        for coord in set(tum_koordinatlar):
            if coord not in graf:
                graf[coord] = {}

        return graf
    # --- BİRLEŞTİRME 2 BİTTİ ---
    
    def en_yakin_dugum(self, x, y):
        """ (x, y) piksel koordinatına en yakın ikili yol düğümünün indeksini döner."""
        en_iyi = None
        en_iyi_mesafe = float("inf")
        
        for i, (dx, dy) in enumerate(self.ikili_yol_dugumleri):
            mesafe = math.hypot(dx -x, dy - y)
            if mesafe < en_iyi_mesafe:
                en_iyi_mesafe = mesafe
                en_iyi = i  
        return en_iyi
    
    
    def _heuristik_dosyasi_yukle(self, dosya_adi):
        """
        '0-136 = 1243' formatındaki bir txt dosyasından,
        {0:1243, 1:1213, ...} şeklinde sözlük üretir.
        """
        heuristik = {}

        # harita.py'nin olduğu klasöre göre yolu çöz
        klasor = os.path.dirname(os.path.abspath(__file__))
        yol = os.path.join(klasor, dosya_adi)

        if not os.path.exists(yol):
            print(f"[HEURISTIK] Dosya bulunamadı: {yol}")
            return heuristik

        try:
            with open(yol, "r", encoding="utf-8") as f:
                for satir in f:
                    satir = satir.strip()
                    if not satir or "=" not in satir:
                        continue

                    sol, sag = satir.split("=", 1)
                    sol = sol.strip()      # "0-136"
                    sag = sag.strip()      # "1243"

                    # "0-136" -> "0"
                    try:
                        dugum_str = sol.split("-")[0]
                        dugum_id = int(dugum_str)
                        deger = float(sag)
                        heuristik[dugum_id] = deger
                    except ValueError:
                        # Hatalı satır varsa atla
                        continue

            print(f"[HEURISTIK] {len(heuristik)} düğüm için heuristik yüklendi.")
        except Exception as e:
            print(f"[HEURISTIK] Okuma hatası: {e}")

        return heuristik
    
    def panel_ciz(self):
        # (panel_ciz fonksiyonunun tamamı burada, değişiklik yok)
        ok_sekme_x_pos = self.KUTU_X_KAPALI - self.OK_SEKME_GENISLIK

        if self.kutu_acik:
            kutu_x = self.KUTU_X_ACIK
            ok_sekme_x_pos = kutu_x - self.OK_SEKME_GENISLIK
            kutu_rect = pygame.Rect(kutu_x, self.KUTU_Y, self.KUTU_GENISLIK, self.KUTU_YUKSEKLIK)
            pygame.draw.rect(self.ekran, self.KUTU_BG, kutu_rect)
            pygame.draw.rect(self.ekran, self.KUTU_KENAR, kutu_rect, 3)

            baslik = self.BASLIK_FONT.render("Engeller", True, self.YAZI_RENK)
            self.ekran.blit(baslik, baslik.get_rect(center=(kutu_x + self.KUTU_GENISLIK / 2, self.KUTU_Y + 35)))
            pygame.draw.line(self.ekran, self.KUTU_KENAR, (kutu_x + 20, self.KUTU_Y + 60), (kutu_x + self.KUTU_GENISLIK - 20, self.KUTU_Y + 60), 2)

            butonlar = [
                ("+ Yaya Geçidi Ekle", "BTN_ADD_YAYA"),
                ("+ Yol Çalışması Ekle", "BTN_ADD_CALISMA"),
                ("+ Kasis Ekle", "BTN_ADD_KASIS"),
                ("+ Trafik Işığı Ekle", "BTN_ADD_ISIK"),
                ("+ Buzlu Zemin Ekle", "BTN_ADD_BUZLU"), 
                ("Seçileni Sil", "BTN_DELETE"),
                ("Seçileni Döndür (90°)", "BTN_ROTATE"),
                ("Seçileni Uzat (+)", "BTN_LONGER"),
                ("Seçileni Kısalt (-)", "BTN_SHORTER"),
            ]
            SAYFA_BASINA = 5
            toplam_sayfa = max(1, math.ceil(len(butonlar) / SAYFA_BASINA))
            aktif_sayfa = max(0, min(self.panel_sayfa, toplam_sayfa - 1))

            start_i = aktif_sayfa * SAYFA_BASINA
            gorunen = butonlar[start_i:start_i + SAYFA_BASINA]
            bx, by = kutu_x + 20, self.KUTU_Y + 80
            bw, bh, gap = self.KUTU_GENISLIK - 40, 40, 10

            def buton_ciz(rect, etiket):
                pygame.draw.rect(self.ekran, (255, 255, 255), rect, border_radius=6)
                pygame.draw.rect(self.ekran, (120, 120, 120), rect, 2, border_radius=6)
                yazi = self.BUTON_FONT.render(etiket, True, (20, 20, 20))
                self.ekran.blit(yazi, yazi.get_rect(center=rect.center))

            rectler = {}
            for i, (etiket, ad) in enumerate(gorunen):
                rect = pygame.Rect(bx, by + i * (bh + gap), bw, bh)
                buton_ciz(rect, etiket)
                rectler[ad] = rect

            self.BTN_ADD_YAYA = rectler.get("BTN_ADD_YAYA")
            self.BTN_ADD_CALISMA = rectler.get("BTN_ADD_CALISMA")
            self.BTN_ADD_KASIS = rectler.get("BTN_ADD_KASIS")
            self.BTN_ADD_ISIK = rectler.get("BTN_ADD_ISIK")
            self.BTN_ADD_BUZLU = rectler.get("BTN_ADD_BUZLU")
            self.BTN_DELETE = rectler.get("BTN_DELETE")
            self.BTN_ROTATE = rectler.get("BTN_ROTATE")
            self.BTN_LONGER = rectler.get("BTN_LONGER")
            self.BTN_SHORTER = rectler.get("BTN_SHORTER")

            # Sayfa okları
            sol_ok = pygame.Rect(kutu_x + 25, self.KUTU_Y + self.KUTU_YUKSEKLIK - 45, 35, 25)
            sag_ok = pygame.Rect(kutu_x + self.KUTU_GENISLIK - 60, self.KUTU_Y + self.KUTU_YUKSEKLIK - 45, 35, 25)
            pygame.draw.rect(self.ekran, (230, 230, 230), sol_ok, border_radius=6)
            pygame.draw.rect(self.ekran, (230, 230, 230), sag_ok, border_radius=6)
            pygame.draw.polygon(self.ekran, (40, 40, 40), [(sol_ok.centerx + 5, sol_ok.centery - 7), (sol_ok.centerx - 5, sol_ok.centery), (sol_ok.centerx + 5, sol_ok.centery + 7)])
            pygame.draw.polygon(self.ekran, (40, 40, 40), [(sag_ok.centerx - 5, sag_ok.centery - 7), (sag_ok.centerx + 5, sag_ok.centery), (sag_ok.centerx - 5, sag_ok.centery + 7)])
            sayfa_text = self.BUTON_FONT.render(f"Sayfa {aktif_sayfa + 1}/{toplam_sayfa}", True, (50, 50, 50))
            self.ekran.blit(sayfa_text, (kutu_x + self.KUTU_GENISLIK / 2 - 45, self.KUTU_Y + self.KUTU_YUKSEKLIK - 40))

            self.BTN_PAGE_LEFT = sol_ok
            self.BTN_PAGE_RIGHT = sag_ok
            
        else:
            self.BTN_ADD_YAYA = None
            self.BTN_ADD_CALISMA = None
            self.BTN_ADD_KASIS = None
            self.BTN_ADD_ISIK = None
            self.BTN_ADD_BUZLU = None 
            self.BTN_DELETE = None
            self.BTN_ROTATE = None
            self.BTN_LONGER = None
            self.BTN_SHORTER = None
            self.BTN_PAGE_LEFT = None
            self.BTN_PAGE_RIGHT = None

        # Ok sekmesi
        self.ok_rect = pygame.Rect(ok_sekme_x_pos, self.OK_SEKME_Y, self.OK_SEKME_GENISLIK, self.OK_SEKME_YUKSEKLIK)
        pygame.draw.rect(self.ekran, self.KUTU_BG, self.ok_rect, border_top_left_radius=8, border_bottom_left_radius=8)
        pygame.draw.rect(self.ekran, self.KUTU_KENAR, self.ok_rect, 2, border_top_left_radius=8, border_bottom_left_radius=8)
        ok_my = self.OK_SEKME_Y + self.OK_SEKME_YUKSEKLIK / 2
        ok_mx = ok_sekme_x_pos + self.OK_SEKME_GENISLIK / 2
        pts = ([(ok_mx - 4, ok_my - 10), (ok_mx + 4, ok_my), (ok_mx - 4, ok_my + 10)] if self.kutu_acik else [(ok_mx + 4, ok_my - 10), (ok_mx - 4, ok_my), (ok_mx + 4, ok_my + 10)])
        pygame.draw.polygon(self.ekran, self.OK_RENK, pts, 3)

       
    def grid_to_pixel(self, gx, gy):
        """
        Grid koordinatlarini (c, r) piksele cevirir.
        Eger gelen degerler zaten piksel cinsindeyse (HUCRE/SUTUN araligindan bariz buyuk),
        oldugu gibi dondurur; boylece manuel/piksel tabanli dugumlerle de uyumlu kalir.
        """
        # Grid araliginda mi diye kaba bir kontrol
        if (
            -self.SUTUN - 2 <= gx <= self.SUTUN + 2
            and -self.SATIR - 2 <= gy <= self.SATIR + 2
        ):
            px = self.KENAR_BOSLUK + self.OFFSET_X + gx * self.HUCRE
            py = self.KENAR_BOSLUK + self.OFFSET_Y + gy * self.HUCRE
            return px, py

        # Zaten piksel gibi duruyorsa dokunma
        return gx, gy
    def dekor_ciz(self):
        """Haritada sabit dekor görsellerini çizer."""
        if getattr(self, "dekor_sol_img", None):
            self.ekran.blit(self.dekor_sol_img, self.dekor_sol_rect)
        if getattr(self, "dekor_sag_img", None):
            self.ekran.blit(self.dekor_sag_img, self.dekor_sag_rect)
                # Ağaçların çizimi
        if self.agac_img:
            for (ax, ay) in self.agac_konumlari:
                rect = self.agac_img.get_rect(center=(ax, ay + 40))  # +40 aşağı kaydırma
                self.ekran.blit(self.agac_img, rect)
                # Sağ üst dekor çizimi
                # Çocuk oyun parkı çizimi
        if getattr(self, "park_img", None):
            self.ekran.blit(self.park_img, self.park_rect)
                # Çardaklar (oyun parkının üstü ve altı)
        if getattr(self, "cardak_img", None):
            if self.cardak_ust_rect:
                self.ekran.blit(self.cardak_img, self.cardak_ust_rect)
            if self.cardak_alt_rect:
                self.ekran.blit(self.cardak_img, self.cardak_alt_rect)





    def ekran_temizle(self):
        self.ekran.fill(self.CIMEN)

    def saat_tik(self, fps=60):
        self.saat.tick(fps)
        
        
        
