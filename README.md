# Nemesis AI — Uyumlanan Satranç Rakibi

Maç sırasında *seni* öğrenen bir satranç oyunu.

Sıradan satranç motorlarının aksine — onlar sadece nesnel olarak güçlü olmaya çalışırlar — **Nemesis maça zayıf başlar ve oynadıkça senin oyun tarzının bir modelini oluşturur**, oyun ilerledikçe *sana karşı* daha da zorlu bir rakibe dönüşür. Ne kadar uzun oynarsan, nasıl düşündüğünü o kadar iyi anlar — ve sana karşı o kadar özel bir mücadele verir.

Ostim Teknik Üniversitesi'nde Derin Öğrenme dersi projesi olarak geliştirildi.

---

## Konsept

Çoğu satranç yapay zekâsı nesnel olarak güçlü olmaya odaklanır — herkese karşı aynı oynar, binlerce hamle ileriye kadar hesap yapar. Nemesis farklı çalışır. Maça zayıf başlar, ama her hamlende:

- **Bir LSTM sinir ağı, hamle geçmişin üzerinden canlı eğitim alır** ve örüntülerini öğrenir
- **Oyuncu profili** agresifliğini, hamle kalitesini ve anlık momentumunu takip eder
- Yapay zekânın güç tahmini (MMR) seni daha iyi tanıdıkça yükselir
- Hamle seçimi **sana özgü eğilimleri çürütmek için** uyarlanır — pervasız bir saldırgansan tuzaklara çekilirsin, pasif oyuncuysan aktiviteye zorlanırsın

Sonuç bir akıl oyununa dönüşür. Sadece daha iyi satranç oynayarak değil, **maç ortasında oyun tarzını değiştirerek** karşı koyabilirsin. Nemesis taktiğini öğrendi mi? Başka bir taktiğe geç ve onu yeniden öğrenmeye zorla. Şu an kolayca kazanıyor musun? Sessizce aşırı güvenini profilliyor — tetikte ol.

---

## Mimari

Proje iki yarımdan oluşur ve aralarında JSON-pipe protokolüyle iletişim kurarlar.

**Önyüz — Qt / C++**
Tüm görselleri ve girdileri yönetir. Mıknatıs etkisiyle kare üzerine oturma özelliğine sahip sürükle-bırak taşları, akıcı kaydırma-yakınlaştırma, sağ tık ile kaydırma ve hata ayıklama için X-Ray modu (`X` tuşu) içerir.

**Arka uç — Python (PyTorch ve python-chess)**
Yapay zekânın tüm beynini görünmez şekilde arka planda çalıştırır. Hamleleri doğrular, oyuncudan öğrenir ve cevap seçer. Qt önyüzü Nemesis'in nasıl düşündüğünü bilmez — sadece hamle gönderir ve cevap alır.

```
ChessBotUI/
├── src/                  # Qt / C++ önyüzü
│   ├── main.cpp
│   ├── ChessBoard.{h,cpp}
│   └── ChessPiece.{h,cpp}
├── engine/               # Python arka ucu
│   ├── main.py           # giriş noktası, QProcess hattını yönetir
│   ├── requirements.txt
│   └── nemesis/
│       ├── encoder.py    # tahta durumu kodlaması
│       ├── lstm.py       # LSTM model mimarisi
│       ├── profile.py    # oyuncu profili ve unutma eğrisi
│       ├── trainer.py    # çevrimiçi eğitim döngüsü
│       ├── evaluator.py  # klasik pozisyon değerlendirici
│       └── selector.py   # uyarlanan hamle seçimi
├── assets/
└── CMakeLists.txt
```

---

## Derin Öğrenme Bileşenleri

LSTM her zaman adımında **778 float'lık girdi** alır:

- 768 float — taş pozisyonlarını kodlayan 12 ikili 8x8 düzlem (her renk ve taş tipi için bir düzlem)
- 6 float — rok hakları, sıra hangi tarafta, en passant karesi
- 2 float — kodlanmış hamle (kaynak kare, hedef kare)
- 2 float — bu hamlenin gözlemlenen agresifliği ve kalitesi

Üç ayrı çıkış başlığından **paralel olarak üç tahmin** üretir:

- Oyuncunun muhtemel sonraki hamlesi (kaynak kare, hedef kare)
- Agresiflik profili (pasif ↔ saldırgan)
- Kalite profili (hata yapan ↔ doğru oynayan)

Gizli durum (hidden state) bir oyun boyunca **hamleler arasında korunur** — modelin senin hakkındaki anlayışı maç boyunca birikir. Her oyuncu hamlesinden sonra ağ, gradyan kırpma ile zaman içinde kesilmiş geri yayılım (truncated BPTT) yapar.

Selector bu LSTM çıktısını **canlı oyuncu profili** (üstel unutma ile maç ortasındaki stil değişiklikleri yakalanır), **MMR güç tahmini** (veri biriktikçe yükselir) ve **klasik pozisyon değerlendiricisi** ile birleştirerek aday hamleleri puanlar.

