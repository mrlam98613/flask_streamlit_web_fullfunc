import requests
import pandas as pd
from bs4 import BeautifulSoup
from A0_config import Lotto_data_DIR

def get_lotto_data_from_page(page: int) -> pd.DataFrame:
    url = f'https://zh.lottolyzer.com/history/hong-kong/mark-six/page/{page}/per-page/50/summary-view'
    response = requests.get(url)

    if response.status_code != 200:
        print(f"❌ Page {page} - Failed to retrieve the webpage. Status code: {response.status_code}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print(f"❌ Page {page} - No table found on the page.")
        return pd.DataFrame()

    headers = [th.text.strip() for th in table.find_all('th')]
    rows = []
    for tr in table.find_all('tr')[1:]:
        cells = [td.text.strip() for td in tr.find_all('td')]
        if cells:
            rows.append(cells)

    df = pd.DataFrame(rows, columns=headers)
    if not {'日期', '中獎號碼', '特別號碼'}.issubset(df.columns):
        print(f"❌ Page {page} - Missing required columns.")
        return pd.DataFrame()

    df = df[['日期', '中獎號碼', '特別號碼']]
    df['中獎號碼'] = df['中獎號碼'].apply(lambda x: x.replace(' ', ','))
    df_split = df['中獎號碼'].str.split(',', expand=True)

    if df_split.shape[1] != 6:
        print(f"❌ Page {page} - Unexpected number of numbers in '中獎號碼'")
        return pd.DataFrame()

    df[['N1', 'N2', 'N3', 'N4', 'N5', 'N6']] = df_split
    df.drop(columns=['中獎號碼'], inplace=True)
    df = df[['日期', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', '特別號碼']]
    df.columns = ['ndate', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7']
    df = df[df['ndate'] != '日期']
    return df

def get_last_lotto_download_func():
    combined_df = pd.DataFrame()
    for page in [1, 2, 3,4,5,6]:
        df = get_lotto_data_from_page(page)
        if not df.empty:
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    if not combined_df.empty:
        combined_df = combined_df.sort_values(by='ndate', ascending=True).reset_index(drop=True)
        combined_df.to_csv(Lotto_data_DIR / 'M1_ZH_lotto_data.csv', index=False)
        # print("✅ Lotto data saved to 'M1_ZH_lotto_data.csv'")
        # print(combined_df)
    else:
        
        print("❌ No data fetched from any page.")

def main():
    get_last_lotto_download_func()

if __name__ == '__main__':
    main()
