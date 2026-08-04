# Asi Barkod: Taşınabilir Yönetim Erişimi

Bu klasör, kaynak kodla birlikte yönetim için gerekli proje kimliklerini ve
tokenları yerel \`HESAPLAR.env\` dosyasında tutar. Dosya Git tarafından dışlanır;
GitHub'a eklenmez.

Yeni veya formatlanmış bir Windows bilgisayarda:

1. Bu proje klasörünü indir veya kopyala.
2. Git, Node.js ve GitHub CLI'yi kur.
3. PowerShell'i proje kökünde aç ve çalıştır:

   \`\`\`powershell
   powershell -ExecutionPolicy Bypass -File .\\scripts\\Hesaplardan-Yonetim-Oturumu-Ac.ps1
   \`\`\`

Bu işlem GitHub yazma erişimini kurar ve Vercel komutları için yönetim tokenını
o PowerShell oturumunda hazırlar. Ardından kaynak kod, canlı PWA ortam
değişkenleri, Vercel projesi ve GitHub reposu yönetilebilir.

## Kritik alanlar

- \`GITHUB_TOKEN\`: repo üzerinde yazma/silme/düzenleme için.
- \`VERCEL_TOKEN\` ve \`VERCEL_REFRESH_TOKEN\`: proje, ortam değişkeni ve
  dağıtım yönetimi için. Vercel kısa ömürlü tokenı gerektiğinde bu yenileme
  anahtarıyla değiştirir.
- \`ABLY_API_KEY\`: PWA'nın telefon-PC iletişimi için Vercel'de kullandığı anahtar.
- \`PWA_URL\`, \`VERCEL_PROJECT_ID\`, \`ABLY_ACCOUNT_CODE\`: ilgili panellere ve
  doğru projeye dönmek için sabit kimlikler.

## Bilerek saklanmayan şey

Web sitelerindeki hesap parolaları geri okunamaz; buna ihtiyaç da yoktur.
Yukarıdaki proje tokenları bu uygulamayı yönetmek için parola yerine kullanılır.
Bir token iptal edilirse, yeni token üretilip \`HESAPLAR.env\` içindeki aynı alan
güncellenmelidir.
