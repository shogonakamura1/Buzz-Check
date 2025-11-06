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
    
    def extract_reservation_data(self, soup):
        """
        予約表から空き状況データを抽出
        
        Args:
            soup (BeautifulSoup): 予約表のHTMLパース結果
            
        Returns:
            dict: スタジオ番号をキー、時間帯ごとの空き状況を値とする辞書
                 形式: {
                     '1st': {
                         '06:00': 'available',  # または 'reserved'
                         '06:30': 'reserved',
                         ...
                     },
                     ...
                 }
        """
        reservation_data = {}
        
        # 予約表のテーブルを探す
        table = soup.find('table', class_='studio_all_reserve_time_table')
        if not table:
            print("予約表が見つかりませんでした")
            return reservation_data
        
        # ヘッダーからスタジオ番号を取得
        headers = table.find('thead').find_all('th')
        studio_numbers = []
        for header in headers[1:]:  # 最初の列（時間列）を除く
            studio_name = header.find('div', class_='studio_reserve_time_table_studio_name')
            if studio_name:
                studio_num = studio_name.text.strip()
                studio_numbers.append(studio_num)
                reservation_data[studio_num] = {}
        
        # 各行から時間と空き状況を抽出
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue
            
            # 時間を取得
            time_cell = cells[0]
            time_str = time_cell.text.strip()
            
            # 各スタジオの空き状況を確認
            for i, cell in enumerate(cells[1:], 0):
                if i >= len(studio_numbers):
                    break
                
                studio_num = studio_numbers[i]
                
                # 予約済みかどうかを判定
                # studio_reserve_time_table_closeクラスのボタンがある = 予約済み
                close_button = cell.find('button', class_='studio_reserve_time_table_close')
                if close_button:
                    status = 'reserved'
                else:
                    # 予約可能なリンクがあるか、または空いている
                    link = cell.find('a')
                    if link:
                        status = 'available'
                    else:
                        # ボタンもリンクもない場合、空いている可能性
                        status = 'available'
                
                reservation_data[studio_num][time_str] = status
        
        return reservation_data
    
    def check_availability(self, reservation_data, studio_numbers, time_slots):
        """
        指定したスタジオと時間帯の空き状況をチェック
        
        Args:
            reservation_data (dict): extract_reservation_data()で取得したデータ
            studio_numbers (list): チェックしたいスタジオ番号のリスト（例: ['1st', '2st']）
            time_slots (list): チェックしたい時間帯のリスト（例: ['10:00', '10:30', '11:00']）
            
        Returns:
            dict: 空き状況の結果
                 形式: {
                     '1st': {
                         '10:00': 'available',
                         '10:30': 'reserved',
                         ...
                     },
                     ...
                 }
        """
        result = {}
        
        for studio_num in studio_numbers:
            if studio_num not in reservation_data:
                print(f"警告: スタジオ {studio_num} が見つかりません")
                continue
            
            result[studio_num] = {}
            for time_slot in time_slots:
                if time_slot in reservation_data[studio_num]:
                    result[studio_num][time_slot] = reservation_data[studio_num][time_slot]
                else:
                    result[studio_num][time_slot] = 'not_found'
        
        return result
    
    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            self.driver.quit()
            print("ブラウザを閉じました")


def main():
    """メイン関数（テスト用）"""
    checker = BuzzChecker(headless=True)
    
    try:
        # 今日の日付でテスト
        today = datetime.now()
        print(f"予約表を取得中: {today.strftime('%Y-%m-%d')}")
        soup = checker.get_reservation_table(today)
        
        # データ抽出
        print("\n予約データを抽出中...")
        reservation_data = checker.extract_reservation_data(soup)
        
        # 結果を表示
        print(f"\n=== 抽出結果 ===")
        print(f"スタジオ数: {len(reservation_data)}")
        
        # 各スタジオの空き状況をサマリー表示
        for studio_num in sorted(reservation_data.keys()):
            times = reservation_data[studio_num]
            available_count = sum(1 for status in times.values() if status == 'available')
            reserved_count = sum(1 for status in times.values() if status == 'reserved')
            print(f"{studio_num}: 空き={available_count}件, 予約済み={reserved_count}件")
        
        # 特定のスタジオと時間帯をチェック（テスト）
        print("\n=== 特定スタジオ・時間帯のチェック ===")
        test_studios = ['1st', '2st']
        test_times = ['10:00', '10:30', '11:00', '11:30']
        availability = checker.check_availability(reservation_data, test_studios, test_times)
        
        for studio_num in test_studios:
            print(f"\n{studio_num}:")
            for time_slot in test_times:
                status = availability[studio_num].get(time_slot, 'not_found')
                status_jp = '空き' if status == 'available' else '予約済み' if status == 'reserved' else '不明'
                print(f"  {time_slot}: {status_jp}")
        
    finally:
        checker.close()


if __name__ == "__main__":
    main()

