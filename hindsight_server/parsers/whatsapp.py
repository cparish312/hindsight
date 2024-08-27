import sys
import pandas as pd

tolerance = 15
def round_to_tolerance(value, tolerance):
    return round(value / tolerance) * tolerance

def is_homescreen(ocr_res):
    qual_d = {"Chats" : (75, 2265), "Updates" : (330, 2265), 
              "Communities" : (555, 2265), "Calls" : (900, 2265)}
    home_screen = True
    for t, (x_rounded, y_rounded) in qual_d.items():
        found_box = ocr_res.loc[(ocr_res['text'] == t) & (ocr_res['x_rounded'] == x_rounded) 
                                & (ocr_res['y_rounded'] == y_rounded)]
        if len(found_box) == 0:
            home_screen = False
    return home_screen

def get_groupchat_name(ocr_res):
    groupchat_name_box = ocr_res.loc[(ocr_res['x_rounded'] == 195) & (ocr_res['y_rounded'] == 165)]
    if len(groupchat_name_box) > 0:
        return groupchat_name_box.iloc[0]['text']
    return None

def parse_whatsapp_ocr_results(ocr_res):
    ocr_res['x_rounded'] = ocr_res['x'].apply(round_to_tolerance, args=(tolerance,))
    ocr_res['y_rounded'] = ocr_res['y'].apply(round_to_tolerance, args=(tolerance,))

    home_screen = is_homescreen(ocr_res)
    groupchat_name = None
    if not home_screen:
        groupchat_name = get_groupchat_name(ocr_res)
    
    return {"is_home_screen" : home_screen, "groupchat_name" : groupchat_name}

