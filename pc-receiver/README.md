# PC Receiver

Windows tarafinda calisir. Telefon PWA'dan Ably ile gelen barkod verisini aktif uygulama alanina klavye gibi yazar.

## Calistirma

Normal kullanimda `Asi-Barkod-Windows-Kurulum-v0.2.6.exe` dosyasini calistirmak yeterlidir. Kurulum paketinin icinde Python ve gereken kutuphaneler bulunur; hedef PC'ye ayri bir uygulama kurulmaz.

Paket 32 bittir ve hem 32 bit hem 64 bit Windows 8/10/11 icin hazirlanmistir. Kurulum aliciyi Windows acilisina ekler; yerel ag portu veya ek guvenlik duvari kurali acmaz.

Kaynak koddan gelistirme amacli elle calistirma:

```bat
python asi_barkod_receiver.py
```

Program acilinca Ably baglantisini kurar. Telefonda Aşı Barkod PWA'yi acip `PC Bul` derseniz cevrimici PC'ler listelenir; hedefi siz secersiniz.

## PC Panel

Ana pencerede Ably baglanti durumu, telefon PWA QR kodu, son gelen telefon,
son okutulan barkod, aktif pencereye yazma ac/kapat, GS ayari ve test barkodu
yazma alani bulunur. IP adresi veya yerel eslestirme sayfasi gerekmez.

Pencereyi kucultmek veya carpiya basmak programi kapatmaz; alici saatin yanindaki sistem tepsisinde calismaya devam eder. Windows ile otomatik basladiginda pencereyi acmadan dogrudan tepside calisir. Kisayola tekrar basmak mevcut pencereyi acar; ikinci bir alici baslatmaz. Pencereyi geri acmak veya programi tamamen kapatmak icin tepsi ikonunun menusunu de kullanabilirsiniz.

Bu Python kurulumunda `tkinter` yoksa pencere yerine konsol modu acilir. Konsol
modu da Ably'den gelen barkodu aktif alana yazabilir.

## Ayarlar

- `Son tus`: telefonun gonderdigi degerden bagimsiz olarak PC'de secilen `ENTER`, `TAB` veya `NONE` uygulanir.
- `GS ayirici`: GS1 `\x1d` karakterinin PC uygulamasina nasil yazilacagi.
  - `unicode`: karakteri oldugu gibi yollar.
  - `ctrl_right_bracket`: barkod cihazlarinda kullanilan Ctrl+] benzeri yol.
  - `remove`: ayiriciyi siler.
  - `pipe`: `|` yazar.
  - `text`: `<GS>` yazar.
- `Aktif alana yaz`: kapatilirsa sadece log tutar.

Bu ayarlar program kapatilip acildiginda korunur ve `%APPDATA%\AsiBarkod\settings.json` dosyasinda saklanir.

## Log

Okutmalar `%APPDATA%\AsiBarkod\logs\scans-YYYY-MM-DD.csv` dosyasina kaydedilir. Log yazilamazsa hata panelde gosterilir ancak barkodun aktif alana yazilmasi engellenmez.
