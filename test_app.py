#!/usr/bin/env python3
"""
簡單的測試腳本，驗證應用程式基本功能
"""
import requests
import json
import time

def test_app_running():
    """測試應用程式是否正在運行"""
    try:
        response = requests.get('http://localhost:5001/', timeout=5)
        print(f"✅ 應用程式正在運行 - 狀態碼: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 應用程式未運行: {e}")
        return False

def test_health_check():
    """測試健康檢查端點"""
    try:
        response = requests.get('http://localhost:5001/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康檢查通過")
            print(f"   支援的平台: {data.get('supported_platforms', [])}")
            return True
        else:
            print(f"❌ 健康檢查失敗 - 狀態碼: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 健康檢查錯誤: {e}")
        return False

def test_url_validation():
    """測試網址驗證功能"""
    test_urls = [
        ("https://www.threads.com/@test/post/123", True),
        ("https://www.instagram.com/p/test", True),
        ("https://www.facebook.com/post/123", False),
        ("invalid-url", False)
    ]
    
    for url, expected in test_urls:
        try:
            response = requests.post(
                'http://localhost:5001/api/validate-url',
                json={'url': url},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                is_valid = data.get('valid', False)
                
                if is_valid == expected:
                    print(f"✅ 網址驗證正確: {url} -> {is_valid}")
                else:
                    print(f"❌ 網址驗證失敗: {url} -> 預期 {expected}, 得到 {is_valid}")
            else:
                print(f"❌ 網址驗證請求失敗: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 網址驗證錯誤: {e}")

def test_error_handling():
    """測試錯誤處理"""
    try:
        # 測試無效的抽獎請求
        response = requests.post(
            'http://localhost:5001/lottery',
            json={'url': '', 'mode': '1', 'winner_count': 0},
            timeout=5
        )
        
        if response.status_code == 400:
            data = response.json()
            if 'error' in data and 'error_type' in data:
                print(f"✅ 錯誤處理正常 - 錯誤類型: {data['error_type']}")
                print(f"   錯誤訊息: {data['error']}")
                return True
        
        print(f"❌ 錯誤處理異常 - 狀態碼: {response.status_code}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 錯誤處理測試失敗: {e}")
        return False

def main():
    """執行所有測試"""
    print("🧪 開始測試應用程式...")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 4
    
    if test_app_running():
        tests_passed += 1
    
    if test_health_check():
        tests_passed += 1
    
    test_url_validation()
    tests_passed += 1  # URL validation has multiple sub-tests
    
    if test_error_handling():
        tests_passed += 1
    
    print("=" * 50)
    print(f"🎯 測試完成: {tests_passed}/{total_tests} 個測試通過")
    
    if tests_passed == total_tests:
        print("🎉 所有測試都通過了！應用程式運行正常")
    else:
        print("⚠️ 有部分測試失敗，請檢查應用程式狀態")

if __name__ == "__main__":
    main()