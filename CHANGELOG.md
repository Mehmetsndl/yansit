# Değişiklik Günlüğü

Bu projedeki tüm önemli değişiklikler bu dosyada tutulur.
Biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) esaslıdır,
sürüm numaraları [Anlamsal Sürümleme](https://semver.org/lang/tr/) kurallarına uyar.

## [Yayınlanmamış]

## [3.2.0] - 2026-11-23
### Eklendi
- **Telefon kamerası** (Android 12+): kamera görüntüsünü monitörde canlı izleme.
  - Arka / ön / harici kamera, 720p – 4K çözünürlük, 30 / 60 / 120 FPS (yüksek hızlı mod).
  - Fener (flaş), ön kamerada önizlemeyi aynalama (kayıt her zaman doğru yönde).
  - Telefon mikrofonundan ses.
  - Başlıkta **Kaynak: Ekran / Kamera** seçici; çalışırken değiştirilebilir.
- **Video kaydı** (ekran ve kamera): alt çubukta "Kaydet" anahtarı, kayıt süresi göstergesi.
  - Kayıt klasörü seçimi (varsayılan: Videolar/Yansıt), mp4 veya mkv biçimi.
  - Kaydederken monitörde gösterme ya da arka planda pencere açmadan kaydetme.
  - Durdururken kayıt dosyası düzgün kapatılır (mp4 bozulmaz); bittiğinde bildirim.
- **Sanal webcam (Linux):** kamerayı v4l2loopback ile OBS, Zoom, Discord gibi uygulamalarda webcam olarak kullanma.

### Düzeltildi
- **"Oyun yayını" hazır ayarlarıyla yansıtma başlamıyordu:** PC'den kontrol kapalıyken "Telefon uykuya geçmesin"
  seçeneği scrcpy tarafından reddediliyordu. Bu seçenekler artık sadece kontrol açıkken gönderiliyor.
- Alt çubuktaki cihaz adları kısaltıldı (model ve bağlantı türü).

### Değişti
- "Kayıt" (işlem kaydı) sayfasının adı **Günlük** oldu; "Kayıt" artık video kaydı demek.

## [3.1.0] - 2026-11-22
### Eklendi
- **Linux desteği** (Fedora, Ubuntu, Arch ve diğerleri):
  - Hazır derlenmiş Linux paketi (`Yansit-vX-linux-x86_64.tar.gz`) ve uygulama menüsüne ekleyen `install.sh`.
  - Kaynak koddan kurulum: `install.sh` eksik paketleri (python3-tkinter) kurar, yalıtılmış Python ortamı hazırlar.
  - scrcpy'nin Linux sürümü uygulama içinden tek tıkla indirilir (adb dahil).
  - Ayarlar `~/.config/yansit`, indirilen scrcpy `~/.local/share/yansit` klasöründe (XDG standardı).
  - Ses efektleri PipeWire (`pw-play`), PulseAudio veya ALSA ile çalınır.
  - USB izni yoksa (udev) uyarı ve çözüm önerisi.
- Uygulama simgesi (pencere, Windows exe ve Linux menüsü).

### Düzeltildi
- Linux'ta renkli emoji fontu kaynaklı olası Tk çökmesine karşı arayüzde düz simgeler kullanılıyor.
- Linux'ta sistemde kurulu yazı tipi (Inter, Noto Sans, Cantarell…) otomatik seçiliyor.

### Değişti
- scrcpy 5.x ile uyumluluk doğrulandı.

## [3.0.0] - 2026-11-22
### Eklendi
- Kenar çubuklu modern arayüz, koyu / açık tema seçimi.
- Animasyonlar: sayfa geçişleri, kayan menü göstergesi, cihaz kartı girişleri,
  radar tarama, bildirim (tost) kayması, Başlat ↔ Durdur renk geçişi, canlı yayın göstergesi ve süre sayacı.
- Program içinde sentezlenen mekanik ses efektleri (tık, anahtar, röle, cırcır, zil); kapatılabilir.
- Uygulama içi güncelleme kontrolü: GitHub'da yeni sürüm çıkınca bildirim ve indirme butonu.
- Her sürüm etiketinde Windows `.exe` dosyasını otomatik derleyen GitHub Actions iş akışı.
- Kayıt sayfasında Kopyala / Temizle.

### Düzeltildi
- **Telefon sesi PC'ye gelmiyordu.** "Telefonda da çalsın" modu artık varsayılan olarak kapalı;
  varsayılan mod cihazın tüm sesini aktarır. Android sürümü önceden kontrol edilir,
  ses alınamazsa sırasıyla tüm-ses → AAC → sadece görüntü yöntemleri denenir ve kullanıcı uyarılır.

### Değişti
- Proje adı **Yansıt** oldu.

## [2.1.0] - 2026-11-22
### Eklendi
- Ana ekranda "Sesi PC'ye aktar" kutucuğu; yansıtma açıkken değiştirilince otomatik yeniden başlatma.
### Değişti
- Arayüz öğeleri ızgara düzeniyle simetrik hizalandı.

## [2.0.0] - 2026-11-22
### Eklendi
- Ağdaki telefonların (mDNS) otomatik listelenmesi ve tek tıkla bağlanma.
- QR kod ile kablosuz hata ayıklama eşleştirmesi.
- Normal ekran paylaşımı modu: PC'den fare/klavye ile kontrol, telefon ekranını kapatma.

## [1.0.0] - 2026-11-22
### Eklendi
- İlk sürüm: scrcpy tabanlı yansıtma, USB ve kablosuz hata ayıklama, OBS için hazır ayarlar,
  oyun sesi aktarımı, kopunca otomatik yeniden bağlanma.

[Yayınlanmamış]: https://github.com/Mehmetsndl/yansit/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/Mehmetsndl/yansit/releases/tag/v3.2.0
[3.1.0]: https://github.com/Mehmetsndl/yansit/releases/tag/v3.1.0
[3.0.0]: https://github.com/Mehmetsndl/yansit/releases/tag/v3.0.0
