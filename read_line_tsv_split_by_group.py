import argparse
import json
import csv
import datetime
import os


def split_tsv_by_group(input_filepath):
    """
    LINEのメッセージが含まれるTSVファイルを、groupIdごとに分割する関数
    """
    # タイムスタンプとベースファイル名の取得
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]

    file_handles = {}
    writers = {}

    print(f"[{input_filepath}] の分割処理を開始します...")

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile, delimiter='\t')

            for line_number, row in enumerate(reader, 1):
                if not row:
                    continue

                try:
                    # 1列目のデータをJSONとして読み込む
                    data = json.loads(row[0])
                    group_id = "individual_or_unknown"  # デフォルト値

                    # events配列の中からgroupIdを探す
                    for event in data.get('events', []):
                        source = event.get('source', {})
                        if source.get('type') == 'group':
                            group_id = source.get('groupId')
                            break  # 最初のグループIDを見つけたらループを抜ける

                    # 新しいgroupIdを見つけた場合、新規ファイルを作成
                    if group_id not in file_handles:
                        out_filename = f"{base_name}_{timestamp}_{group_id}.tsv"
                        # 改行コードの自動変換を防ぐため newline='' を指定
                        f = open(out_filename, 'w', encoding='utf-8', newline='')
                        file_handles[group_id] = f
                        writers[group_id] = csv.writer(f, delimiter='\t')
                        print(f"新規ファイル作成: {out_filename}")

                    # 該当するファイルに行を書き込む
                    writers[group_id].writerow(row)

                except json.JSONDecodeError:
                    print(f"行 {line_number} のJSONパースに失敗したためスキップします。")
                    continue

    finally:
        # 開いているすべてのファイルを確実に閉じる
        for f in file_handles.values():
            f.close()

    print("分割処理が完了しました！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="LINEのTSVデータをgroupIdごとに分割します。")
    parser.add_argument("input_file", help="分割したい元のTSVファイルパス")

    args = parser.parse_args()

    if os.path.exists(args.input_file):
        split_tsv_by_group(args.input_file)
    else:
        print(f"エラー: ファイル '{args.input_file}' が見つかりません。")