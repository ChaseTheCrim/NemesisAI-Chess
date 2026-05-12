# Nemesis AI — Uyumlanan Satranç Rakibi

Maç sırasında *seni* öğrenen yapay zeka.

Klasik satranç oynaması için tasarlanmış yapay zeka botları(bkz: stockfish) sadece zor olmak için yapılmış botlardır. Nemesis öyle değildir. **Nemesis sen oyunu oynadıkça aktif olarak *sana* adapte olur**. Senin oyun tarzının bir modelini oluşturur ve sadece senin için özel bir rakip haline gelir. Maç uzadıkça senin düşüncelerinle düşünür, senin fikirlerinle güçlenir ve sana aradığın o eşi benzeri olmayan mücadeleyi sunar.

Ostim Teknik Üniversitesi'nde Derin Öğrenme dersi projesi olarak geliştirildi.

---

## Mantık

Çoğu satranç için geliştirilmiş yapay zeka, herkese karşı aynı hesapları yapar. Her zaman sen daha piyonunu oynatmadan binlerde hamle ilerden senin yapacaklarını bilir. Bu satrancın çarpışan rekabet ve zihin kuvveti gerektiren yapısını baltalar. Maç başladığı an oynanacak bir maç oynamazsın. Kaybedilecek bir maç izlersin. Nemesis'i farklı kılan tarafı; 

- Maçın başında yüzlercı yıldır bilinen *"Satranç Teorisi"* dışında hiçbir anlam mekanizması yoktur. **Maç başlamadan senin yapılabilir ilk 15 hamleni bilmez.**
- Bunun yerine özelleştirilmiş olan bir **Recursive Neural Network yapısı olan LSTM kullanır**. Oyuncunun hamlelerini teker teker öğrenir. **SANA ADAPTE OLUR.**
- Ne kadar agresif? Ne kadar defansif? ***Senin* hamlelerin üzerinden senin oynama şemanı çıkartır.**
- Maç daha çetin bir hale geldikçe öğrendiği şeylerin efektifliği **kendi MMR'ı** ile birlikte artar.
- Oyuncuyu konfor noktasında söküp almak için tasarlanmıştır *"Kalkanlarını çekmiş düşmanların kalkanlarını yıkması, mızraklarıyla saldıran rakiplerin mızraklarını kırması"* için tasarlanmıştır.

Nemesis temelinde bu özellikleriyle sıralanabilir. Peki bu ne mi sağlar? 2000'li yıllardan beri hepimizin artık kabullendiği ruhsuz yapay zeka botlarının aksine sadece iyi satranç oynamaz. Oyuncuyu sürekli olarak yeni taktikler denemeye, kendini sınamaya ve kendini daha iyi bir oyuncu yapmaya, clutch olan hamleleri görmeye zorlar. Satranç hak ettiği yer olan zihinlerin amansız kapışmasına tekrardan bürünür. Nemesis sana adapte olması için tasarlanmış olabilir, ancak ona karşı yeni taktikler bulabilecek kadar iyi düşündün mü? Düşünsen iyi olur. Yoksa onu yenmen beklediğinden daha zor olucak.

---

## Mimari

Bu Proje iki ana kapsam altında üretilmiştir:

**Frontend C++/Qt**
Itch.io üzerinden copyright hakları bedava olan ve inanılmaz güzel gözüken pixel temalı taşlar, arka planda çalışan ağır eğitim süreçlerine balta koymaması ve akıcı ve olması için C++ üzerinden Qt yoluyla ince bir işçilik ile hazırlanmıştır. Quality of life için her bir taş yakın oldukları karoya bir manyetizma mekaniği ile oturtulmuş ve dikkat gerektiren hamlelere yakından bakabilmek için yakınlaştırma ve ekran hareket ettirme özellikleri eklenmiştir. Kolay taş kontrolü için her taş için hitboxlar ayarlanmış ve "X" tuşu ile bunların görülebilmesi için debug ayarı eklenmiştir. Öyle ki, nemesis engine olmadan player vs player bile oynanabilmesi için tasarlanmış bir motordur.

