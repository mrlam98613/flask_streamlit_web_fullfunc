from pathlib import Path
import os
import shutil

def copy_and_rename_pathlib(src_path, dest_path, new_name):
    src_path = Path(src_path)
    dest_path = Path(dest_path)

    if not src_path.exists():
        print(f"❌ 檔案不存在，無法複製：{src_path}")
        return

    # 確保目的地資料夾存在
    dest_path.mkdir(parents=True, exist_ok=True)
    # 組成新的檔案路徑（改名）
    new_path = dest_path / new_name
    # 複製並重新命名
    shutil.copy2(src_path, new_path)  # copy2 會保留原檔 metadata

    # print(f"✅ Copied and renamed: {src_path.name} → {new_path}")


def folder_copy():
    current_dir = Path(__file__).resolve().parent

    # 來源：同層目錄下的 Lotto_Data_Folder
    source_dir = current_dir / 'Lotto_Data_Folder'

    # 目的地：跳到 msk_2026_X → A_msk_lotto_data_folder
    save_path_1 = current_dir.parent / 'A_msk_lottery_data_folder'
    
    # 建立目的地資料夾（如尚未存在）
    os.makedirs(save_path_1, exist_ok=True)
    

    # 確認來源資料夾存在
    if not source_dir.exists():
        print(f"⚠️ Lotto_Data_Folder 資料夾不存在：{source_dir}")
        return False

    csv_files = list(source_dir.glob("*.csv"))
    
    if not csv_files:
        print("⚠️ 找不到任何 CSV 檔案。")
        return False
    
    
    # print("📂 以下 CSV 已複製：")
    

    # for file in csv_files:
        # shutil.copy(file, save_path_1)
        # print(f"  ✅ copy 1 = {file.name}")
        
        # 如果是 M2，就額外 rename 並 copy 到 save_path_3
        # if file.name == 'M2_last_upgrade_lotto_data.csv':
            # copy_and_rename_pathlib(file, save_path_1, "M2_lotto_history.csv")

            # print(f"  ✅ copy 2 = {file.name}")
    m1 = current_dir / 'Lotto_Data_Folder'/'M1_ZH_lotto_data.csv'
    m2 = current_dir / 'Lotto_Data_Folder'/'M2_last_upgrade_lotto_data.csv'
    m3 = current_dir / 'Lotto_Data_Folder'/'M3_lotto_prize_results.csv'
    m4 = current_dir / 'Lotto_Data_Folder'/'M4_lotto_prize_summary.csv'
    shutil.copy(m1, save_path_1)
    shutil.copy(m2, save_path_1)
    shutil.copy(m3, save_path_1)
    shutil.copy(m4, save_path_1)
    # print(f"  ✅ copy m1 = {m1.name}")
    # print(f"  ✅ copy m2 = {m2.name}")
    # print(f"  ✅ copy m3 = {m3.name}")
    # print(f"  ✅ copy m4 = {m4.name}")
    
    return True

def main():
    if folder_copy():
        # if copy 成功，才回傳 True
        return True
    else:
        return False
        #     ''')

if __name__ == "__main__":
    main()
