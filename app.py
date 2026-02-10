import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import io

# ==========================================
# 画面設定
# ==========================================
st.set_page_config(page_title="マキテックHP 抽出ツール v9", layout="wide")
st.title("マキテックHP 製品ページalt抽出ツール v9")

# ==========================================
# 除外URLリスト（Set型）
# ==========================================
EXCLUDE_URL_LIST = {
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
}

# サイドバー
with st.sidebar:
    st.header("設定")
    target_url = st.text_input("1. 調査元URL", placeholder="https://www.makitech.co.jp/conveyor/index-2.html")
    st.info(f"除外URL: {len(EXCLUDE_URL_LIST)} 件登録済み")

if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None

# ==========================================
# メイン処理
# ==========================================
if st.button("抽出を開始する", type="primary"):
    if not target_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("解析を開始します..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                session = requests.Session()
                res = session.get(target_url, headers=headers, timeout=15)
                res.encoding = res.apparent_encoding
                soup = BeautifulSoup(res.text, 'html.parser')

                # 巡回リンクの収集
                links = []
                for a in soup.find_all('a', href=True):
                    full_url = urljoin(target_url, a['href'])
                    if (".html" in full_url) and (full_url != target_url) and ("#" not in full_url):
                        if full_url not in EXCLUDE_URL_LIST and full_url not in links:
                            links.append(full_url)

                if not links:
                    st.warning("対象ページが見つかりませんでした。")
                else:
                    all_data = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, link in enumerate(links):
                        status_text.text(f"解析中 ({i+1}/{len(links)}): {link}")
                        time.sleep(0.3)
                        
                        # ページごとのデータ初期化（最悪URLだけでも残すため）
                        row = {
                            "型番": "未取得",
                            "URL": link,
                            "Title": "",
                            "Keywords": "",
                            "Description": ""
                        }
                        
                        try:
                            r = session.get(link, headers=headers, timeout=10)
                            r.encoding = r.apparent_encoding
                            ps = BeautifulSoup(r.text, 'html.parser')
                            
                            # A: 型番の取得 (安全な取得方法)
                            t_div = ps.find('div', class_='m-t-20 text-medium')
                            if t_div:
                                row["型番"] = t_div.get_text(strip=True)
                            
                            # C: タイトルの取得
                            if ps.title and ps.title.string:
                                row["Title"] = ps.title.string.strip()

                            # D: Keywords
                            kw_tag = ps.find("meta", attrs={'name': 'keywords'})
                            if kw_tag and kw_tag.get("content"):
                                row["Keywords"] = kw_tag["content"].strip()

                            # E: Description
                            desc_tag = ps.find("meta", attrs={'name': 'description'})
                            if desc_tag and desc_tag.get("content"):
                                row["Description"] = desc_tag["content"].strip()
                            
                            # F以降: alt属性の抽出
                            alts = []
                            for img in ps.find_all('img'):
                                alt_val = img.get('alt')
                                if alt_val is not None:
                                    alt_clean = alt_val.strip()
                                    if alt_clean and alt_clean not in alts:
                                        alts.append(alt_clean)
                            
                            for idx, val in enumerate(alts, start=1):
                                row[f"alt {idx}"] = val
                                
                        except Exception as e:
                            # 接続エラーなどが起きても、ここまでの row (URL入り) を保存
                            st.write(f"⚠️ 解析制限あり: {link} (詳細: {e})")
                        
                        all_data.append(row)
                        progress_bar.progress((i + 1) / len(links))
                    
                    # DataFrame作成
                    df = pd.DataFrame(all_data)
                    
                    # 列順の正規化
                    fixed_cols = ["型番", "URL", "Title", "Keywords", "Description"]
                    # 実際に存在する列だけを抽出（念のため）
                    existing_fixed = [c for c in fixed_cols if c in df.columns]
                    dynamic_cols = [c for c in df.columns if c not in fixed_cols]
                    df = df[existing_fixed + dynamic_cols]
                    
                    st.session_state.extracted_df = df
                    status_text.text(f"完了しました。合計 {len(all_data)} 件のページをリストアップしました。")

            except Exception as e:
                st.error(f"初期エラー: {e}")

# 結果表示とダウンロード
if st.session_state.extracted_df is not None:
    st.subheader("抽出結果")
    st.dataframe(st.session_state.extracted_df, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.extracted_df.to_excel(writer, index=False)
    
    st.download_button(
        label="エクセルをダウンロード",
        data=output.getvalue(),
        file_name="makitech_alt_full_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
