"""
Read LINE record file to send the data to Discord server or to a local file system

Usage:
  read_line_tsv.py <configfile> <textfile> <folder_payloads> <folder> <folder_cached>
  read_line_tsv.py <configfile> <textfile> <folder_payloads>

  <configfile>: path to the target-specific .ini file
  <textfile>: file in which LINE data is stored
  <folder_payloads>: file folder where past payloads are stored
  <folder>: file folder where data is extracted
            (folder is used for the first of two phases of sending data)
  <folder_cached>: file folder where data is cached
            (folder is used to supplement images and files, which might be archived)

Examples:
  1.. read_line_tsv.py "config_a.ini" "line_2024.tsv" All_Payloads LINE_2024 LINE_CACHE
  2.. read_line_tsv.py "config_a.ini" "line_2024.tsv" All_Payloads

  The first example structure is to download
    the relevant messages and files to the target folder
  THe second example is to send data to the discord server
    that is directed in the configuration file.

"""
from docopt import docopt
import configparser

# coding: utf-8
import time
import http
import pandas as pd
import json
import requests
import urllib.parse
from requests.utils import requote_uri
from io import BytesIO
import os
import datetime

def fire_get_user(group_id,id):

    fileURL = f"https://api.line.me/v2/bot/group/{group_id}/member/{id}"
    response = requests.get(
        url=fileURL,
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30.0,
    )
    return response.json()

def fire_get_image(id, folder_all_past_payload):
    fileURL = f"https://api-data.line.me/v2/bot/message/{id}/content"
    response = requests.get(
        url=fileURL,
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30.0,
    )
    # for missing files, loook for the saved files
    if response.status_code != 200:
        file = os.path.join(folder_all_past_payload,id+"_image.jpg")
        if (os.path.exists(file) == True):
            with open(file, 'rb') as file_object:
                return file_object.read()

    return response.content

def fire_message(line_message,username, encoded_image_byte="",image_filename="",
                 displayName = "", pictureUrl = "",
                 file_folder=""):
    if file_folder != None:
        if (os.path.exists(file_folder) == False):
            os.mkdir(file_folder)
    if len(line_message) > 1900:
        line_message = line_message[0:1900] + "\n==== 1900文字を超えたため、割愛されています。====\n====全文を確認ください===="

    if image_filename != "":
        files = {
            "attachment": ( requote_uri(image_filename), encoded_image_byte)
        }

        params = {
            "payload_json": json.dumps(
                {
                    "username": f"{displayName}(username)",
                    "avatar_url": pictureUrl,
                    "content": f"{line_message}\n{image_filename}",
                    "tts": False,
                },ensure_ascii=False
            )
        }

    else:
        params = {
            "payload_json": json.dumps(
                {
                    "username": f"{displayName}(username)",
                    "avatar_url": pictureUrl,
                    "content": line_message,
                    "tts": False,
                }
            ,ensure_ascii=False)
        }
    url_params = {"wait":True}
    response_id = None
    if image_filename != "":
        if file_folder != None:
            file_path = f"{id}_" + image_filename
            file_path = os.path.join(file_folder,file_path)
            with open(file_path, 'wb') as file:
                file.write(encoded_image_byte)
        else:
            response = requests.post(
                url=webhookURL,
                params=url_params,
                data=params,
                files=files,
                headers={},
                timeout=30.0,
            )
            response.raise_for_status()
            webhook_res = response.json()
            response_id = webhook_res['id']
            # print(webhook_res, end="")

    else:
        if file_folder != None:
            file_path = f"{id}.json"
            file_path = os.path.join(file_folder, file_path)
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(json.dumps(params, ensure_ascii=False))
        else:
            response = requests.post(
                url=webhookURL,
                params=url_params,
                data=params,
                headers={},
                timeout=30.0,
            )

            response.raise_for_status()
            webhook_res = response.json()
            response_id = webhook_res['id']

    return response_id

