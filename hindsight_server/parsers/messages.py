import sys
import pandas as pd

sys.path.insert(0, "../")
import utils

tolerance = 20
def round_to_tolerance(value, tolerance):
    return round(value / tolerance) * tolerance

def is_homescreen(ocr_res):
    found_box = ocr_res.loc[(ocr_res['text'] == "Messages") & (ocr_res['x_rounded'] >= 180) & (ocr_res['x_rounded'] <= 195)
                            & (ocr_res['y_rounded'] == 195)]

    if len(found_box) > 0:
        return True
    return False

def get_groupchat_name(ocr_res):
    groupchat_name_box = ocr_res.loc[(ocr_res['x_rounded'] >= 255) & (ocr_res['x_rounded'] <= 270) & (ocr_res['y_rounded'] == 195)]
    if len(groupchat_name_box) > 0:
        return groupchat_name_box.iloc[0]['text']
    return None

keyboard_text_boxes = {'a': (90, 1830),
                        'V': (525, 1980),
                        'b': (630, 1965),
                        'n': (735, 1980),
                        'm': (825, 1980),
                        'k': (840, 1815),
                        'e': (255, 1665),
                        'j': (735, 1800),
                        't': (465, 1665),
                        'W': (135, 1665),
                        'h': (630, 1815),
                        'u': (675, 1665),
                        'g': (525, 1830),
                        'r': (360, 1680),
                        'S': (195, 1830),
                        'SMS': (975, 1425),
                        'f': (420, 1800)}
keyboard_y_min = 1240
def detect_keyboard(ocr_res, found_threshold=0.8):
    ocr_res['x_rounded'] = ocr_res['x'].apply(round_to_tolerance, args=(tolerance,))
    ocr_res['y_rounded'] = ocr_res['y'].apply(round_to_tolerance, args=(tolerance,))
    keyboard_boxes_found = list()
    for t, (x_rounded, y_rounded) in keyboard_text_boxes.items():
        found_box = ocr_res.loc[(ocr_res['text'] == t) & (ocr_res['x_rounded'] == x_rounded) 
                                & (ocr_res['y_rounded'] == y_rounded)]
        if len(found_box) == 1:
            keyboard_boxes_found.append(t)
    return (len(keyboard_boxes_found) / len(keyboard_text_boxes)) >= found_threshold

def get_from_non_groupchat(row, chat_name):
        if row['x_rounded'] != 60:
            return "Myself"
        else:
            return chat_name

def parse_messages_ocr_results(ocr_res):
    ocr_res['x_rounded'] = ocr_res['x'].apply(round_to_tolerance, args=(tolerance,))
    ocr_res['y_rounded'] = ocr_res['y'].apply(round_to_tolerance, args=(tolerance,))

    home_screen = is_homescreen(ocr_res)
    if home_screen:
        return {"is_home_screen" : home_screen, "groupchat_name" : None}
    
    groupchat_name = get_groupchat_name(ocr_res)

    y_min = 300
    y_max = keyboard_y_min if detect_keyboard(ocr_res) else 2130
    ocr_res = ocr_res.loc[(ocr_res['y'] >= y_min) & (ocr_res['y'] <= y_max)]
    if len(ocr_res) == 0:
        return {"is_home_screen" : home_screen, "groupchat_name" : None}
    ocr_res['text_size'] = ocr_res.apply(lambda row:  row['w'] / len(row['text']), axis=1)

    texts_ocr_res = ocr_res.loc[ocr_res['text_size'] >= 18]
    texts_ocr_res = utils.add_sep_ids(texts_ocr_res, new_threshold=20, var_name="text_id")

    texts_agged_df = texts_ocr_res.groupby(['text_id']).agg(x=("x", pd.Series.min), y=("y", pd.Series.min), 
                                                        x_rounded=("x_rounded", pd.Series.min), y_rounded=("y_rounded", pd.Series.min),
                                                        text=("text", " ".join))

        
    return {"is_home_screen" : home_screen, "groupchat_name" : groupchat_name}