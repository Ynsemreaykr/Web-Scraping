import logging
import re
from typing import Optional, Dict, List

from config import Config
from processing.text_utils import tr_lower

logger = logging.getLogger(__name__)

MANDATORY_CATEGORIES = [
    "Trafik Kazasi",
    "Yangin",
    "Elektrik Kesintisi",
    "Hirsizlik",
    "Suc ve Cinayet",
    "Kulturel Etkinlikler",
]

KEYWORDS: Dict[str, Dict[str, int]] = {
    "Trafik Kazasi": {
        "trafik kazasi": 10,
        "trafik kazası": 10,
        "trafikte": 5,
        "trafikte meydana gelen": 10,
        "trafik yoğunluğu": 2,
        "trafik yogunlugu": 2,
        "kaza yaptı": 8,
        "kaza yapti": 8,
        "kaza geçirdi": 8,
        "kaza gecirdi": 8,
        "kazaya karıştı": 8,
        "kazaya karisti": 8,
        "kazasında": 8,
        "kazasinda": 8,
        "kazası": 7,
        "kazasi": 7,
        "çarptı": 6,
        "carpti": 6,
        "çarpışma": 7,
        "carpisma": 7,
        "çarpıştı": 7,
        "carpisti": 7,
        "çarpışan": 6,
        "carpisan": 6,
        "kafa kafaya": 9,
        "zincirleme": 8,
        "devrildi": 5,
        "takla": 5,
        "takla attı": 8,
        "ölümlü kaza": 10,
        "olumlu kaza": 10,
        "yaralı": 4,
        "yarali": 4,
        "yaralandı": 3,
        "yaralandi": 3,
        "yaralılar": 4,
        "hafif yaralı": 6,
        "motosiklet": 3,
        "bisiklet": 3,
        "otomobil": 2,
        "kamyon": 3,
        "minibüs": 3,
        "minibus": 3,
        "otobüs": 3,
        "otobus": 3,
        "tır": 3,
        "sürücü": 3,
        "surucu": 3,
        "yayaya çarptı": 8,
        "yayaya carpti": 8,
        "kırmızı ışık": 4,
        "makas attı": 4,
        "alkollü sürücü": 6,
        "kontrolden çıktı": 4,
        "kontrolden cikti": 4,
        "virajda": 3,
        "tır devrildi": 10,
        "devrilen tır": 10,
        "devrilen tir": 10,
        "devrilen": 6,
        "dorsesinin altında": 9,
        "dorsesinin altinda": 9,
        "dorsesinin": 5,
        "hayatini kaybetti": 2,
        "feci kaza": 9,
        "kavşak": 4,
        "kavsak": 4,
        "yolunda": 1,
        "otoyolda": 4,
        "emniyet şeridinde": 3,
        "jandarma": 1,
        "polis ekipleri": 1,
        "olay yerinde": 2,
        "d100": 6,
        "d-100": 6,
        "tem otoyolu": 7,
        "tem'de": 5,
        "tem de": 5,
        "altında kaldı": 6,
        "altinda kaldi": 6,
        "dorsesinin altında": 8,
        "dorsesinin altinda": 8,
        "otoyolda": 5,
        "karayolunda": 5,
        "seyir halinde": 5,
        "ehliyetine el kondu": 7,
        "alkolmetre": 5,
        "çarpıp kaçtı": 9,
        "carpip kacti": 9,
        "yaralamalı kaza": 10,
        "yaralamali kaza": 10,
        "ölmüştü": 3,
        "olmustu": 3,
        "can kaybı": 5,
        "can kaybi": 5,
        "trafik kazası geçirdi": 10,
        "trafik kazasi gecirdi": 10,
        "araçlar çarpıştı": 9,
        "araclar carpisti": 9,
        "önündeki araca": 5,
        "onundeki araca": 5,
        "bariyerlere çarptı": 7,
        "bariyerlere carpti": 7,
        "refüje": 5,
        "refuje": 5,
        "trafikte aksama": 6,
        "yoğunluk oluştu": 3,
        "yogunluk olustu": 3,
    },
    "Yangin": {
        "yangın": 10,
        "yangin": 10,
        "yangına": 8,
        "yangina": 8,
        "yangın çıktı": 10,
        "yangin cikti": 10,
        "alev aldı": 6,
        "alev aldi": 6,
        "alev topuna döndü": 8,
        "itfaiye": 8,
        "itfaiye ekipleri": 8,
        "söndürüldü": 6,
        "sonduruldu": 6,
        "tutuştu": 5,
        "tutustu": 5,
        "küle döndü": 6,
        "orman yangını": 10,
        "araç yandı": 8,
        "elektrik yangını": 8,
        "duman": 1,
        "yanan ev": 9,
        "yanan işyeri": 9,
        "yanan isyeri": 9,
        "yangın ihbarı": 8,
        "yangin ihbari": 8,
        "yangın çıkaran": 8,
        "dumandan etkilenen": 7,
        "söndürme çalışması": 8,
        "sondurme calismasi": 8,
        "alevlere müdahale": 8,
        "alevlere mudahale": 8,
        "yangın söndürüldü": 9,
        "yangin sonduruldu": 9,
        "bina yangını": 10,
        "bina yangini": 10,
        "çatı katında yangın": 9,
        "cati katinda yangin": 9,
        "fabrikada yangın": 10,
        "fabrikada yangin": 10,
    },
    "Elektrik Kesintisi": {
        "elektrik kesintisi": 10,
        "elektrik kesintisi yaşanacak": 12,
        "elektrik kesintileri": 10,
        "enerji kesintisi": 10,
        "elektrik kesildi": 8,
        "elektrik kesilecek": 9,
        "elektriğin kesilmesi": 9,
        "elektrigin kesilmesi": 9,
        "elektriksiz": 7,
        "elektrik yok": 8,
        "ışıklar söndü": 7,
        "isiklar sondu": 7,
        "ışıksız": 6,
        "isiksiz": 6,
        "karanlıkta kaldı": 6,
        "trafo": 5,
        "trafo patladı": 8,
        "trafo arızası": 8,
        "trafo arizasi": 8,
        "SEDAŞ": 4,
        "SEDAS": 4,
        "sedas": 4,
        "dağıtım şirketi": 7,
        "dagitim sirketi": 7,
        "elektrik bağlantısı": 5,
        "hat arızası": 6,
        "hat arizasi": 6,
        "bakım çalışması": 6,
        "bakim calismasi": 6,
        "bakım nedeniyle": 7,
        "bakim nedeniyle": 7,
        "akım kesildi": 6,
        "güç kesintisi": 8,
        "kesinti yaşandı": 4,
        "kesinti yasanacak": 6,
        "kesinti duyurusu": 9,
        "kesinti listesi": 9,
        "programlı kesinti": 10,
        "programli kesinti": 10,
        "planlı kesinti": 10,
        "planli kesinti": 10,
        "plansız kesinti": 9,
        "plansiz kesinti": 9,
        "abonelerin dikkatine": 8,
        "elektrik kesintisi programı": 10,
        "elektrik kesintisi programi": 10,
        "şebeke": 5,
        "sebeke": 5,
        "gedaş": 8,
        "gedas": 8,
        "boğaziçi elektrik": 8,
        "bogazici elektrik": 8,
        "kesinti saatleri": 9,
        "elektrik ne zaman gelecek": 9,
        "şebekede arıza": 8,
        "sebekede ariza": 8,
        "yük gerilim": 5,
        "yuk gerilim": 5,
        "şalter indi": 7,
        "salter indi": 7,
        "elektrik arızası": 7,
        "elektrik arizasi": 7,
        "kesinti yaşayacak": 8,
        "kesinti yasayacak": 8,
        "ilçede kesinti": 8,
        "ilcede kesinti": 8,
    },
    "Hirsizlik": {
        "hırsızlık": 10,
        "hirsizlik": 10,
        "hırsızlığa": 9,
        "çalındı": 8,
        "calindi": 8,
        "soygun": 10,
        "gasp": 10,
        "kapkaç": 10,
        "kapkac": 10,
        "dolandırıcı": 8,
        "dolandirici": 8,
        "dolandırıldı": 8,
        "dolandirildi": 8,
        "dolandırıcılık": 9,
        "dolandiricilik": 9,
        "yankesici": 8,
        "zimmet": 6,
        "hırsız": 8,
        "hirsiz": 8,
        "soyuldu": 8,
        "ev soyuldu": 9,
        "işyerinden çalındı": 9,
        "evden çalındı": 8,
        "operasyon": 0,
        "gözaltı": 0,
        "tutuklandı": 0,
        "market soygunu": 10,
        "evden hırsızlık": 10,
        "evden hirsizlik": 10,
        "işyerine giren": 8,
        "isyerine giren": 8,
        "silahlı soygun": 10,
        "silahli soygun": 10,
        "kasa soygunu": 10,
        "bisiklet çalındı": 8,
        "bisiklet calindi": 8,
        "motosiklet çalındı": 8,
        "motosiklet calindi": 8,
        "otomobil çalındı": 8,
        "otomobil calindi": 8,
        "hırsızlık olayı": 9,
        "hirsizlik olayi": 9,
        "çalıntı araç": 8,
        "calinti arac": 8,
        "kapıyı kırarak": 7,
        "kapiyi kirarak": 7,
        "güvenlik kamerasına": 5,
        "guvenlik kamerasina": 5,
        "şüpheli şahıs": 6,
        "supheli sahis": 6,
        "jandarma operasyonu": 5,
        "polis baskını": 6,
        "polis baskini": 6,
    },
    "Suc ve Cinayet": {
        "cinayet": 12,
        "katliam": 12,
        "öldürüldü": 10,
        "olduruldu": 10,
        "olduren": 8,
        "öldüren": 8,
        "öldü": 3,
        "oldu": 0,
        "öldüğü": 4,
        "oldugu": 0,
        "biri öldü": 10,
        "kişi öldü": 10,
        "kisi öldü": 10,
        "kisi öldu": 10,
        "ölüme neden": 10,
        "olume neden": 10,
        "taksirle öldürme": 12,
        "taksirle oldurme": 12,
        "taksirle ölüm": 12,
        "taksirle olum": 12,
        "cinayet şüphelisi": 12,
        "cinayet suphelisi": 12,
        "narkotik": 10,
        "uyuşturucu": 9,
        "uyusturucu": 9,
        "uyuşturucu operasyonu": 12,
        "uyusturucu operasyonu": 12,
        "narkotik operasyonu": 12,
        "narkotik ekipleri": 11,
        "sahte hesap": 10,
        "sahte hesap operasyonu": 12,
        "siber dolandırıcılık": 11,
        "siber dolandiricilik": 11,
        "kesici alet": 10,
        "kesici aletle": 11,
        "bıçaklı saldırı": 11,
        "bicakli saldiri": 11,
        "silahlı çatışma": 11,
        "silahli catisma": 11,
        "silahlı kavga": 10,
        "silahli kavga": 10,
        "silahlı saldırı": 11,
        "silahli saldiri": 11,
        "silah çekti": 10,
        "silah cekti": 10,
        "silahını çekti": 10,
        "silahini cekti": 10,
        "silahlarını çektiler": 10,
        "silahlarini cektiler": 10,
        "infaz": 10,
        "cinayetle": 9,
        "cinayete": 9,
        "ölümle sonuçlanan": 9,
        "olumle sonuclanan": 9,
        "yaralamaya sebep": 6,
        "tecavüz": 11,
        "tecavuz": 11,
        "cinsel saldırı": 11,
        "cinsel saldiri": 11,
        "kaçakçılık": 8,
        "kacakcilik": 8,
        "uyuşturucu taciri": 10,
        "zehir taciri": 10,
        "zehir tacirlerinin": 10,
        "ağır suçlardan": 10,
        "agir suclardan": 10,
        "ağır suç": 10,
        "agir suc": 10,
        "aranan şahıs": 8,
        "aranan sahis": 8,
        "aranan isim": 8,
        "saldırıda": 6,
        "saldirisinin": 6,
        "saldırgan": 8,
        "saldirgan": 8,
        "bar saldırısı": 12,
        "bar saldirisi": 12,
        "dehşet anları": 7,
        "dehset anlari": 7,
        "gizli sera": 10,
        "saldırıda hayatını kaybetti": 12,
        "saldirisinda hayatini kaybetti": 12,
        "operasyonla yakalandı": 8,
        "operasyonla yakalandi": 8,
        "kanlı gece": 10,
        "kanli gece": 10,
        "kanlı saldırı": 10,
        "kanli saldiri": 10,
        "gece kulübü saldırı": 12,
        "gece kulubu saldiri": 12,
        "bıçakladı": 10,
        "bicakladi": 10,
        "bıçakla": 9,
        "bicakla": 9,
        "dövülerek öldürüldü": 12,
        "dovulerek olduruldu": 12,
        "dövülerek": 8,
        "dovulerek": 8,
        "darbetti": 7,
        "vandalizm": 8,
        "dehşeti yaşattı": 10,
        "dehseti yasatti": 10,
        "dehşet yaşattı": 10,
        "dehset yasatti": 10,
        "camdan ateş": 10,
        "camdan ates": 10,
        "tahliye edildi": 6,
        "tahliyesine karar": 6,
        "cezaevinden çıktı": 7,
        "cezaevinden cikti": 7,
        "cezaevinden tahliye": 8,
        "hapisten çıktı": 7,
        "hapisten cikti": 7,
        "tetikçi": 10,
        "tetikci": 10,
        "fuhuş": 10,
        "fuhus": 10,
        "hapis cezası": 8,
        "hapis cezasi": 8,
        "aranıyordu": 5,
        "araniyordu": 5,
        "müebbet": 8,
        "tutuklanan": 7,
    },
    "Kulturel Etkinlikler": {
        "kültür": 6,
        "kultur": 6,
        "kültürel": 7,
        "kulturel": 7,
        "kültür merkezi": 10,
        "kultur merkezi": 10,
        "festival": 8,
        "konser": 8,
        "konser verilecek": 10,
        "ücretsiz konser": 10,
        "ucretsiz konser": 10,
        "sergi": 8,
        "sergi açıldı": 10,
        "sergi acildi": 10,
        "tiyatro": 8,
        "tiyatro oyunu": 9,
        "sahnelendi": 8,
        "sahne aldı": 7,
        "etkinlik": 3,
        "etkinliği": 3,
        "etkinligi": 3,
        "etkinlik düzenlendi": 10,
        "etkinlik duzenlendi": 10,
        "etkinliğe": 3,
        "kutlama etkinliği": 6,
        "şenlik": 8,
        "senlik": 8,
        "müzik": 2,
        "gösteri": 6,
        "gosteri": 6,
        "açılış töreni": 6,
        "acilis toreni": 6,
        "açılışı": 6,
        "sanat": 3,
        "sanatsever": 3,
        "dans gösterisi": 6,
        "bale": 6,
        "opera gösterisi": 7,
        "opera sahnesi": 7,
        "resital": 6,
        "fuar": 8,
        "panayır": 8,
        "turnuva": 5,
        "yarışma": 4,
        "yarismasi": 5,
        "konferans": 6,
        "seminer": 6,
        "söyleşi": 6,
        "soylesi": 6,
        "kermes": 6,
        "maraton": 5,
        "müze": 5,
        "tören": 5,
        "toren": 5,
        "belediyesi düzenliyor": 6,
        "davetiye": 5,
        "bilet satışa": 5,
        "sinema": 5,
        "belgesel": 5,
        "atölye": 7,
        "atolye": 7,
        "workshop": 6,
        "dinleti": 7,
        "şiir": 5,
        "siir": 5,
        "kitap fuarı": 9,
        "kitap fuari": 9,
        "gençlik festivali": 9,
        "genclik festivali": 9,
        "şölen": 7,
        "solen": 7,
        "kultur ve sanat": 9,
        "kültür ve sanat": 9,
        "halk oyunları": 8,
        "halk oyunlari": 8,
        "mehter": 6,
        "lansman": 5,
        "tanıtım günü": 6,
        "tanitim gunu": 6,
        "düzenlenecek": 2,
        "duzenlenecek": 2,
        "gerçekleşecek": 2,
        "gerceklesecek": 2,
        "gerçekleştirilecek": 2,
        "gerceklestirilecek": 2,
        "katılıma açık": 7,
        "katilima acik": 7,
        "ücretsiz etkinlik": 10,
        "ucretsiz etkinlik": 10,
        "halk konseri": 10,
        "kültür müdürlüğü": 8,
        "kultur mudurlugu": 8,
        "gençlik şöleni": 9,
        "genclik soleni": 9,
        "millet bahçesi": 2,
        "millet bahcesi": 2,
        "sahneledi": 7,
        "oynadı": 4,
        "oynadi": 4,
        "müzik ziyafeti": 7,
        "muzik ziyafeti": 7,
    },
}

