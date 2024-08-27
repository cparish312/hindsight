import sys
import pandas as pd

tolerance = 15
def round_to_tolerance(value, tolerance):
    return round(value / tolerance) * tolerance

def is_google_news(ocr_res):
    found_box = ocr_res.loc[(ocr_res['text'] == "Search or type URL") & (ocr_res['x_rounded'] >= 180) & (ocr_res['x_rounded'] <= 195)
                            & (ocr_res['y_rounded'] == 195)]

    if len(found_box) > 0:
        return True
    return False

def parse_chrome_ocr_results(ocr_res):
    ocr_res['x_rounded'] = ocr_res['x'].apply(round_to_tolerance, args=(tolerance,))
    ocr_res['y_rounded'] = ocr_res['y'].apply(round_to_tolerance, args=(tolerance,))

    google_news = is_google_news(ocr_res)
    
    return {"is_google_news" : google_news}