**Backend Python (C bazlı kütüphaneler)**
Mucizenin yaşandığı yer tam olarak burasıdır, json formatında frontend tarafından gönderilmiş bilgiler "Nemesis Engine" içinde işlenir. Yarım saniyeden kısa bir sürede oyuncunun yaptığı hamle yapay zeka mekanizması içinde geri işleme yoluyla sinir ağına sokulur ve oyuncuyu öğrenme işlemi başlar, "Satranç Teorisi" üzerine el ile yazılmış değerlendirme metriklerini kullanarak her hamlesinin değerini hesaplar. Kendine ait profil sistemi sayesinde LTSM tarafından öğrenilen hamleler pattern recognizition yoluyla sınıflandırılır ve oyuncuya karşı direnç kazanır. Bütün bu işlemleri yaparken ise, Python kullanmasının yavaşlığına PyTorch gibi C temelli kütüphaneler yoluyla size hissettirmez bile.

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

## Nemesis'in Öğrenmesi

LSTM her zaman adımında **778 float'lık girdi** alır:

- 768 float — taş pozisyonlarını kodlayan 12 ikili 8x8 düzlem (her renk ve taş tipi için bir düzlem)
- 6 float — rok hakları, sıra hangi tarafta, en passant karesi
- 2 float — kodlanmış hamle (kaynak kare, hedef kare)
- 2 float — bu hamlenin gözlemlenen agresifliği ve kalitesi

Nemesis daha öncesinde bahsettiğimiz gibi, LTSM üzerine kuruludur ve her tur oyun ile alakalı *778 floatlık bilgiyi frontend üzerinden alır*, bu bilgiler şu şekildedir:
- 768 - taş pozisyonları ve tahta
- 6 - rok, sıra, en passent bilgisi
- 2 - oynanan hamle ile başangıç ile bitiş noktası
- 2 - hamle evaluation değerleri

Bu işin sonucunda LSTM'e kaydedilen bilgiler yolunda şimdilik **üç ana tahmin yapılır**, bı tahminler şöyledir:

- Evaluation değerleri üzerinden; sonraki hamle tahmini
- Oyuncunun tansiyonu (Agresif mi? Pasif mi?)
- Oyuncunun bilgi düzeyi (MMR miktarı)

Bu bilgiler eşiliğinde hidden state bir oyun boyunca, her hamle arasında korunur. Oyuncunun yaptığı hamlelerin her birisi geri besleme aşamalarında hesaplanır ve gradyanlar ince bir şekilde hesaplanır.

İleri besleme sonucu oluşan LSTM çıktısı, oyuncu profili için belirlenmiş aralıklarda oynamaya sebep olur, bu değerler; MMR, hamle değerlendirmesi ve oyuncunun oynama stilleri üzerinedir. Bu bilgiler, "evaluator" a gönderilir.

### Evaluator 

Evaluator, diğer adıyla poziyson değerlendiricisi aslen internet üzerinden almayı düşündüğüm, hatta zamanında stockfish ile denediğim bir mekanikti. Ancak stockfish'i böyle bir projede kullanmanın projenin ruhuna aykırı olduğuna inandığım için bu konu üstüne uzun süre düşünerek, kendi değerlendiricimi yazdım. Bu değerlendirici 1970'li senelerden beri herkese açık olarak paylaşılan "Satranç Teorisi" üzerine kurulu.

- **Taş Değeri** — Her taşın kendine ait innate değerleri (piyon=100, at=320, vb.)
- **Taş Konum Değeri** — Her taşın her karedeki yerlerine göre kazandıkları ekstra önem miktarı
- **Hamle miktarı** — Bir taşın her yapabildiği hamle miktarına eşdeğer şekilde bonus önem miktarı
- **Piyon aktifliği** — Piyonların aktif kullanımına teşvik için aktiflik ve çifte duruş puanlaması
- **Tehdit algılama** — Tek hamlelik ileriyi ön görebilen "Static Exchange Evaluation" algoritması

Bu sayede, belki bir stockfish olmasada, öğrenme profilinin gelişimi yoluyla çekici bir deneyim sunmayı hedefliyorum.

### Static Exchange Evaluation

Her hamle, Nemesis'in oyun sırasındaki MMR ve oyuncu MMR miktarına bağlı dört farklı temelden yararlanır.