# Beraberlik: agir suclar hirsizliktan once; kultur en son
PRIORITY_ORDER = [
    "Trafik Kazasi",
    "Yangin",
    "Elektrik Kesintisi",
    "Suc ve Cinayet",
    "Hirsizlik",
    "Kulturel Etkinlikler",
]

CATEGORY_DISPLAY = {
    "Trafik Kazasi": "Trafik Kazası",
    "Yangin": "Yangın",
    "Elektrik Kesintisi": "Elektrik Kesintisi",
    "Hirsizlik": "Hırsızlık",
    "Suc ve Cinayet": "Suç ve Cinayet",
    "Kulturel Etkinlikler": "Kültürel Etkinlikler",
}

_TURK_SUFFIX = r"[a-zçğıöşü]{0,8}"

# URL: tek basina "kultur/kültür" cok haberi kultur saniyordu; dar segment
_URL_KULTUR_HIGH = (
    "kultur-sanat",
    "konser",
    "festival",
    "sergi",
    "tiyatro",
    "fuar",
)
_URL_KULTUR_MED = ("kultur", "kültür", "sanat", "etkinlik", "muzik", "müzik")
_URL_KULTUR_LOW = ()

_URL_ASAYIS = (
    "asayis",
    "asayiş",
    "3-sayfa",
    "3sayfa",
    "guvenlik",
    "güvenlik",
    "emniyet",
)

