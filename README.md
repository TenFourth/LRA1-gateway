# LRA1-gateway
LRA1で受け取ったデータをRaspberry Piで中継し、Webサーバーへ送るためのプログラムです

## 環境変数

設定値を環境変数にセットして動作を変更できます

### 送信先の設定

`HTTP_POST_URL` でデータの送信先を設定します

```例:
HTTP_POST_URL='http://localhost/upload.php'
```

### HTTP認証について

以下の環境変数をセットすれば、BASIC認証のヘッダを付与してデータを送信します

* HTTP_POST_USER
* HTTP_POST_PASSWORD
