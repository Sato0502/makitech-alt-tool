import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import io

# 画面の設定
st.set_page_config(page_title="マキテックHP alt抽出ツール")

# タイトル
st.title("マキテックHP　製品ページalt抽出ツール")

# URL入力欄
st.subheader("URL入力欄")
target_url = st.text_input("URLを記入してください", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")

# 注記
st.caption("※記入したURLから2層目のページのaltを抽出するため、各カテゴリのメニューページを記入してください。")

if st.button("抽出する"):
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("共通メニューを除外して、メインコンテンツのみ抽出中..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                res = requests.get(target_url, headers=headers)
                res.encoding = res.apparent_encoding
                soup = BeautifulSoup(res.text, 'html.parser')

                # リンク収集
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
                            
                            # A列: 型番判別
                            t_div = ps.find('div', class_='m-t-20 text-medium')
                            model = t_div.get_text(strip=True) if t_div else "未設定"
                            
                            # C,D,E列: メタ情報
                            title = ps.title.string if ps.title else ""
                            meta_k = ps.find("meta", attrs={"name": "keywords"})
                            kwd = meta_k["content"] if meta_k else ""
                            meta_d = ps.find("meta", attrs={"name": "description"})
                            desc = meta_d["content"] if meta_d else ""

                            # --- 【改良ポイント】不要なエリアを削除 ---
                            # ヘッダー、フッター、サイドナビを解析対象から物理的に削除します
                            for unwanted in ps.find_all(['header', 'footer', 'nav', 'aside']):
                                unwanted.decompose()
                            
                            # さらに特定のIDやクラス（サイドメニュー等）を削除
                            for unwanted_id in ['side', 'sidebar', 'sub-menu', 'header', 'footer']:
                                tag = ps.find(id=unwanted_id)
                                if tag: tag.decompose()
                            
                            for unwanted_class in ['l-header', 'l-footer', 'l-side', 'm-sideNav']:
                                for tag in ps.find_all(class_=unwanted_class):
                                    tag.decompose()

                            # 残った部分（メインコンテンツ）からaltを取得
                            # 優先的にメインの器を探し、なければ全体から（ただし上記で不要なものは消去済み）
                            main = ps.find('div', id='contents') or ps.find('main') or ps.find('article') or ps.find('div', class_='l-main') or ps
                            
                            alt_list = []
                            for img in main.find_all('img'):
                                alt_text = img.get('alt', '').strip()
                                # 空でない、かつ「ロゴ」や「TOP」などの共通ワードを除外（必要に応じて追加可能）
                                if alt_text and alt_text not in ["サイトマップ", "TOP", "お問合せ"]:
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
                        st.success(f"完了！ {len(all_data)} ページのメインデータを抽出しました。")
                        st.dataframe(df)

                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="エクセルデータをダウンロード",
                            data=output.getvalue(),
                            file_name="makitech_alt_list.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
