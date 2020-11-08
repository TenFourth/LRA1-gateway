# LRA1-gateway
LoRaモジュール(LRA1)で受け取ったデータをRaspberry Piで中継し、Webサーバーへ送るためのプログラムです

## インストール

スクリプトファイル(lra1-gateway.py)を `/usr/local/sbin` へコピーします

```shell
$ sudo cp ./sbin/lra1-gateway.py /usr/local/sbin
```

SystemdのUnitファイルを `/etc/systemd/system` へコピーします。コピーしたらUnitをreloadし、自動起動を有効にします

```shell
$ sudo cp ./etc/systemd/system/lra1-gateway.service /etc/systemd/system
$ sudo systemctl daemon-reload
$ sudo systemctl enable lra1-gateway.service
```

設定ファイルを `/usr/local/etc` へコピーします。必要に応じて設定内容を変更してください

```shell
$ sudo cp ./etc/lra1-gateway.conf /usr/local/etc
```

## 環境変数

設定値を環境変数にセットして動作を変更できます。Systemdから起動する場合は `/usr/local/etc/lra1-gateway.conf` を変更します

### 送信先の設定

`HTTP_POST_URL` でデータの送信先を設定します。受け取ったLRA1のデータを転送する際のURLです

```例:
HTTP_POST_URL='http://localhost/upload.php'
```

### HTTP認証について

以下の環境変数をセットすれば、BASIC認証のヘッダを付与してデータを送信します。認証が不要な場合は空のままにします

* HTTP_POST_USER
* HTTP_POST_PASSWORD

### LoRaモジュールの設定

| 設定名 | 説明 |
|-------|------|
| LRA1_SERIAL_DEV | 通信ポートのパスを指定します (例: /dev/ttyS0) |
| LRA1_SERIAL_BAUD | シリアル通信のボーレートを指定します |
| LRA1_SERIAL_TIMEOUT | 指定した時間(秒数)データが来ない時に、BREAK信号を送って待ち受け状態をやり直します |
| LRA1_ENABLE_DISPLAY | LRA1評価ボードに搭載のLCDディスプレイにメッセージを表示するようにします |
