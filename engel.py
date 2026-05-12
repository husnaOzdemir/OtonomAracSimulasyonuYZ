import pygame, math, random


class Engel:
    def ciz(self):
        pass

    def carpisti_mi(self, x, y):
        return False


class YayaGecidi(Engel):
    # ... (Bu sınıfın tamamı aynı, değişiklik yok)
    _tum_yaya_gorselleri = []

    def __init__(self, harita, p1, p2, genislik):
        self.h = harita
        self.genislik = genislik
        self.cizgi_genislik = max(6, int(self.genislik * 0.12))
        self.bosluk = self.cizgi_genislik

        self.yayalar_aktif_mi = False
        self.aktif_sure = 5000
        self.pasif_sure = 8000
        self.son_degisim_zamani = pygame.time.get_ticks() + 3000

        self.yaya_hiz = 0.3
        self.yaya_konumlari = []
        self.yaya_yonleri = []
        self.yaya_sayisi = 3
        self.yaya_aralik = 0.3
        self.yaya_bekleme_suresi = 0

        if not YayaGecidi._tum_yaya_gorselleri:
            try:
                tek_yaya_orijinal = pygame.image.load("yaya2.png").convert_alpha()
                scaled_yaya = pygame.transform.scale(tek_yaya_orijinal, (30, 30))
                YayaGecidi._tum_yaya_gorselleri.append(scaled_yaya)
            except pygame.error:
                print("Uyarı: 'yaya2.png' dosyası bulunamadı. Yayalar daire olarak çizilecek.")

        self.secilen_yaya_orijinal = random.choice(YayaGecidi._tum_yaya_gorselleri) if YayaGecidi._tum_yaya_gorselleri else None
        self.yaya_gorsel_1 = None
        self.yaya_gorsel_2 = None
        self._yol_yonune_dik_yerlestir(p1, p2)

    def _yol_yonune_dik_yerlestir(self, p1_orijinal, p2_orijinal):
        merkez_x = (p1_orijinal[0] + p2_orijinal[0]) / 2
        merkez_y = (p1_orijinal[1] + p2_orijinal[1]) / 2
        dogrular = []
        for seg in self.h.yollar:
            for i in range(len(seg) - 1):
                p1, p2 = seg[i], seg[i + 1]
                if p1[0] == p2[0] or p1[1] == p2[1]:
                    dogrular.append((p1, p2))
        en_iyi = None
        en_kucuk = float('inf')
        for yol_p1, yol_p2 in dogrular:
            (x1, y1), (x2, y2) = yol_p1, yol_p2
            vx, vy = (x2 - x1), (y2 - y1)
            uzunluk = math.hypot(vx, vy)
            if uzunluk == 0:
                continue
            ux, uy = vx / uzunluk, vy / uzunluk
            wx, wy = merkez_x - x1, merkez_y - y1
            t = max(0, min(uzunluk, wx * ux + wy * uy))
            px = x1 + ux * t
            py = y1 + uy * t
            dik = abs(wx * (-uy) + wy * ux)
            if dik < en_kucuk:
                en_kucuk = dik
                en_iyi = (yol_p1, yol_p2, (px, py), t, ux, uy)
        sonuc = en_iyi
        if sonuc is None:
            self.p1 = p1_orijinal
            self.p2 = p2_orijinal
        else:
            yol_p1, yol_p2, (proj_x, proj_y), _t, ux, uy = sonuc
            dik_ux = -uy
            dik_uy = ux
            yaya_gecidi_uzunlugu = self.h.YOL_KALINLIK
            yarim = yaya_gecidi_uzunlugu / 2
            self.p1 = (proj_x + dik_ux * yarim, proj_y + dik_uy * yarim)
            self.p2 = (proj_x - dik_ux * yarim, proj_y - dik_uy * yarim)
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk > 0:
            self.yaya_aci = math.degrees(math.atan2(-vy, vx))
        else:
            self.yaya_aci = 0
        if self.secilen_yaya_orijinal:
            self.yaya_gorsel_1 = pygame.transform.rotate(self.secilen_yaya_orijinal, self.yaya_aci)
            self.yaya_gorsel_2 = pygame.transform.rotate(self.secilen_yaya_orijinal, self.yaya_aci + 180)

    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def update(self):
        simdiki_zaman = pygame.time.get_ticks()
        if self.yayalar_aktif_mi:
            if simdiki_zaman - self.son_degisim_zamani > self.aktif_sure:
                self.yayalar_aktif_mi = False
                self.son_degisim_zamani = simdiki_zaman
                self.yaya_konumlari = []
                self.yaya_yonleri = []
        else:
            if simdiki_zaman - self.son_degisim_zamani > self.pasif_sure:
                self.yayalar_aktif_mi = True
                self.son_degisim_zamani = simdiki_zaman
                self.yaya_konumlari = [0.0]
                self.yaya_yonleri = [True]
        if self.yayalar_aktif_mi:
            self._yayalari_hareket_ettir()

    def _yayalari_hareket_ettir(self):
        if not self.yaya_konumlari:
            return
        for i in range(len(self.yaya_konumlari) - 1, -1, -1):
            if self.yaya_yonleri[i]:
                self.yaya_konumlari[i] += self.yaya_hiz / self.genislik
                if self.yaya_konumlari[i] >= 1.0:
                    self.yaya_konumlari.pop(i)
                    self.yaya_yonleri.pop(i)
            else:
                self.yaya_konumlari[i] -= self.yaya_hiz / self.genislik
                if self.yaya_konumlari[i] <= 0.0:
                    self.yaya_konumlari.pop(i)
                    self.yaya_yonleri.pop(i)
        if len(self.yaya_konumlari) < self.yaya_sayisi:
            self.yaya_bekleme_suresi -= 1
            if self.yaya_bekleme_suresi <= 0:
                if random.random() < 0.02:
                    baslangic_tarafi = random.choice([True, False])
                    yeni_konum = 0.0 if baslangic_tarafi else 1.0
                    yeni_yon = baslangic_tarafi
                    yeterince_uzak = True
                    for mevcut_konum in self.yaya_konumlari:
                        if abs(mevcut_konum - yeni_konum) < self.yaya_aralik:
                            yeterince_uzak = False
                            break
                    if yeterince_uzak:
                        self.yaya_konumlari.append(yeni_konum)
                        self.yaya_yonleri.append(yeni_yon)
                        self.yaya_bekleme_suresi = random.randint(30, 120)
                        
    def icinde_mi(self, x, y):
        # çizgisel engeller için ortak nokta-projeksiyon kontrolü
        try:
            t, dik, uzunluk = self._proj_ve_mesafe(x, y)
            return (0 <= t <= uzunluk) and dik <= (self.genislik / 2)
        except:
            return False


    def carpisti_mi(self, x, y):
        if not self.yayalar_aktif_mi:
            return False
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        if 0 <= t <= uzunluk and dik <= self.genislik / 2:
            return True
        return False

    def ciz(self):
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return
        ux, uy = vx / uzunluk, vy / uzunluk
        px, py = -uy, ux
        t = 0
        while t <= uzunluk:
            cx = x1 + ux * t
            cy = y1 + uy * t
            yarim = self.genislik / 2
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            pygame.draw.line(ekran, (255, 255, 255), a, b, self.cizgi_genislik)
            t += self.cizgi_genislik + self.bosluk
        if self.yayalar_aktif_mi and self.yaya_konumlari:
            yaya_rengi_fallback = (220, 50, 50)
            yaya_yaricap_fallback = 7
            yanal_konumlar = [self.genislik * -0.3, 0, self.genislik * 0.3]
            for i, (yaya_konum, yaya_yon) in enumerate(zip(self.yaya_konumlari, self.yaya_yonleri)):
                t = uzunluk * yaya_konum
                yanal_index = i % len(yanal_konumlar)
                kaydirma = yanal_konumlar[yanal_index]
                cx = int(x1 + ux * t + px * kaydirma)
                cy = int(y1 + uy * t + py * kaydirma)
                if self.yaya_gorsel_1:
                    g = self.yaya_gorsel_1 if yaya_yon else self.yaya_gorsel_2
                    rect = g.get_rect(center=(cx, cy))
                    ekran.blit(g, rect)
                else:
                    pygame.draw.circle(ekran, yaya_rengi_fallback, (cx, cy), yaya_yaricap_fallback)
                    pygame.draw.circle(ekran, (0, 0, 0), (cx, cy), yaya_yaricap_fallback, 2)


