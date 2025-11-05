"""
BUZZ福岡本店 予約状況チェッカー
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta


class BuzzChecker:
    """BUZZ福岡本店の予約状況をチェックするクラス"""
    
    BASE_URL = "https://buzz-st.com/fukuokahonten"
    
    def __init__(self, headless=True):
        """
        初期化
        
        Args:
            headless (bool): ヘッドレスモードで実行するか（True: バックグラウンド実行、False: ブラウザ表示）
        """
        self.headless = headless
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Seleniumドライバーのセットアップ"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # ユーザーエージェントを設定（ボット対策回避）
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # ChromeDriverManagerで正しいドライバーを取得
        import os
        import stat
        try:
            base_path = ChromeDriverManager().install()
            print(f"ChromeDriverManagerが返したパス: {base_path}")
            
            # ベースパスがディレクトリかファイルかを確認
            if os.path.isdir(base_path):
                search_dir = base_path
            else:
                search_dir = os.path.dirname(base_path)
            
            # 実行可能なchromedriverファイルを探す
            driver_path = None
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # ファイル名がchromedriverで、拡張子がないか、実行可能なファイル
                    if file == 'chromedriver' or (file.startswith('chromedriver') and '.' not in file):
                        # 実行可能かチェック
                        if os.path.isfile(file_path):
                            file_stat = os.stat(file_path)
                            if stat.S_IXUSR & file_stat.st_mode:  # 実行権限があるか
                                driver_path = file_path
                                break
                if driver_path:
                    break
            
            if not driver_path:
                # 見つからない場合は、システムのChromeDriverを使用
                print("実行可能なchromedriverが見つかりません。システムのChromeDriverを使用します。")
                service = Service()
            else:
                print(f"使用するChromeDriver: {driver_path}")
                service = Service(driver_path)
        except Exception as e:
            print(f"ChromeDriverManagerでエラー: {e}")
            # フォールバック: システムのChromeDriverを使用
            service = Service()
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # ページ読み込みタイムアウトを設定
        self.driver.set_page_load_timeout(30)
    
    def get_reservation_table(self, target_date):
        """
        指定日付の予約表を取得
        
        Args:
            target_date (datetime): 確認したい日付
            
        Returns:
            BeautifulSoup: 予約表のHTMLパース結果
        """
        try:
            # ベースURLにアクセス
            print(f"アクセス中: {self.BASE_URL}")
            self.driver.get(self.BASE_URL)
            
            # ページが読み込まれるまで待機
            time.sleep(3)
            
            # 予約表セクションが表示されるまで待機
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table, .reservation-table, #reservation-table"))
                )
            except:
                print("予約表が見つかりません。ページ構造を確認します...")
                # ページのHTMLを取得して確認
                print(self.driver.page_source[:1000])
            
            # 日付選択の処理（必要に応じて実装）
            # まずは現在表示されている日付の予約表を取得
            
            # HTMLを取得
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            print(f"予約表のHTMLを取得しました（長さ: {len(html)}文字）")
            
            return soup
            
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            raise
    
    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            self.driver.quit()
            print("ブラウザを閉じました")


def main():
    """メイン関数（テスト用）"""
    checker = BuzzChecker(headless=False)  # デバッグ用にブラウザを表示
    
    try:
        # 今日の日付でテスト
        today = datetime.now()
        soup = checker.get_reservation_table(today)
        
        # HTMLの一部を表示（デバッグ用）
        print("\n=== 取得したHTMLの一部 ===")
        print(soup.prettify()[:2000])
        
    finally:
        checker.close()


if __name__ == "__main__":
    main()

