import zipfile
import re
import sys

def extract_text(docx_file):
    try:
        with zipfile.ZipFile(docx_file, 'r') as zf:
            xml_content = zf.read('word/document.xml').decode('utf-8')
        texts = re.findall(r'<w:t(?:.*?)>(.*?)</w:t>', xml_content)
        return ''.join(texts)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    doc_path = 'c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/DRAFT_Special student transportation_V3.docx'
    print(extract_text(doc_path))