_URL_YANGIN = ("yangin", "yangın", "itfaiye")

# URL'de tek basina "elektrik" / "kesinti" cok yanlis pozitif (uretim, zam); daraltildi
_URL_ELEKTRIK_STRONG = (
    "sedas",
    "sedaş",
    "gedas",
    "gedaş",
    "trafo-ariza",
    "trafo-arıza",
    "elektrik-kesintisi",
    "elektrik-kesinti",
    "enerji-kesintisi",
    "kesinti-program",
    "planli-kesinti",
    "programli-kesinti",
)

# Uretim / yenilenebilir / tesis — "kesinti" etiketi degil; govde kirli olsa bile bastir
_RE_ELEKTRIK_URETIM = re.compile(
    r"(?u)"
    r"elektrik.{0,60}(?:üret|uret|üretti|uretti|üreten|ureten|üretilen|uretilen|"
    r"üretim|uretim|üretildi|uretildi)|"
    r"(?:üretilen|uretilen|üretim|uretim).{0,40}elektrik|"
    r"elektrik.{0,40}üretildi|atik.{0,30}elektrik|elektrik.{0,30}atik|"
    r"milyonlarca\s*kwh|milyonlarcakwh|kwh.{0,40}(?:üret|uret|üretti|uretti|kapasite|"
    r"katkı|kati|karşılan|karsilan)|"
    r"(?:ges\b|güneş\s*(?:enerji|panel|santral)|gunes\s*(?:enerji|panel|santral)|"
    r"ruzgar\s*türbin|ruzgâr\s*türbin|ruzgar\s*enerji|ruzgâr\s*enerji|"
    r"jeotermal|biyogaz|biyometan|kojenerasyon|chp\b)"
    r".{0,55}(?:elektrik|kwh|üret|uret|santral|kapasite)|"
    r"(?<![a-zçğıöşü])isu(?![a-zçğıöşü]).{0,55}(?:kwh|elektrik|üret|uret|milyon)|"
    r"(?:izaydaş|izaydas).{0,55}(?:kwh|elektrik|üret|uret|milyon)",
)
_RE_ELEKTRIK_OUTAGE_STRONG = re.compile(
    r"(?u)"
    r"elektrik\s+kesintisi|enerji\s+kesintisi|programl[ıi]\s+kesinti|planl[ıi]\s+kesinti|"
    r"plans[ıi]z\s+kesinti|kesinti\s+duyurusu|kesinti\s+listesi|kesinti\s+saatleri|"
    r"kesinti\s+yaşan|kesinti\s+yasan|kesinti\s+yaşayacak|kesinti\s+yasayacak|"
    r"elektrik\s+kesildi|elektrik\s+kesilecek|elektriksiz|elektrik\s+yok|"
    r"trafo.{0,18}(?:arıza|ariza|patlad|yangın|yangin)|"
    r"elektrik\s+ne\s+zaman\s+gelecek|abonelerin\s+dikkat|kesinti\s+program",
)


def _elektrik_uretim_suppresses_kesintisi(combined_tr: str) -> bool:
    return bool(
        _RE_ELEKTRIK_URETIM.search(combined_tr)
        and not _RE_ELEKTRIK_OUTAGE_STRONG.search(combined_tr)
    )


def _url_trafik_boost(u: str) -> int:
    """Slug'da 'kazan' gibi 'kaza' alt dizgisini trafik sayma."""
    if "trafik" in u or "trafik-kaza" in u:
        return 12
    if re.search(r"(?u)(?<![a-zçğıöşü])kaza(?![a-zçğıöşü])", u):
        return 12
    return 0


def _url_elektrik_boost(u: str) -> int:
    if re.search(r"(?u)kesintisiz", u):
        return 0
    if any(x in u for x in _URL_ELEKTRIK_STRONG):
        return 14
    if re.search(r"(?u)elektrik.{0,25}kesinti|kesinti.{0,20}elektrik", u):
        return 14
    if re.search(r"(?u)(?<![a-zçğıöşü])kesinti(?!siz)[a-zçğıöşü]{0,8}(?![a-zçğıöşü])", u):
        return 8
    return 0


_RE_SUC_SIGNAL = re.compile(
    r"(?u)silahlı\s+saldır|silahli\s+saldir|silahlı\s+saldir|cinayet|"
    r"eğlence\s+mekan|eglence\s+mekan|gece\s+kulüb|gece\s+kulup|"
    r"kanlı\s+gece|kanli\s+gece|kurşun\s+yağ|kursun\s+yag|"
    r"zehir\s+tacir|gizli\s+sera|narkotik|uyuşturucu|uyusturucu|"
    r"ağır\s+suç|agir\s+suc|bar\s+saldır|silah.{0,8}çek|silah.{0,8}cek|"
    r"bıçaklı|bicakli|bıçakladı|bicakladi|bıçakla|bicakla|saldırgan|saldirgan|dehşet\s+an|dehset\s+an|"
    r"(?:biri|kişi|kisi)\s+öldü|(?:\d+)\s+öl[üu]|ölüme\s+neden|olume\s+neden|"
    r"taksirle\s+öl|taksirle\s+ol|infaz|restoran.{0,30}silah|"
    r"operasyonla\s+yakalan|katliam|sahte\s+hesap|kesici\s+alet|"
    r"tecavüz|tecavuz|cinsel\s+saldır|öldürüldü|olduruldu|"
    r"dehşet\s*yaşattı|dehset\s*yasatti|camdan\s+dehşet|camdan\s+dehset"
)

_RE_SU_KESINTISI = re.compile(
    r"(?u)"
    r"su\s+kesinti|sular\s+(?:ne\s+zaman|kesilecek|kesildi|gelecek)|"
    r"su\s+kesilecek|su\s+kesildi|su\s+arızası|su\s+arizasi|"
    r"(?<![a-zçğıöşü])isu(?![a-zçğıöşü]).{0,60}(?:kesinti|su\s+kesilecek|sular)|"
    r"su\s+kesintisi|sular.{0,30}gelecek|su\s+kesintisi\s+alarm"
)

