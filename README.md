# Aşı Barkod Okuyucu

Telefon kamerasıyla aşı DataMatrix veya QR kodunu okuyup seçilen Windows
bilgisayardaki aktif alana klavye gibi yazan kişisel kullanım sistemidir.

## Yapı

- `asi-barkod-pwa`: iPhone ve Android için tek PWA.
- `pc-receiver`: Windows 8.1/10/11 için x64 ve x86 PC alıcısı.
- `packaging/windows`: Windows kurulum paketi tanımı.
- `scripts`: paket üretimi ve yalnız eski kurulum kalıntılarını temizleme araçları.

Aktarım tamamen Ably üzerindedir. Telefon ve PC aynı ağda olmak zorunda değildir.
Telefon başarılı sonucu ancak PC alıcısı barkodu aktif alana yazdığını onaylarsa gösterir.

## Günlük kullanım

1. Windows PC'de Aşı Barkod PC Alıcısını açık bırakın.
2. PC uygulamasındaki QR kodla veya doğrudan aşağıdaki adresle telefonu açın:

   `https://asi-barkod-pwa.vercel.app/`

3. Telefonda hedef PC'yi seçin ve barkodu okutun.

PC ekranında iki durum satırı görünür:

- **PWA sitesi**: Vercel'deki telefon sitesine erişim kontrolü.
- **Ably bulut bağlantısı**: PC'nin telefonlardan bulunup barkod alabilme durumu.

Yeşil durum erişilebilir/bağlı, kırmızı durum bağlantı hatası demektir.

## Temiz Windows kurulumu

1. GitHub Releases içinden PC mimarisine uygun en güncel paketi indirin:
   `-x64.exe` 64-bit Windows, `-x86.exe` 32-bit Windows içindir.
2. Kuruluma yönetici izni verin; uygulama `C:\Program Files\Asi Barkod` içine kurulur.
3. Kurulum tamamlanınca alıcı yönetici yetkisiyle açılır. Masaüstü/Başlat kısayolu
   da uygulamayı aynı yetki isteğiyle başlatır; sağ tıkla “Yönetici olarak
   çalıştır” gerekmez.

PC'deki **Güncellemeleri denetle** düğmesi yeni paketi indirir; indirme yüzdesi ve MB bilgisi ekranda görünür.

## Geliştirme ve yayın

PWA:

```powershell
Set-Location .\asi-barkod-pwa
npm ci
npm test
npm run build
npx vercel --prod --yes
```

Windows paketi:

```powershell
.\scripts\build-windows-package.ps1 -Architecture both
```

Yeni sürümde `pc-receiver/asi_barkod_receiver.py`, `packaging/windows/AsiBarkod.iss`,
`packaging/windows/version_info.txt`, `CHANGELOG.md` ve GitHub Release notu birlikte güncellenir.
