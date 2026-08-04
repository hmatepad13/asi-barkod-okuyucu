# Aşı Barkod PWA

Android ve iPhone'un ortak telefon uygulamasıdır. Kamera ile GS1 DataMatrix ve
QR kod okur; seçilen Windows PC'ye Ably üzerinden teslim onayı alarak gönderir.

## Kullanım

1. Telefonda `https://asi-barkod-pwa.vercel.app/` adresini açın veya ana ekrana ekleyin.
2. Açılıştaki PC listesinden hedef bilgisayarı seçin.
3. Barkodu kare hedefin ortasına getirin ve **OKU**'ya basın.
4. Başarı yalnız PC alıcısı veriyi yazdığını onayladığında gösterilir.

Telefon ve PC aynı Wi-Fi'da, hotspotta veya farklı ağlarda olabilir; internet
ve Ably bağlantısı yeterlidir. Yerel IP, port ve sertifika kurulumu yoktur.

## Geliştirme

```powershell
npm ci
npm test
npm run build
npx vercel --prod --yes
```

PWA sürümünü yalnız `app/release.ts` içinden yükseltin. Bu değer, uygulamanın
kendini yenilemesi için kullanılan service-worker adresine de eklenir.
