import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
import time
from urllib.parse import urljoin
import io

# 画面の設定
st.set_page_config(page_title="マキテックHP alt抽出ツール v3")

# タイトル
st.title("マキテックHP　製品ページalt抽出ツール v3")

# URL入力欄
st.subheader("URL入力欄")
target_url = st.text_input("URLを記入してください", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")

# 注記
st.caption("※記入したURLから2層目のページのaltを抽出するため、各カテゴリのメニューページを記入してください。")

if st.button("抽出する"):
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("メインコンテンツのみを厳選して抽出中（v3）..."):
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
                    st.warning("対象となる2層目のページが見つかりませんでした。")
                else:
                    all_data = []
                    progress_bar = st.progress(0)
                    
                    for i, link in enumerate(links):
                        time.sleep(0.5)
                        try:
                            r = requests.get(link, headers=headers, timeout=10)
                            r.encoding = r.apparent_encoding
                            ps = BeautifulSoup(r.text, 'html.parser')
                            
                            # メタ情報取得
                            t_div = ps.find('div', class_='m-t-20 text-medium')
                            model = t_div.get_text(strip=True) if t_div else "未設定"
                            title = ps.title.string if ps.title else ""
                            meta_k = ps.find("meta", attrs={"name": "keywords"})
                            kwd = meta_k["content"] if meta_k else ""
                            meta_d = ps.find("meta", attrs={"name": "description"})
                            desc = meta_d["content"] if meta_d else ""

                            # --- 【v3 根本修正】特定のメインエリア内のみを探す ---
                            # マキテック様の製品ページで「中身」が詰まっている可能性が高いクラスを優先順位順に指定
                            main_area = None
                            
                            # 1. まず id="contents" を探す
                            main_area = ps.find(id='contents')
                            
                            # 2. なければ class="l-main" を探す
                            if not main_area:
                                main_area = ps.find(class_='l-main')
                            
                            # 3. それもなければ、h1（製品名）がある親要素を探す
                            if not main_area:
                                h1 = ps.find('h1')
                                if h1:
                                    main_area = h1.parent

                            alt_list = []
                            if main_area:
                                # 【重要】main_areaの中にある画像だけをループ
                                for img in main_area.find_all('img'):
                                    alt_text = img.get('alt', '').strip()
                                    
                                    # さらに、メインエリアの中に紛れ込んだ共通パーツを除外
                                    # 「お問合せ」「TOP」「ロゴ」など、明らかにメニュー的なものは弾く
                                    noise_words = ["TOP", "サイトマップ", "お問合せ", "採用", "会社情報", "製品情報", "お客様サポート", "CAD", "カタログ", "ロゴ"]
                                    if alt_text and not any(word in alt_text for word in noise_words):
                                        alt_list.append(alt_text)
                            
                            row = {"型番": model, "URL": link, "Title": title, "Keywords": kwd, "Description": desc}
                            for idx, val in enumerate(alt_list):
                                row[f"alt {idx+1}"] = val
                            all_data.append(row)
                        except:
                            continue
                        progress_bar.progress((i + 1) / len(links))

                    if all_data:
                        df = pd.DataFrame(all_data)
                        st.success("v3 抽出完了！")
                        st.dataframe(df)
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button(label="エクセルデータをダウンロード", data=output.getvalue(), file_name="makitech_alt_list_v3.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