_RE_SPOR_CONTEXT = re.compile(
    r"(?u)"
    r"(?<![a-zçğıöşü])lig(?![a-zçğıöşü])|efeler\s+lig|süper\s+lig|super\s+lig|"
    r"(?<![a-zçğıöşü])maç(?![a-zçğıöşü])|(?<![a-zçğıöşü])mac(?![a-zçğıöşü])|"
    r"play[\s-]off|galibiyet|mağlubiyet|maglubiyet|"
    r"(?<![a-zçğıöşü])gol(?![a-zçğıöşü])|futbol|voleybol|basketbol|"
    r"(?<![a-zçğıöşü])boks(?![a-zçğıöşü])|güreş|gures|atletizm|"
    r"şampiyon|sampiyon|play\s*off|deplasman|fikstur|fikstür|"
    r"transfer\s+mesai|bonservis|kadro\s+hesab|antrenman|"
    r"taraftar|tribün|tribun|forvet|defans|kaleci|teknik\s+direktör|"
    r"[a-zçğıöşü]*spor[a-zçğıöşü]{0,8}(?![a-zçğıöşü])|"
    r"(?<![a-zçğıöşü])turnuva[a-zçğıöşü]{0,6}(?![a-zçğıöşü])|"
    r"(?<![a-zçğıöşü])u\d{2}(?![a-zçğıöşü])|"
    r"finalde?\b|yenildi\b|kazandı\b|kazandi\b|beraberlik\b|mağlup\b|maglup\b|"
    r"nerede\s+oynadığ|nerede\s+oynadig|forma\s+giy|sezon.{0,20}performans"
)

_RE_TRAFIK_REGULATION = re.compile(
    r"(?u)"
    r"trafik\s+ceza|fahiş\s+(?:trafik|ceza)|fahis\s+(?:trafik|ceza)|"
    r"tüvtürk|tuvturk|muayene.{0,25}(?:kural|geçe|gece)|"
    r"ehliyet\s+(?:kural|sınav|sinav)|"
    r"kasko.{0,30}(?:trafik|sigorta|dönem|donem|sayfa)|"
    r"trafik\s+sigorta|sigorta.{0,20}(?:yeni\s+dönem|yeni\s+donem|yeni\s+sayfa)|"
    r"trafik.{0,20}(?:düzenleme|duzenleme|kural|yasa|talimat)|"
    r"(?:ceza|düzenleme|duzenleme).{0,20}talimat"
)

_RE_CRASH_VEHICLE_NOFIRE = re.compile(
    r"(?u)(?:tır|tir|kamyon|otomobil|minibüs|minibus|otobüs|otobus).{0,100}"
    r"(?:devrilen|devrildi|dorse|çarpış|carpis|çarpıştı|carpisti|altında\s+kaldı|altinda\s+kaldi)|"
    r"(?:tem\b|otoyol|karayolu|tünel|tunel).{0,80}"
    r"(?:çarpış|carpis|zincirleme|kaza|devrilen|devrildi|araçlar|araclar)"
)
_RE_FIRE_BODY = re.compile(
    r"(?u)yangın|yangin|itfaiye|alev(?:ler)?|yanan\s|yanmış|yanmis|tutuş|tutus|duman|söndür|sondur|"
    r"yangına\s+müdahale|yangina\s+mudahale|küle\s+dön|kule\s+don"
)

_RE_SIYASI = re.compile(
    r"(?u)"
    r"iktidara?\s+(?:çağrı|cagri|seslendi)|"
    r"(?:chp|mhp|ak\s+parti|hdp|iyi\s+parti).{0,40}(?:operasyon|çağrı|cagri)|"
    r"gelin\s+operasyon\s+yapalım|gelin\s+operasyon\s+yapalim|"
    r"meclis.{0,30}(?:operasyon|soruşturma|sorusturma)|"
    r"siyasi.{0,20}(?:operasyon|baskı|baski)|"
    r"muhalefet.{0,30}(?:operasyon|çağrı|cagri)|"
    r"tbmm.{0,40}(?:konuştu|konustu|savunma|strateji)|"
    r"cumhurbaşkan.{0,30}(?:talimat|düzenleme|duzenleme|imzalad)|"
    r"teşkilat.{0,30}(?:uyar|duyur|toplandı|toplandi)|"
    r"teskilat.{0,30}(?:uyar|duyur|toplandi)|"
    r"(?:duyuran|duyurdu|açıkladı|acikladi).{0,30}teşkilat|"
    r"(?:duyuran|duyurdu|acikladi).{0,30}teskilat|"
    r"(?:saadet\s+partisi|iyi\s+parti|chp|mhp|hdp|ak\s+parti).{0,60}(?:çıkış|cikis|eleştir|elestir|yorum)|"
    r"(?:milletvekili|vekil|genel\s+başkan|genel\s+baskan).{0,40}(?:yorum|değerlendir|degerlendird|konuş|konus)|"
    r"cumhurbaşkan.{0,40}(?:açılış|acilis|proje|ziyaret)|"
    r"(?:türkkan|turkkan|gergerlioğlu|gergerlioglu|tipioğlu|tipioglu).{0,50}(?:yorum|değerlendir|degerlendird|konuş|konus|çıkış|cikis)|"
    r"(?:değerlendir|degerlendird).{0,40}(?:konuklar|tv'de|tvde|programı|programi)|"
    r"(?:konuklar|tv).{0,30}(?:değerlendir|degerlendird)|"
    r"nato\b|eyy\s+amerika|ey\s+amerika|"
    r"(?:bakan\b|bakanı\b|bakani\b).{0,50}(?:ziyaret|geliyor|açıkladı|acikladi|konuştu|konustu)|"
    r"valilik|milletvekili|ilçe\s+başkan|ilce\s+baskan|belediye\s+başkan|belediye\s+baskan|"
    r"pazarcılar\s+odası|pazarcilar\s+odasi|hayırlı\s+olsun\s+ziyaret|hayirli\s+olsun\s+ziyaret|"
    r"saadet.{0,30}ziyaret|chp.{0,25}ziyaret"
)


