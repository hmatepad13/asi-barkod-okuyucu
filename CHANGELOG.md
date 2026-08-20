# Sürüm Notları

## PWA 2026.08.20.6 - 20 Ağustos 2026

- ZXing-WASM 3.1.3, Next.js 16.3.1, React 19.2.8 ve Ably 2.27.0 sürümlerine
  yükseltildi; PWA'nın kendi barındırdığı ZXing WASM dosyası da aynı sürümle
  eşlendi.
- Normal, yarı ölçek, blur ve mavi kanal okumalarında tekrarlanan ZXing
  seçenekleri tek bir okuyucu modülünde toplandı.
- Gerçek ZXing motorunu çalıştıran GS1 DataMatrix ve dikey baskı boşluğu
  regresyon testleri eklendi. Bozuk örnekte normal okumanın başarısız, yarı
  ölçek kurtarmasının başarılı olduğu otomatik doğrulanıyor.
- Artık kullanılmayan eski yerel ağ açıklaması kaldırıldı.
- Kaynak koddaki eski `android-pwa` istemci adı kaldırıldı; kalıcı ad yalnız
  `Aşı Barkod PWA` olarak bırakıldı.
- Üretim ve geliştirme bağımlılıklarında bilinen `npm audit` kayıtları sıfıra
  indirildi.

## PWA 2026.08.20.5 - 20 Ağustos 2026

- Yarı ölçekli kurtarma da başarısız olursa çalışan, kamera çözünürlüğüne göre
  orantılanmış `2,2 / 310` blur kurtarması eklendi.
- Gerçek bozuk baskı fotoğrafında küçültmeden yapılan testte yalnız yaklaşık
  2,0–2,5 px aralığı doğru çözdüğü için blur normal ve yarı ölçekli okumadan
  sonra çalışır.

## PWA 2026.08.20.4 - 20 Ağustos 2026

- Fabrika baskısında ince dikey beyaz boşluklar bulunan DataMatrix kodları için
  normal okuma başarısız olduğunda yarı ölçekli yeniden örnekleme eklendi.
- Kurtarma yalnız ilk deneme başarısızsa çalışır; normal barkodların hızı ve
  merkezdeki hedef dışındaki kodları reddetme davranışı korunur.

## PWA 2026.08.20.3 - 20 Ağustos 2026

- Fotoğraf seçme düğmesi, anlaşılır galeri/QR simgeli dikdörtgen `GALERİDEN QR`
  düğmesi olarak yenilendi.

## PWA 2026.08.20.2 - 20 Ağustos 2026

- Uygulama başlığına kısa sürüm etiketi eklendi (`v20.2`).

## PWA 2026.08.20.1 - 20 Ağustos 2026

- WhatsApp'tan gelen QR ekran görüntüleri için `FOTOĞRAFTAN QR` seçeneği eklendi.
- Seçilen PNG/JPG/WebP ekran görüntüsündeki QR kod mevcut seçili PC'ye, normal
  kamera okumasıyla aynı Ably teslim-onay sürecinden geçirilerek gönderilir.
- Kamera ile DataMatrix/QR okuma, PC bulma ve mevcut gönderim akışı değiştirilmedi.

## v0.5.0 - 5 Ağustos 2026

- PC alıcısı yalnız Ably ile çalışacak şekilde sadeleştirildi; eski yerel HTTP,
  UDP keşif, port, konsol ve iPhone köprü kodları çıkarıldı.
- PC ekranına PWA sitesi erişim göstergesi eklendi: erişilebilirse yeşil,
  erişilemiyorsa kırmızı.
- PWA sitesi ve Ably bağlantı durumları, telefon sitesi adresinin altında art arda gösterilir.
- Tepsiye küçültülmüş uygulama masaüstü/Başlat kısayoluna basılınca tekrar açılır.
- PWA yalnız Ably mimarisini kullanır; terminal bağlantı hatasından sonra Ably
  istemcisi yeniden oluşturulur.
- PWA güncelleme sürümü service-worker kaydına bağlandı.
- Kurulum yalnız 64-bit Windows'a gider ve `C:\Program Files\Asi Barkod` yolunu kullanır.
