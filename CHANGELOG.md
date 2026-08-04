# Sürüm Notları

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
