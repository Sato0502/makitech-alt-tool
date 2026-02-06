import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
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
        with st.spinner("ヘッダー・サイドメニュー・フッターを厳密に除外して抽出中..."):
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

                            # --- 【改良ポイント】コメントアウトを基準にエリアを削除 ---
                            # 1. サイドメニュー以降を全て削除 ()
                            comments = ps.find_all(string=lambda text: isinstance(text, Comment))
                            for comment in comments:
                                if 'Sidemenu' in comment:
                                    # Sidemenuコメント以降の全ての要素を削除
                                    for sibling in comment.find_all_next():
                                        sibling.decompose()
                                    comment.extract()
                                
                                # 2. フッター以降を全て削除 ()
                                if '/#page-wrapper' in comment:
                                    for sibling in comment.find_all_next():
                                        sibling.decompose()
                                    comment.extract()

                            # 3. ヘッダーメニュー（ご提示いただいたクラス名等）を削除
                            # topbar-nav や btn-danger を含むメニューエリアを狙い撃ち
                            for header_part in ps.find_all(['nav', 'div'], class_=['topbar-nav', 'container-fluid', 'metismenu']):
                                header_part.decompose()
                            
                            # 念のため特定のリンクキーワードを含む親要素も消す（TOP、会社情報など）
                            for nav_link in ps.find_all('a'):
                                if nav_link.get_text(strip=True) in ["TOP", "製品情報", "会社情報", "お客様サポート", "採用情報"]:
                                    parent = nav_link.find_parent('li') or nav_link.find_parent('div')
                                    if parent: parent.decompose()

                            # --- 抽出対象エリアの決定 ---
                            # メインコンテンツが格納される可能性が高いIDを指定
                            main = ps.find('div', id='contents') or ps.find('main') or ps.find('article') or ps
                            
                            alt_list = []
                            for img in main.find_all('img'):
                                alt_text = img.get('alt', '').strip()
                                # 共通ロゴ等の除外ワードを強化
                                if alt_text and alt_text not in ["サイトマップ", "TOP", "お問合せ", "インフォメーション", "製品情報", "会社情報"]:
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
                        st.success(f"完了！ メインエリアのデータを抽出しました。")
                        st.dataframe(df)

                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        
                        st.download_button(label="エクセルデータをダウンロード", data=output.getvalue(), file_name="makitech_alt_list.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