if __name__ == '__main__':

    arguments = docopt(__doc__, version="0.1")
    config_file = arguments["<configfile>"]
    input_filename = arguments["<textfile>"]
    folder_all_past_payload = arguments["<folder_payloads>"]
    file_folder = arguments["<folder>"]
    file_cache_folder = arguments["<folder_cached>"]

    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf8')
    token = config['token']['token']
    webhookURL = config['webhook']['webhook_url']
    targetGroup = config['LINE']['target_group']
    target_discord_server = config['discord']['server']
    target_discord_channel = config['discord']['channel']

    http.client.HTTPSConnection.debuglevel = 1

    # constant filename to read existing reference to the posted messageIDs
    message_pair = {}
    file_path = f"output_message_pair_{targetGroup}.json"
    if (os.path.exists(file_path) == True):
        with open(file_path, 'r', encoding='utf-8') as file:
            file_data_message_pair = json.load(file)
            if len(file_data_message_pair.keys()) > 0:
                message_pair = file_data_message_pair

    # folder_all_past_payload is defined via command-line argument <folder_payloads>
    files = os.listdir(folder_all_past_payload) if os.path.exists(folder_all_past_payload) else []
    all_payload_files = [[f[:18],f]for f in files]

    files = os.listdir(file_cache_folder) if file_cache_folder else []
    all_cached_files = [[f[:18],f]for f in files]

    datetime_string = datetime.datetime.now().strftime("%Y%m%d %H%M%S")
    datetime_string.replace(":","-")
    df_load = pd.read_csv(delimiter="\t", filepath_or_buffer=input_filename, header=None)

    jsoned_data = [json.loads(a) for a in df_load[0]]

    list_of_messages = [[l1, l3['type'], l3['message']['type'], l3['message']['id'], l3['message'], l3['source'],l3['timestamp']] for
                        l1, l2, l3, l4 in
                        [[index, len(row['events']), event, row] for index, row in enumerate(jsoned_data) for event in
                         row['events']] if 'message' in l3]
    filestack = []
    userstack = []
    list_of_messages = list(pd.DataFrame(list_of_messages, columns=["a", "b", "c", "d", "e", "f","g"]).drop_duplicates(subset=["d"],
                                                                                                keep="last").sort_values("g").values)

    for line_number, string_of_message, type_of_message,id,value_of_message, source,timestamp in list_of_messages:

        print(line_number,value_of_message['id'],string_of_message,type_of_message,id, end="")

        if type_of_message == "text":
            if 'quotedMessageId' in value_of_message:
                print("\t",value_of_message['text'].replace("\n","-n"),value_of_message['quotedMessageId'])
            else:
                print("\t",value_of_message['text'].replace("\n","-n"))
                # fire_message(value_of_message['text'],source['userId'])
        elif type_of_message == "image":
            print("\t", "image", value_of_message['id'])
            filestack.append([type_of_message,value_of_message['id'],"image.jpg"])
        elif type_of_message == "file":
            print("\t","file",value_of_message['id'],value_of_message['fileName'])
            filestack.append([type_of_message,value_of_message['id'],value_of_message['fileName']])
        if 'group' in source['type']:
            print("\t",'group',source['groupId'], source['userId'])
            if not ( source['userId'] in [a[1] for a in userstack]):
                userstack.append([source['groupId'],source['userId']])
        else:
            print("\t", 'individual', source['userId'])

    for index,( type_name, id, filename) in enumerate(filestack):

        #get file data first, instead of retrieving from LINE via API
        found_binary = []
        file = ""
        found_file_in_cache = [b for b in all_cached_files if b[0] == id]
        found_file_in_all = [b for b in all_payload_files if b[0] == id]
        if len(found_file_in_cache) != 0:
            file_id, filename = found_file_in_cache[0]
            file = os.path.join(file_cache_folder,filename)
        elif len(found_file_in_all) != 0:
            file_id, filename = found_file_in_all[0]
            # file = os.path.join(folder_all_past_payload,id+"_image.jpg")
            file = os.path.join(folder_all_past_payload,filename)
        if file != "":
            if (os.path.exists(file) == True):
                with open(file, 'rb') as file_object:
                    found_binary = file_object.read()

        if found_binary != []:
            filestack[index].append(found_binary)
        else:
            file_binary = fire_get_image(id, folder_all_past_payload)
            filestack[index].append(file_binary)

    for index,( group_id, id) in enumerate(userstack):
        user_json = fire_get_user(group_id,id)
        userstack[index].append(user_json)

    for loop_count, (line_number, string_of_message, type_of_message,id,value_of_message, source, timestamp) in enumerate(list_of_messages):
        print(f"\r{loop_count} of total {len(list_of_messages)}", end="")
        message_time = datetime.datetime.fromtimestamp( timestamp / 1000).strftime("%Y/%m/%d %H:%M:%S")
        time.sleep(2)
        displayName = ""
        pictureUrl  = ""
        spacer_text = "================"
        if not ('type' in source):
            continue
        if not source['type'] == "group":
            continue
        if targetGroup != None and targetGroup != "":
            if not source['groupId'] in [targetGroup]:
                continue

        for (group_id,user_id,user_json) in [b for b in userstack if b[1] == source['userId']]:
            #error after user is removed
            if 'displayName' in user_json:
                displayName = user_json['displayName']
            else:
                displayName = source['userId']
            if 'pictureUrl' in user_json:
                pictureUrl = user_json['pictureUrl']
        if type_of_message in ["image","file","video"]:
            if id in [a[1] for a in filestack]:
                filestack_line = [b for b in filestack if b[1] == id]
                sending_lines = f"=\n\nID:{id} / {message_time} / {spacer_text}\n"
                # sending_lines += filestack_line[0][2]
                post_message_id = fire_message(sending_lines,source['userId'],encoded_image_byte=filestack_line[0][3],image_filename=filestack_line[0][2],displayName=displayName,pictureUrl=pictureUrl,file_folder=file_folder)
                message_pair[id] = post_message_id
        elif type_of_message == "sticker":
            sending_lines = (f"=\n\nID:{id} / {message_time} / {spacer_text}\n==(sticker)==\n"
                          + value_of_message['stickerId'] + "\n==(sticker)==\n")
            post_message_id = fire_message(sending_lines,source['userId'],displayName=displayName,pictureUrl=pictureUrl,file_folder=file_folder)
            message_pair[id] = post_message_id
        else:
            quotedMessageId = ""
            preceding_text = "参照元が過去すぎて取得できません"
            sending_lines = f"=\n\nID:{id} / {message_time} / {spacer_text}\n" + value_of_message['text']
            if 'quotedMessageId' in value_of_message:
                quotedMessageId = value_of_message['quotedMessageId']
                if value_of_message['quotedMessageId'] in [a[3] for a in list_of_messages]:
                    value_line = [a for a in list_of_messages if a[3] == value_of_message['quotedMessageId']][0]
                    if value_line[4]['type'] == "text":
                        preceding_text = value_line[4]['text']
                else:
                    for messageid_in_payload,messageid_filename in all_payload_files:
                        if messageid_in_payload == quotedMessageId:
                            if messageid_filename[-4:] == "json":
                                with open(os.path.join(folder_all_past_payload,messageid_filename), 'r', encoding='utf-8') as file:
                                    file_message_from_payload = json.load(file)
                                preceding_text = json.loads(file_message_from_payload['payload_json'])['content']

                # 参照元ID と リンク
                reply_id = None
                if quotedMessageId in message_pair.keys():
                    reply_id = message_pair[quotedMessageId]
                    sending_lines = (f"=\n\nID:{id} / {message_time} / {spacer_text}\n==(参照元抜粋開始)==\n"
                                     f"参照元ID:{quotedMessageId}/https://discord.com/channels/{target_discord_server}/{target_discord_channel}/{reply_id}\n"
                                     f"> {preceding_text[0:40]}\n==(参照元抜粋終了)==\n\n") + value_of_message['text']
                else:
                    sending_lines = (f"=\n\nID:{id} / {message_time} / {spacer_text}\n==(参照元抜粋開始)==\n"
                                     f"参照元ID:{quotedMessageId}\n"
                                     f"> {preceding_text[0:40]}\n==(参照元抜粋終了)==\n\n") + value_of_message['text']

            def chunk_for_discord(text, limit=1750):
                """Yields chunks of text for Discord messages."""
                for i in range(0, len(text), limit):
                    yield text[i:i + limit]

            if len(sending_lines) < 1800:
                post_message_id = fire_message(sending_lines, source['userId'], displayName=displayName,
                                               pictureUrl=pictureUrl, file_folder=file_folder)
                message_pair[id] = post_message_id
            else:
                chunks = [a for a in chunk_for_discord(sending_lines)]
                chunk_number = len(chunks)
                for i, chunk in enumerate(chunks):
                    chunk = (f"\n==== LINEメッセージが1800文字を超えたため、分割されています。(開始)====\n({i+1}件/全体{chunk_number}件)\n" +
                             chunk + "\n==== LINEメッセージが1800文字を超えたため、分割されています。(終了)====")
                    post_message_id = fire_message(chunk, source['userId'], displayName=displayName,
                                                   pictureUrl=pictureUrl, file_folder=file_folder)
                    if i == 0:
                        message_pair[id] = post_message_id

        # message_pair[id] = post_message_id
        if file_folder == None:
            jsonified_message_list= json.dumps(message_pair)
            file_path = f"output_message_pair_{targetGroup}_{datetime_string}_temp.json"
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(jsonified_message_list)

    if file_folder == None:
        jsonified_message_list= json.dumps(message_pair)
        file_path = f"output_message_pair_{targetGroup}_{datetime_string}.json"
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(jsonified_message_list)