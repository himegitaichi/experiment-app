import streamlit as st
import os
import random
import csv
import datetime
from PIL import Image
import pandas as pd

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
# 2. 関数定義（再開機能用）
# ==========================================


# 完了済みの画像をチェックする関数
def get_done_images(user_name):
    csv_path = os.path.join(RESULTS_DIR, f"result_{user_name}.csv")

    # 1. ファイルが存在しない場合
    if not os.path.exists(csv_path):
        return []

    # 2. ファイル読み込み
    try:
        df = pd.read_csv(csv_path)
        if "image_file" in df.columns:
            return df["image_file"].tolist()
        else:
            return []
    except pd.errors.EmptyDataError:
        return []
    except Exception:
        return []


# 画像リストの読み込み（シャッフル & 済み除外）
def load_image_list(user_name):
    image_files = []

    # imagesフォルダの中身を直接見る（フラット構造）
    if os.path.exists(IMAGE_DIR):
        files = os.listdir(IMAGE_DIR)
        for f in files:
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                # 地域コードで始まるファイルのみ対象
                for region_code in REGION_MAP.values():
                    if f.startswith(region_code):
                        image_files.append(f)
                        break

    # --- ランダムシャッフル（分類実験なのでランダム推奨） ---
    # ※再現性を保ちたい場合はここで seed を固定する手もありますが、
    # 通常はランダムでOKです。
    random.shuffle(image_files)

    # --- 済み画像を除外 ---
    done_files = get_done_images(user_name)

    remaining_files = []
    for filename in image_files:
        if filename not in done_files:
            remaining_files.append(filename)

    return remaining_files, len(image_files)


# ==========================================
# 3. アプリケーション本体
# ==========================================

# --- 画面A: ユーザー名入力 (スタート画面) ---
if "user_name" not in st.session_state or st.session_state["user_name"] == "":
    st.title("🏯 地域分類実験")
    st.info(
        "ご協力ありがとうございます。 表示される画像が、どの地域の建物か 直感で選んでください。"
    )
    st.markdown(
        """
    ご協力ありがとうございます。
    表示される画像が、**どの地域の建物か** 直感で選んでください。
    """
    )

    name_input = st.text_input(
        "お名前（またはID）を入力してください",
        placeholder="例: yamada",
        key="input_name",
    )

    if st.button("実験を開始する", type="primary"):
        if name_input:
            st.session_state["user_name"] = name_input
            st.rerun()
        else:
            st.warning("名前を入力してください。")

# --- 画面B: 実験メイン画面 ---
else:
    user_name = st.session_state["user_name"]

    # 画像リストの更新（未回答のものだけ取得）
    target_images, total_count = load_image_list(user_name)
    done_count = total_count - len(target_images)

    # 全部終わっている場合
    if not target_images:
        st.balloons()
        st.success(
            f"お疲れ様でした！ {total_count}枚全ての画像の分類が完了しています。"
        )
        st.info("データは保存されています。ブラウザを閉じて終了してください。")
        st.stop()

    # 現在の画像
    filename = target_images[0]

    # 進捗バー
    progress = done_count / total_count
    st.progress(progress)
    st.caption(f"画像: {done_count + 1} / {total_count}")

    # 画像の表示
    img_path = os.path.join(IMAGE_DIR, filename)
    try:
        image = Image.open(img_path)
        st.image(image, use_container_width=True)
    except Exception as e:
        st.error(f"画像エラー: {filename} を読み込めませんでした。スキップします。")

    # --- 回答処理関数 ---
    def save_answer(selected_region_display):
        # 1. 選択された地域をコードに変換
        selected_code = REGION_MAP[selected_region_display]

        # 2. 正解抽出
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

        # 4. データ作成
        record = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_name,
            "image_file": filename,
            "true_region": true_region,
            "prompt_type": prompt_type,
            "selected_region": selected_code,
            "is_correct": is_correct,
        }

        # 5. ★ 逐次保存処理 (Appendモード)
        csv_filename = f"result_{user_name}.csv"
        csv_path = os.path.join(RESULTS_DIR, csv_filename)
        is_new_file = not os.path.exists(csv_path)

        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=record.keys())
                if is_new_file:
                    writer.writeheader()
                writer.writerow(record)

            st.rerun()  # 次の画像へ

        except Exception as e:
            st.error(f"保存エラー: {e}")

    # --- ボタンの配置 ---
    st.write("### 地域を選択してください")

    cols = st.columns(3)
    for i, region_name in enumerate(REGIONS_DISPLAY):
        if cols[i % 3].button(region_name, use_container_width=True):
            save_answer(region_name)

# ==========================================
# 4. 管理者用メニュー
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.write(f"Login: {st.session_state.get('user_name', 'Guest')}")
    st.write("🔧 **管理者メニュー**")

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
