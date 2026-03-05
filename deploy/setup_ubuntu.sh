#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "请使用 sudo 运行：sudo bash deploy/setup_ubuntu.sh -d example.com -p /opt/image-share"
  exit 1
fi

DOMAIN=""
APP_DIR=""
APP_USER="image-share"
APP_PORT="8000"

usage() {
  cat <<EOF
用法:
  sudo bash deploy/setup_ubuntu.sh -d <domain> -p <app_dir> [-u app_user] [-P app_port]

示例:
  sudo bash deploy/setup_ubuntu.sh -d img.example.com -p /opt/image-share
EOF
}

while getopts ":d:p:u:P:h" opt; do
  case "$opt" in
    d) DOMAIN="$OPTARG" ;;
    p) APP_DIR="$OPTARG" ;;
    u) APP_USER="$OPTARG" ;;
    P) APP_PORT="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) echo "参数 -$OPTARG 需要值"; usage; exit 1 ;;
    \?) echo "未知参数: -$OPTARG"; usage; exit 1 ;;
  esac
done

if [[ -z "$DOMAIN" || -z "$APP_DIR" ]]; then
  usage
  exit 1
fi

if [[ ! -f "$APP_DIR/app.py" ]]; then
  echo "未找到 $APP_DIR/app.py，请确认项目路径正确"
  exit 1
fi

echo "[1/6] 安装依赖 (python3 + caddy)"
apt update
apt install -y python3 caddy

echo "[2/6] 创建运行用户"
id -u "$APP_USER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin "$APP_USER"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "[3/6] 写入 systemd 服务"
cat > /etc/systemd/system/image-share.service <<EOF
[Unit]
Description=Image Share Web App
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now image-share

echo "[4/6] 写入 Caddy 配置"
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    encode gzip
    reverse_proxy 127.0.0.1:$APP_PORT
}
EOF

echo "[5/6] 重启 Caddy"
systemctl enable caddy
systemctl restart caddy

echo "[6/6] 完成，检查状态"
systemctl --no-pager --full status image-share || true
systemctl --no-pager --full status caddy || true

echo "部署完成： https://$DOMAIN"