1. **Temel Değer** — Bu hamle özünde ne kadar iyi?
2. **Oyuncu Stil Uyumu** — Oyuncunun oluşturduğu patternlarla nasıl bir etkileşim üretiyor?
3. **Tahmin Tuzağı** — Oyuncunun yapacağı tahimini hareketleri cezalandırıyor mu?
4. **MMR Orantılı Noise** — Nemesis oyuncu ile alakalı daha fazla pattern çıkarttıkça rastgelelik miktarı azalır.

MMR zamanla artar ve Nemesis'in ilk başlarda gerçekten zayıf bile oynadığı zamanlar olur. Ancak zaman ilerledikçe daha keskin hal alan MMR oyuncuyu giderek köşeye sıkıştırır.

---

## Source Code Üzerinden Kurulum

### Gereksinimler

- C++17 derleyicisi olan Qt 6 (MinGW veya MSVC)
- Python 3.9 veya daha yenisi
- CMake 3.16 veya daha yenisi
- Windows 11 İşletim Sistemi

### Compiling

GitHub repository'si klonlama:

```bash
git clone https://github.com/ChaseTheCrim/ChessBotUI.git
cd ChessBotUI
```

Python ortamını kur:

```bash
cd engine
python -m venv venv
venv\Scripts\activate          # Windows
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

## Peki bunlar çok mu uzun geldi?

Eğer bütün bunlar çok yorucu geldiyse, her zaman Release versiyonu indirip tek tık ile (**ChessBotUI.exe**) açıp oynayabilirsin!

---

## Kontroller

Oyuncu, *Nemesis'e karşı bir şansı olması için* ve *centilmenlik için* **Beyaz** ile başlar. Nemesis ise her zaman **Siyah** ile başlar.

|        İşlev         |              Kontrol             |
|----------------------|----------------------------------|
| Taş hareket ettir    | Sol tıkla sürükle                |
| Görünümü kaydır      | Sağ tıkla sürükle                |
| Yakınlaştır/Uzaklaştır | Fare tekerleği                 |
| Görünümü sıfırla     | Orta tık                         |
| Hitbox göster/gizle  | `X` tuşu (hata ayıklama modu)    |

Oyun klasik satranç kurallarıyla oynanır; **şah**, **mat**, **pat**, ilk 50 hamle kuralları geçerlidir.

---

## Update Planları:

Şu anda zaman kısıtlamaları sebebiyle, NemesisAI çalışır durumda bir uygulama olsada, yinede developer olarak eklemek istediğim oldukça şey var, bunlar kısaca;

- **Var olan patternlar için elle yazılmış bir kütüphane** — Nemesis seninle alakalı bulduğu bilgileri işliyor, ancak bu patternlara karşı daha dayanıklı olması için bilindik oyun şemalarına dair bir kütüphane (çobana matı, sicilan savunması etc.)
- **Hamler arası zaman ölçümü** — Oyuncunun her hamlesi arasında ne kadar süre olduğunun hesaplanması ile oyuncunun zihinsel ruh halini anlayıp tedirginliğini avantaja çevirebilmek.
- **Kalıcı hafıza** — Şu anda Nemesis sadece oyun içinde öğrenir ve oyun bittikten sonra yapay sinir ağı sıfırlanır. Eğitimin oyunlar arası devam'ı en büyük hedeflerimden birisi.
- **Ses efekleri ve Anmiasyonlar** — Daha temiz, derin ve eğlenceli bir deneyim için oyuna animasyonlar, efekler, sesler eklemek ve zenginleştirmek istiyorum.
- **Başka Platformlara Yönelik Çalışmalar** — Şu anda sadece Windows 11 sistemlerde test edilmiştir ve sadece Windows sistemlerde denemesi tavsiye edilir. Ancak başka sistemlerdede optimize ve kullanılablir olması hedeflenmektedir.

---

## Lisans

Bu proje MIT Lisansı altında yayınlanmıştır. Klasik pozisyon değerlendiricisi kamuya açık satranç ilkelerinden (materyal değerleri, taş-kare tabloları, hareketlilik, tehdit algılama) inşa edildi ve üçüncü taraf motor kodu içermez.
