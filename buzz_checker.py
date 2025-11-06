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
import argparse
import re


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


def parse_date_input(date_input):
    """
    日付入力をパースしてdatetimeオブジェクトを返す
    
    Args:
        date_input (str): 日付入力（例: '2025-11-10', '火曜', '火', 'today', 'tomorrow'）
        
    Returns:
        datetime: パースされた日付
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_input.lower() in ['today', '今日', 'きょう']:
        return today
    
    if date_input.lower() in ['tomorrow', '明日', 'あした', 'あす']:
        return today + timedelta(days=1)
    
    # 曜日指定（日本語）
    weekday_map = {
        '月': 0, '月曜': 0, '月曜日': 0,
        '火': 1, '火曜': 1, '火曜日': 1,
        '水': 2, '水曜': 2, '水曜日': 2,
        '木': 3, '木曜': 3, '木曜日': 3,
        '金': 4, '金曜': 4, '金曜日': 4,
        '土': 5, '土曜': 5, '土曜日': 5,
        '日': 6, '日曜': 6, '日曜日': 6,
    }
    
    if date_input in weekday_map:
        target_weekday = weekday_map[date_input]
        current_weekday = today.weekday()
        days_ahead = (target_weekday - current_weekday) % 7
        if days_ahead == 0:
            days_ahead = 7  # 今日が該当曜日なら次週
        return today + timedelta(days=days_ahead)
    
    # YYYY-MM-DD形式
    try:
        date_obj = datetime.strptime(date_input, '%Y-%m-%d')
        return date_obj
    except ValueError:
        pass
    
    # YYYY/MM/DD形式
    try:
        date_obj = datetime.strptime(date_input, '%Y/%m/%d')
        return date_obj
    except ValueError:
        pass
    
    raise ValueError(f"日付形式が正しくありません: {date_input}")


def parse_studio_input(studio_input):
    """
    スタジオ入力をパースしてリストを返す
    
    Args:
        studio_input (str): スタジオ入力（例: '1st', '1st,2st,3st', 'all', '1-5'）
        
    Returns:
        list: スタジオ番号のリスト（例: ['1st', '2st', '3st']）
    """
    if studio_input.lower() in ['all', '全て', 'すべて', '全']:
        return [f'{i}st' for i in range(1, 13)]
    
    # カンマ区切り
    if ',' in studio_input:
        studios = [s.strip() for s in studio_input.split(',')]
        return [s if s.endswith('st') else f'{s}st' for s in studios]
    
    # 範囲指定（例: 1-5）
    range_match = re.match(r'(\d+)-(\d+)', studio_input)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        return [f'{i}st' for i in range(start, end + 1)]
    
    # 単一スタジオ
    studio = studio_input.strip()
    if not studio.endswith('st'):
        studio = f'{studio}st'
    return [studio]


def parse_time_input(time_input):
    """
    時間帯入力をパースしてリストを返す
    
    Args:
        time_input (str): 時間帯入力（例: '10:00', '10:00-12:00', '10:00,11:00,12:00'）
        
    Returns:
        list: 時間帯のリスト（例: ['10:00', '10:30', '11:00', '11:30']）
    """
    # カンマ区切り
    if ',' in time_input:
        return [t.strip() for t in time_input.split(',')]
    
    # 範囲指定（例: 10:00-12:00）
    range_match = re.match(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', time_input)
    if range_match:
        start_hour = int(range_match.group(1))
        start_min = int(range_match.group(2))
        end_hour = int(range_match.group(3))
        end_min = int(range_match.group(4))
        
        time_slots = []
        current = datetime(2000, 1, 1, start_hour, start_min)
        end_time = datetime(2000, 1, 1, end_hour, end_min)
        
        while current <= end_time:
            time_slots.append(current.strftime('%H:%M'))
            current += timedelta(minutes=30)
        
        return time_slots
    
    # 単一時間
    return [time_input.strip()]


def display_results(availability, studio_numbers, time_slots):
    """
    結果をコンソールに表示
    
    Args:
        availability (dict): 空き状況データ
        studio_numbers (list): チェックしたスタジオ番号のリスト
        time_slots (list): チェックした時間帯のリスト
    """
    print("\n" + "="*60)
    print("予約状況チェック結果")
    print("="*60)
    
    for studio_num in studio_numbers:
        if studio_num not in availability:
            continue
        
        print(f"\n【{studio_num}】")
        available_times = []
        reserved_times = []
        
        for time_slot in time_slots:
            status = availability[studio_num].get(time_slot, 'not_found')
            if status == 'available':
                available_times.append(time_slot)
            elif status == 'reserved':
                reserved_times.append(time_slot)
        
        if available_times:
            print(f"  ✓ 空き: {', '.join(available_times)}")
        if reserved_times:
            print(f"  ✗ 予約済み: {', '.join(reserved_times)}")
        
        # 一部空いている判定
        if available_times and reserved_times:
            print(f"  ⚠ 一部空いています（{len(available_times)}/{len(time_slots)}時間帯が空き）")
    
    print("\n" + "="*60)


def show_usage():
    """使用方法を表示"""
    usage_text = """
使用方法:
  python buzz_checker.py [日付] [スタジオ] [時間帯] [オプション]

