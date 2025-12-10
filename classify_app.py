import streamlit as st
import os
import random
import csv
import datetime
from PIL import Image

# ==========================================
# 1. 設定
# ==========================================
IMAGE_DIR = "images"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# 選択肢ボタンの表示順
REGIONS_DISPLAY = ["佐賀", "宮崎", "大阪", "奈良", "滋賀", "埼玉"]
# 表示名とファイル名の地域コードの対応表
REGION_MAP = {
    "佐賀": "saga",
    "宮崎": "miyazaki",
    "大阪": "osaka",
    "奈良": "nara",
    "滋賀": "shiga",
    "埼玉": "saitama",
}

# ==========================================
# 2. セッション状態の初期化
# ==========================================
if "images" not in st.session_state:
    # 画像ファイルのみを取得してシャッフル
    if os.path.exists(IMAGE_DIR):
        all_images = [
            f
            for f in os.listdir(IMAGE_DIR)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        random.shuffle(all_images)
    else:
        st.error(f"エラー: '{IMAGE_DIR}' フォルダが見つかりません。")
        all_images = []

    st.session_state["images"] = all_images
    st.session_state["current_index"] = 0
    st.session_state["results"] = []  # 結果の一時保存用
    st.session_state["user_name"] = ""  # 被験者名
    st.session_state["started"] = False  # 開始フラグ
    st.session_state["finished"] = False  # 終了フラグ

# ==========================================
# 3. 画面描画
# ==========================================

# --- 画面A: ユーザー名入力 (スタート画面) ---
if not st.session_state["started"]:
    st.title("🏯 地域分類実験")
    st.markdown(
        """
    ご協力ありがとうございます。
    表示される画像が、**どの地域の建物か** 直感で選んでください。
    """
    )

    name_input = st.text_input(
        "お名前（またはID）を入力してください", placeholder="例: yamada"
    )

    if st.button("実験を開始する", type="primary"):
        if name_input:
            st.session_state["user_name"] = name_input
            st.session_state["started"] = True
            st.rerun()
        else:
            st.warning("名前を入力してください。")

# --- 画面C: 終了画面 ---
elif st.session_state["finished"]:
    st.balloons()
    st.success(
        f"お疲れ様でした！ {len(st.session_state['results'])}枚の画像の分類が完了しました。"
    )
    st.info("ブラウザを閉じて終了してください。")

# --- 画面B: 実験メイン画面 ---
else:
    # 現在の画像情報を取得
    current_idx = st.session_state["current_index"]
    total_images = len(st.session_state["images"])

    if total_images == 0:
        st.error("画像が見つかりません。")
        st.stop()

    filename = st.session_state["images"][current_idx]

    # 進捗バー
    progress = (current_idx + 1) / total_images
    st.progress(progress)
    st.caption(f"画像: {current_idx + 1} / {total_images}")

    # 画像の表示
    img_path = os.path.join(IMAGE_DIR, filename)
    try:
        image = Image.open(img_path)

        # ★ ここでファイル名を表示します
        st.write(f"**現在の画像ファイル名:** `{filename}`")

        st.image(image, use_container_width=True)
    except Exception as e:
        st.error(f"画像エラー: {filename} を読み込めませんでした。スキップします。")

    # --- CSV保存関数 ---
    def save_csv():
        csv_filename = f"result_{st.session_state['user_name']}.csv"
        csv_path = os.path.join(RESULTS_DIR, csv_filename)

        if st.session_state["results"]:
            keys = st.session_state["results"][0].keys()
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(st.session_state["results"])

    # --- 回答処理関数 ---
    def save_answer(selected_region_display):
        # 1. 選択された地域をコードに変換
        selected_code = REGION_MAP[selected_region_display]

        # 2. ファイル名から正解とプロンプトタイプを抽出
        # ファイル名形式: saga_simple_001.png
        true_region = "unknown"
        prompt_type = "unknown"
        try:
            parts = filename.split("_")
            if len(parts) >= 2:
                true_region = parts[0]
                prompt_type = parts[1]
        except:
            pass

        # 3. 正誤判定
        is_correct = 1 if selected_code == true_region else 0

        # 4. データをリストに追加
        record = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": st.session_state["user_name"],
            "image_file": filename,
            "true_region": true_region,
            "prompt_type": prompt_type,
            "selected_region": selected_code,
            "is_correct": is_correct,
        }
        st.session_state["results"].append(record)

        # 5. 次の画像へ、または終了処理
        if current_idx + 1 < total_images:
            st.session_state["current_index"] += 1
        else:
            save_csv()
            st.session_state["finished"] = True

        st.rerun()

    # --- ボタンの配置 ---
    st.write("### 地域を選択してください")

    # 3列グリッドでボタン配置
    cols = st.columns(3)
    for i, region_name in enumerate(REGIONS_DISPLAY):
        if cols[i % 3].button(region_name, use_container_width=True):
            save_answer(region_name)

# ==========================================
# 4. 管理者用メニュー (サイドバー)
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.write("🔧 **管理者メニュー**")
    st.info("実験終了後、ここから結果CSVをダウンロードできます。")

    if st.checkbox("結果ファイルを表示"):
        if os.path.exists(RESULTS_DIR):
            files = os.listdir(RESULTS_DIR)
            if not files:
                st.write("まだ結果ファイルはありません。")
            for f in files:
                file_path = os.path.join(RESULTS_DIR, f)
                with open(file_path, "rb") as file:
                    st.download_button(
                        label=f"📥 Download {f}",
                        data=file,
                        file_name=f,
                        mime="text/csv",
                    )
