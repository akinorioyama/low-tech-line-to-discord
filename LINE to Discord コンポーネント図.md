# LINE to Discord コンポーネント図

LINE のメッセージ投稿から Discord への投稿までの、構成要素（コンポーネント）と
データの流れを左から右へ示した図です。

![LINE to Discord コンポーネント図](LINE%20to%20Discord%20%E3%82%B3%E3%83%B3%E3%83%9D%E3%83%BC%E3%83%8D%E3%83%B3%E3%83%88%E5%9B%B3.svg)

> 図ファイル: [`LINE to Discord コンポーネント図.svg`](LINE%20to%20Discord%20%E3%82%B3%E3%83%B3%E3%83%9D%E3%83%BC%E3%83%8D%E3%83%B3%E3%83%88%E5%9B%B3.svg)
> （ブラウザで開く・ダウンロード・画像への変換が可能な単独の SVG ファイル）

---

## 4 つのステージ（左 → 右）

| ステージ | 主なコンポーネント | 役割 |
| --- | --- | --- |
| **① LINE** | LINEメッセージ / LINE API | グループ投稿（文・画像・ファイル）。Messaging API が Webhook を送り、Content API が添付の実体を返す。 |
| **② Google（GAS）** | `LINE_message_webhook.gs` / スプレッドシート `record_log` / `DownloadFiles.gs` / Google Drive | Webhook の生 JSON をシートに蓄積し、時間トリガーで添付を Drive に保存（ファイル名＝messageId）。 |
| **③ ローカル（Python）** | TSV(`Line record`) / `split_by_group.py` / `read_line_tsv.py`（抽出①・送信②）/ `message_pair` | シートを TSV 化 → グループ分割 → 抽出フェーズでキャッシュ準備 → 送信フェーズで Discord へ。`message_pair`（ID対応表）を参照・更新。 |
| **④ Discord** | Discord Webhook / Discord チャンネル | Webhook 経由で実際にメッセージと添付を投稿。 |

**線の凡例:** 実線＝自動処理、破線＝手作業（スプレッドシートの TSV 出力、Drive からのダウンロード）。

---

## 関連ドキュメント

* セットアップ（GAS 側）:
  [LINEからGoogle Apps Scripts連携 セットアップ手順.md](LINE%E3%81%8B%E3%82%89Google%20Apps%20Scripts%E9%80%A3%E6%90%BA%20%E3%82%BB%E3%83%83%E3%83%88%E3%82%A2%E3%83%83%E3%83%97%E6%89%8B%E9%A0%86.md)
* 運用手順（Python 側）:
  [LINE to Discord コピー手順.md](LINE%20to%20Discord%20%E3%82%B3%E3%83%94%E3%83%BC%E6%89%8B%E9%A0%86.md)
* 内部処理の説明:
  [LINE to Discord 内部処理の説明.md](LINE%20to%20Discord%20%E5%86%85%E9%83%A8%E5%87%A6%E7%90%86%E3%81%AE%E8%AA%AC%E6%98%8E.md)
