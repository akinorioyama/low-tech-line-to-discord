function saveFilesToDrive() {
  const SPREAD_SHEET_ID = '<SPREAD_SHEET_ID>'
  const SHEET_NAME = '<SHEET_NAME>'
  const ss = SpreadsheetApp.openById(SPREAD_SHEET_ID);
  const sheet = ss.getSheetByName(SHEET_NAME);
  var gFolder = '<SAVE_FOLDER_ID>'
  var folder  = DriveApp.getFolderById(gFolder);
  var folder_files = folder.getFiles();
  var file_list = []
while (folder_files.hasNext()) {
  var file = folder_files.next();
  var filename = file.getName()
  if (file_list.includes(filename)) {
    continue
  }
  file_list.push(filename)
}
  const lastRow = sheet.getLastRow() + 1;
  if (lastRow == 1){
    return;
  }
  const range = sheet.getRange(1,1,lastRow,1)
  const range_values = range.getValues()
  const bearer_string = "<BEARER STRING>"
  var header_items = {
        "Authorization": "Bearer " + bearer_string ,
                  };
const options = {
  'method': 'GET',
  'headers': header_items,
  'followRedirects': false,
  'muteHttpExceptions': false,
  'muteHttpExceptions': true,
  'timeout': 30
}
   for (var i=0; i<range_values.length; i++) {
    try {
      console.log(i);
      let message_obj = JSON.parse(range_values[i]);
      var message_id = message_obj['events'][0]['message']['id']
      var message_type = message_obj['events'][0]['message']['type']
      if (file_list.includes(message_id)) {
        continue
      }
      if (message_type != "image" && message_type != "file" ){
        continue;
      }

      var fileURL = "https://api-data.line.me/v2/bot/message/"+ message_id + "/content"
      console.log(options)
      let response_ret = UrlFetchApp.fetch(fileURL, options);
      var code = response_ret.getResponseCode();
      if (code == '200'){
        var res_content = response_ret.getContent();
        var res_content_blob = response_ret.getBlob();

        var file_temp = folder.createFile(res_content_blob);
        file_temp.setName(message_id)
        file_list.push(message_id)
        console.log("create file"+message_id)
      }
    } catch(e) {
      console.log(e)
    }

      }
}