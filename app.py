import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
import time
from urllib.parse import urljoin
import io

# 画面の設定
st.set_page_config(page_title="マキテックHP alt抽出ツール v4")

# タイトル
st.title("マキテックHP　製品ページalt抽出ツール v4")

# URL入力欄
st.subheader("URL入力欄")
target_url = st.text_input("URLを記入してください", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")

# 注記
st.caption("※記入したURLから2層目のページのaltを抽出するため、各カテゴリのメニューページを記入してください。")

if st.button("抽出する"):
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("共通パーツを徹底的にフィルタリング中（v4）..."):
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
                    
                    # --- 除外したいワードのリスト（ここに追加してください） ---
                    NOISE_WORDS = [
                        "TOP", "サイトマップ", "お問合せ", "お問い合わせ", "採用情報", "会社情報", 
                        "製品情報", "お客様サポート", "CAD", "カタログ", "ロゴ", "インフォメーション",
                        "製品データ一覧", "カタログ一覧", "CADデータダウンロードご希望の方",
                        "新卒採用情報", "キャリア採用情報", "搬送システム製品", "マキテック",
                        "コンベヤ製品のパイオニア", "株式会社マキテック", "HOME"
                    ]

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

                            # 抽出エリアの限定
                            main_area = ps.find(id='contents') or ps.find(class_='l-main') or ps.find('main') or ps
                            
                            alt_list = []
                            if main_area:
                                for img in main_area.find_all('img'):
                                    alt_text = img.get('alt', '').strip()
                                    
                                    # 除外判定
                                    # 1. 空ではない
                                    # 2. NOISE_WORDSに含まれる単語がaltの中に「一つも含まれていない」場合のみ採用
                                    if alt_text:
                                        is_noise = any(word in alt_text for word in NOISE_WORDS)
                                        if not is_noise:
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
                        st.success("v4 抽出完了！")
                        st.dataframe(df)
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button(label="エクセルデータをダウンロード", data=output.getvalue(), file_name="makitech_alt_list_v4.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
