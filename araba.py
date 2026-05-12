import math
import pygame

from sezgisel_olmayan import bfs_yol, ucs_yol, _engel_cezasi
from optimal_sezgisel import astar_yol, ida_star_yol,  _kenar_maliyeti
from greedy import greedy_yol, greedy_rotala
from dfs import dfs_yol
from npc_araba import NPCArac
from engel import YolCalismasi, YayaGecidi, TrafikIsigi, HizKesici, KayganZemin


class Araba(NPCArac):
    """
    Ana araç sağ şeridi tercih eder; seçilen algoritma (BFS/UCS/A*) ile hedef düğüm için rota kurar.
    Engel maliyetleri dinamik rota seçiminde dikkate alınır.
    """

    def __init__(self, harita, engeller_ref, npc_ref, x, y, genislik, yukseklik, gorsel_yolu="mainaraba.png", algoritma_getir=None):
        super().__init__(
            harita,
            x,
            y,
            genislik,
            yukseklik,
            resim_yolu=gorsel_yolu,
            yedek_renk=(220, 0, 0),
            engeller_ref=engeller_ref,
            npc_ref=npc_ref,
        )
        # Sabit hız/ivme tercihleri (ana araç)
        self.normal_maks_hiz = 2.0
        self.normal_ivme = 0.12
        self.kaygan_maks_hiz = self.normal_maks_hiz * 1.2
        self.kaygan_ivme = self.normal_ivme * 1.1
        self.kasis_hizi = self.normal_maks_hiz * 0.55
        self.serit_tercihi = "sag"
        self.kaygan_zemin_uzerinde = False
        self.sensor_mesafeleri = []
        self.hedef_global_id = 136  # Hedef düğüm ID'si
        self.hedefe_ulasti = False
        self.son_maliyet = 0.0
        self.son_adim = 0
        self.katedilen_patika = [] # Geçilen düğüm patikası
        self.son_patika = [] # Son rota patikası
        self.cimen_yasakli_kenarlar = set()
        self.rota_yeni_engeller = set()
        self.algoritma_getir = algoritma_getir or (lambda: None)
        self.ilk_patika = []  # Oyunun ilk hesaplanan rotasŽñnŽñ saklama listesi
        self.dfs_kilitli_rota = None
        self.dfs_modu_aktif = False

        
        # --- HIZ KONTROLÜ VE SERİT HİZALAMA ---
        # Sensör mesafesine göre hız kontrolü (0 dereceli sensör)
        hiz_carpan = 1.0
        sensor_mesafeleri = self.get_sensor_distances() # Sensör mesafelerini al
        on_sensor_mesafe = sensor_mesafeleri[1] if len(sensor_mesafeleri) > 1 else 150  # 0 dereceli sensör (index 1)
        
        if on_sensor_mesafe <= 15:
            # Mesafe 15 veya daha azsa dur
            durmali = True
        elif on_sensor_mesafe <= 25:
            # Mesafe 25 veya daha azsa hızı 1/10 oranında düşür
            hiz_carpan = min(hiz_carpan, 0.1)
        if self._ana_araba_tam_ondami():
            durmali = True
            hiz_carpan = min(hiz_carpan, 0.20)
        # Mesafe > 15 ise default hız (hiz_carpan = 1.0 zaten)
        self.hiz *= hiz_carpan
        
        # --- DİNAMİK ROTA VE DÜĞÜM TAKİP SİSTEMİ ---
        self.rota_engel_ids = set()
        
        # Ana araç için sensörler görünür (NPC'ler görünmez)
        self.sensorler_gorunur = True

        self._seritte_hizala()


    def _seritte_hizala(self):
        """Araci en yakin dugume yapistirir ve acisini hedefe gore ayarlar."""
        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        if not dugumler:
            return
        baslangic_id = self._en_yakin_dugumu_bul(self.x, self.y)
        if baslangic_id is None or baslangic_id >= len(dugumler):
            return
        self.x, self.y = dugumler[baslangic_id]
        self.onceki_dugum_id = baslangic_id
        self.aktif_patika = [baslangic_id]
        self.katedilen_patika = [baslangic_id]
        self.son_patika = list(self.aktif_patika)
        self.aktif_adim = 0
        self.hedef_dugum_id = None
        # Baslangicta seride hizala: baslangic dugumunun ilk komsusuna yonlen
        self.aci = 0
        graf = getattr(self.h, "ikili_yol_graf", {})
        komsular = graf.get(baslangic_id, {})
        komsu_id = None
        # İlk komşuya yönel
        if isinstance(komsular, dict) and komsular:
            komsu_id = next(iter(komsular))
        elif isinstance(komsular, (list, tuple)) and komsular:
            komsu_id = komsular[0]
        if komsu_id is not None and komsu_id < len(dugumler):
            kx, ky = dugumler[komsu_id]
            dx, dy = kx - self.x, ky - self.y
            if dx != 0 or dy != 0:
                self.aci = -math.degrees(math.atan2(dy, dx)) 
        elif self.hedef_global_id < len(dugumler):
            hx, hy = dugumler[self.hedef_global_id]
            dx, dy = hx - self.x, hy - self.y
            self.aci = -math.degrees(math.atan2(dy, dx))
        self.image = self.orijinal_gorsel
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def _yasakli_kenarlar(self):
        """Yol çalışmaları + çim engeline göre yasaklı kenarlar (NPC metodu)."""
        yasak = self._yol_calismasi_kenarlari() # Yol çalışması kenarları
        yasak = yasak.union(getattr(self, "cimen_yasakli_kenarlar", set())) # Çim engeli kenarları
        return yasak
        
    def _rota_maliyet_adim(self, rota):
        """Verilen patikanin toplam kenar maliyetini ve adim sayisini dondurur."""

        # Rota maliyeti = graf'taki kenar maliyeti + engel cezası

        graf = getattr(self.h, "ikili_yol_graf", {})
        engeller = self.get_engeller()
        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        yasakli = self._yasakli_kenarlar()
        algo = self.algoritma_getir()

        toplam = 0.0

        # Rota üzerindeki her kenar için maliyeti hesapla
        for a, b in zip(rota, rota[1:]):

            # A* / IDA* seçiliyse: algoritmanın kullandığı maliyet ile aynı hesap

            if algo in ("A*", "IDA*"):
                km = _kenar_maliyeti(self.h, graf, dugumler, a, b, engeller, yasakli)
                if km is None:
                    # Yol çalışması / yasak kenar yüzünden bu kenar geçilemez
                    return float("inf"), max(0, len(rota) - 1)
                toplam += km
                continue


            # 1) Graf'taki yol maliyetini al
            try:
                w = graf[a][b]
            except:
                # O bağlantı graf'ta tanımlı değilse
                w = 0.0

            # 2) Engel katsayısı + taban maliyeti hesapla
            #    Formül: w + w * katsayi == w * (1 + katsayi)
            kenar_m = _engel_cezasi(self.h, engeller, a, b, w)

            # Engel fonksiyonu None döndürürse (ör. yol çalışması)
            if kenar_m is None:
                kenar_m = w

            # 3) Toplam maliyete ekle
            toplam += kenar_m

        adim = max(0, len(rota) - 1)
        return toplam, adim


    # --- DİNAMİK ROTA HESAPLAMA VE GÜNCELLEME ---
    def _rota_hazirla(self):
        dugumler = getattr(self.h, "ikili_yol_dugumleri", []) # Düğüm listesi
        if not dugumler:
            return
        # Başlangıç düğümünü bul
        baslangic_id = self._en_yakin_dugumu_bul(self.x, self.y)
        if baslangic_id is None:
            return
        algo = self.algoritma_getir()
        if not algo:
            return
        yasakli = self._yasakli_kenarlar()
        rota = []
        dfs_start_idx = None
        if algo == "BFS":
            rota = bfs_yol(self.h, baslangic_id, self.hedef_global_id, self.get_engeller(), yasakli)
        elif algo == "UCS":
            rota = ucs_yol(self.h, baslangic_id, self.hedef_global_id, self.get_engeller(), yasakli)
        elif algo == "A*": 
            rota = astar_yol(self.h, baslangic_id, self.hedef_global_id, self.get_engeller(), yasakli)
        elif algo == "IDA*":
            rota = ida_star_yol(self.h, baslangic_id, self.hedef_global_id, self.get_engeller(), yasakli)
        elif algo == "Greedy":
            # Eski mevcut_rota parametresi kaldırıldı.
            rota = greedy_rotala(
                self.h,
                baslangic_id,
                self.get_engeller(),
                yasakli,
            )
        elif algo == "DFS":

            baslangic_id = baslangic_id

            mevcut_rota = getattr(self, "dfs_kilitli_rota", None)

            # Eğer DFS modundaysak ve rota eşik aşmıyorsa eski DFS rotasını kullan
            if self.dfs_modu_aktif and mevcut_rota:
                if not self._dfs_rota_esigi_asiyor_mu(mevcut_rota):
                    self.aktif_patika = list(mevcut_rota)
                    self.son_patika = list(mevcut_rota)
                    return  

            # Eşik aşıldı veya ilk defa çalışıyor → yeniden DFS çöz
            engeller = self.get_engeller()
            rota = dfs_yol(self.h, baslangic_id, engeller, yasakli)

            # DFS rotasını kilitle
            self.dfs_kilitli_rota = list(rota)
            self.dfs_modu_aktif = True

            dfs_start_idx = self._dfs_yeni_rota_baslangic_indisi(rota)


        # Rota bulunduysa aktif patikayı ayarla
        if rota and len(rota) > 1:
            if not self.ilk_patika:
                self.ilk_patika = list(rota)
            self.aktif_patika = list(rota)
            self.son_patika = list(rota)
            start_idx = dfs_start_idx if dfs_start_idx is not None else 0
            start_idx = max(0, min(start_idx, len(rota) - 2))
            self.aktif_adim = start_idx + 1
            self.hedef_dugum_id = rota[start_idx + 1]
            self.onceki_dugum_id = rota[start_idx]
            self.son_maliyet, self.son_adim = self._rota_maliyet_adim(rota)
            # Rota üzerindeki engel ID'lerini güncelle
            self.rota_engel_ids = self._rota_ile_kesisen_engeller()
            return
        # Yol yoksa varsayılan NPC hesaplamasına dön
        super()._rota_hazirla()
        
    def _dfs_rota_esigi_asiyor_mu(self, rota):
        if not rota or len(rota) < 2:
            return False

        from dfs import _engel_cezasi
        ESIG = 17.0
        engeller = self.get_engeller()

        for a, b in zip(rota, rota[1:]):
            ceza = _engel_cezasi(self.h, engeller, a, b)
            if ceza is None:
                return True
            if ceza > ESIG:
                return True

        return False

    def _dfs_yeni_rota_baslangic_indisi(self, rota):
        if not rota or len(rota) < 2:
            return 0

        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        aktif_patika = getattr(self, "aktif_patika", [])
        aktif_adim = getattr(self, "aktif_adim", 0)
        current_node = None

        if aktif_patika and aktif_adim > 0:
            prev_idx = max(0, min(len(aktif_patika) - 1, aktif_adim - 1))
            current_node = aktif_patika[prev_idx]

        if current_node is not None and current_node in rota:
            idx = rota.index(current_node)
            return max(0, min(idx, len(rota) - 2))

        if not dugumler:
            return 0

        best_idx = 0
        best_dist = float('inf')
        for i in range(len(rota) - 1):
            node_id = rota[i]
            if node_id >= len(dugumler):
                continue
            nx, ny = dugumler[node_id]
            dist = math.hypot(self.x - nx, self.y - ny)
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        return max(0, min(best_idx, len(rota) - 2))

    def _fizik_engel_etkisi(self):
            """Bulunduğu engel türüne göre hız/ivme ayarı yapar."""

            durum = self._aktif_engel_durumu()

            # -------------------------
            # 1) Yol çalışması › dur
            # -------------------------
            if durum["yol_calismasi"]:
                self.hiz = 0
                return

            # -------------------------
            # 2) Yaya geçidi aktif › dur
            # -------------------------
            if durum["yaya_aktif"]:
                self.hiz = 0
                return

            # -------------------------
            # 3) Kırmızı ışık › dur
            # -------------------------
            if durum["kirmizi_isik"]:
                self.hiz = 0
                return

            # -------------------------
            # 4) Sarı ışık › yavaşla
            # -------------------------
            if durum["sari_isik"]:
                self.hiz = min(self.hiz, self.normal_maks_hiz * 0.4)
                return

            # -------------------------
            # 5) Kasis › yavaş sür
            # -------------------------
            if durum["kasis"]:
                self.hiz = min(self.hiz, self.kasis_hizi)
                return

            # -------------------------
            # 6) Kaygan zemin › hızlan
            # -------------------------
            if durum["kaygan"]:
                self.hiz = min(self.hiz + self.kaygan_ivme, self.kaygan_maks_hiz)
                return

            # -------------------------
            # 7) Normal yol › normal hızlan
            # -------------------------
            self.hiz = min(self.hiz + self.normal_ivme, self.normal_maks_hiz) 
            
    def _rota_ile_kesisen_engeller(self):
        """
        Mevcut rotanın (aktif_patika) üzerinden geçen engellerin id() setini döndürür.
        Sadece ROTAYI etkileyen engeller (yol çalışması, aktif yaya geçidi,
        kırmızı ışık, kasis, kaygan zemin) hesaba katılır.
        """
        rota = getattr(self, "aktif_patika", [])
        if not rota or len(rota) < 2:
            return set()

        engeller = self.get_engeller()
        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        if not dugumler or not engeller:
            return set()

        etkileyen = set()

        for a, b in zip(rota, rota[1:]):
            if a >= len(dugumler) or b >= len(dugumler):
                continue

            ax, ay = dugumler[a]
            bx, by = dugumler[b]

            uzunluk = math.hypot(bx - ax, by - ay)
            # Kenar boyunca birkaç noktadan örnek al
            adim = max(4, int(uzunluk / 40)) or 1

            for i in range(adim + 1):
                t = i / adim
                x = ax + (bx - ax) * t
                y = ay + (by - ay) * t

                for e in engeller:
                    # Yol çalışması › her zaman önemli (rota kapanabilir)
                    if isinstance(e, YolCalismasi):
                        if e.icinde_mi(x, y):
                            etkileyen.add(id(e))

                    # Yaya geçidi › sadece yayalar AKTİFSE rotayı ciddi etkiler
                    elif isinstance(e, YayaGecidi):
                        if getattr(e, "yayalar_aktif_mi", False) and e.carpisti_mi(x, y):
                            etkileyen.add(id(e))

                    # Trafik ışığı › kırmızıysa rotayı etkileyen say
                    elif isinstance(e, TrafikIsigi):
                        if getattr(e, "durum", "") == "kirmizi" and e.carpisti_mi(x, y):
                            etkileyen.add(id(e))

                    # Kasis / kaygan zemin › kenar maliyetini değiştirir
                    elif isinstance(e, (HizKesici, KayganZemin)):
                        if e.icinde_mi(x, y):
                            etkileyen.add(id(e))

        return etkileyen
           
    def _rotadaki_yeni_engeller_blokluyor_mu(self):
        """Yeni eklenen engeller güzergahı tamamen kapatıyorsa True döner."""
        for engel in getattr(self, "rota_yeni_engeller", ()):
            if isinstance(engel, YolCalismasi):
                return True
            if isinstance(engel, YayaGecidi) and getattr(engel, "yayalar_aktif_mi", False):
                return True
            if isinstance(engel, TrafikIsigi) and getattr(engel, "durum", "") == "kirmizi":
                return True
        return False
           

    def rota_engel_icinde_mi(self):
        """
        Mevcut rota üzerinde engel setinde değişiklik var mı?
        - Rota yoksa -> False (ve snapshot sıfırlanır)
        - Rota varsa -> önceki snapshot ile kıyaslanır,
          sadece YENİ eklenen engel varsa True döner.
        """
        rota = getattr(self, "aktif_patika", [])
        if not rota or len(rota) < 2:
            # Rota yoksa referans seti sıfırla
            self.rota_engel_ids = set()
            return False

        # Şu an rotayla kesişen engeller
        engeller = self.get_engeller()
        engel_map = {id(e): e for e in engeller}
        mevcut = self._rota_ile_kesisen_engeller()

        # Daha önce kaydedilen snapshot
        eski = getattr(self, "rota_engel_ids", set())

        # Rotayla kesişen ve ÖNCE yokken şimdi gelen engeller
        yeni_eklenen = mevcut - eski

        # Snapshot'ı güncelle (bir sonraki frame için)
        self.rota_engel_ids = mevcut
        self.rota_yeni_engeller = {engel_map[eid] for eid in yeni_eklenen if eid in engel_map}

        # Sadece yeni engel geldiyse rota değiştir
        return bool(yeni_eklenen)

    # --- ANA GÜNCELLEME METODU ---
    def guncelle(self):
        """NPCArac guncelle uzerine kucuk ayarlar: sag serit + dinamik rota."""
        if self.hedefe_ulasti:
            self.hiz = 0
            self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
            self.rect = self.image.get_rect(center=(self.x, self.y))
            return
        if not self.algoritma_getir():
            # Algoritma secilene kadar bekle
            self.hiz = 0
            self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
            self.rect = self.image.get_rect(center=(self.x, self.y))
            return
        # NPC'lere yol ver: cok yakinda NPC varsa ilerleme
        for npc in self.get_npcs():
            if npc is None or npc is self:
                continue
            if npc.rect.inflate(12, 12).colliderect(self.rect):
                self.hiz = 0
                return
            
        onceki_x, onceki_y = self.x, self.y
        self.serit_tercihi = "sag"
        
        # Dinamik olarak yasak kenarlari guncelle
        self.yasakli_kenarlar = self._yasakli_kenarlar()
        
        # Rota engel icerisinde mi? Varsa rota yenile
        if self.rota_engel_icinde_mi():
            self._rota_hazirla()

        # Hedefe geldiyse super().guncelle() cagirilip rota bozulmadan durdur
        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        if dugumler and self.hedef_global_id < len(dugumler):
            hx, hy = dugumler[self.hedef_global_id]
            if math.hypot(self.x - hx, self.y - hy) <= self.dugum_tol:
                if getattr(self, "aktif_patika", None):
                    self.son_patika = list(self.aktif_patika)
                self.hedefe_ulasti = True
                self.hiz = 0
                self.hedef_dugum_id = None
                self.aktif_adim = 0
                self.image = pygame.transform.rotate(self.orijinal_gorsel, self.aci)
                self.rect = self.image.get_rect(center=(self.x, self.y))
                return

        # Rota her karede temizlenebilecegi icin son gorulen patikayi sakla
        if getattr(self, "aktif_patika", None):
            self.son_patika = list(self.aktif_patika)

        self._fizik_engel_etkisi()
        
        super().guncelle()
        
        # --- ÇARPIŞMA KONTROLÜ (ANA ARAÇ İÇİN) ---
        # Hareket sonrasinda NPC ile carpistiysak geri al ve dur
        for npc in self.get_npcs():
            if npc is None or npc is self:
                continue
            if npc.rect.colliderect(self.rect):
                self.x, self.y = onceki_x, onceki_y
                self.rect = self.image.get_rect(center=(self.x, self.y))
                self.hiz = 0
                break
        # ---------------------------------------------------------
        
        # **DÜĞÜM TAKİP SİSTEMİ**
        # Aracın geçtiği en yakın düğümü belirleyerek
        # Game.update() içindeki MAALİYET ARTIRMA mekanizmasını tetikler.
        dugumler = getattr(self.h, "ikili_yol_dugumleri", [])
        # En yakın düğümü bul ve kaydet
        if dugumler:
            en_yakin_id = None
            en_yakin_mesafe = float('inf')
            
            # En yakın düğümü bul
            for i, (dx, dy) in enumerate(dugumler):
                mesafe = math.hypot(self.x - dx, self.y - dy)
                if mesafe < en_yakin_mesafe:
                    en_yakin_mesafe = mesafe
                    en_yakin_id = i
            
            # Eğer en yakın düğüm 40 birimden yakınsa ve önceki düğüm değilse kaydet
            if en_yakin_mesafe < 40:
                if not getattr(self, "katedilen_patika", None):
                    self.katedilen_patika = []
                if not self.katedilen_patika or self.katedilen_patika[-1] != en_yakin_id:
                    self.katedilen_patika.append(en_yakin_id)
                self.onceki_dugum_id = en_yakin_id

    def ciz(self):
        self.h.ekran.blit(self.image, self.rect)
        self.sensorleri_ciz()
        
    def _aktif_engel_durumu(self):
        engeller = self.get_engeller()
        
        ax, ay = self.x, self.y
        yol_k = getattr(self.h, "YOL_KALINLIK", 100)
        
        aktif = {
            "yol_calismasi": False,
            "yaya_aktif": False,
            "kirmizi_isik": False,
            "sari_isik": False,
            "kasis": False,
            "kaygan": False,
        }
        
        for engel in engeller:

            # --- Yol çalışması › asla içine girilemez
            if isinstance(engel, YolCalismasi) and engel.icinde_mi(ax, ay):
                aktif["yol_calismasi"] = True

            # --- Yaya geçidi aktifse durmak zorunda
            elif isinstance(engel, YayaGecidi) and engel.carpisti_mi(ax, ay):
                aktif["yaya_aktif"] = True

            # --- Trafik ışığı
            elif isinstance(engel, TrafikIsigi):
                if engel.durum == "kirmizi":
                    if engel.carpisti_mi(ax, ay):
                        aktif["kirmizi_isik"] = True
                elif engel.durum == "sari":
                    if engel.carpisti_mi(ax, ay):
                        aktif["sari_isik"] = True

            # --- Kasis (yavaşlatır)
            elif isinstance(engel, HizKesici) and engel.icinde_mi(ax, ay):
                aktif["kasis"] = True

            # --- Kaygan zemin (hızlandırır)
            elif isinstance(engel, KayganZemin) and engel.icinde_mi(ax, ay):
                aktif["kaygan"] = True

        return aktif

    
    def rota_yenile(self, keep_steps: bool = False):
        """Disaridan algoritma degisiminde aktif rota bilgilerini sifirlar.

        keep_steps=True ise katedilen_patika korunur; panelde adim sayaci
        yeni rota olusturulsa bile devam eder.
        """
        self.aktif_patika = []
        self.son_patika = []
        self.ilk_patika = []
        if not keep_steps:
            self.katedilen_patika = []
        self.hedef_dugum_id = None
        self.aktif_adim = 0
        self.onceki_dugum_id = None
        self.hedefe_ulasti = False
        self.son_maliyet = 0.0
        self.son_adim = 0
        self.dfs_modu_aktif = False
        self.dfs_kilitli_rota = None
