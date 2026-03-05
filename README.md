# 图片共享网页

这是一个可上传本地图片、并让所有访问者都能浏览的网页。

## 一、本地运行（开发/体验）

```bash
python3 app.py
```

浏览器打开：`http://localhost:8000`

---

## 二、如何变成“真实网页”（公网可访问）

下面是最实用的一套流程：**云服务器 + 域名 + Caddy(自动 HTTPS) + systemd 守护进程**。

### 1) 准备一台云服务器

推荐系统：Ubuntu 22.04/24.04。确保服务器安全组放通：

- `22`（SSH）
- `80`（HTTP）
- `443`（HTTPS）

### 2) 把代码上传到服务器

方式一：`git clone`

```bash
git clone <你的仓库地址> image-share
cd image-share
```

方式二：直接复制项目目录到服务器。

### 3) 启动并验证应用

```bash
python3 app.py
```

在服务器上本地验证：

```bash
curl http://127.0.0.1:8000
```

看到 HTML 即表示服务正常。

### 4) 配置域名解析

在域名服务商后台添加 `A` 记录：

- 主机记录：`@`（或 `www`）
- 记录值：你的云服务器公网 IP

等待 DNS 生效（通常几分钟到几十分钟）。

### 5) 用 Caddy 暴露公网并自动申请 HTTPS

安装 Caddy（Ubuntu）：

```bash
sudo apt update
sudo apt install -y caddy
```

复制仓库里的模板并替换域名：

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/your-domain.com/你的域名/g' /etc/caddy/Caddyfile
```

启动/重启 Caddy：

```bash
sudo systemctl restart caddy
sudo systemctl enable caddy
```

现在可通过：`https://你的域名` 访问。

### 6) 让 Python 服务后台常驻（开机自启）

创建专用用户（可选但推荐）：

```bash
sudo useradd -r -s /usr/sbin/nologin image-share || true
sudo chown -R image-share:image-share /path/to/image-share
```

安装 systemd 服务：

```bash
sudo cp deploy/image-share.service /etc/systemd/system/image-share.service
sudo sed -i 's#/path/to/image-share#你的实际项目路径#g' /etc/systemd/system/image-share.service
sudo systemctl daemon-reload
sudo systemctl enable --now image-share
```

查看运行状态：

```bash
sudo systemctl status image-share
```

查看日志：

```bash
journalctl -u image-share -f
```

---

## 三、生产建议（强烈推荐）

- 把 `uploads/` 挂载到独立磁盘或定期备份（防止误删/丢盘）。
- 定期清理超大或违规图片，避免磁盘打满。
- 若用户较多，建议后续升级：
  - 图片对象存储（S3/OSS/COS）
  - CDN 加速
  - 更完整的鉴权与审核机制
- 当前示例适合小型项目/学习演示；正式商用建议使用成熟 Web 框架与更完整安全策略。

---

## 四、功能

- 上传图片（png/jpg/jpeg/gif/webp，最大 10MB）
- 自动生成唯一文件名，避免覆盖
- 所有人都可在首页看到已上传图片


## 五、一键部署（Ubuntu）

如果你已经有：
- 一台 Ubuntu 服务器
- 一个已解析到服务器公网 IP 的域名
- 项目代码目录（含 `app.py`）

可直接执行：

```bash
sudo bash deploy/setup_ubuntu.sh -d 你的域名 -p 你的项目路径
```

例如：

```bash
sudo bash deploy/setup_ubuntu.sh -d img.example.com -p /opt/image-share
```

脚本会自动完成：
- 安装 `python3` 与 `caddy`
- 创建运行用户
- 写入并启动 `systemd` 服务
- 写入 Caddy 反向代理配置并开启 HTTPS

部署后访问：`https://你的域名`