位置引数（順番指定）:
  日付    日付指定（例: 2025-11-10, 火曜, today, tomorrow）
          省略時は 'today' が使用されます
  スタジオ  スタジオ指定（例: 1st, 1st,2st,3st, all, 1-5）
          省略時は 'all' が使用されます
  時間帯  時間帯指定（例: 10:00, 10:00-12:00, 10:00,11:00,12:00）
          省略時は全時間帯が使用されます

オプション:
  -d, --date DATE      日付指定（位置引数でも指定可能）
  -s, --studio STUDIO  スタジオ指定（位置引数でも指定可能）
  -t, --time TIME      時間帯指定（位置引数でも指定可能）
  --show-browser       ブラウザを表示する
  -h, --help          このヘルプメッセージを表示

使用例:
  python buzz_checker.py 火曜 1st,2st 10:00-12:00
  python buzz_checker.py today all
  python buzz_checker.py --date 火曜 --studio 1-5 --time 14:00,15:00
  python buzz_checker.py 2025-11-10 1st 10:00
"""
    print(usage_text)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='BUZZ福岡本店 予約状況チェッカー',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python buzz_checker.py 火曜 1st,2st 10:00-12:00
  python buzz_checker.py today all
  python buzz_checker.py --date 火曜 --studio 1-5 --time 14:00,15:00
  
位置引数で指定する場合、順番は [日付] [スタジオ] [時間帯] です。
オプション引数（--date, --studio, --time）でも同じように指定できます。
        """
    )
    
    # 位置引数（順番指定）
    parser.add_argument('date_pos', nargs='?', type=str, default='today',
                       metavar='日付',
                       help='日付指定（例: 2025-11-10, 火曜, today, tomorrow）')
    parser.add_argument('studio_pos', nargs='?', type=str, default='all',
                       metavar='スタジオ',
                       help='スタジオ指定（例: 1st, 1st,2st,3st, all, 1-5）')
    parser.add_argument('time_pos', nargs='?', type=str, default=None,
                       metavar='時間帯',
                       help='時間帯指定（例: 10:00, 10:00-12:00, 10:00,11:00,12:00）')
    
    # オプション引数（--date, --studio, --time でも指定可能）
    parser.add_argument('--date', '-d', type=str, dest='date_opt',
                       help='日付指定（オプション形式）')
    parser.add_argument('--studio', '-s', type=str, dest='studio_opt',
                       help='スタジオ指定（オプション形式）')
    parser.add_argument('--time', '-t', type=str, dest='time_opt',
                       help='時間帯指定（オプション形式）')
    
    parser.add_argument('--headless', action='store_true', default=True,
                       help='ヘッドレスモードで実行（デフォルト: True）')
    parser.add_argument('--show-browser', action='store_true',
                       help='ブラウザを表示する（--headlessの逆）')
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparseが自動的にヘルプを表示して終了する
        # 追加でカスタムusageを表示
        if e.code == 0:  # ヘルプ表示時（正常終了）
            show_usage()
        return
    
    # オプション引数が指定されている場合はそちらを優先
    date_input = args.date_opt if args.date_opt else args.date_pos
    studio_input = args.studio_opt if args.studio_opt else args.studio_pos
    time_input = args.time_opt if args.time_opt else args.time_pos
    
    # ヘッドレスモードの設定
    headless = args.headless and not args.show_browser
    
    checker = BuzzChecker(headless=headless)
    
    try:
        # 日付をパース
        try:
            target_date = parse_date_input(date_input)
            weekday_names = ['月', '火', '水', '木', '金', '土', '日']
            weekday = weekday_names[target_date.weekday()]
            print(f"チェック対象日: {target_date.strftime('%Y年%m月%d日')} ({weekday}曜日)")
        except ValueError as e:
            print(f"エラー: 日付のパースに失敗しました - {e}")
            print()
            show_usage()
            return
        
        # スタジオをパース
        try:
            studio_numbers = parse_studio_input(studio_input)
            print(f"チェック対象スタジオ: {', '.join(studio_numbers)}")
        except ValueError as e:
            print(f"エラー: スタジオのパースに失敗しました - {e}")
            print()
            show_usage()
            return
        
        # 予約表を取得
        print(f"\n予約表を取得中...")
        soup = checker.get_reservation_table(target_date)
        
        # データ抽出
        print("予約データを抽出中...")
        reservation_data = checker.extract_reservation_data(soup)
        
        # 時間帯の処理
        if time_input:
            try:
                time_slots = parse_time_input(time_input)
            except ValueError as e:
                print(f"エラー: 時間帯のパースに失敗しました - {e}")
                print()
                show_usage()
                return
        else:
            # 時間帯が指定されていない場合は全時間帯を使用
            if reservation_data:
                # 最初のスタジオから全時間帯を取得
                first_studio = list(reservation_data.keys())[0]
                time_slots = sorted(reservation_data[first_studio].keys())
            else:
                print("エラー: 予約データが取得できませんでした")
                return
        
        print(f"チェック対象時間帯: {len(time_slots)}時間帯")
        
        # 空き状況をチェック
        availability = checker.check_availability(reservation_data, studio_numbers, time_slots)
        
        # 結果を表示
        display_results(availability, studio_numbers, time_slots)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        print()
        show_usage()
    finally:
        checker.close()


if __name__ == "__main__":
    main()