class YolCalismasi(Engel):
    # ... (Bu sınıfın tamamı aynı, değişiklik yok)
    def __init__(self, harita, p1, p2, genislik):
        self.h = harita
        self.p1 = p1
        self.p2 = p2
        self.genislik = genislik

    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def carpisti_mi(self, x, y):
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        return (0 <= t <= uzunluk) and (dik <= self.genislik / 2)
    
    def icinde_mi(self, x, y):
        """
        Aracın bu çizgisel engelin üzerinde olup olmadığını kontrol eder.
        _proj_ve_mesafe: (t, dik_mesafe, uzunluk)
        """
        try:
            t, dik, uzunluk = self._proj_ve_mesafe(x, y)
            return (0 <= t <= uzunluk) and (dik <= self.genislik / 2)
        except:
            return False


    def ciz(self):
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return
        ux, uy = vx / uzunluk, vy / uzunluk
        px, py = -uy, ux
        yarim = self.genislik / 2
        adim = max(8, int(self.genislik * 0.18))
        t = 0
        while t <= uzunluk:
            cx = x1 + ux * t
            cy = y1 + uy * t
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            renk = (255, 140, 0) if (int(t / adim) % 2 == 0) else (230, 120, 0)
            pygame.draw.line(ekran, renk, a, b, max(6, int(self.genislik * 0.6)))
            t += adim


