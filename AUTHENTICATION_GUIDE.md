# 🔐 Threads 認證使用指南

## 概述

本抽獎工具現已支援 Threads 認證功能，可以存取需要登入的 Threads 內容。系統提供多種認證模式，包括手動登入、自動認證和靈活的用戶提示模式。

## 🎯 功能特點

- **🔒 安全認證**: 加密儲存登入狀態
- **🍪 Cookie 持久化**: 一次登入，重複使用
- **🔄 多種模式**: 支援自動、手動、提示等模式
- **⚡ 智能檢測**: 自動判斷是否需要認證
- **🛡️ 會話管理**: 自動處理過期和重新認證

## 📋 認證模式

### 1. PROMPT 模式（預設，推薦）
需要認證時提示用戶選擇，最靈活的方式。

### 2. MANUAL 模式
每次都進行互動式手動登入。

### 3. AUTO 模式
自動使用已儲存的 cookies，適合重複使用。

### 4. DISABLED 模式
完全禁用認證，只能存取公開內容。

## 🚀 快速開始

### 方法一：使用測試腳本

```bash
# 執行認證測試工具
python3 test_manual_auth.py
```

選擇 "手動認證測試"，然後：
1. 輸入要測試的 Threads 貼文網址
2. 在彈出的瀏覽器中完成登入
3. 系統會自動儲存登入狀態供未來使用

### 方法二：環境變數配置

創建 `.env` 檔案或設置環境變數：

```bash
# 認證模式設定
THREADS_AUTH_MODE=prompt          # prompt, manual, auto, disabled

# Cookie 儲存位置（可選）
THREADS_COOKIE_FILE=~/.lottery_web_cookies.json

# 會話超時時間（小時）
THREADS_SESSION_TIMEOUT=24

# 手動登入超時時間（秒）
THREADS_MANUAL_TIMEOUT=300
```

### 方法三：直接使用抽獎工具

在網頁中使用抽獎工具時：
1. 輸入需要認證的 Threads 網址
2. 如果需要認證，系統會自動提示
3. 選擇認證方式並完成登入
4. 之後的使用會自動載入已儲存的認證

## 💡 使用技巧

### 首次使用
1. 使用 `test_manual_auth.py` 進行首次登入
2. 成功登入後，cookies 會自動儲存
3. 之後使用抽獎工具會自動認證

### 認證狀態管理
```python
# 檢查認證狀態
python3 -c "
from src.main.python.auth import AuthManager
from src.main.python.config.auth_config import auth_config

auth_manager = AuthManager(auth_config)
print(auth_manager.get_auth_status())
"
```

### 清除儲存的認證
```python
# 清除 cookies
python3 -c "
from src.main.python.auth.cookie_storage import CookieStorage
from src.main.python.config.auth_config import auth_config

storage = CookieStorage(auth_config.cookie_file_path)
storage.clear_cookies()
print('已清除儲存的認證資訊')
"
```

## 🔧 進階配置

### 自定義 Cookie 加密
```bash
# 設置自定義加密金鑰
export THREADS_COOKIE_KEY="your_secret_key_here"
```

### 調整會話超時
```bash
# 設置 cookies 有效期（小時）
export THREADS_SESSION_TIMEOUT=48
```

### 程式中使用
```python
from src.main.python.config.auth_config import AuthConfig, AuthMode
from src.main.python.services.scrapers.selenium_threads_scraper import SeleniumThreadsScraper

# 設置認證模式
config = AuthConfig()
config.update_mode(AuthMode.AUTO)

# 使用帶認證的爬蟲
scraper = SeleniumThreadsScraper(headless=False)
comments = scraper.scrape_comments("https://www.threads.com/@username/post/...")
scraper.cleanup()
```

## ⚠️ 注意事項

### 安全性
- **Cookie 加密儲存**: 所有 cookies 都經過加密處理
- **本地儲存**: 認證資訊只存在本地電腦
- **會話管理**: 自動檢測過期並清理無效認證

### 合規性
- **個人使用**: 僅用於個人學習和測試目的
- **頻率限制**: 避免頻繁爬取以遵守服務條款
- **尊重政策**: 遵守 Meta/Threads 的使用政策

### 技術限制
- **需要 Chrome**: 需要安裝 Google Chrome 瀏覽器
- **網路要求**: 需要穩定的網路連線
- **動態變化**: Meta 可能更改認證機制

## 🔍 疑難排解

### 1. 認證失敗
```bash
# 清除舊的 cookies 並重新登入
python3 -c "
from src.main.python.auth.cookie_storage import CookieStorage
storage = CookieStorage('~/.lottery_web_cookies.json')
storage.clear_cookies()
print('請重新執行認證')
"
```

### 2. ChromeDriver 問題
```bash
# 清理 ChromeDriver 快取
rm -rf ~/.wdm
```

### 3. 權限問題
```bash
# 確保 Cookie 檔案可寫
chmod 600 ~/.lottery_web_cookies.json
```

### 4. 檢查日誌
爬蟲會輸出詳細的日誌信息，包括：
- 認證檢測結果
- Cookie 載入狀態
- 認證流程進度

## 📞 獲取協助

如遇到問題，請：
1. 檢查 Chrome 瀏覽器是否正確安裝
2. 確認網路連線正常
3. 查看終端輸出的錯誤訊息
4. 嘗試清除儲存的 cookies 重新認證

## 🎉 成功案例

認證成功後，您應該能夠：
- ✅ 存取需要登入的 Threads 貼文
- ✅ 爬取私人或限制性內容的留言
- ✅ 自動重用登入狀態
- ✅ 進行正常的抽獎流程

---

**💡 提示**: 首次使用建議先執行 `python3 test_manual_auth.py` 來熟悉認證流程。