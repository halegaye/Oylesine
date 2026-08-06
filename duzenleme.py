from datetime import datetime
import json
import re


def convert_txt_file_to_json(
    input_txt_file="id_listesi.txt", output_json_file="users.json"
):
    try:
        with open(input_txt_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex ile metindeki tüm Telegram ID sayılarını çek
        found_ids = re.findall(r"\b\d{8,11}\b", content)
        unique_ids = list(dict.fromkeys(found_ids))

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted_users = [
            {
                "id": int(uid),
                "username": "",
                "join_date": current_time,
                "status": "active",
            }
            for uid in unique_ids
        ]

        with open(output_json_file, "w", encoding="utf-8") as f:
            json.dump(formatted_users, f, ensure_ascii=False, indent=4)

        print(
            f"🎉 {len(formatted_users)} adet kullanıcı başarıyla '{output_json_file}' dosyasına aktarıldı!"
        )

    except FileNotFoundError:
        print(f"❌ '{input_txt_file}' dosyası bulunamadı, lütfen adı kontrol et.")


if __name__ == "__main__":
    convert_txt_file_to_json("id_listesi.txt")