class HizKesici(Engel):
    def __init__(self, harita, p1, p2, genislik, carpma_orani=0.6):
        self.h = harita
        self.p1 = p1
        self.p2 = p2
        self.genislik = genislik
        self.carpma_orani = carpma_orani

    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def icinde_mi(self, x, y):
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        return (0 <= t <= uzunluk) and (dik <= self.genislik / 2)

    def carpisti_mi(self, x, y):
        # Kasis üzerindeki maliyet/çarpışma kontrolleri için kapsama testi
        return self.icinde_mi(x, y)

    def ciz(self):
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        L = math.hypot(vx, vy)
        if L == 0:
            return
        ux, uy = vx / L, vy / L
        px, py = -uy, ux
        yarim = self.genislik / 2
        cizgi = max(6, int(self.genislik * 0.18))
        aralik = cizgi
        t = 0
        renkler = [(255, 210, 0), (60, 60, 60)]
        i = 0
        while t <= L:
            cx = x1 + ux * t
            cy = y1 + uy * t
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            pygame.draw.line(ekran, renkler[i % 2], a, b, cizgi)
            t += aralik
            i += 1


# engel.py dosyasındaki TrafikIsigi sınıfı
class TrafikIsigi(Engel):
    # ... (self.__init__, gorsel_konumunu_guncelle, guncelle metotları aynı kalır)
    
    def __init__(self, harita, c=0, r=0, yon='dikey', baslangic_durumu="kirmizi", kirmizi_sure_sn=3, yesil_sure_sn=3, sari_sure_sn=2):
        self.h = harita
        self.c, self.r = c, r
        self.pixel_pos = self.h.kose(c, r)
        self.yon = yon
        self.tip = "isik"
        self.lamba_yaricap = int(self.h.HUCRE * 0.1) if self.h.HUCRE > 0 else 5
        self.surukleniyor_ilk = False
        self.kutu_rect = pygame.Rect(0, 0, 0, 0)
        self.kutu_genislik = 0
        self.kutu_yukseklik = 0
        self.kirmizi_pos = (0, 0)
        self.sari_pos = (0, 0)
        self.yesil_pos = (0, 0)
        self.stop_line_p1 = (0, 0)
        self.stop_line_p2 = (0, 0)
        self.gorsel_konumunu_guncelle()
        self.durum = baslangic_durumu
        self.kirmizi_sure = kirmizi_sure_sn * 60
        self.yesil_sure = yesil_sure_sn * 60
        self.sari_sure = sari_sure_sn * 60
        if self.durum == "kirmizi":
            self.zamanlayici = self.kirmizi_sure
        elif self.durum == "yesil":
            self.zamanlayici = self.yesil_sure
        else:
            self.zamanlayici = self.sari_sure

    def gorsel_konumunu_guncelle(self):
        lamba_araligi = self.lamba_yaricap * 2.5
        is_dikey_kutu = self.yon == 'yatay' or self.surukleniyor_ilk
        if self.surukleniyor_ilk:
            self.pixel_pos = pygame.mouse.get_pos()
        if is_dikey_kutu:
            self.kutu_genislik = self.lamba_yaricap * 2 + int(self.lamba_yaricap * 0.5)
            self.kutu_yukseklik = (self.lamba_yaricap * 6) + (self.lamba_yaricap * 2)
            offset_y = 0 if self.surukleniyor_ilk else -(self.h.YOL_KALINLIK / 2 + self.kutu_yukseklik / 2 + 5)
            offset_x = 0
        else:
            self.kutu_genislik = (self.lamba_yaricap * 6) + (self.lamba_yaricap * 2)
            self.kutu_yukseklik = self.lamba_yaricap * 2 + int(self.lamba_yaricap * 0.5)
            offset_y = -(self.h.YOL_KALINLIK / 2 + self.kutu_yukseklik / 2 + 5)
            offset_x = 0
        self.kutu_rect = pygame.Rect(self.pixel_pos[0] + offset_x - self.kutu_genislik / 2, self.pixel_pos[1] + offset_y - self.kutu_yukseklik / 2, self.kutu_genislik, self.kutu_yukseklik)
        if is_dikey_kutu:
            mx = self.kutu_rect.centerx
            self.kirmizi_pos = (mx, self.kutu_rect.top + lamba_araligi)
            self.sari_pos = (mx, self.kirmizi_pos[1] + lamba_araligi)
            self.yesil_pos = (mx, self.sari_pos[1] + lamba_araligi)
        else:
            my = self.kutu_rect.centery
            self.kirmizi_pos = (self.kutu_rect.left + lamba_araligi, my)
            self.sari_pos = (self.kirmizi_pos[0] + lamba_araligi, my)
            self.yesil_pos = (self.sari_pos[0] + lamba_araligi, my)
        if not self.surukleniyor_ilk:
            yr = self.h.YOL_KALINLIK / 2
            if self.yon == 'dikey':
                self.stop_line_p1 = (self.pixel_pos[0] - yr, self.pixel_pos[1])
                self.stop_line_p2 = (self.pixel_pos[0] + yr, self.pixel_pos[1])
            else:
                self.stop_line_p1 = (self.pixel_pos[0], self.pixel_pos[1] - yr)
                self.stop_line_p2 = (self.pixel_pos[0], self.pixel_pos[1] + yr)
            px, py = self.pixel_pos
            ux, uy = (0, 1) if self.yon == 'dikey' else (1, 0)
            self.p1 = (px - ux * 1, py - uy * 1)
            self.p2 = (px + ux * 1, py + uy * 1)

    def guncelle(self):
        if self.surukleniyor_ilk:
            self.gorsel_konumunu_guncelle()
            return
        self.zamanlayici -= 1
        if self.zamanlayici <= 0:
            if self.durum == "kirmizi":
                self.durum = "yesil"; self.zamanlayici = self.yesil_sure
            elif self.durum == "yesil":
                self.durum = "sari"; self.zamanlayici = self.sari_sure
            elif self.durum == "sari":
                self.durum = "kirmizi"; self.zamanlayici = self.kirmizi_sure

    def ciz(self):
        ekran = self.h.ekran
        
        # <<< GÜNCEL KURAL: STOP ÇİZGİSİ SADECE KIRMIZIDA ÇİZİLİR >>>
        if not self.surukleniyor_ilk and (self.durum == "kirmizi"):
            try:
                pygame.draw.line(ekran, self.h.STOP_LINE_RENK, 
                                 (int(self.stop_line_p1[0]), int(self.stop_line_p1[1])), 
                                 (int(self.stop_line_p2[0]), int(self.stop_line_p2[1])), 4)
            except TypeError:
                pass
        
        pygame.draw.rect(ekran, self.h.ISIK_KUTU, self.kutu_rect, border_radius=5)
        k, s, y = self.h.KAPALI_KIRMIZI, self.h.KAPALI_SARI, self.h.KAPALI_YESIL
        if self.durum == "kirmizi":
            k = self.h.ACIK_KIRMIZI
        elif self.durum == "sari":
            s = self.h.ACIK_SARI
        elif self.durum == "yesil":
            y = self.h.ACIK_YESIL
            
        pygame.draw.circle(ekran, k, (int(self.kirmizi_pos[0]), int(self.kirmizi_pos[1])), int(self.lamba_yaricap))
        pygame.draw.circle(ekran, s, (int(self.sari_pos[0]), int(self.sari_pos[1])), int(self.lamba_yaricap))
        pygame.draw.circle(ekran, y, (int(self.yesil_pos[0]), int(self.yesil_pos[1])), int(self.lamba_yaricap))

    def carpisti_mi(self, x, y):
        return math.hypot(self.pixel_pos[0] - x, self.pixel_pos[1] - y) < self.h.HUCRE * 0.6