### Klasik Değerlendirici

Pozisyon değerlendiricisi tamamen 1970'lerden beri kamuya açık satranç ilkelerinden inşa edildi:

- **Materyal sayımı** — taşların göreli değerleri (piyon=100, at=320, vb.)
- **Taş-kare tabloları** — her taşın her karedeki konumsal bonusu
- **Hareketlilik** — daha çok yasal hamleye sahip taraf için bonus
- **Piyon yapısı** — çift ve izole piyonlar için cezalar
- **Tehdit algılama** — havada kalan taşlar gibi tek hamlelik taktikleri yakalayan basitleştirilmiş Static Exchange Evaluation

Stockfish kadar güçlü değil, ama LSTM'in çevrimiçi eğitimi için tutarlı bir "bu hamle iyi mi kötü mü" sinyali vermeye fazlasıyla yetiyor.

### Uyarlanma Nasıl Çalışır

Her hamle puanlaması, mevcut MMR'a göre ağırlıklandırılan dört bileşenden oluşur:

1. **Temel değerlendirme** — bu hamle nesnel olarak ne kadar iyi?
2. **Stil karşı koyma** — oyuncunun profilini çürütüyor mu?
   - Pervasız saldırgan → sağlam, tuzaklı hamleler
   - Pasif oyuncu → aktivite zorlayıcı hamleler
   - Kendine güvenli momentum → komplikasyon getirici hamleler
3. **Tahmin tuzağı** — oyuncunun gitmesi muhtemel kareyi cezalandırıyor mu?
4. **MMR ölçekli gürültü** — yapay zeka oyuncunun modelini netleştirdikçe rastgelelik azalır

MMR tabanında (~1000), aday havuzu geniş ve gürültü yüksektir — Nemesis gerçekten yenilebilir hisseder. MMR tavanında (~1500), havuz daralır ve LSTM profili keskin, hedefli oyunu yönlendirir.

---

## Kurulum

### Gereksinimler

- C++17 derleyicisi olan Qt 6 (MinGW veya MSVC)
- Python 3.9 veya daha yenisi
- CMake 3.16 veya daha yenisi

### Derleme

Repoyu klonla:

```bash
git clone https://github.com/ChaseTheCrim/ChessBotUI.git
cd ChessBotUI
```

Python ortamını kur:

```bash
cd engine
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
```

Qt önyüzünü derle:

```bash
cd ..
mkdir build
cd build
cmake ..
ninja
```

Çalıştır:

```bash
.\ChessBotUI.exe
```

---

## Hazır Sürüm

Kaynaktan derlemek istemiyor musun? En son sürüm zip dosyasını [Releases sayfasından](../../releases) indirebilirsin. Sıkıştırılmış klasörü aç ve `ChessBotUI.exe`'yi çalıştır — Python veya derleme gerekmez.

---

## Nasıl Oynanır

Sen **beyaz** oynarsın, Nemesis **siyah** oynar. Tahta köşede yer alır — özgürce kaydırabilir ve yakınlaştırabilirsin.

| İşlem                | Kontrol                          |
|----------------------|----------------------------------|
| Taş hareket ettir    | Sol tıkla sürükle                |
| Görünümü kaydır      | Sağ tıkla sürükle                |
| Yakınlaştır/Uzaklaştır | Fare tekerleği                  |
| Görünümü sıfırla     | Orta tık                         |
| Hitbox göster/gizle  | `X` tuşu (hata ayıklama modu)    |

Oyun **şah mat**, **pat**, **üçlü tekrar**, **50 hamle kuralı** veya **yetersiz materyal** durumunda biter. Sonuç tahta üzerinde gösterilir.

---

## Gelecek Çalışmalar

Mevcut uygulama temel uyarlanma mekaniğini yakalıyor. Tasarlanmış ama henüz uygulanmamış birkaç genişletme:

- **Tuzak örüntü kütüphanesi** — hangi oyuncu profilini sömüreceğiyle etiketlenmiş taktik kurulumlar (çoban matı, son sıra zayıflığı, aşırı yüklü taş tuzakları)
- **Hamle zamanlaması** — oyuncunun her hamleyi ne kadar düşündüğünü (anlık hamleler vs tereddüt) LSTM girdisine dahil etmek
- **Oyunlar arası hafıza** — şu anda Nemesis oyunlar arasında seni unutuyor. Diske kaydedilmiş kalıcı profil, düzenli rakipleri hatırlamasını sağlar
- **Terfi seçimi** — oyuncu şu anda piyon terfisinde sadece otomatik vezir seçebiliyor; alt terfi için bir arayüz diyalogu gerekir

---

## Lisans

Bu proje MIT Lisansı altında yayınlanmıştır. Klasik pozisyon değerlendiricisi kamuya açık satranç ilkelerinden (materyal değerleri, taş-kare tabloları, hareketlilik, tehdit algılama) inşa edildi ve üçüncü taraf motor kodu içermez.
