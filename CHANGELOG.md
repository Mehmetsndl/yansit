# Değişiklik Günlüğü

Bu projedeki tüm önemli değişiklikler bu dosyada tutulur.
Biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) esaslıdır,
sürüm numaraları [Anlamsal Sürümleme](https://semver.org/lang/tr/) kurallarına uyar.

## [Yayınlanmamış]

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

[Yayınlanmamış]: https://github.com/Mehmetsndl/yansit/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/Mehmetsndl/yansit/releases/tag/v3.0.0