# --- GÜNCELLENMİŞ KAYGAN ZEMİN SINIFI ---
class KayganZemin(Engel):
    def __init__(self, harita, p1, p2, genislik, kayma_etkisi=0.3):
        self.h = harita
        self.p1 = p1
        self.p2 = p2
        self.genislik = genislik
        self.kayma_etkisi = kayma_etkisi 
        
        # Sadece orijinal görseli yükle ve cache'le
        # Bu, her karede diskten okuma yapmayı engeller
        self.gorsel_orijinal = None
        try:
            gorsel_adi = "buzlu.png" 
            self.gorsel_orijinal = pygame.image.load(gorsel_adi).convert_alpha() 
        except Exception as e:
            print(f"Uyarı: '{gorsel_adi}' görseli yüklenemedi: {e}")
            
        # Görselin geçici olarak saklanacağı değişkenler
        self.gorsel_cache = None
        self.gorsel_rect_cache = None
        self.son_p1 = None
        self.son_p2 = None


    def _proj_ve_mesafe(self, x, y):
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        uzunluk = math.hypot(vx, vy)
        if uzunluk == 0:
            return 0, float('inf'), 0
        ux, uy = vx / uzunluk, vy / uzunluk
        wx, wy = x - x1, y - y1
        t = wx * ux + wy * uy
        dik = abs(wx * (-uy) + wy * ux)
        return t, dik, uzunluk

    def icinde_mi(self, x, y):
        t, dik, uzunluk = self._proj_ve_mesafe(x, y)
        return (0 <= t <= uzunluk) and (dik <= self.genislik / 2)

    def carpisti_mi(self, x, y):
        return False

    def _ciz_placeholder(self):
        """Görsel yüklenemezse veya hata olursa yedek çizim yapar."""
        ekran = self.h.ekran
        (x1, y1), (x2, y2) = self.p1, self.p2
        vx, vy = (x2 - x1), (y2 - y1)
        L = math.hypot(vx, vy)
        if L == 0: return
        ux, uy = vx / L, vy / L
        px, py = -uy, ux
        yarim = self.genislik / 2
        cizgi = max(6, int(self.genislik * 0.18))
        aralik = cizgi
        t = 0
        renkler = [(200, 220, 255), (230, 240, 255)] 
        i = 0
        while t <= L:
            cx = x1 + ux * t
            cy = y1 + uy * t
            a = (cx + px * (-yarim), cy + py * (-yarim))
            b = (cx + px * (yarim), cy + py * (yarim))
            pygame.draw.line(ekran, renkler[i % 2], a, b, cizgi)
            t += aralik
            i += 1

    def ciz(self):
        ekran = self.h.ekran

        # --- GÜNCELLEME: Görseli p1/p2 değiştiyse yeniden hesapla ---
        # Bu, sürükleme (main.py'den p1/p2 değiştiğinde) ve
        # yeniden boyutlandırma (helpers'dan p1/p2 değiştiğinde)
        # sırasında görselin güncel kalmasını sağlar.
        
        # p1 veya p2 değiştiyse, görseli yeniden hesapla
        if self.p1 != self.son_p1 or self.p2 != self.son_p2:
            self.son_p1 = self.p1
            self.son_p2 = self.p2
            
            vx, vy = (self.p2[0] - self.p1[0]), (self.p2[1] - self.p1[1])
            uzunluk = math.hypot(vx, vy)
            
            if uzunluk < 1: 
                uzunluk = 1 # 0'a bölme hatasını engelle
                
            aci = math.degrees(math.atan2(-vy, vx))
            
            if self.gorsel_orijinal:
                try:
                    # Orijinal görseli ölçekle ve döndür
                    gorsel_olcekli = pygame.transform.scale(
                        self.gorsel_orijinal, (int(uzunluk), int(self.genislik))
                    )
                    gorsel = pygame.transform.rotate(gorsel_olcekli, aci)
                    
                    # Resmin merkezini p1-p2 hattının merkezine ata
                    merkez_x = (self.p1[0] + self.p2[0]) / 2
                    merkez_y = (self.p1[1] + self.p2[1]) / 2
                    gorsel_rect = gorsel.get_rect(center=(merkez_x, merkez_y))

                    # Hesaplanan değerleri cache'le
                    self.gorsel_cache = gorsel
                    self.gorsel_rect_cache = gorsel_rect
                    
                except Exception as e:
                    # Ölçekleme hatası (genellikle uzunluk=0)
                    print(f"Hata: Kaygan zemin görseli işlenemedi: {e}")
                    self.gorsel_cache = None
                    self.gorsel_rect_cache = None
            else:
                self.gorsel_cache = None
                self.gorsel_rect_cache = None

        # --- Çizim Aşaması ---
        if self.gorsel_cache and self.gorsel_rect_cache:
            # Cache'lenmiş (hesaplanmış) görseli ekrana çiz
            ekran.blit(self.gorsel_cache, self.gorsel_rect_cache)
        else:
            # Görsel yoksa veya yüklenemediyse, yedek çizimi yap
            self._ciz_placeholder()
