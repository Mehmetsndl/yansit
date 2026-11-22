<div align="center">

# ◩ Yansıt

**Android telefonunun ekranını ve sesini bilgisayara yansıt.**
Arkadaşına ekran göstermek, PC'den telefonu kullanmak ya da OBS ile oyun yayını açmak için.

[![Son sürüm](https://img.shields.io/github/v/release/Mehmetsndl/yansit?label=s%C3%BCr%C3%BCm&color=7C6CFF)](https://github.com/Mehmetsndl/yansit/releases/latest)
[![İndirme](https://img.shields.io/github/downloads/Mehmetsndl/yansit/total?label=indirme&color=22C55E)](https://github.com/Mehmetsndl/yansit/releases)
[![Lisans](https://img.shields.io/github/license/Mehmetsndl/yansit?label=lisans)](LICENSE)

### [⬇ Yansit.exe'yi indir](https://github.com/Mehmetsndl/yansit/releases/latest)

<img src="docs/baglanti-koyu.png" width="760" alt="Yansıt koyu tema">

</div>

## Özellikler

- **Kurulumsuz:** `Yansit.exe`'yi indir, çalıştır. Python gerekmez.
- **Kablosuz bağlantı:** Ağdaki telefonlar kendiliğinden listelenir, çift tıklayıp bağlanırsın.
- **QR ile eşleştirme:** Telefonla QR kodu okut, eşleşme ve bağlantı kendiliğinden tamamlanır.
- **USB desteği:** Kabloyla bağlanabilir, eski telefonlarda tek tıkla kablosuza geçebilirsin.
- **Ses aktarımı:** Telefonun sesi PC'den çıkar. Android sürümüne göre en uygun yöntem seçilir; bir yöntem çalışmazsa sıradakine geçilir.
- **PC'den kontrol:** Fare ve klavyeyle telefonu kullanabilir, panoyu paylaşabilir, dosyayı pencereye sürükleyip telefona atabilirsin.
- **OBS yayını için hazır ayarlar:** Kablolu, kablosuz ve zayıf Wi-Fi seçenekleri var. Pencere adı sabit kaldığı için OBS kaynağı her seferinde tekrar seçilmeden bulunur.
- **Otomatik yeniden bağlanma:** Wi-Fi kısa süre koparsa yayın kendiliğinden geri gelir.
- **Modern arayüz:** Koyu ve açık tema, animasyonlar, mekanik ses efektleri (istersen kapatabilirsin).
- **Güncelleme bildirimi:** Yeni sürüm çıkınca uygulama haber verir.

<table><tr>
<td><img src="docs/baglanti-acik.png" alt="Açık tema"></td>
<td><img src="docs/ayarlar-koyu.png" alt="Ayarlar"></td>
</tr></table>

## Kurulum

1. [Son sürümden](https://github.com/Mehmetsndl/yansit/releases/latest) `Yansit.exe`'yi indir ve boş bir klasöre koy.
2. Çalıştır. İlk açılışta sol alttaki **scrcpy indir** butonuna bas. Bu bir kere yapılır, yaklaşık 10 MB iner.
3. Windows "bilinmeyen yayıncı" uyarısı verirse **Ek bilgi → Yine de çalıştır** de.

<details>
<summary>Kaynak koddan çalıştırma</summary>

```bash
git clone https://github.com/Mehmetsndl/yansit
cd yansit
pip install -r requirements.txt
python yansit.py
```
Windows'ta `Baslat.bat` aynı işi yapar. Kendi exe'ni oluşturmak için `ExeYap.bat` dosyasını kullan.
</details>

## Telefonu hazırlama (bir kere)

1. **Ayarlar → Telefon hakkında → Yapım numarası** satırına 7 kez dokun. Geliştirici seçenekleri açılır.
2. **Geliştirici seçenekleri** içinde **USB hata ayıklama** ve/veya **Kablosuz hata ayıklama** seçeneğini aç.
3. Xiaomi/POCO telefonlarda **USB hata ayıklama (Güvenlik ayarları)** seçeneği de açık olmalı, yoksa PC'den kontrol çalışmaz.

## Kullanım

**Kablosuz (Android 11+):** Telefon ve PC aynı Wi-Fi ağında olmalı.
1. İlk sefer: **QR ile yeni telefon eşleştir** → telefonda *Kablosuz hata ayıklama → Cihazı QR koduyla eşle* → kodu okut.
2. Sonraki seferler: telefonda Kablosuz hata ayıklamayı aç, listede telefonuna çift tıkla, sonra **Başlat**'a bas.

**Kablolu:** Kabloyu tak, telefonda **izin ver**'e bas, alttan cihazı seç, **Başlat**'a bas.

### PC'den kontrol kısayolları
| Kısayol | İşlev | Kısayol | İşlev |
|---|---|---|---|
| Sağ tık | Geri | Orta tık | Ana ekran |
| Alt+S | Son uygulamalar | Alt+F | Tam ekran |
| Alt+R | Döndür | Alt+O | Telefon ekranını kapat/aç |
| Ctrl+C / V | Pano paylaşımı | Sürükle-bırak | Dosyayı telefona gönder |

### OBS ile yayın
- Ayarlar sayfasında **Oyun yayını · Kablolu** veya **Kablosuz** hazır ayarını seç.
- OBS'de **Kaynak ekle → Pencere Yakalama → `[scrcpy.exe]: Yansit`** seç, yakalama yöntemi olarak *Windows 10 (1903 ve üzeri)* kullan.
- Ses için: **Uygulama Ses Yakalama → scrcpy.exe**.
- Yansıtma penceresini simge durumuna küçültme, yoksa OBS'de siyah görünür. Pencerenin başka pencerelerin arkasında kalması sorun değil.

## Sık sorulanlar

<details><summary><b>Ses gelmiyor</b></summary>

- Alt çubuktaki **Sesi aktar** anahtarı açık mı? Ses aktarımı **Android 11 veya üstünü** gerektirir.
- Varsayılan modda telefonun bütün sesi PC'ye gelir ve telefonun hoparlörü susar. Bu normaldir.
- **Telefonda da çalsın** modu (Android 13+) açıksa bazı oyun ve uygulamalar sesini vermeyebilir. Bu seçeneği kapat.
- Android 11'de başlatırken telefonun kilidi açık olmalı.
</details>

<details><summary><b>Telefon listede görünmüyor</b></summary>

- Telefon ve PC aynı ağda mı? Misafir ağları ve bazı okul/yurt ağları cihazların birbirini görmesini engeller. Bu durumda kabloyla ya da **Elle bağlan** bölümünden bağlan.
- Windows Güvenlik Duvarı `adb.exe` için izin sorarsa **Özel ağlar**'a izin ver.
</details>

<details><summary><b>Görüntü takılıyor</b></summary>

**Zayıf Wi-Fi** hazır ayarını seç, 5 GHz Wi-Fi kullan ya da kabloyla bağlan.
</details>

Sorun yaşarsan **Kayıt** sayfasından kaydı kopyalayıp bir [issue](https://github.com/Mehmetsndl/yansit/issues) aç.

## Sürüm takibi

Sürümler [Anlamsal Sürümleme](https://semver.org/lang/tr/) (`ANA.ARA.YAMA`) kuralına uyar. Tüm değişiklikler [CHANGELOG.md](CHANGELOG.md) dosyasında yazılıdır. Uygulama açılışta GitHub'daki son sürümü kontrol eder; yeni sürüm varsa sol altta bildirim çıkar.

**Yeni sürüm yayınlama (geliştirici için):**
1. `yansit.py` içindeki `__version__` değerini artır, örneğin `3.1.0`.
2. `CHANGELOG.md` dosyasına `## [3.1.0] - TARİH` başlıklı bir bölüm ekle.
3. Commit'le ve etiketi gönder:
   ```bash
   git commit -am "Sürüm 3.1.0"
   git tag v3.1.0
   git push && git push --tags
   ```
4. GitHub Actions `Yansit.exe` dosyasını derler ve sürüm notlarıyla birlikte bir **Release** yayınlar.

## Teşekkür

Yansıt, ekran yansıtma için Genymobile'ın açık kaynaklı [scrcpy](https://github.com/Genymobile/scrcpy) projesini (Apache 2.0) kullanır. scrcpy, uygulamanın içinden resmi GitHub sürümlerinden indirilir. Yansıt bu aracın üstüne kurulmuş Türkçe bir arayüzdür.

## Lisans

[MIT](LICENSE)
