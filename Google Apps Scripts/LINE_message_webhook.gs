/**
* @OnlyCurrentDoc
*/
const SHEET_NAME = 'record_log'

// 一行分のデータを受け取って、シート末尾に記録する
function addRecord(records = []) {
    const ss = SpreadsheetApp.getActiveSpreadsheet()
    const sheet = ss.getSheetByName(SHEET_NAME);
    // 最終行の一行下に追記
    const lastRow = sheet.getLastRow() + 1;
    if (records.length == 0){
      return;
    }
    console.log(lastRow,records.length);
    console.log(records)
    const range = sheet.getRange(lastRow, 1, 1, records.length)
    range.setValues([records])
}

// POSTリクエストに対する処理
function doPost(e) {
  // データが空なら処理しない
  if (e == null || e.postData == null || e.postData.contents == null) return;

  // リクエストを受け取ってオブジェクト化
  const requestJSON = e.postData.contents;
  console.log(requestJSON);
  addRecord([requestJSON]);
  // const requestObj = JSON.parse(requestJSON);

  // // 以降は LINE Messaging API の仕様に準じた処理
  // const events = requestObj.events;
  // // events は配列で渡ってくるので、繰り返し処理する
  // events.forEach((event) => {
  //   // メッセージイベントのみ受け付ける
  //   if (event.type !== 'message') return;
  //   const message = event.message;
  //   // テキスト入力のみ受け付ける
  //   if (message.type !== 'text') return;

  //   // 記録するデータを取得
  //   const datetime = new Date();
  //   const userId = event.source.userId;
  //   const text = message.text;

  //   const records = [datetime, userId, text];

  //   // スプレッドシートに記載
  //   addRecord(records);
  // })
}