# --- SINIF SONU ---


# --- YARDIMCI FONKSİYONLAR (GÜNCELLENDİ) ---
def yol_dogrularini_cikar(yollar_listesi):
    alt = []
    for seg in yollar_listesi:
        for i in range(len(seg) - 1):
            p1, p2 = seg[i], seg[i + 1]
            if p1[0] == p2[0] or p1[1] == p2[1]:
                alt.append((p1, p2))
    return alt


def projeksiyon_ve_yakin_dik_mesafe(p1, p2, x, y):
    (x1, y1), (x2, y2) = p1, p2
    vx, vy = (x2 - x1), (y2 - y1)
    uzunluk = math.hypot(vx, vy)
    if uzunluk == 0:
        return (x1, y1), float('inf'), 0, 0, 0
    ux, uy = vx / uzunluk, vy / uzunluk
    wx, wy = x - x1, y - y1
    t = max(0, min(uzunluk, wx * ux + wy * uy))
    px = x1 + ux * t
    py = y1 + uy * t
    dik = abs(wx * (-uy) + wy * ux)
    return (px, py), dik, t, ux, uy


def en_yakin_duz_segmente_projeksiyon(harita, x, y):
    dogrular = yol_dogrularini_cikar(harita.yollar)
    en_iyi = None
    en_kucuk = float('inf')
    for p1, p2 in dogrular:
        (px, py), dik, t, ux, uy = projeksiyon_ve_yakin_dik_mesafe(p1, p2, x, y)
        if dik < en_kucuk:
            en_kucuk = dik
            en_iyi = (p1, p2, (px, py), t, ux, uy)
    return en_iyi


