# ANNE — Güçlendirme ve teslim raporu

Tarih: **8 Eylül 2026**. Kaynak: kullanıcının sağladığı `anne-main.zip`.
Bu çalışma yerel bir kaynak-kod iyileştirmesidir; upstream sürüm veya güvenlik sertifikası değildir.
Orijinal arşiv ve çalışma alanındaki `main.tex` değiştirilmedi.

## Tamamlanan somut düzeltmeler

1. **Bellek gizliliği:** FractalMemory ve LocalMemory, parametreli SQLite işlemlerinde
   bilinen kimlik bilgisi desenlerini maskeler. Hipotez, karar, hata, ölçek, kural ve
   empati kayıtları aynı sınırdan geçer. JSON terim belleği ve GitHub bellek yazımı
   da maskeleme uygular. Toplu ve isimlendirilmiş SQL parametreleri test edildi.
2. **İzin politikası:** Boş araç kümesi artık hiçbir araca izin vermez. Dışarıdan
   verilen kümenin sonradan değiştirilmesi politikayı değiştirmez. Kayıtlı okuma
   araçları çalıştırılmadan önce AgencyGate de kontrol edilir.
3. **Çevrimdışı bağımsızlık:** Gemini SDK'sı sağlayıcı oluşturuluncaya kadar yüklenmez.
   Bulut SDK'ları isteğe bağlı paket gruplarına taşındı. Eksik SDK için açık hata verilir.
4. **Doğrulama ayrımı:** Heuristik filtre başarısı ile olgusal doğrulama ayrıldı.
   `verified`, `refuted`, `unverified`, `conflicting` sonuçları ve kaynak bilgisi
   ayrı raporlanır. Doğrulayıcı hatası veya eksik kaynak, doğrulanmış sayılmaz.
5. **Kontrollü yanıt:** `require_verified_response=True`, doğrulanamayan yanıtı
   saklar; çürütülen/çelişen yanıtlar normal modda da saklanır. Doğrulanmamış model
   önerileri belleğe yerleşik bilgi olarak etiketlenmez. `AgentResult.verification`
   alanı aday yanıtın durumunu ve yanıtın saklanıp saklanmadığını gösterir.
6. **ANLA düzeltmesi:** Ayrı özneler hakkındaki “true … others … false” ifadesi artık
   yalnızca zıt kelimeler içerdiği için reddedilmez. Bu hâlâ dilsel bir sezgiseldir.
7. **MITOS açıklığı:** Rastgele üretilen puanlar `SIMULATION` ve
   `seeded_random_fixture` etiketleriyle taşınır. Seçim, doğruluk veya eylem yetkisi değildir.
8. **Yeniden deneme bütünlüğü:** Her yeni çerçevede FailFast tekrar çalışır; ilk
   isteğin kanıt ve yetki gereksinimleri düşürülemez. Üst döngü kimliği ve derinlik
   kalıcı kayıtlara eklenir. Hipotez kimlikleri döngüye özgüdür; geçmiş üzerine yazılmaz.
9. **Öğrenme puanı:** Aynı kuralın tekrar kaydedilmesi otomatik güven bonusu üretmez;
   gelen puanların ortalaması korunur. Bu değişiklik yine de öğrenme kanıtı değildir.
10. **Test/deney altyapısı:** Eksik modül import'u ve HALT durum tutarsızlığı düzeltildi.
    Eşlenmiş çıktı tekrar-oynatımı, etiket bağımsızlığı ve güvenlik regresyonları eklendi.

## Kullanım

Arşivi açıp `anne-main` dizinine geçin. Python 3.12 veya üzeri gerekir.
Geliştirme bağımlılıkları kendi ortamınızda kurulu değilse:

```bash
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

Gemini kullanacaksanız ayrıca `python -m pip install -e ".[gemini]"` çalıştırın.
Bulut sağlayıcılarının API anahtarı, model erişimi ve canlı servis davranışı bu
çalışmada doğrulanmadı. Sağlayıcıdaki varsayılan model adlarının kullanılabilirliğini
kendi hesabınızda kontrol edin; bu arşiv yeni model önerisi yapmaz.

### Bağımsız referans bağlantısı

```python
from anne.agent.offline import create_offline_agent
from anne.core.verification import ReferenceClaim, ReferenceVerifier

