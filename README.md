# lottery web

Threads/Instagram 抽獎網頁專案 - 基於 Flask 的網頁應用程式，支援從 Threads 和 Instagram 貼文留言中進行抽獎。

## Quick Start

1. **Read CLAUDE.md first** - Contains essential rules for Claude Code
2. Follow the pre-task compliance checklist before starting any work
3. Use proper module structure under `src/main/python/`
4. Commit after every completed task

## 專案概述

開發一個基於 Flask 的網頁應用程式，支援從 Threads 和 Instagram 貼文留言中進行抽獎。使用網頁爬蟲技術獲取留言資料，提供三種不同的抽獎模式，並支援將中獎結果匯出為 Excel 檔案。

## 功能特色

- 🎯 支援 Threads 和 Instagram 貼文抽獎
- 🎨 三種抽獎模式：關鍵字篩選、所有留言者、標註指定帳號
- 📊 Excel 匯出功能
- 🔄 自動識別平台類型
- 💻 響應式網頁設計

## 技術架構

- **後端框架**: Flask (Python)
- **前端技術**: HTML, CSS, JavaScript (原生)
- **爬蟲工具**: BeautifulSoup4, Selenium
- **Excel處理**: openpyxl 或 xlsxwriter
- **其他依賴**: requests, pandas

## 安裝說明

1. 克隆專案
```bash
git clone <repository-url>
cd lottery-web
```

2. 建立虛擬環境
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. 安裝依賴
```bash
pip install -r requirements.txt
```

4. 執行應用程式
```bash
python app.py
```

## 專案結構

```
lottery-web/
├── app.py                 # Flask 主程式
├── requirements.txt       # Python 依賴套件
├── config.py             # 配置檔案
├── src/                   # 源代碼
│   ├── main/
│   │   ├── python/       # Python 代碼
│   │   │   ├── core/     # 核心業務邏輯
│   │   │   ├── utils/    # 工具函式
│   │   │   ├── models/   # 數據模型
│   │   │   ├── services/ # 服務層
│   │   │   │   ├── scrapers/  # 爬蟲模組
│   │   │   │   └── lottery/   # 抽獎邏輯
│   │   │   └── api/      # API 端點
│   │   └── resources/    # 資源文件
│   └── test/             # 測試代碼
├── templates/            # HTML 模板
├── static/              # 靜態資源
└── output/              # 輸出文件

```

## 使用方式

1. 訪問網頁應用程式
2. 輸入 Threads 或 Instagram 貼文網址
3. 選擇抽獎模式
4. 設定相關參數（關鍵字、標註數量等）
5. 點擊「開始抽獎」
6. 查看中獎結果並可下載 Excel 檔案

## Development Guidelines

- **Always search first** before creating new files
- **Extend existing** functionality rather than duplicating  
- **Use Task agents** for operations >30 seconds
- **Single source of truth** for all functionality

## 注意事項

1. 爬蟲可能因平台更新而需要調整
2. 大量爬取可能被平台限制
3. 建議加入適當的延遲避免被封鎖
4. Instagram 可能需要登入才能獲取完整留言

## License

[Your License Here]

## Contributors

- Created with Claude Code
- Template by Chang Ho Chien | HC AI 說人話channel | v1.0.0