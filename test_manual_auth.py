#!/usr/bin/env python3
"""
測試 Threads 手動認證功能
此腳本展示如何使用互動式登入來認證 Threads 帳戶
"""
import sys
import os
sys.path.append(os.getcwd())

from src.main.python.config.auth_config import AuthConfig, AuthMode
from src.main.python.services.scrapers.selenium_threads_scraper import SeleniumThreadsScraper


def test_manual_authentication():
    """測試手動認證功能"""
    
    print("🔐 Threads 手動認證測試")
    print("=" * 50)
    
    # 設置手動認證模式
    config = AuthConfig()
    config.update_mode(AuthMode.MANUAL)
    
    print(f"📋 認證模式: {config.auth_mode.value}")
    print(f"📁 Cookie 儲存位置: {config.cookie_file_path}")
    print()
    
    # 測試網址（使用者可以替換成自己想測試的網址）
    test_url = input("請輸入要測試的 Threads 貼文網址（或按 Enter 使用預設）: ").strip()
    if not test_url:
        test_url = "https://www.threads.com/@threads/post/C-hGtjvOl_k"  # Threads 官方帳號的貼文
    
    print(f"🌐 測試網址: {test_url}")
    print()
    
    try:
        # 創建爬蟲（非無頭模式以便手動登入）
        print("🚀 啟動 Selenium 瀏覽器...")
        scraper = SeleniumThreadsScraper(
            headless=False,  # 顯示瀏覽器視窗以便手動登入
            timeout=30
        )
        
        print("✅ 瀏覽器啟動成功")
        print()
        
        # 嘗試爬取留言（會觸發認證流程）
        print("📝 開始爬取留言...")
        comments = scraper.scrape_comments(test_url)
        
        print(f"🎉 成功爬取 {len(comments)} 條留言！")
        
        # 顯示前幾條留言作為示例
        if comments:
            print("\\n📋 留言預覽:")
            for i, comment in enumerate(comments[:5], 1):
                print(f"  {i}. @{comment.username}: {comment.content[:100]}...")
        
        # 檢查認證狀態
        auth_status = scraper.auth_manager.get_auth_status()
        print(f"\\n🔐 認證狀態: {auth_status}")
        
        # 清理
        scraper.cleanup()
        print("\\n✅ 測試完成，瀏覽器已關閉")
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cookie_persistence():
    """測試 Cookie 持久化功能"""
    
    print("\\n🍪 Cookie 持久化測試")
    print("=" * 30)
    
    # 檢查是否有已儲存的 cookies
    config = AuthConfig()
    
    from src.main.python.auth.cookie_storage import CookieStorage
    cookie_storage = CookieStorage(config.cookie_file_path)
    
    cookie_info = cookie_storage.get_cookie_info()
    
    if cookie_info:
        print("✅ 發現已儲存的 cookies:")
        print(f"   網域: {cookie_info['domain']}")
        print(f"   儲存時間: {cookie_info['saved_at']}")
        print(f"   Cookie 數量: {cookie_info['cookie_count']}")
        print(f"   是否過期: {cookie_info['expired']}")
        
        if not cookie_info['expired']:
            print("\\n🔄 測試自動認證...")
            
            # 設置自動認證模式
            config.update_mode(AuthMode.AUTO)
            
            test_url = "https://www.threads.com/@threads/post/C-hGtjvOl_k"
            
            try:
                scraper = SeleniumThreadsScraper(headless=True, timeout=20)
                comments = scraper.scrape_comments(test_url)
                
                print(f"✅ 自動認證成功！爬取了 {len(comments)} 條留言")
                scraper.cleanup()
                
            except Exception as e:
                print(f"❌ 自動認證失敗: {e}")
        else:
            print("⚠️  儲存的 cookies 已過期")
    else:
        print("ℹ️  沒有找到儲存的 cookies")


def show_config_options():
    """顯示配置選項"""
    
    print("\\n⚙️  認證配置選項")
    print("=" * 30)
    
    config = AuthConfig()
    
    print("可用的認證模式:")
    for mode in AuthMode:
        current = " (目前)" if mode == config.auth_mode else ""
        print(f"  • {mode.value}: {mode.name}{current}")
    
    print(f"\\n環境變數設定範例:")
    print(config.create_example_env())


def main():
    """主函數"""
    
    print("🎯 Threads 認證系統測試工具")
    print("=" * 50)
    
    while True:
        print("\\n請選擇測試項目:")
        print("1. 手動認證測試（需要在瀏覽器中登入）")
        print("2. Cookie 持久化測試")
        print("3. 顯示配置選項")
        print("4. 退出")
        
        choice = input("\\n請輸入選擇 (1-4): ").strip()
        
        if choice == "1":
            test_manual_authentication()
        elif choice == "2":
            test_cookie_persistence()
        elif choice == "3":
            show_config_options()
        elif choice == "4":
            print("👋 再見！")
            break
        else:
            print("❌ 無效選擇，請輸入 1-4")


if __name__ == "__main__":
    main()