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
# 【メンテナンス用】除外URLリスト
# ==========================================
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
    "https://www.makitech.co.jp/sitemap.html",
    "https://www.makitech.co.jp/privacy.html",
    "https://www.makitech.co.jp/conveyor/index.html",
    "https://www.makitech.co.jp/conveyor/index-2.html",
    "https://www.makitech.co.jp/conveyor/index-3.html",
    "https://www.makitech.co.jp/conveyor/index-11.html",
    "https://www.makitech.co.jp/conveyor/index-14.html",
    "https://www.makitech.co.jp/conveyor/index-5.html",
    "https://www.makitech.co.jp/conveyor/index-13.html",
    "https://www.makitech.co.jp/conveyor/index-10.html",
    "https://www.makitech.co.jp/conveyor/index-9.html",
    "https://www.makitech.co.jp/conveyor/index-4.html",
    "https://www.makitech.co.jp/conveyor/index-12.html",
    "https://www.makitech.co.jp/conveyor/parts/index.html",
    "https://www.makitech.co.jp/conveyor/index-7.html",
    "https://www.makitech.co.jp/conveyor/index-6.html",
    "https://www.makitech.co.jp/conveyor/index-8.html",
    "https://www.makitech.co.jp/carry/index.html",
    "https://www.makitech.co.jp/carry/rokurin.html",
    "https://www.makitech.co.jp/carry/logistics_equipment_rental",
    "https://www.makitech.co.jp/logistics/index.html",
    "https://www.makitech.co.jp/construction/subaru/index.html",
    "https://www.makitech.co.jp/construction/cyclesystem/index.html",
    "https://www.makitech.co.jp/solar/index.html", 
    "https://www.makitech.co.jp/makiled/index.html", 
    "https://www.makitech.co.jp/construction/grating.html", 
    "https://www.makitech.co.jp/pc/index.html", 
    "https://www.makitech.co.jp/makihome/index.html", 
    "https://www.makitech.co.jp/crusher/index.html", 
    "https://www.makitech.co.jp/lifetech/", 
    "https://www.makitech.co.jp/support/faq01.html", 
    "https://www.makitech.co.jp/support/yougo.html", 
    "https://www.makitech.co.jp/solution/",  
]

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
                    if (".html" in url) and (url != target_url) and ("#" not in url):
                        if url not in EXCLUDE_URL_LIST:
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
                            
                            # 型番の取得
                            t_div = ps.find('div', class_='m-t-20 text-medium')
                            model = t_div.get_text(strip=True) if t_div else "未設定"
                            
                            # タイトル
                            page_title = ps.title.string if ps.title else ""

                            # Keywords の取得 (D列用)
                            kw_tag = ps.find("meta", attrs={'name': 'keywords'})
                            keywords = kw_tag["content"] if kw_tag and kw_tag.has_attr("content") else ""

                            # Description の取得 (E列用)
                            desc_tag = ps.find("meta", attrs={'name': 'description'})
                            description = desc_tag["content"] if desc_tag and desc_tag.has_attr("content") else ""
                            
                            # 画像altの取得 (F列以降用)
                            main = ps.find(id='contents') or ps.find(class_='l-main') or ps
                            alts = [img.get('alt', '').strip() for img in main.find_all('img') if img.get('alt')]
                            
                            # データの格納（定義順がExcelの列順になります）
                            row = {
                                "型番": model,          # A列
                                "URL": link,           # B列
                                "Title": page_title,   # C列
                                "Keywords": keywords,  # D列
                                "Description": description # E列
                            }
                            
                            # F列以降にalt属性を動的に追加
                            for idx, val in enumerate(alts):
                                row[f"alt {idx+1}"] = val
                                
                            all_data.append(row)
                        except:
                            continue
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
        file_name="alt_list_updated.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
