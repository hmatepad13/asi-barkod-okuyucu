# PWA kamera geri dönüş notu

24 Temmuz 2026 tarihinde daha sabit görüntü ve daha hızlı tepki için kamera
yakınlaştırması 2× yerine 1×, tarama sayısı da üç yerine bir yapıldı.

Gerçek iPhone kullanımında okuma belirgin biçimde bozulursa önceki çalışan ayar:

- Kamera açılış yakınlaştırması: `2×`
- Tarama sayısı: `3`
- Denemeler arasındaki süre: `120 ms`
- İlk deneme: normal renkli görüntü
- İkinci ve üçüncü deneme: `grayscale(1) contrast(1.35)`
- Ekrandaki ilerleme metni: `1/3`, `2/3`, `3/3`

Merkezdeki kare dışındaki barkodu reddetme ve kare içinde merkeze en yakın
DataMatrix'i seçme davranışı geri dönüşte de korunmalıdır.

## 1080p değişikliği

24 Temmuz 2026 tarihinde kamera isteği `3840×2160` yerine `1920×1080` yapıldı.
Tarama karesinin işleme boyutu `1600–2400` aralığından `1200–1600` aralığına
indirildi. Görünen hedef genişliği normal ekranda `%58 / 240 px`, küçük ekranda
`%56 / 210 px` iken sırasıyla `%50 / 210 px` ve `%48 / 180 px` yapıldı.

1080p ile 2×2 cm DataMatrix okuması belirgin şekilde bozulursa ilk geri dönüş
adımı yalnız kamera isteğini tekrar `3840×2160` yapmak olmalıdır; 2× zoom ve üç
tarama döngüsü ayrıca gerekmedikçe geri getirilmemelidir.