verifier = ReferenceVerifier((
    ReferenceClaim(
        claim="The measured sample contains 12 records.",
        source="independently-checked-observation:sample-001",
        supported=True,
    ),
))
agent = create_offline_agent(
    model="YOUR_INSTALLED_LOCAL_MODEL",
    workspace="workspace",
    db_path="anne_offline.db",
    response_verifier=verifier,
    require_verified_response=True,
)
```

`ReferenceVerifier` yalnızca uygulamanın güvenilir olarak sağladığı **tam iddia**
ile eşleşir. Kelimeleri farklı bir yanıt veya fazladan bir iddia doğrulanmaz.
Kaynak dizesinin dolu olması, kaynağın dünyada gerçekten doğru olduğunu kanıtlamaz.
Gerçek bir doğrulayıcı için `ClaimVerifier.verify()` sözleşmesini uygulayın.
Modelin kendi ürettiği kaynakları veya SEMANTIC_FRAME alanını bu güven sınırına aktarmayın.

### Eşlenmiş deney

```bash
python benchmarks/scripts/run_paired_replay.py --dataset datasets/paired_replay_demo.json --output benchmarks/results/my_replay.json
python benchmarks/scripts/run_anla_ablation.py
```

Paket kurulu değilse Linux/macOS için komutların başına `PYTHONPATH=src` ekleyin;
PowerShell'de önce `$env:PYTHONPATH="src"` ayarlayın.

Kendi deneyinizde model ve üretim ayarlarını, aynı dondurulmuş çıktıları, ölçülen
üretim süresini ve bağımsız değerlendirici etiketlerini kaydedin. Etiketler karar
kapılarına verilmez. Her örnek temiz bellekle değerlendirilir. Geliştirme ve test
verilerini ayrı tutun; demo verisi **development** olarak işaretlidir.

Yanlış kabul oranı yanlış/uygunsuz örnekler, yanlış ret oranı doğru/uygun örnekler
üzerinden hesaplanır; ilgili sınıf yoksa oran `null` olur. Çekimserlik ve kapı
gecikmesi ayrıca raporlanır. Bu deney iki farklı model çalıştırması değil,
aynı model çıktısına filtre uygulanmasının karşılaştırmasıdır.

## Doğrulama sonuçları

Son tam çalıştırma: **227 başarılı, 2 atlanan, 0 başarısız test** (Python 3.13.15).
Toplam **140 Python dosyası** sözdizimi kontrolünden geçti.

Test komutları, sonuçları ve ortam bilgisi `docs/validation/` altındadır.
İki gerçek ses adaptörü testi yerel ses/mikrofon bağımlılıkları bulunmadığından
atlanır; çekirdek ve yeni regresyon testleri çalıştırılır. Testlerde gerçek API
anahtarı veya bulut çağrısı kullanılmadı; yeni bağımlılık kurulmadı.

- Eski 30 örneklik geliştirme fikstüründe ANLA ON: 0 yanlış kabul.
- Yeni 6 örneklik sentetik demoda ANNE: **2 yanlış kabul**, 0 yanlış ret,
  1 kanıt eksikliği nedeniyle çekimserlik. Yanlış kabul oranı 2/4 = **%50**.
- İkinci sonuç bilerek korunmuştur: “Rome/Fransa-Berlin” karşı örneklerine özel
  kurallar ekleyip genel doğruluk varmış izlenimi verilmemiştir.
- Python dosyaları sözdizimi kontrolünden geçirildi. `ruff`, `mypy` ve `setuptools`
  ortamda bulunmadığından lint, statik tür kontrolü ve wheel derlemesi çalıştırılmadı.
  CI yapılandırması güncellendi, fakat GitHub üzerinde çalıştırıldığı iddia edilmez.

## Açık kalan araştırma ve üretim işleri

- **Genel olgusal doğrulama tamamlanmış değildir.** Varsayılan konuşma modu yanlış
  fakat `unverified` etiketli yanıt döndürebilir. Sıkı mod, kanıt yoksa yanıt vermez;
  yanlış yanıtı kendiliğinden doğruya dönüştürmez.
- ANLA ve EthicCore sezgiselleri kapsamlı mantık/etik/güvenlik kanıtı değildir.
- MITOS hâlâ temsili üretim kullanır; gerçek keşif, transfer ve otonom öğrenme
  başarısı bağımsız veriyle ölçülmelidir. Eski öğrenme modülleri tamamen birleştirilmedi.
- Mevcut planlayıcı, ses uygulaması ve sağlayıcı istemcileri üretim sertifikalı değildir.
  Gerçek sandbox/shadow/canary yürütücüler ve güvenli dış eylem akışları tamamlanmadı.
- Maskeleme bilinen desenler içindir; şifreleme veya her tür gizli veriyi bulma garantisi
  değildir. Önceden yazılmış veritabanlarını temizlemez; genel ikili artifact depolarını
  değiştirmez. SQL verisi her zaman parametre olarak bağlanmalıdır.
- GitHub bellek sınıfını doğrudan kullanmak hâlâ yetkilendirilmiş ağ yazımı yapar.
  Okuma araçlarına eklenen AgencyGate kontrolü tüm bağımsız depolama API'lerini
  kapsayan bir sandbox değildir. Gerçek hesaplarda kapsamı dar kimlik bilgileri kullanın.

## Arşiv içeriği

Kaynaklar, mevcut belgeler, yeni regresyonlar, demo veri kümesi ve gerçek çalışma
çıktıları birlikte verilir. Test veritabanları, önbellekler, geçici dizinler ve
derlenmiş dosyalar dağıtım dışıdır. `SHA256SUMS.txt`, bu dosyanın kendisi dışındaki
dağıtım dosyalarının bütünlük özetlerini içerir.