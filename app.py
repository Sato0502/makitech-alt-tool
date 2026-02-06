import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import io

# 画面を広く使う設定
st.set_page_config(page_title="マキテックHP alt抽出ツール v6", layout="wide")

st.title("マキテックHP　製品ページalt抽出ツール v6")

# --- サイドバー：除外リストの管理 ---
with st.sidebar:
    st.header("🛠 除外URLリスト管理")
    st.write("削除したいURLやキーワードを1行ずつ入力してください。")
    
    # 削除したいURLを大量に入れられるテキストエリア
    # heightを指定して枠を大きくしています
    exclude_text = st.text_area(
        "除外リスト（メモ帳）", 
        value=st.session_state.get('exclude_list_raw', ""),
        height=400,
        placeholder="https://www.makitech.co.jp/index.html\n/support/\n/company/",
        help="ここに登録された文字を含む行は、抽出結果から自動的に削除されます。"
    )
    # セッションに保存して保持
    st.session_state['exclude_list_raw'] = exclude_text
    exclude_list = [line.strip() for line in exclude_text.split("\n") if line.strip()]
    
    st.info(f"現在 {len(exclude_list)} 件の除外ルールが適用されています。")

    # リストをクリアするボタン
    if st.button("リストをすべてクリア"):
        st.session_state['exclude_list_raw'] = ""
        st.rerun()

# --- メインエリア：抽出設定 ---
col1, col2 = st.columns([2, 1])
with col1:
    target_url = st.text_input("調査元のメニューページURL", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")
with col2:
    st.write("") # スペース調整
    extract_btn = st.button("Step 1: データを抽出する", use_container_width=True)

# セッション状態の初期化
if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None

# --- 抽出処理 ---
if extract_btn:
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("全ページを詳細に調査中..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                res = requests.get(target_url, headers=headers)
                res.encoding = res.apparent_encoding
                soup = BeautifulSoup(res.text, 'html.parser')

                links = []
                for a in soup.find_all('a', href=True):
                    url = urljoin(target_url, a['href'])
                    if (".html" in url) and (url != target_url) and ("#" not in url):
                        if url not in links:
                            links.append(url)

                if not links:
                    st.warning("対象ページが見つかりませんでした。")
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

# --- 結果の表示とフィルタリング ---
if st.session_state.extracted_df is not None:
    df_display = st.session_state.extracted_df.copy()
    
    # 除外リストに基づいて行を削除
    if exclude_list:
        for ex in exclude_list:
            df_display = df_display[~df_display['URL'].str.contains(ex, na=False)]
    
    st.divider()
    st.subheader(f"抽出・フィルタ結果 （現在 {len(df_display)} 行）")
    st.dataframe(df_display, use_container_width=True)

    # ダウンロードボタン
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_display.to_excel(writer, index=False)
    
    st.download_button(
        label="Step 2: フィルタ済みのエクセルをダウンロード",
        data=output.getvalue(),
        file_name="makitech_alt_list_final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.caption("※左側の除外リストを書き換えると、即座に上の表に反映されます。")
