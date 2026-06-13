# LINE to Discord 内部処理の説明

本書は、`read_line_tsv.py` が **内部で何をしているか** を説明する技術メモです。
実際の操作手順は別紙
[LINE to Discord コピー手順.md](LINE%20to%20Discord%20%E3%82%B3%E3%83%94%E3%83%BC%E6%89%8B%E9%A0%86.md)
を参照してください。

---

## 対象スクリプト

`read_line_tsv.py` … LINE のメッセージデータ（TSV）を読み込み、添付ファイルと共に
Discord へ転送する本体スクリプト。

---

## 2 つの実行モード（フェーズ）

コマンドライン引数の**数**で動作が切り替わります。判定は内部変数 `file_folder`
（＝コマンドの `\<抽出先フォルダ\>`）の有無で行われます。

| モード | 引数 | `file_folder` | 動作 |
| --- | --- | --- | --- |
| **抽出モード** | 5 個（…payloads / folder / folder_cached） | フォルダ名あり | Discord に送信せず、メッセージ・添付をローカルフォルダへ**書き出す**だけ。 |
| **送信モード** | 3 個（…payloads まで） | `None` | Discord へ実際に**送信**し、メッセージ ID 対応表を保存する。 |

* `fire_message()` は `file_folder` がある（抽出モード）と、テキストは `<id>.json`、
  添付は `<id>_<ファイル名>` としてフォルダに保存するだけで、**送信は行わない**。
* `file_folder` が `None`（送信モード）のときだけ Webhook へ POST する。

---

## 全体の処理フロー

1. **設定読み込み（.ini）** … `token` / `webhook_url` / `target_group`（対象 groupId）
   / Discord の `server`・`channel`。
2. **マスター対応表の読み込み** … `output_message_pair_<target_group>.json` があれば
   `message_pair` に展開する。
3. **既存ファイルの索引化** … ペイロードフォルダ・キャッシュフォルダの一覧を取得し、
   **ファイル名の先頭 18 桁（= messageId）** をキーに探せるようにする。
4. **TSV 読み込み** … pandas で読み込み、各行 1 列目の JSON を展開する。
5. **メッセージ抽出** … 各 JSON の `events` から `message` を持つものを取り出す。
6. **重複排除と整列** … messageId 単位で重複を除き（後述）、時刻順に並べ替える。
7. **添付ファイルの実体収集** … image / file を `filestack` に集める。
8. **ユーザー情報の収集** … グループ発言者を `userstack` に集める。
9. **送信／書き出しループ** … メッセージごとに Discord 送信、または抽出モードでは
   ファイル書き出し。
10. **対応表の保存** … 送信モードでは 1 件ごとに途中経過（`_temp`）を上書きし、
    最後に確定版を保存する。

---

## 重複排除（デデュープ）

LINE の Webhook は同じメッセージを再送・重複することがあります。そのため：

* `messageId` を一意キーとして重複を排除する。
* 同じ messageId が複数あるときは **timestamp が新しいもの** を採用する。
* 最終的に **timestamp 昇順**（古い→新しい）に並べ替えてから処理する。

---

## 添付ファイルの取得（フォールバック順）

`filestack` の各 image / file について、次の順で実体を探します。

1. **キャッシュフォルダ**（`file_cached` など）に messageId 一致のファイルがあれば使う。
2. なければ **ペイロードフォルダ**（`all_payload_*`）を探す。
3. それも無ければ **LINE Content API** から取得（`fire_get_image()`）。
   API が 200 を返さない場合は、ペイロードフォルダ内の `<id>_image.jpg` を
   最終フォールバックとして読む。

> LINE は添付ファイルを一定期間で取得不能にするため、Google Drive 由来の
> キャッシュや過去ペイロードから補完できるようにしている。これが
> キャッシュフォルダ・ペイロードフォルダを用意する理由。

---

## ユーザー情報の取得

* `fire_get_user()` が `group/{groupId}/member/{userId}` を呼び、
  `displayName` と `pictureUrl` を解決する（取得済みは `userstack` に保持）。
* 退会済みなどで取得できない場合は、表示名として `userId` をそのまま使う。

---

## 引用（返信）リンクの解決

テキストメッセージに `quotedMessageId`（引用元）が含まれる場合：

1. 引用元の本文を、(a) 同じバッチの処理対象、または
   (b) 過去ペイロードの `*.json` から探す。
2. 引用元の messageId が `message_pair` に登録済みなら、対応する Discord
   メッセージへの URL を生成する。
   ```
   https://discord.com/channels/<server>/<channel>/<discord_message_id>
   ```
3. 引用元の抜粋（先頭 40 文字）とリンクを「参照元抜粋」ブロックとして本文の
   先頭に付けて送信する。
4. 引用元が古すぎて辿れない場合は「参照元が過去すぎて取得できません」と表示する。

---

## メッセージ ID 対応表（`message_pair`）の仕組み

引用リンクを貼るために、**LINE の messageId → Discord の messageId** の対応表を
保持します。

* **実行開始時**: マスター `output_message_pair_<groupId>.json` を読み込む。
* **送信のたび**: `message_pair[LINEのID] = DiscordのID` を記録する。
* **送信モードの逐次保存**: 1 件処理するごとに
  `output_message_pair_<groupId>_<日時>_temp.json` を上書き保存する（中断対策）。
* **完了時**: `output_message_pair_<groupId>_<日時>.json` を確定保存する。
* マスターへは**自動でマージされない**。次回実行で過去分の引用リンクを有効に
  するには、**手作業でマージ**する必要がある。

> ✅ 別紙「コピー手順」の **「ペア情報（JSON）ファイルのマージ」** が必要なのは、
> この「マスターへ自動マージしない」仕様のため。具体的なマージ手順・例は
> [LINE to Discord コピー手順.md](LINE%20to%20Discord%20%E3%82%B3%E3%83%94%E3%83%BC%E6%89%8B%E9%A0%86.md)
> を参照。

---

## 文字数制限の処理

Discord の 1 メッセージあたりの文字数に合わせて、2 段構えで対処しています。

* `fire_message()` 内: **1900 文字**を超えると単純に切り詰め、末尾に割愛注記を付ける
  （安全弁）。
* 送信ループ本体: **1800 文字**を超えるテキストは **1750 文字ごとにチャンク分割**し、
  複数メッセージとして送信する（各チャンクに分割注記を付与）。対応表には
  **先頭チャンクの Discord ID** を登録する。

---

## レート制御

送信ループでは 1 件ごとに `time.sleep(2)` を入れ、LINE / Discord API への
過剰なアクセスを避けている。

---

## 関連スクリプト

* `read_line_tsv_split_by_group.py` … 1 つの TSV を `groupId` ごとに分割する
  （グループ別に処理する前段）。
