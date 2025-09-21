import subprocess
import time
from PIL import Image
import pytesseract
import io
import re

# Tesseract yolu (Windows)
# Eğer tesseract.exe farklı bir yerde yüklüyse bu yolu güncelleyin.
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def adb_screenshot():
    """
    Telefon ekranının anlık görüntüsünü adb komutuyla yakalar ve byte olarak döndürür.
    """
    try:
        result = subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Hata: adb komutu çalıştırılamadı. Hata kodu: {e.returncode}")
        print("Lütfen adb'nin doğru şekilde kurulduğundan ve telefonunuzun bağlı olduğundan emin olun.")
        return None

def ocr_numbers(image_bytes):
    """
    Görüntü byte'larını kullanarak OCR yapar ve potansiyel telefon numaralarını ayıklar.
    """
    if not image_bytes:
        return set()

    # Byte verisini PIL Image'a çevir
    image = Image.open(io.BytesIO(image_bytes))
    
    # Tesseract için özel yapılandırma: Sadece rakamları, '+' ve boşluk karakterini tanır.
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789+ '
    text = pytesseract.image_to_string(image, config=custom_config)
    
    # Telefon numaralarını daha kesin bir şekilde yakalamak için yeni regex kullanıldı.
    # 1. (+90 ile başlayan 10 rakamlı Türk numaraları)
    # 2. (+ ile başlayan ve 6-15 arası rakam içeren uluslararası numaralar)
    # 3. Yalnızca 10 rakamdan oluşan diziler (örneğin, 5xx...)
    # Bu kalıplar, alakasız uzun rakam dizilerinin yakalanmasını engeller.
    regex = r'(\+90\s?\d{10})|(\+\d{6,15})|(\b\d{10}\b)'
    numbers = re.findall(regex, text)
    
    cleaned_numbers = set()
    for match in numbers:
        # re.findall birden fazla grup döndürdüğü için eşleşen grubu seç
        num_str = ''.join(match)
        
        # Sadece rakamları ve '+' işaretini koru
        clean_num = ''.join(filter(lambda x: x.isdigit() or x == '+', num_str))
        
        # Temizlenmiş numaranın makul bir uzunlukta olup olmadığını tekrar kontrol et
        if len(clean_num.replace('+', '')) >= 10:
            cleaned_numbers.add(clean_num)
            
    return cleaned_numbers

if __name__ == "__main__":
    all_numbers = set()
    print("Ekran yakalama başladı. WhatsApp'ı açın ve numaraları görmek için kaydırın. Bitirmek için Ctrl+C'ye basın.")

    try:
        while True:
            img_bytes = adb_screenshot()
            if img_bytes:
                new_numbers = ocr_numbers(img_bytes)
                
                # Yeni bulunan numaraları eski listeyle karşılaştır
                new_numbers_to_print = new_numbers - all_numbers
                if new_numbers_to_print:
                    print("Yeni numaralar bulundu:", new_numbers_to_print)
                    all_numbers.update(new_numbers_to_print)
                
            time.sleep(1.5)  # her 1.5 saniyede bir ekran yakala
    except KeyboardInterrupt:
        # Kaydı bitir ve CSV oluştur
        with open("whatsapp_numbers.csv", "w", encoding="utf-8") as f:
            f.write("\n".join(all_numbers))
        print(f"Durduruldu. Toplam {len(all_numbers)} numara CSV olarak kaydedildi.")