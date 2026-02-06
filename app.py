import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import io

# 画面設定
st.set_page_config(page_title="マキテックHP 抽出ツール v7", layout="wide")

st.title("マキテックHP　製品ページalt抽出ツール v7")

# ==========================================
# 【メンテナンス用】ここに除外したいURLをどんどん追加してください
# ==========================================
# カンマ( , )とクォーテーション( " )を忘れないように入力してください
EXCLUDE_URL_LIST = [
    "https://www.makitech.co.jp/index.html",
    "https://www.makitech.co.jp/product.html",
    "https://www.makitech.co.jp/company/index.html",
    "https://www.makitech.co.jp/support/index.html",
    "https://www.makitech.co.jp/support/data.html",
    "https://www.makitech.co.jp/support/catalog.html",
    "https://www.makitech.co.jp/support/form01.html",
    "https://www.makitech.co.jp/support/form03.html",
    "https://www.makitech.co.jp/recruitment/index.html",
    "https://www.makitech.co.jp/recruitment/recruit_career.html",
    # ここに好きなだけ追加できます
]
# ==========================================

# サイドバー設定
with st.sidebar:
    st.header("設定")
    target_url = st.text_input("1. 調査元URL", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")
    st.info(f"現在、プログラム内に {len(EXCLUDE_URL_LIST)} 件の除外URLが登録されています。")

if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None

if st.button("抽出を開始する"):
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("ページを巡回中..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                res = requests.get(target_url, headers=headers)
                res.encoding = res.apparent_encoding
                soup = BeautifulSoup(res.text, 'html.parser')

                links = []
                for a in soup.find_all('a', href=True):
                    url = urljoin(target_url, a['href'])
                    # 基本フィルタ（htmlであること、自分自身でないこと）
                    if (".html" in url) and (url != target_url) and ("#" not in url):
                        # ★ここで「除外リスト」に入っているURLは最初から飛ばす
                        if url not in EXCLUDE_URL_LIST:
                            if url not in links:
                                links.append(url)

                if not links:
                    st.warning("対象ページが見つかりませんでした（すべて除外された可能性もあります）。")
                else:
                    all_data = []
                    progress_bar = st.progress(0)
                    for i, link in enumerate(links):
                        time.sleep(0.3)
                        try:
                            r = requests.get(link, headers=headers, timeout=10)
                            r.encoding = r.apparent_encoding
                            ps = BeautifulSoup(r.text, 'html.parser')
                            
                            t_div = ps.find('div', class_='m-t-20 text-medium')
                            model = t_div.get_text(strip=True) if t_div else "未設定"
                            
                            main = ps.find(id='contents') or ps.find(class_='l-main') or ps
                            alts = [img.get('alt', '').strip() for img in main.find_all('img') if img.get('alt')]
                            
                            row = {"型番": model, "URL": link, "Title": ps.title.string if ps.title else ""}
                            for idx, val in enumerate(alts):
                                row[f"alt {idx+1}"] = val
                            all_data.append(row)
                        except: continue
                        progress_bar.progress((i + 1) / len(links))
                    
                    st.session_state.extracted_df = pd.DataFrame(all_data)
            except Exception as e:
                st.error(f"エラー: {e}")

if st.session_state.extracted_df is not None:
    st.subheader("抽出結果")
    st.dataframe(st.session_state.extracted_df, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.extracted_df.to_excel(writer, index=False)
    
    st.download_button(
        label="エクセルをダウンロード",
        data=output.getvalue(),
        file_name="alt_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