def engel_uzunlugunu_degistir(harita, engel, delta_px):
    if isinstance(engel, TrafikIsigi):
        if delta_px > 0:
            engel.yesil_sure = min(engel.yesil_sure + 60, 600)
        else:
            engel.yesil_sure = max(engel.yesil_sure - 60, 60)
        if engel.durum == "yesil":
            engel.zamanlayici = engel.yesil_sure
    else:
        merkez = ((engel.p1[0] + engel.p2[0]) / 2, (engel.p1[1] + engel.p2[1]) / 2)
        mevcut_uzunluk = math.hypot(engel.p2[0] - engel.p1[0], engel.p2[1] - engel.p1[1])
        yeni_uzunluk = max(20, mevcut_uzunluk + delta_px)
        sonuc = en_yakin_duz_segmente_projeksiyon(harita, *merkez)
        if sonuc is None:
            return
        p1, p2, (px, py), _t, ux, uy = sonuc
        yarim = yeni_uzunluk / 2
        engel.p1 = (px - ux * yarim, py - uy * yarim)
        engel.p2 = (px + ux * yarim, py + uy * yarim)

# 90 derece döndürme fonksiyonu
def engel_dondur_90(harita, engel):
    if isinstance(engel, TrafikIsigi):
        # Trafik ışığı için bu kod zaten doğru çalışıyor (dikey/yatay geçişi)
        engel.yon = 'yatay' if engel.yon == 'dikey' else 'dikey'
        engel.gorsel_konumunu_guncelle()
    else:
        # Diğer engeller için (YayaGecidi, YolCalismasi, HizKesici, KayganZemin)
        
        # 1. Engelin mevcut merkezini ve uzunluğunu al
        merkez = ((engel.p1[0] + engel.p2[0]) / 2, (engel.p1[1] + engel.p2[1]) / 2)
        uzunluk = math.hypot(engel.p2[0] - engel.p1[0], engel.p2[1] - engel.p1[1])

        # 2. Engelin mevcut yön vektörünü (unit vector) hesapla
        if uzunluk < 1e-6:
            e_ux, e_uy = 1.0, 0.0 # Eğer uzunluk sıfırsa, varsayılan olarak yatay kabul et
        else:
            e_ux = (engel.p2[0] - engel.p1[0]) / uzunluk
            e_uy = (engel.p2[1] - engel.p1[1]) / uzunluk

        # 3. En yakın yol segmentinin merkezini (px, py) ve yön vektörünü (yol_ux, yol_uy) bul
        sonuc = en_yakin_duz_segmente_projeksiyon(harita, *merkez)
        if sonuc is None:
            return
        _sp1, _sp2, (px, py), _t, yol_ux, yol_uy = sonuc

        # 4. Engelin yönü ile yolun yönü paralel mi diye kontrol et
        # Dot product (iç çarpım) kullan:
        # Paralel iseler |dot_product| ~ 1
        # Dik iseler |dot_product| ~ 0
        dot_product = e_ux * yol_ux + e_uy * yol_uy

        # 5. Yeni yönü belirle
        yarim = uzunluk / 2
        
        # abs(dot_product) > 0.9: Engelin yönü yolun yönüne çok yakın (paralel)
        if abs(dot_product) > 0.9: 
            # Şu an YOLA PARALEL -> YOLA DİK yap
            yeni_ux, yeni_uy = -yol_uy, yol_ux
            engel.p1 = (px - yeni_ux * yarim, py - yeni_uy * yarim)
            engel.p2 = (px + yeni_ux * yarim, py + yeni_uy * yarim)
        else:
            # Şu an YOLA DİK (veya başka bir açıda) -> YOLA PARALEL yap
            yeni_ux, yeni_uy = yol_ux, yol_uy
            engel.p1 = (px - yeni_ux * yarim, py - yeni_uy * yarim)
            engel.p2 = (px + yeni_ux * yarim, py + yeni_uy * yarim)
            
        # Not: KayganZemin'in p1/p2'si değiştiği için, 'ciz' fonksiyonu
        # bir sonraki karede görseli otomatik olarak güncelleyecektir.
        # Ekstra bir şey yapmaya gerek yok.
#! --- DÜZELTİLMİŞ FONKSİYON SONU ---
