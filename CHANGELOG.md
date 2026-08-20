# Sürüm Notları

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