def _apply_context_penalties(combined_tr: str, scores: Dict[str, int]) -> None:
    t = combined_tr

    # --- Karayolu/TEM kazasi; yangın kelimesi yok → Yangın degil ---
    if _RE_CRASH_VEHICLE_NOFIRE.search(t) and not _RE_FIRE_BODY.search(t):
        scores["Yangin"] -= 450
        scores["Trafik Kazasi"] += 28

    # --- Su kesintisi → Elektrik degil ---
    if _RE_SU_KESINTISI.search(t):
        scores["Elektrik Kesintisi"] -= 500

    # --- Elektrik uretim ---
    if re.search(r"(?u)kesintisiz", t):
        scores["Elektrik Kesintisi"] -= 100
    if _elektrik_uretim_suppresses_kesintisi(t):
        scores["Elektrik Kesintisi"] -= 500
    elif re.search(
        r"(?u)elektrik.{0,55}(üret|uret|üretti|uretti|üreten|ureten)|üretilen.{0,30}elektrik|"
        r"elektrik.{0,40}üretildi|atik.{0,25}elektrik|elektrik.{0,25}atik|"
        r"milyonlarca\s*kwh|kwh.{0,25}(üret|uret|karşılan|karsilan|üretti)",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 120
    if re.search(
        r"(?u)(elektrik|enerji|doğalgaz|dogalgaz).{0,40}(zam|tarife|fiyat|sinyali)|"
        r"zam\s+sinyali|doğalgaza\s+zam|dogalgaza\s+zam",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 120
    if re.search(
        r"(?u)istihdam|i̇stihdama|istihdama|iş\s+kur|is\s+kur|istihdama\s+kesintisiz",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 80

    # --- SEDAŞ/GEDAŞ toplu sözleşme/sendika → Elektrik Kesintisi degil ---
    if re.search(
        r"(?u)(sedaş|sedas|gedaş|gedas).{0,80}(toplu\s+sözleşme|toplu\s+sozlesme|"
        r"sendika|grev|işçi|isci|tes-iş|tes-is|zam\s+talebi|maaş|maas)",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 500

    # --- Baraj / içme suyu / arıtma → Elektrik / Yangın degil ---
    if re.search(
        r"(?u)baraj|sapanca|yuvacık|yuvacik|içme\s+suyu|icme\s+suyu|arıtma|aritma|"
        r"su\s+projesi|su\s+projeler|su\s+şebekesi|su\s+sebekesi",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 380
        scores["Yangin"] -= 220
        scores["Kulturel Etkinlikler"] -= 120

    # --- Finans / ekonomi → Trafik, Kültürel degil ---
    # altın: "altında" icinde yanlis eslesmesin (alt + ek)
    if re.search(
        r"(?u)(?<![a-zçğıöşü])(?:altın|altin)(?![a-zçğıöşü])|"
        r"döviz|doviz|borsa|faiz|merkez\s+bank|dolar\s+kuru|euro\s+kuru|sterlin|"
        r"tahmin|yatırım|yatirim|ekonomist|gramı|grami|ons|beklenti|piyasa|çeyrek|ceyrek|"
        r"bitcoin|fon\b|temettü|temettu|bddk|spk\b",
        t,
    ):
        scores["Trafik Kazasi"] -= 160
        scores["Kulturel Etkinlikler"] -= 200
        scores["Suc ve Cinayet"] -= 100

    # --- Askerlik / bedelli → yanlis kategorileri dusur (tumunu sifirlamasin) ---
    if re.search(
        r"(?u)bedelli\s+askerlik|askerlik\s+ücreti|askerlik\s+ucreti|celp\s+dönemi|celp\s+donemi",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 450
        scores["Trafik Kazasi"] -= 350
        scores["Yangin"] -= 350
        scores["Elektrik Kesintisi"] -= 350
        scores["Hirsizlik"] -= 350
        scores["Suc ve Cinayet"] -= 280

    # --- Elektrik akımı / çarpması (kaza, kesinti degil) ---
    if re.search(
        r"(?u)elektrik\s+akımı|elektrik\s+akimi|akıma\s+kapıl|akima\s+kapil|"
        r"elektrik\s+çarpması|elektrik\s+carpmasi|elektrik\s+çarptı|elektrik\s+carpti",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 300
        scores["Trafik Kazasi"] -= 360
        scores["Hirsizlik"] -= 420

    # --- Servis / okul otobüsü kazası → Trafik, Hırsızlık degil ---
    if re.search(r"(?u)servis\s+kazası|servis\s+kazasi|okul\s+servis", t):
        scores["Trafik Kazasi"] += 42
        scores["Hirsizlik"] -= 350

    # --- Suc sinyali → Trafik degil ---
    if _RE_SUC_SIGNAL.search(t):
        scores["Trafik Kazasi"] -= 120

    # --- Suc sinyali → Hirsizlik degil (hirsiz yoksa) ---
    if _RE_SUC_SIGNAL.search(t):
        if not re.search(
            r"(?u)hırsızlık|hirsizlik|hırsız\b|hirsiz\b|soygun|kapkaç|kapkac|çalındı|calindi|market\s+soygun",
            t,
        ):
            scores["Hirsizlik"] -= 100

    # --- Gozalti + Baskan / siyasi → Hirsizlik degil ---
    if re.search(r"(?u)gözaltı|gozalti", t) and re.search(
        r"(?u)başkan\b|baskan\b|belediye|chp\b|ak\s+parti|maaşlı|maaslı|sevgili",
        t,
    ):
        if not re.search(
            r"(?u)hırsız|hirsiz|soygun|çalındı|calindi|kapkaç|kapkac|hırsızlık|hirsizlik",
            t,
        ):
            scores["Hirsizlik"] -= 120

    # --- Tahliye / tutuklama → Hirsizlik degil, Suc olabilir ---
    if re.search(r"(?u)tahliye\s+edildi|tahliye\s+oldu|tahliyesine\s+karar", t):
        if not re.search(r"(?u)hırsız|hirsiz|soygun|çalındı|calindi", t):
            scores["Hirsizlik"] -= 200

    # --- Trafik ceza/kural/muayene → gercek kaza degil ---
    if _RE_TRAFIK_REGULATION.search(t) and not re.search(
        r"(?u)kaza(?!nır|ndır|nan|nma)|çarptı|carpti|yaralı|yarali|devrildi|takla",
        t,
    ):
        scores["Trafik Kazasi"] -= 200

    # --- Yol projesi / ihale / yapım → Trafik Kazasi degil ---
    if re.search(
        r"(?u)proje\s+onay|proje.{0,20}onaylandı|proje.{0,20}onaylandi|kotko\b|"
        r"ihale|yapım|yapim|inşaat|insaat|bağlantı\s+yolu|baglanti\s+yolu|"
        r"kavşak\s+projesi|kavsak\s+projesi|yol\s+yapım|yol\s+yapim|merkezi.{0,25}bitir|"
        r"(?:yıl|yil)\s+içinde\s+bitir|güzergah|guzergah",
        t,
    ) and not re.search(
        r"(?u)kaza(?!n)|çarptı|carpti|yaralı|yarali|can\s+kayb|öldü|oldu",
        t,
    ):
        scores["Trafik Kazasi"] -= 220

    # --- Ağaç devrildi, fırtına → Trafik degil ---
    if re.search(r"(?u)ağaç.{0,20}devril|agac.{0,20}devril|fırtına|firtina|rüzgar|ruzgar", t):
        if not re.search(r"(?u)kaza|çarptı|carpti|araç|arac", t):
            scores["Trafik Kazasi"] -= 150

    # --- Yol/otoyol 'durdu' (aksama) kaza degil ---
    if re.search(
        r"(?u)(?:yol|otoyol|liman\s+yolu|bağlantı|baglanti).{0,35}durdu",
        t,
    ) and not re.search(
        r"(?u)kaza|çarp|devril|ölü|olu|yaralı|yarali|çarpış|carpis",
        t,
    ):
        scores["Trafik Kazasi"] -= 200

    # --- Kötü koku ihbarı → Yangın degil (duman/alev yoksa) ---
    if re.search(r"(?u)kötü\s+koku|kotu\s+koku|koku\s+ihbar", t) and not _RE_FIRE_BODY.search(t):
        scores["Yangin"] -= 320

    # --- Kamyon/TIR + yolda olay → Trafik (Suç degil) ---
    if re.search(
        r"(?u)(kamyon|tır|tir).{0,40}(otomobil|araca?\s+saplandı|araca?\s+saplandi|"
        r"yola\s+düştü|yola\s+dustu|düştü|dustu|devrildi)",
        t,
    ) and not re.search(r"(?u)cinayet|saldırı|saldiri|bıçak|bicak|silah", t):
        scores["Suc ve Cinayet"] -= 150
        scores["Trafik Kazasi"] += 15

    # --- Spor → tum kategorileri bastir (gercek olay yoksa) ---
    if _RE_SPOR_CONTEXT.search(t) and not re.search(
        r"(?u)(?<![a-zçğıöşü])kaza(?!n)|yangın|yangin|kesinti|hırsız|hirsiz|cinayet|saldırı|saldiri",
        t,
    ):
        for c in MANDATORY_CATEGORIES:
            scores[c] -= 200

    # --- Ihale / yapim / yikilacak → Kultur degil ---
    if re.search(
        r"(?u)ihale|yapım|yapim|inşaat|insaat|yıkılacak|yikilacak|teklif\s+sundu|"
        r"yeni\s+adres|taşınacak|tasinacak",
        t,
    ) and not re.search(
        r"(?u)konser|festival|sergi|tiyatro|etkinlik\s+düzenlendi|sahne|gösteri|gosteri",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 200

    # --- Cenaze / defin → Kultur degil ---
    if re.search(
        r"(?u)cenaze|defin|mevlit|mevlid|son\s+yolculuğ|son\s+yolculug|toprağa\s+veril|topraga\s+veril",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 200

    # --- Siyasi → esit ceza kazanan degistirmez; kultur/trafik/yangin agir dusur ---
    if _RE_SIYASI.search(t):
        scores["Kulturel Etkinlikler"] -= 450
        scores["Trafik Kazasi"] -= 320
        scores["Yangin"] -= 320
        scores["Elektrik Kesintisi"] -= 320
        scores["Hirsizlik"] -= 260
        scores["Suc ve Cinayet"] -= 140

    # --- Meteoroloji / hava durumu ---
    if re.search(
        r"(?u)meteoroloji|hava\s+durumu|sağanak|saganak|yağış|yagis|kar\s+yağışı|kar\s+yagisi|"
        r"sıcaklık|sicaklik|derece|fırtına\s+uyarı|firtina\s+uyari|karabasan|"
        r"gün\s+gün\s+açıkladı|gun\s+gun\s+acikladi",
        t,
    ) and not re.search(
        r"(?u)kaza|yangın|yangin|sel\s+felaketi|can\s+kayb",
        t,
    ):
        for c in MANDATORY_CATEGORIES:
            scores[c] -= 150
        if not re.search(r"(?u)konser|festival|sergi|tiyatro|sahne", t):
            scores["Kulturel Etkinlikler"] -= 260

    # --- İçme suyu / altyapı projesi → Yangın ve Kültürel degil ---
    if re.search(
        r"(?u)içme\s+suyu|icme\s+suyu|su\s+projesi|su\s+projeler|su\s+şebekesi|su\s+sebekesi",
        t,
    ):
        scores["Yangin"] -= 220
        scores["Kulturel Etkinlikler"] -= 220

    # --- Cumhurbaskani acilis / altyapi acilis → Kültürel / Yangın degil ---
    if re.search(
        r"(?u)cumhurbaşkan.{0,55}(?:açılış|acilis|açılışını|acilisini|yaptı|yapti)|"
        r"cumhurbaskan.{0,55}(?:açılış|acilis|açılışını|acilisini|yaptı|yapti)|"
        r"(?:proje|tesis|fabrika|santral).{0,35}(?:açılış|acilis|açılışını|acilisini)",
        t,
    ) and not re.search(
        r"(?u)konser|festival|sergi|tiyatro|müze|muze",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 200
        scores["Yangin"] -= 280

    # --- Sinema / film → Hirsizlik degil ---
    if re.search(
        r"(?u)sinema|film\s+vizyona|vizyona\s+gir|film\s+gösterim|film\s+gosterim|"
        r"(?:\d+)\s+yeni\s+film",
        t,
    ):
        scores["Hirsizlik"] -= 480

    # --- Operasyon: asayiş / dijital suç → Hırsızlık degil; gerekirse Suç ---
    if re.search(r"(?u)operasyon", t) and not re.search(
        r"(?u)hırsız|hirsiz|soygun|çalındı|calindi|kapkaç|kapkac",
        t,
    ):
        scores["Hirsizlik"] -= 120
    if re.search(r"(?u)operasyon", t) and re.search(
        r"(?u)gözaltı|gozalti|tutuklandı|tutuklandi|dijital\s+suç|dijital\s+suc|siber\s+operasyon|"
        r"silah.{0,15}operasyon",
        t,
    ):
        if not re.search(
            r"(?u)hırsızlık|hirsizlik|hırsız\b|hirsiz\b|soygun|çalındı|calindi",
            t,
        ):
            scores["Hirsizlik"] -= 450
        scores["Suc ve Cinayet"] += 24

    # --- Holding / yönetim + tahliye → Hırsızlık degil ---
    if re.search(r"(?u)tahliye\s+edildi|tahliye\s+oldu", t) and re.search(
        r"(?u)holding|yönetim\s+kurulu|yonetim\s+kurulu",
        t,
    ):
        if not re.search(r"(?u)hırsız|hirsiz|soygun|çalındı|calindi|hırsızlık|hirsizlik", t):
            scores["Hirsizlik"] -= 400

    # --- Tehdit iddiası → Kültürel degil, suc / basin ---
    if re.search(r"(?u)tehdit\s+iddiası|tehdit\s+iddiasi", t):
        scores["Kulturel Etkinlikler"] -= 320
        scores["Suc ve Cinayet"] += 38

    # --- Sinema salonu film listesi → kültürel etkinlik degil ---
    if re.search(r"(?u)sinema\s+salonlarında|sinema\s+salonlarinda", t) and re.search(
        r"(?u)yeni\s+film|vizyona",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 420

    # --- Sağlık / kanser haberi → Suç ve Kültürel degil ---
    if re.search(
        r"(?u)erken\s+teşhis|erken\s+teshis|kanserden\s+kurtul|kanser\b|ameliyat|"
        r"tedavi\s+gördü|tedavi\s+gordu",
        t,
    ) and not _RE_SUC_SIGNAL.search(t):
        scores["Suc ve Cinayet"] -= 240
        scores["Kulturel Etkinlikler"] -= 220

    # --- Eğitim / okul personeli → Kültürel degil ---
    if re.search(
        r"(?u)okul\s+müdür|okul\s+mudur|müdürü\s+ve\s+öğretmen|muduru\s+ve\s+ogretmen|"
        r"görevden\s+uzaklaştır|gorevden\s+uzaklastir|veli.{0,20}şikayet|veli.{0,20}sikayet",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 300

    # --- Tıklama / müjde + rahatsız → Hırsızlık degil ---
    if re.search(r"(?u)müjde\b|mujde\b", t) and re.search(r"(?u)rahatsız|rahatsiz", t):
        scores["Hirsizlik"] -= 450

    # --- SEDAŞ / dağıtım şirketi + kazı çukur araç (kesinti degil) ---
    if re.search(r"(?u)(?:sedaş|sedas|gedaş|gedas)", t) and re.search(
        r"(?u)çukur|cukur|kazı|kazi|kazdı|kazdi|belediye\s+aracı|belediye\s+araci|düştü|dustu|devril",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 520

    # --- Köprü bakım trafik aksaması → Elektrik degil ---
    if re.search(r"(?u)köprü|kopru", t) and re.search(
        r"(?u)bakım|bakim|onarım|onarim|çalışması|calismasi",
        t,
    ) and re.search(r"(?u)trafik|felç|felc|yoğunluk|yogunluk", t):
        scores["Elektrik Kesintisi"] -= 480

    # --- Nöbetçi eczane listesi → Kültürel degil ---
    if re.search(r"(?u)nöbetçi\s+eczane|nobetci\s+eczane|nöbetçi\s+eczaneler|nobetci\s+eczaneler", t):
        scores["Kulturel Etkinlikler"] -= 520

    # --- Manevi değer / genel belediye söylemi → Kültürel degil ---
    if re.search(r"(?u)manevi\s+değer|manevi\s+deger", t):
        scores["Kulturel Etkinlikler"] -= 450

    # --- KBRN / sivil savunma / afet farkındalık (itfaiye yangını degil) ---
    # Not: Govde/sidebar'da "yanmış" gecmesi _RE_FIRE_BODY ile cezayi iptal etmesin.
    if re.search(
        r"(?u)kbrn|sivil\s+savunma|"
        r"afet.{0,100}farkındalık|afet.{0,100}farkindalik|"
        r"afet.{0,100}farkındalığı|afet.{0,100}farkindaligi",
        t,
    ):
        scores["Yangin"] -= 720
        if re.search(
            r"(?u)farkındalık|farkindalik|eğitim|egitim|personeline|personel|tatbikat|"
            r"artırıldı|artirildi|korunma|hazırlık|hazirlik",
            t,
        ):
            scores["Kulturel Etkinlikler"] += 62
        else:
            scores["Kulturel Etkinlikler"] -= 100

    # --- Fidan / ağaçlandırma / Tüpraş çevre → Yangın / Elektrik degil ---
    _planting = bool(
        re.search(
            r"(?u)(?:100\s+bin\s+fidan|tüpraş|tupras).{0,50}(?:fidan|ağaçlandır|agaclandir)|"
            r"(?:fidan|ağaçlandır|agaclandir).{0,40}(?:tüpraş|tupras|100\s+bin)",
            t,
        )
    )
    if _planting or (
        re.search(
            r"(?u)fidan|ağaçlandır|agaclandir|orman\s+sağlığı|orman\s+sagligi|"
            r"100\s+bin\s+fidan",
            t,
        )
        and not _RE_FIRE_BODY.search(t)
    ):
        scores["Yangin"] -= 520
    if re.search(r"(?u)tüpraş|tupras", t) and re.search(
        r"(?u)fidan|ağaçlandır|agaclandir|100\s+bin",
        t,
    ):
        scores["Elektrik Kesintisi"] -= 620
        scores["Kulturel Etkinlikler"] += 52

    # --- Dağıtım şirketi + çukur + araç düştü → Trafik / olay, Hırsızlık degil ---
    if re.search(r"(?u)(?:sedaş|sedas|gedaş|gedas)", t) and re.search(
        r"(?u)çukur|cukur|kazı|kazi|kazdı|kazdi",
        t,
    ) and re.search(r"(?u)arac|araç|düştü|dustu|devril", t):
        scores["Hirsizlik"] -= 500
        scores["Trafik Kazasi"] += 55

    # --- Soba faciası (çoğu CO / dumansız) — klasik yangın degilse bastir ---
    if re.search(r"(?u)soba\s+facias", t) and not re.search(
        r"(?u)yangın|yangin|alev|itfaiye|yanan\s|duman",
        t,
    ):
        scores["Yangin"] -= 420

    # --- TEM/otoyol + (feci) kaza — govde yanlis "yangin" kelimesinden etkilenmesin ---
    if re.search(
        r"(?u)(?:tem\b|tem\s+otoyolu|otoyol).{0,120}(?:feci\s+)?kaza|"
        r"(?:feci\s+)?kaza.{0,80}(?:tem\b|tem\s+otoyolu|otoyol)",
        t,
    ):
        scores["Yangin"] -= 780
        scores["Trafik Kazasi"] += 60

    # --- TEM / otoyol zincirleme kaza → Yangın degil ---
    if re.search(r"(?u)(?:tem\b|otoyol).{0,80}zincirleme|zincirleme.{0,40}(?:tem\b|otoyol)", t):
        scores["Yangin"] -= 520
        scores["Trafik Kazasi"] += 35

    # --- ÖTV / Meclis otomobil düzenlemesi → Trafik kazası degil ---
    if re.search(r"(?u)ötv|otv", t) and re.search(
        r"(?u)otomobil|araç|arac|meclis|düzenleme|duzenleme|onaylandı|onaylandi",
        t,
    ):
        scores["Trafik Kazasi"] -= 380

    # --- Baro / yeni avukat kaydı → Kültürel etkinlik degil ---
    if re.search(r"(?u)baro", t) and re.search(
        r"(?u)yeni\s+avukat|avukatlar?\s+(?:katıldı|katildi|kaydoldu)|staj\s+sürecini|staj\s+surecini|"
        r"yemin\s+etti",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 450

    # --- Adliye / başsavcılık istatistik → Kültürel degil ---
    if re.search(
        r"(?u)adliye|başsavcılık|bassavcilik|cumhuriyet\s+başsavcılığı|"
        r"dosyalarda.{0,20}rekor|yargı\s+tarih",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 480

    # --- Dolandırıcılık iddiası / mağdur anlatımı → Suç, Kültürel degil ---
    if re.search(r"(?u)dolandırıcılık\s+iddiası|dolandiricilik\s+iddiasi|dolandırıcılık\s+iddia", t):
        scores["Kulturel Etkinlikler"] -= 450
        scores["Suc ve Cinayet"] += 28

    # --- Hastane + deprem/sağlık farkındalığı → Kültürel degil ---
    if re.search(r"(?u)hastan", t) and re.search(
        r"(?u)deprem\s+farkındalık|deprem\s+farkindalik|112\s+günü|112\s+gunu",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 400

    # --- Gıda tarım toplantı / sorunlar masaya → Kültürel / Trafik-Suç degil ---
    # Slug genelde asayiş/kaza; Suc+Trafik URL bonusu yanlis kategori yapıyordu.
    if re.search(r"(?u)gıda|gida|tarım|tarim|hayvancılık|hayvancilik", t) and re.search(
        r"(?u)masaya\s+yatırıldı|masaya\s+yatirildi|toplantı|toplanti|çalıştay|calistay",
        t,
    ):
        scores["Kulturel Etkinlikler"] += 78
        scores["Trafik Kazasi"] -= 560
        scores["Suc ve Cinayet"] -= 420

    # --- Turnuva / spor sahası + talihsiz kaza — karayolu kazası degil ---
    if re.search(r"(?u)turnuva|spor\s+salon|sahada|maçta|macta", t) and re.search(
        r"(?u)talihsiz\s+kaza|\bkaza\b",
        t,
    ):
        if not re.search(
            r"(?u)tem\b|otoyol|karayolu|trafik|otomobil|kamyon|minibüs|minibus|"
            r"sürücü|surucu|yayaya\s+çarptı|yayaya\s+carpti|emniyet\s+şeridi|emniyet\s+seridi",
            t,
        ):
            scores["Trafik Kazasi"] -= 520

    # --- Liseli şef / meslek okulu sergi (egitim) → Kültürel zayıflat ---
    if re.search(r"(?u)liseli|meslek\s+lisesi|meslek\s+okul", t) and re.search(
        r"(?u)şef|sef|sergiledi|yetenek",
        t,
    ):
        scores["Kulturel Etkinlikler"] -= 320

    # --- Yaşam mücadelesi / vefat (trafik unsuru yok) → Trafik kazası degil ---
    if re.search(r"(?u)yaşam\s+mücadelesi|yasam\s+mucadelesi", t) and not re.search(
        r"(?u)kaza|çarp|trafik|otoyol|tem\b|araç|arac|sürücü|surucu",
        t,
    ):
        scores["Trafik Kazasi"] -= 380

    # --- Umre / toplu dolandırıcılık şikayeti → Hırsızlık degil, Suç ---
    if re.search(r"(?u)dolandırıldı|dolandirildi|dolandırıldığını", t) and re.search(
        r"(?u)umre|karakol|şikayet|şikayeti|200\s+kişi",
        t,
    ):
        scores["Hirsizlik"] -= 450
        scores["Suc ve Cinayet"] += 32

    # --- Cinayet + dolandırılma sözü (alıntı) → Hırsızlık degil ---
    if re.search(r"(?u)öldüren|olduren|cinayet|baba\s+ve\s+oğlu|baba\s+ve\s+oglu", t) and re.search(
        r"(?u)dolandır|keşke|keske",
        t,
    ):
        scores["Hirsizlik"] -= 500
        scores["Suc ve Cinayet"] += 40

    # --- Tabip/hekim örgütü raporu → Kültürel degil ---
    if re.search(r"(?u)hekimsen|tabipler\s+birliği|tabipler\s+birligi|doktorlar\s+birliği", t):
        scores["Kulturel Etkinlikler"] -= 300


def _count_keyword(text_tr: str, kw: str) -> int:
    k = tr_lower(kw.strip())
    if not k:
        return 0
    # "kesintisiz" (ara yok) icinde "kesinti" sayilmasin — yanlis Elektrik Kesintisi
    if k == "kesinti":
        return len(
            re.findall(
                r"(?u)(?<![a-zçğıöşü])kesinti(?!siz)[a-zçğıöşü]{0,8}(?![a-zçğıöşü])",
                text_tr,
            )
        )
    escaped = re.escape(k)
    if " " in k:
        return len(re.findall(rf"(?u)(?<![a-zçğıöşü]){escaped}(?![a-zçğıöşü])", text_tr))
    return len(
        re.findall(
            rf"(?u)(?<![a-zçğıöşü]){escaped}{_TURK_SUFFIX}(?![a-zçğıöşü])",
            text_tr,
        )
    )


def _combo_boosts(combined_tr: str) -> Dict[str, int]:
    extra = {c: 0 for c in MANDATORY_CATEGORIES}
    if re.search(
        r"(?u)trafik.{0,80}kaza(?!n[a-zçğıöşü])|kaza(?!n[a-zçğıöşü]).{0,80}trafik|"
        r"(?<![a-zçğıöşü])yol.{0,50}kaza(?!n[a-zçğıöşü])|otoyol.{0,50}kaza(?!n[a-zçğıöşü])|d100|d-100|"
        r"araçlar.{0,30}çarpış|araclar.{0,30}carpis|çarpıştı|carpisti|yaralamalı\s+kaza|yaralamali\s+kaza",
        combined_tr,
    ):
        extra["Trafik Kazasi"] += 14
    if re.search(
        r"(?u)yangın.{0,20}çıktı|yangin.{0,20}cikti|alev.{0,15}aldi|yanan\s+(?:ev|işyeri|araç|arac)|"
        r"itfaiye.{0,25}müdahale|itfaiye.{0,25}mudahale|yangına.{0,15}müdahale|yangina.{0,15}mudahale",
        combined_tr,
    ):
        extra["Yangin"] += 11
    # Not: sedas/sedaş tek başına (ör. çukur kazısı haberi) kesinti sayılmasın — yanlış Elektrik.
    if re.search(
        r"(?u)elektrik.{0,40}kesinti|kesinti.{0,30}elektrik|trafo.{0,20}arıza|"
        r"trafo.{0,20}ariza|abone.{0,25}kesinti|mahalle.{0,40}kesinti|kesinti.{0,20}program|"
        r"kesinti.{0,20}saat|elektrik.{0,25}ne\s+zaman",
        combined_tr,
    ) and not re.search(r"(?u)kesintisiz", combined_tr) and not _elektrik_uretim_suppresses_kesintisi(
        combined_tr
    ) and not _RE_SU_KESINTISI.search(combined_tr):
        extra["Elektrik Kesintisi"] += 14
    if re.search(
        r"(?u)hırsız|hirsiz|soygun|çalındı|calindi|kapkaç|kapkac|silahlı\s+soygun|silahli\s+soygun|"
        r"evden\s+hırsız|evden\s+hirsiz",
        combined_tr,
    ) and not re.search(
        r"(?u)katliam|cinayet|narkotik|uyuşturucu|uyusturucu|sahte\s+hesap|kesici\s+alet",
        combined_tr,
    ):
        extra["Hirsizlik"] += 9
    if re.search(
        r"(?u)katliam|cinayet|narkotik.{0,45}ekip|narkotik\s+operasyon|uyuşturucu\s+operasyon|"
        r"uyusturucu\s+operasyon|sahte\s+hesap.{0,25}operasyon|bilgilendirme\s+seferberliği.{0,40}narkotik|"
        r"narkotik.{0,30}bilgilendirme|kesici\s+aletle\s+cinayet|bar\s+katliam|kanlı\s+gece.{0,30}cinayet|"
        r"gözaltı.{0,15}katliam|gozaltı.{0,15}katliam|"
        r"kanlı\s+gece|kanli\s+gece|kanlı\s+saldırı|kanli\s+saldiri|"
        r"(?:\d+)\s+(?:ölü|olu|öldü|oldu).{0,30}(?:\d+)\s+yaralı",
        combined_tr,
    ):
        extra["Suc ve Cinayet"] += 14
    if re.search(
        r"(?u)konser|festival|sergi|tiyatro|fuar|yarışma|yarismasi|kermes|tören|toren|"
        r"kültür\s+merkezi|kultur\s+merkezi|müze|muze|sanat.{0,15}günü|sanat.{0,15}gunu|"
        r"gösteri|gosteri|atölye|atolye|dinleti|şölen|solen",
        combined_tr,
    ):
        extra["Kulturel Etkinlikler"] += 4
    if re.search(
        r"(?u)etkinlik\s+düzenlendi|etkinlik\s+duzenlendi|etkinlik.{0,15}(?:açık|acik|ücretsiz|ucretsiz|davet|katılım|katilim)",
        combined_tr,
    ):
        extra["Kulturel Etkinlikler"] += 5
    return extra


def _url_boosts(url: str, combined_tr: str = "") -> Dict[str, int]:
    u = tr_lower(url or "")
    b = {c: 0 for c in MANDATORY_CATEGORIES}
    if any(x in u for x in _URL_KULTUR_HIGH):
        b["Kulturel Etkinlikler"] += 12
    if any(x in u for x in _URL_KULTUR_MED):
        b["Kulturel Etkinlikler"] += 5
    if any(x in u for x in _URL_KULTUR_LOW):
        b["Kulturel Etkinlikler"] += 2
    if not (combined_tr and _elektrik_uretim_suppresses_kesintisi(combined_tr)):
        b["Elektrik Kesintisi"] += _url_elektrik_boost(u)
    b["Trafik Kazasi"] += _url_trafik_boost(u)
    if any(x in u for x in _URL_YANGIN):
        b["Yangin"] += 12
    if any(x in u for x in _URL_ASAYIS):
        b["Trafik Kazasi"] += 7
        b["Suc ve Cinayet"] += 8
        b["Hirsizlik"] += 5
    return b


class NewsClassifier:
    """Baslik agirlikli anahtar kelime + URL / cumle kombinasyonlari."""

    # Semantik katman kapalıyken bile makul sikilik; gürültülü haberleri elemek icin
    MIN_SCORE = 8
    TITLE_WEIGHT = 2

    def classify(self, title: str, content: str, article_url: str = "") -> Optional[str]:
        title_tr = tr_lower(title or "")
        body_tr = tr_lower(content or "")
        combined_tr = f"{title_tr} {body_tr}"

        scores = {cat: 0 for cat in MANDATORY_CATEGORIES}

        for category, kws in KEYWORDS.items():
            for kw, weight in kws.items():
                nt = _count_keyword(title_tr, kw)
                nb = _count_keyword(body_tr, kw)
                if nt or nb:
                    scores[category] += weight * (nt * self.TITLE_WEIGHT + nb)

        for cat, add in _combo_boosts(combined_tr).items():
            scores[cat] += add
        for cat, add in _url_boosts(article_url, combined_tr).items():
            scores[cat] += add

        _apply_context_penalties(combined_tr, scores)

        # Baslik uretim haberi ise govde/sidebar kesinti kelimeleri skoru sifirlasin
        if _RE_ELEKTRIK_URETIM.search(title_tr) and not _RE_ELEKTRIK_OUTAGE_STRONG.search(title_tr):
            scores["Elektrik Kesintisi"] = 0

        for c in MANDATORY_CATEGORIES:
            scores[c] = max(0, scores[c])

        # ONEMLI: Gomme tum kategorilere benzer puan ekler; anahtar kelime 0 iken
        # her kategori MIN_SCORE uzerine cikabiliyordu. Semantik yalnizca zaten gecerli
        # anahtar kelime sinyali varken uygulanir.
        kw_max = max(scores.values(), default=0)
        if kw_max < self.MIN_SCORE:
            logger.debug("Siniflandirma yok (anahtar kelime esigi): %s", scores)
            return None

        w_sem = int(getattr(Config, "SEMANTIC_CLASSIFIER_WEIGHT", 0) or 0)
        if w_sem > 0:
            raw_snip = f"{(title or '').strip()} {(content or '').strip()}"[:2500]
            if len(raw_snip.strip()) >= 100:
                try:
                    from processing.semantic_category import semantic_category_similarities

                    sims = semantic_category_similarities(raw_snip)
                    for c in MANDATORY_CATEGORIES:
                        scores[c] += int(round(sims.get(c, 0.0) * w_sem))
                except Exception as e:
                    logger.warning("Semantik kategori katkisi atlandi: %s", e)

        for c in MANDATORY_CATEGORIES:
            scores[c] = max(0, scores[c])

        max_score = max(scores.values(), default=0)
        if max_score < self.MIN_SCORE:
            logger.debug("Siniflandirma yok (esik): %s", scores)
            return None

        tied = [c for c in PRIORITY_ORDER if scores[c] == max_score]
        best = tied[0]
        logger.debug("Puanlar: %s -> Secilen: %s", scores, best)
        return best

    def classify_with_scores(self, title: str, content: str) -> dict:
        combined_tr = f"{tr_lower(title)} {tr_lower(content)}"
        out = {}
        for category, keywords in KEYWORDS.items():
            matched = [kw for kw in keywords if _count_keyword(combined_tr, kw) > 0]
            out[category] = {"count": len(matched), "matched": matched}
        return out

    def get_all_keywords_flat(self) -> Dict[str, List[str]]:
        return {cat: sorted(kws.keys()) for cat, kws in KEYWORDS.items()}


classifier = NewsClassifier()
