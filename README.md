# Yapay Zekâ Tabanlı Otonom Araç Simülasyonu

Bu proje, Python ve Pygame kullanılarak geliştirilmiş yapay zekâ tabanlı bir otonom araç ve rota bulma simülasyonudur.

Projede araçların harita üzerinde belirlenen hedef noktaya ulaşması için farklı arama algoritmaları kullanılmaktadır. Simülasyon içerisinde trafik sistemi, yol maliyetleri, engeller ve dinamik çevresel faktörler dikkate alınarak araç hareketleri gerçekleştirilmektedir.

---

# Proje Amacı

Bu projenin amacı:

- Yapay zekâ arama algoritmalarını görsel bir simülasyon ortamında uygulamak
- Otonom araç mantığını temel seviyede modellemek
- Farklı rota bulma algoritmalarını karşılaştırmak
- Trafik ve çevresel faktörlerin rota üzerindeki etkilerini incelemek
- Yapay zekâ derslerinde kullanılan algoritmaları uygulamalı olarak göstermek

olarak belirlenmiştir.

---

#Kullanılan Yapay Zekâ Algoritmaları

Projede birden fazla rota bulma algoritması kullanılmaktadır.

| Algoritma | Açıklama |
|---|---|
| BFS | En kısa adım sayısını bulmaya çalışır |
| DFS | Derinlik öncelikli arama yaklaşımı kullanır |
| UCS | Yol maliyetlerini dikkate alır |
| Greedy Best First Search | Hedefe en yakın düğümü önceliklendirir |
| A* | Sezgisel bilgi ve maliyeti birlikte kullanır |
| IDA* | Bellek optimizasyonlu sezgisel arama yaklaşımıdır |

---

#Simülasyon Özellikleri

✅ Harita üzerinde araç hareketi  
✅ Gerçek zamanlı rota oluşturma  
✅ Dinamik engel sistemi  
✅ Yol maliyet hesaplamaları  
✅ NPC araçlar  
✅ Trafik ışıkları  
✅ Yaya geçitleri  
✅ Hız kesiciler  
✅ Kaygan zemin sistemi  
✅ Sezgisel rota analizi  
✅ Debug modu  
✅ Manuel düğüm sistemi  
✅ Algoritma karşılaştırması  

---

#Engel ve Trafik Sistemi

Projede araç hareketlerini etkileyen farklı çevresel faktörler bulunmaktadır.

| Sistem | Etkisi |
|---|---|
| Trafik Işığı | Aracın belirli süre beklemesine neden olur |
| Yol Çalışması | Yolun kapanmasına veya maliyetin artmasına neden olur |
| Hız Kesici | Aracın hızını düşürür |
| Kaygan Zemin | Hareket maliyetini etkiler |
| Yaya Geçidi | Araç hareketini yavaşlatabilir |

Bu sistemler sayesinde algoritmaların farklı koşullar altında nasıl davrandığı gözlemlenebilmektedir.

---

#Kullanılan Teknolojiler

| Teknoloji | Kullanım Amacı |
|---|---|
| Python | Ana programlama dili |
| Pygame | Simülasyon ve görselleştirme |
| JSON | Düğüm verilerini saklama |
| OOP | Sistem modelleme |
| Heuristic Table | Sezgisel maliyet hesaplama |

---

#Proje Yapısı

```text
OtonomAracSimulasyonuYZ
│
├── main.py
├── araba.py
├── npc_araba.py
├── harita.py
├── engel.py
│
├── dfs.py
├── greedy.py
├── sezgisel_olmayan.py
├── optimal_sezgisel.py
│
├── manuel_dugumler.json
├── heuristik_136.txt
│
├── mainaraba.png
├── oyunpark.png
├── yaya2.png
│
└── README.md
```

---

# 📌 Dosya Açıklamaları

| Dosya | Görevi |
|---|---|
| `main.py` | Simülasyonun ana çalışma dosyası |
| `harita.py` | Harita ve yol sistemini oluşturur |
| `araba.py` | Ana aracın davranışlarını yönetir |
| `npc_araba.py` | NPC araç hareketlerini yönetir |
| `engel.py` | Engel sistemlerini içerir |
| `dfs.py` | DFS algoritmasını içerir |
| `greedy.py` | Greedy Best First Search algoritmasını içerir |
| `sezgisel_olmayan.py` | BFS ve UCS algoritmalarını içerir |
| `optimal_sezgisel.py` | A* ve IDA* algoritmalarını içerir |
| `manuel_dugumler.json` | Manuel düğüm verileri |
| `heuristik_136.txt` | Sezgisel maliyet değerleri |

---

# 🎮 Simülasyon Mantığı

Araçlar harita üzerinde belirlenen başlangıç noktasından hedef noktaya ulaşmaya çalışmaktadır.

Seçilen algoritma:

- yol maliyetlerini
- engelleri
- trafik durumunu
- hedef uzaklığını

dikkate alarak rota oluşturmaktadır.

Farklı algoritmaların:

- hız
- maliyet
- rota uzunluğu
- engellerden kaçınma davranışı

gibi özellikleri karşılaştırılabilmektedir.

---

#Yapay Zekâ ve Algoritma Analizi

Bu proje yalnızca görsel bir simülasyon değil, aynı zamanda algoritmaların performanslarının analiz edilebildiği bir çalışma ortamı sunmaktadır.

Projede:

- sezgisel algoritmaların avantajları
- maliyet tabanlı rota hesaplama
- arama derinliği farkları
- optimal rota davranışları

incelenebilmektedir.

---


#Kullanım

Uygulama çalıştırıldığında simülasyon ekranı açılır.

Kullanıcı:

- algoritma seçimi yapabilir
- aracın rota davranışını gözlemleyebilir
- engellerin etkisini inceleyebilir
- farklı algoritmaları karşılaştırabilir
- debug modunu kullanabilir

---

#Debug Sistemi

Projede düğüm yapısını ve rota bağlantılarını incelemek için debug sistemi bulunmaktadır.

Debug modu sayesinde:

- düğüm yapıları
- yol bağlantıları
- rota hesaplamaları

görsel olarak analiz edilebilmektedir.

---

# ⭐ Not

Bu proje eğitim amacıyla geliştirilmiş yapay zekâ ve rota bulma simülasyonu projesidir.
