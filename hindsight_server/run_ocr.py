"""Runs frames insert and OCR on any screenshots not in the database."""
from PIL import Image

import tzlocal
from zoneinfo import ZoneInfo

from config import RUNNING_PLATFORM

if RUNNING_PLATFORM == 'Darwin':
    from ocrmac import ocrmac
else:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor

from db import HindsightDB

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

db = HindsightDB()

def run_ocr(frames, doctr_model):
    frame_ids = list(frames['id'])
    img_docs = DocumentFile.from_images(list(frames['path']))
    ocr_res = doctr_model(img_docs)
    json_output = ocr_res.export()

    for page_num, p in enumerate(json_output['pages']):
        img_ocr_res = list()
        page_y, page_x = p['dimensions']
        for block_num, b in enumerate(p['blocks']):
            for line_num, l in enumerate(b['lines']):
                for word in l['words']:
                    x = word['geometry'][0][0] * page_x
                    y = word['geometry'][0][1] * page_y
                    w = (word['geometry'][1][0] * page_x) - x
                    h = (word['geometry'][1][1] * page_y) - y
                    img_ocr_res.append((x, y, w, h, word['value'], word['confidence'], block_num, line_num))
        if len(img_ocr_res) == 0:
            img_ocr_res = [[0, 0, 0, 0, None, 0, None, None]]
        db.insert_ocr_results(frame_ids[page_num], img_ocr_res)

def run_ocr_batched(df, batch_size=20):
    """Runs doctr OCR in a batched fashion to balance efficiency and reliability."""
    doctr_model = ocr_predictor(pretrained=True)
    num_batches = len(df) // batch_size + (1 if len(df) % batch_size > 0 else 0)
    for i in range(num_batches):
        print("Batch", i)
        start_index = i * batch_size
        end_index = start_index + batch_size
        frames_batch = df.iloc[start_index:end_index]
        run_ocr(frames_batch, doctr_model=doctr_model)
        
def extract_text_from_frame_mac(path):
    """Uses ocrmac to run OCR on the provided image path."""
    ocr_res = ocrmac.OCR(Image.open(path), recognition_level='accurate').recognize(px=True) # px converts to pil coordinates
    # x, y, w, h, text, conf, block_num, line_num
    ocr_res = [(r[2][0], r[2][1], r[2][2]-r[2][0], r[2][3]-r[2][1], r[0], r[1], None, None) for r in ocr_res]
    if len(ocr_res) == 0:
        ocr_res = [[0, 0, 0, 0, None, 0, None, None]]
    return ocr_res

def run_ocr_mac(frame_id, frame_path=None):
    """Runs OCR on the given frame_id and inserts results to ocr_results table."""
    ocr_res = db.get_ocr_results(frame_id=frame_id)
    if len(ocr_res) > 0:
        print(f"Already have OCR results for {frame_id}")
        return ocr_res
    frame_path = db.get_frames(frame_ids=[frame_id]).iloc[0]['path'] if frame_path is None else frame_path
    ocr_res = extract_text_from_frame_mac(frame_path)
    db.insert_ocr_results(frame_id, ocr_res)
    print(f"Inserted ocr results for {frame_path}")
    return ocr_res
