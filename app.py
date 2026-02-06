import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import io

# 画面の設定
st.set_page_config(page_title="マキテックHP alt抽出ツール")

# タイトル（C2相当）
st.title("マキテックHP　製品ページalt抽出ツール")

# URL入力欄（C5, C6相当）
st.subheader("URL入力欄")
target_url = st.text_input("URLを記入してください", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")

# 注記（C8相当）
st.caption("※記入したURLから2層目のページのaltを抽出するため、各カテゴリのメニューページを記入してください。")

# 抽出ボタン（C10相当）
if st.button("抽出する"):
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("抽出中... 少々お待ちください"):
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(target_url, headers=headers)
                res.encoding = res.apparent_encoding
                soup = BeautifulSoup(res.text, 'html.parser')

                # リンク収集
                links = []
                for a in soup.find_all('a', href=True):
                    url = urljoin(target_url, a['href'])
                    # 対象のURL構造を判定（/solution/等にも対応）
                    if (".html" in url) and (url != target_url):
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
                            
                            # A列: 型番判別
                            t_div = ps.find('div', class_='m-t-20 text-medium')
                            model = t_div.get_text(strip=True) if t_div else "未設定"
                            
                            # C,D,E列: メタ情報
                            title = ps.title.string if ps.title else ""
                            meta_k = ps.find("meta", attrs={"name": "keywords"})
                            kwd = meta_k["content"] if meta_k else ""
                            meta_d = ps.find("meta", attrs={"name": "description"})
                            desc = meta_d["content"] if meta_d else ""

                            # F列以降: alt
                            main = ps.find('div', id='contents') or ps.find('main') or ps.find('div', class_='l-main') or ps
                            alts = [img.get('alt').strip() for img in main.find_all('img') if img.get('alt')]
                            
                            row = {"型番": model, "URL": link, "Title": title, "Keywords": kwd, "Description": desc}
                            for idx, val in enumerate(alts):
                                row[f"alt {idx+1}"] = val
                            all_data.append(row)
                        except:
                            continue
                        progress_bar.progress((i + 1) / len(links))

                    # 結果表示とダウンロード
                    if all_data:
                        df = pd.DataFrame(all_data)
                        st.success(f"完了！ {len(all_data)} ページのデータを抽出しました。")
                        st.dataframe(df)

                        # エクセルダウンロードボタン（C16相当）
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="エクセルデータをダウンロード",
                            data=output.getvalue(),
                            file_name="alt_extract_result.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
