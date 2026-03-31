import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from urllib.parse import urljoin
import time

import httpx
from bs4 import BeautifulSoup

# Cấu hình
BASE_URL = "https://tuyensinh.ctu.edu.vn" #url trang web
DATA_DIR = Path(__file__).parent / "data" #thư mục chứa dữ liệu
DATA_DIR.mkdir(exist_ok=True) #tạo thư mục nếu chưa có

# Headers để giả lập browser
HEADERS = {#headers để giả lập trình duyệt
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"#user-agent để giả lập trình duyệt tranh bi chan khi vo qua nhieu
}
# vao lay du lieu bang cách gia lap moi lan lay 3 lan neu ko dc thi cho qua toi link tiep theo
def fetch_page(url: str, retries: int = 3) -> str:#ham tai noi dung trang HTML
    """Tải nội dung trang HTML (có hỗ trợ Retry và chống Rate Limit)"""#ham tai noi dung trang HTML
    for attempt in range(retries):#lap lai so lan retry
        try:
            time.sleep(1) # Nghỉ 1s tránh việc server ngắt SSL ngẫu nhiên
            # Sử dụng httpx.Client để chủ động đóng connection sau khi xong hoặc reset nếu lỗi
            with httpx.Client(timeout=15.0) as client:#client de ket noi den trang web
                response = client.get(url, headers=HEADERS)#gui request den trang web
                if response.status_code == 404:#kiem tra neu loi 404
                    print(f"❌ Lỗi 404: Trang không tồn tại - {url}")#in ra loi 404
                    return "" # Loại bỏ trang do không còn tồn tại
                response.raise_for_status()#kiem tra loi
                return response.text#tra ve noi dung trang
        except Exception as e:#kiem tra loi
            print(f"⚠️ Lỗi (lần {attempt + 1}/{retries}) - {url}: {e}")#in ra loi
            time.sleep(2) # Chờ vài giây trước khi thử lại
    print(f"❌ Bỏ qua URL do thử lại thất bại quá nhiều lần: {url}")#in ra loi
    return ""

#trich xuat tru lieu trang html xoa het hamm scrip la src html
def extract_text_from_html(html: str) -> str:#ham trich xuat text tu HTML
    try:
        soup = BeautifulSoup(html, 'html.parser')#tao soup de phan tich HTML

        # Ưu tiên lấy khu vực nội dung chính nếu có.
        main = soup.find('main') or soup.find('article') or soup.body or soup

        # Xóa các tag/script/style/metadata và khu vực điều hướng.
        for tag in main(['script', 'style', 'meta', 'link', 'svg', 'noscript']):#xoa cac the html ko can thiet
            tag.decompose()

        for tag in main.find_all(['nav', 'footer', 'header', 'aside', 'form']):#xoa cac the html ko can thiet
            tag.decompose()

        # Xóa các block theo class/id thường là menu/sidebars.
        for tag in main.find_all(True):#xoa cac the html ko can thiet
            if tag is None or not hasattr(tag, 'get'):#kiem tra neu the html ko ton tai hoac ko co thuoc tinh get
                continue#bo qua
            try:
                classes = tag.get('class') or []#lay class cua the html
                tag_id = tag.get('id') or ""#lay id cua the html
                class_id = " ".join(classes) + " " + tag_id#noi class va id lai
            except Exception:#kiem tra loi
                # Some nodes can behave unexpectedly; skip them.
                continue#bo qua
            class_id = class_id.lower()#chuyen class_id ve chu thuong
            if any(key in class_id for key in ['menu', 'nav', 'breadcrumb', 'sidebar', 'footer', 'header', 'pagination', 'search', 'share', 'social']):#kiem tra xem class_id co chua cac tu khoa nao ko
                tag.decompose()#xoa the html

        text = main.get_text(separator='\n', strip=True)#lay text tu the html

        # Làm sạch text, bỏ trùng lặp và dòng nhiễu.các từ/phrase rác thường gặp trên web (menu, button, navbar).
        noise = {
            'trang chủ', 'tin mới', 'danh mục', 'tìm kiếm', 'xem thêm', 'xem thêm...',
            'liên hệ', 'đăng nhập', 'đăng ký', 'đăng xuất', 'chia sẻ', 'theo dõi'
        }
        cleaned: List[str] = []#cleaned: chua ket qua khi doc thanh 1 list
        seen = set()#seen: chua cac tu da xuat hien de tranh lap lai
        for raw in text.split('\n'):#tach text thanh cac dong
            line = re.sub(r"\s+", " ", raw).strip()#loai bo khoang trang thua
            if not line:#kiem tra neu dong trong
                continue#bo qua
            lower = line.lower()
            if lower in noise:#kiem tra xem dong co chua cac tu khoa nao ko
                continue#bo qua
            if len(line) < 4:#kiem tra neu do dai dong nho hon 4
                continue#bo qua
                continue
            if line.startswith(('===', '---', '***')):#kiem tra xem dong co chua cac ki tu dac biet ko
                continue#bo qua
            if lower in seen:#kiem tra xem dong co chua cac tu da xuat hien ko
                continue#bo qua
            seen.add(lower)#them dong vao danh sach da xuat hien
            cleaned.append(line)#them dong vao danh sach ket qua

        return '\n'.join(cleaned)#noi cac dong lai thanh chuoi
    except Exception as e:#kiem tra loi
        print(f"❌ Lỗi parse HTML: {e}")#in ra loi
        return ""


def clean_text(text: str) -> str:#ham lam sach text
    """Làm sạch text: xóa Cyrillic, normalize whitespace, remove junk"""
    # 1. Xóa Cyrillic (encoding lỗi từ scraper)
    text = re.sub(r'[\u0400-\u04FF]', '', text)#xoa cac ki tu cyrillic
    
    # 2. Xóa HTML tags (nếu có sót)
    text = re.sub(r'<[^>]+>', '', text)#xoa cac the html
    
    # 3. Normalize multiple spaces → 1 space
    text = re.sub(r' {2,}', ' ', text)#loai bo khoang trang thua
    
    # 4. Normalize newlines: nhiều empty lines → 1 newline
    text = re.sub(r'\n\s*\n+', '\n', text)#loai bo khoang trang thua
    
    # 5. Strip whitespace từng line + remove junk lines
    lines = [ln.strip() for ln in text.split('\n')]#tach text thanh cac dong
    lines = [ln for ln in lines if len(ln) > 3 and ln not in {#kiem tra xem do dai dong nho hon 4 va khong chua cac tu khoa nao ko
        'trang chủ', 'tin mới:', 'danh mục', 'tìm kiếm', 'xem thêm', 
        'liên hệ', 'thông báo', 'phu luc'
    }]
    
    return '\n'.join(lines)#noi cac dong lai thanh chuoi


def scrape_homepage() -> str:#ham lay trang chu
    """Scrape trang chủ"""
    print("🔄 Đang tải trang chủ...")#in ra thong bao
    html = fetch_page(BASE_URL)#lay trang chu
    return extract_text_from_html(html)#trich xuat text tu trang chu

#extract_major_videos la ham trich xuat video theo nganh tu HTML
def extract_major_videos(html: str, page_url: str) -> List[Dict[str, str]]:#ham trich xuat video theo nganh tu HTML
    """Trích xuất video theo ngành từ HTML (nếu có)."""
    results: List[Dict[str, str]] = []#results: chua ket qua khi doc thanh 1 list
    if not html:#kiem tra neu html trong
        return results#tra ve results

    soup = BeautifulSoup(html, 'html.parser')#tao soup de phan tich HTML
    seen = set()#seen: chua cac tu da xuat hien de tranh lap lai

    for video in soup.find_all('video'):#tim tat ca video
        source = video.find('source')#tim source
        src = source.get('src', '').strip() if source else ''#lay src
        if not src:#kiem tra neu src trong
            continue#bo qua

        video_url = urljoin(page_url, src)#noi page_url va src lai
        if video_url in seen:#kiem tra xem video_url co chua cac tu da xuat hien ko
            continue#bo qua
        seen.add(video_url)#them video_url vao danh sach da xuat hien

        poster = video.get('poster', '').strip()#lay poster
        poster_url = urljoin(page_url, poster) if poster else ''#noi page_url va poster lai

        # Tìm container gần nhất để lấy tên ngành, mã ngành, link chi tiết.
        container = video#container: chua the html gan nhat
        for _ in range(5):#lap 5 lan
            parent = container.parent if container else None#lay parent
            if not parent:#kiem tra neu parent trong
                break#thoat vong lap
            container = parent#gan parent cho container

        title = ''#title: chua ten nganh
        major_code = ''#major_code: chua ma nganh
        detail_url = ''#detail_url: chua link chi tiet

        if container:#kiem tra neu container ton tai
            heading = container.find(['h1', 'h2', 'h3', 'h4'])#tim heading
            if heading:
                title = re.sub(r"\s+", " ", heading.get_text(" ", strip=True)).strip()#loai bo khoang trang thua

            block_text = container.get_text("\n", strip=True)#lay text tu the html
            m = re.search(r"Mã\s*ngành\s*[:：]\s*([0-9A-Za-z]+)", block_text, flags=re.IGNORECASE)#tim ma nganh
            if m:
                major_code = m.group(1).strip()#lay ma nganh

            # Ưu tiên link có chữ "chi tiết".
            detail_a = container.find('a', string=re.compile(r"chi\s*tiết", re.IGNORECASE))
            if not detail_a:
                detail_a = container.find('a', href=True)
            if detail_a and detail_a.get('href'):
                detail_url = urljoin(page_url, detail_a.get('href').strip())

        results.append(
            {
                "title": title,
                "major_code": major_code,
                "video_url": video_url,
                "poster_url": poster_url,
                "detail_url": detail_url,
                "page_url": page_url,
            }
        )

    return results


def scrape_all_pages() -> tuple:
    """Scrape tất cả các trang của website - URLs hoàn chỉnh"""
    pages_to_scrape = {
        "01_trang_chu": BASE_URL,
        "02_thong_tin_tuyen_sinh": f"{BASE_URL}/thong-tin-tuyen-sinh",
        "03_phuong_thuc_xet_tuyen": "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/943-phuong-thuc-xet-tuyen.html",
        "04_phuong_thuc_1": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen/937-phuong-thuc-1.html",
        "05_phuong_thuc_2": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen/938-phuong-thuc-2.html",
        "06_phuong_thuc_3": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen/939-phuong-thuc-3.html",
        "07_phuong_thuc_4": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen/947-phuong-thuc-4.html",
        "08_phuong_thuc_5": "https://tuyensinh.ctu.edu.vn/phuong-thuc-xet-tuyen/1046-phuong-thuc-5.html",
        "09_dai_hoc_chinh_quy": f"{BASE_URL}/dai-hoc-chinh-quy",
        "10_chuong_trinh_tien_tien_cq": "https://tuyensinh.ctu.edu.vn/dai-hoc-chinh-quy/chuong-trinh-tien-tien.html",
        "11_chuong_trinh_chat_luong_cao_cq": "https://tuyensinh.ctu.edu.vn/dai-hoc-chinh-quy/chuong-trinh-chat-luong-cao.html",
        "12_chuong_trinh_tien_tien": f"{BASE_URL}/chuong-trinh-tien-tien",
        "13_chuong_trinh_chat_luong_cao": f"{BASE_URL}/chuong-trinh-chat-luong-cao",
        # 🔥 Thông tin chính quy chi tiết
        "14_danh_muc_to_hop_xet_tuyen": "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/1126-thong-bao-danh-muc-to-hop-xet-tuyen-dai-hoc-chinh-quy-nam-2026.html",
        "15_lich_thi_nang_khieu": "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/1143-lich-du-kien-to-chuc-thi-cac-mon-nang-khieu-nam-2026.html",
        "16_lich_v_sat": "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/1127-lich-to-chuc-ky-thi-vsat-nam-2026.html",
        "17_quy_tac_quy_doi_diem": "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/1142-quy-ta-c-quy-doi-diem-trong-tuyen-sinh-dai-hoc-chinh-quy-nam-2026.html",
        "18_nguong_dau_vao": "https://tuyensinh.ctu.edu.vn/chuong-trinh-dai-tra/177-thong-tin/1140-nguong-dau-vao-dai-hoc-chinh-quy-nam-2026.html",
        # 🔥 Các chương trình khác
        "19_vua_lam_vua_hoc": "https://ctc.ctu.edu.vn/tuyen-sinh/tuyen-sinh-he-vua-lam-vua-hoc.html",
        "20_tu_xa": "https://ctc.ctu.edu.vn/tuyen-sinh/tuyen-sinh-he-tu-xa.html",
        "21_sau_dai_hoc": "https://gs.ctu.edu.vn/",
        "23_tan_sinh_vien": "https://tansinhvien.ctu.edu.vn/",
        # 🔥 Trang giới thiệu ngành chi tiết (ưu tiên lấy đúng mã tổ hợp từ trang ngành)
        "24_gioi_thieu_an_toan_thong_tin": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1003-an-toan-thong-tin.html",
        # 1. Ngành Chương Trình Chất Lượng Cao
        "25_cnkt_hoa_hoc_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/768-cong-nghe-ky-thuat-hoa-hoc-chat-luong-cao.html",
        "26_cntt_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/748-cong-nghe-thong-tin-chat-luong-cao.html",
        "27_cn_thuc_pham_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/899-cong-nghe-thuc-pham-clc.html",
        "28_kinh_doanh_quoc_te_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/747-kinh-doanh-quoc-te-chat-luong-cao.html",
        "29_ngon_ngu_anh_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/901-ngon-ngu-anh-clc.html",
        "30_kt_dien_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/900-ky-thuat-dien-clc.html",
        "31_kt_phan_mem_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1004-ky-thuat-phan-mem-clc.html",
        "32_kt_xay_dung_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/910-ky-thuat-xay-dung-clc.html",
        "33_kt_dieu_khien_tdh_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1044-ky-thuat-dieu-khien-va-tu-dong-hoa-clc.html",
        "34_qt_dich_vu_dllh_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1000-quan-tri-dich-vu-dllh-clc.html",
        "35_qt_kinh_doanh_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1001-quan-tri-kinh-doanh-clc.html",
        "36_tc_ngan_hang_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/908-tai-chinh-ngan-hang-clc.html",
        "37_httt_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1048-he-thong-thong-tin-chat-luong-cao.html",
        "38_mang_mt_ttdl_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1095-mang-may-tinh-va-truyen-thong-du-lieu-clc.html",
        "39_thu_y_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1099-thu-y-chuong-trinh-chat-luong-cao.html",

        # 2. Ngành công nghệ
        "40_cnkt_hoa_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/551-cong-nghe-ky-thuat-hoa-hoc.html",
        "41_cn_thuc_pham": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/464-cong-nghe-thuc-pham.html",
        "42_kt_co_khi": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/769-ky-thuat-co-khi-co-khi-che-tao-may.html",
        "43_kt_co_dien_tu": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/490-ky-thuat-co-dien-tu.html",
        "44_kt_dien": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/489-ky-thuat-dien.html",
        "45_kt_dien_tu_vien_thong": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/486-ky-thuat-dien-tu-vien-thong.html",
        "46_kt_dieu_khien_tdh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/488-ky-thuat-dieu-khien-va-tu-dong-hoa.html",
        "47_kt_vat_lieu": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/744-ky-thuat-vat-lieu.html",
        "48_kt_xd_ct_thuy": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/753-ky-thuat-xay-dung-cong-trinh-thuy.html",
        "49_logistics": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1002-logistics-quan-ly-chuoi-cung-ung.html",
        "50_ql_cong_nghiep": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/491-quan-ly-cong-nghiep.html",
        "51_kt_xay_dung": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/485-ky-thuat-xay-dung.html",
        "52_kt_y_sinh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1054-ky-thuat-y-sinh.html",
        "53_dbcl_at_thuc_pham": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1096-dam-bao-chat-luong-va-an-toan-thuc-pham.html",
        "54_logistics_s": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1129-logistics-quan-ly-chuoi-cung-ung-s.html",
        "55_kien_truc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1021-kien-truc.html",

        # 3. Ngành Công Nghệ Thông Tin
        "56_at_thong_tin": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1003-an-toan-thong-tin.html",
        "57_cntt": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/496-cong-nghe-thong-tin.html",
        "58_cntt_h": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/847-cong-nghe-thong-tin-h.html",
        "59_he_thong_thong_tin": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/552-he-thong-thong-tin.html",
        "60_kt_phan_mem": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/495-ky-thuat-phan-mem.html",
        "61_mang_mt_ttdl": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/494-m-ng-may-tinh-va-truy-n-thong-d-li-u.html",
        "62_truyen_thong_da_phuong_tien": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/998-truyen-thong-da-phuong-tien.html",
        "63_kh_may_tinh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/493-khoa-hoc-may-tinh.html",
        "64_tt_nhan_tao": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1093-tri-tue-nhan-tao.html",
        "65_kt_co_khi_clc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1145-ky-thuat-co-khi-chuong-trinh-chat-luong-cao.html",
        "66_kt_xd_ct_giao_thong": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1146-ky-thuat-xay-dung-cong-trinh-giao-thong.html",
        "67_tk_vi_mach_ban_dan": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1053-thiet-ke-vi-mach-ban-dan.html",
        "68_duong_sat_toc_do_cao": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1147-duong-sat-toc-do-cao-nganh-ky-thuat-xay-dung-cong-trinh-giao-thong.html",

        # 4. Ngành Khoa Học Chính Trị
        "69_chinh_tri_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/539-chinh-tri-hoc.html",
        "70_triet_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/538-triet-hoc.html",

        # 5. Ngành Khoa Học Tự Nhiên
        "71_cs_sinh_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/546-cong-nghe-sinh-hoc.html",
        "72_cs_sinh_hoc_tt": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/886-cong-nghe-sinh-hoc-chuong-trinh-tien-tien.html",
        "73_hoa_duoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/745-hoa-duoc.html",
        "74_hoa_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/525-hoa-hoc.html",
        "75_vat_ly_ky_thuat": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/528-vat-ly-ky-thuat.html",
        "76_sinh_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/766-sinh-hoc-sinh-hoc.html",
        "77_toan_ung_dung": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/885-toan-ung-dung.html",

        # 6. Ngành Khoa Học Xã Hội
        "78_ngon_ngu_anh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/772-ngon-ngu-anh-ngon-ngu-anh.html",
        "79_ngon_ngu_anh_h": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/843-ngon-ngu-anh-ngon-ngu-anh-h.html",
        "80_ngon_ngu_phap": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/533-ngon-ngu-phap.html",
        "81_nna_phien_dich": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/773-ngon-ngu-anh-phien-dich-bien-dich-tieng-anh.html",
        "82_thong_tin_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/532-thong-tin-hoc.html",
        "83_xa_hoi_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/565-xa-hoi-hoc.html",
        "84_van_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/887-van-hoc.html",
        "85_du_lich": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1051-du-lich.html",
        "86_du_lich_h": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1056-du-lich-h.html",
        "87_tam_ly_hoc_gd": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1097-tam-ly-hoc-giao-duc.html",
        "88_bao_chi": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1052-bao-chi.html",
        "89_du_lich_s": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1131-du-lich-s.html",

        # 7. Ngành Kinh Tế
        "90_ke_toan": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/499-ke-toan.html",
        "91_kiem_toan": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/500-kiem-toan.html",
        "92_kd_nong_nghiep": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/566-kinh-doanh-nong-nghiep.html",
        "93_kd_quoc_te": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/508-kinh-doanh-quoc-te.html",
        "94_kd_thuong_mai": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/750-kinh-doanh-thuong-mai.html",
        "95_kinh_te": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/498-kinh-te.html",
        "96_kt_nong_nghiep_h": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/845-kinh-te-nong-nghiep-h.html",
        "97_kt_nong_nghiep": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/507-kinh-te-nong-nghiep.html",
        "98_marketing": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/505-marketing.html",
        "99_kt_tn_thien_nhien": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/509-kinh-te-tai-nguyen-thien-nhien.html",
        "100_qt_dv_dl_lh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/504-quan-tri-dich-vu-du-lich-va-lu-hanh.html",
        "101_qt_kinh_doanh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/888-quan-tri-kinh-doanh.html",
        "102_qt_kinh_doanh_h": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/844-quan-tri-kinh-doanh-h.html",
        "103_tc_ngan_hang": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/502-tai-chinh-ngan-hang.html",
        "104_thong_ke": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/999-thong-ke.html",
        "105_thuong_mai_dt": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1094-thuong-mai-dien-tu.html",
        "106_ke_toan_s": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1132-ke-toan-s.html",

        # 8. Ngành Luật
        "107_luat": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/763-luat-luat-hanh-chinh.html",
        "108_luat_h": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/846-luat-luat-hanh-chinh-h.html",
        "109_luat_kinh_te": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1020-luat-kinh-te.html",
        "110_luat_dan_su": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1098-luat-dan-su-va-to-tung-dan-su.html",
        "111_luat_s": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1128-luat-luat-hanh-chinh-s.html",

        # 9. Ngành Môi Trường
        "112_kh_moi_truong": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/512-khoa-hoc-moi-truong.html",
        "113_kt_cap_thoat_nuoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1005-ky-thuat-cap-thoat-nuoc.html",
        "114_kt_moi_truong": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/511-ky-thuat-moi-truong.html",
        "115_ql_dat_dai": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/514-quan-ly-dat-dai.html",
        "116_qh_vung_do_thi": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1022-quy-hoach-vung-va-do-thi.html",
        "117_kt_o_to": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1047-ky-thuat-o-to.html",
        "118_ql_tnmt": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/513-quan-ly-tai-nguyen-va-moi-truong.html",

        # 10. Ngành Nông Nghiệp
        "119_bv_thuc_vat": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/470-bao-ve-thuc-vat.html",
        "120_chan_nuoi": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/465-chan-nuoi.html",
        "121_cn_sau_thu_hoach": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/564-cong-nghe-sau-thu-hoach.html",
        "122_cn_rhq_cq": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/469-cong-nghe-rau-hoa-qua-va-canh-quan.html",
        "123_kh_cay_trong": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/774-khoa-hoc-cay-trong-khoa-hoc-cay-trong.html",
        "124_nong_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/468-nong-hoc.html",
        "125_nn_cnc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/906-nong-nghiep-cong-nghe-cao.html",
        "126_ql_dat_phan_bon": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/907-quan-ly-dat-va-cong-nghe-phan-bon.html",
        "127_thu_y": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/466-thu-y.html",
        "128_sinh_hoc_ung_dung": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/751-sinh-hoc-ung-dung.html",

        # 11. Ngành Sư Phạm
        "129_sp_gd_cong_dan": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/537-giao-duc-cong-dan.html",
        "130_sp_gd_the_chat": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/550-giao-duc-the-chat.html",
        "131_sp_gd_tieu_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/475-giao-duc-tieu-hoc.html",
        "132_sp_lich_su": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/479-su-pham-lich-su.html",
        "133_sp_sinh_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/477-su-pham-sinh-hoc.html",
        "134_sp_ngu_van": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/478-su-pham-ngu-van.html",
        "135_sp_dia_ly": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/480-su-pham-dia-ly.html",
        "136_sp_hoa_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/476-su-pham-hoa-hoc.html",
        "137_sp_tieng_anh": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/481-su-pham-tieng-anh.html",
        "138_sp_tieng_phap": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/482-su-pham-tieng-phap.html",
        "139_sp_vat_ly": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/474-su-pham-vat-ly.html",
        "140_sp_tin_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/749-su-pham-tin-hoc.html",
        "141_sp_khtn": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1050-su-pham-khoa-hoc-tu-nhien.html",
        "142_sp_ls_dl": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1101-su-pham-lich-su-dia-ly.html",
        "143_sp_toan_hoc": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/473-su-pham-toan-hoc.html",
        "144_sp_gd_mam_non": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/1049-giao-duc-mam-non.html",

        # 12. Ngành Thủy Sản
        "145_benh_hoc_thuy_san": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/520-benh-hoc-thuy-san.html",
        "146_cb_thuy_san": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/518-cong-nghe-che-bien-thuy-san.html",
        "147_nt_thuy_san": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/519-nuoi-trong-thuy-san.html",
        "148_nt_thuy_san_tt": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/746-nuoi-trong-thuy-san-chuong-trinh-tien-tien.html",
        "149_ql_thuy_san": "https://tuyensinh.ctu.edu.vn/gioi-thieu-nganh/521-quan-ly-thuy-san.html",
    }
    
    data = {}
    major_videos: List[Dict[str, str]] = []
    
    # Khôi phục video_index cũ để không bị mất
    json_path = DATA_DIR / "nganh_video_index.json"
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                old_json = json.load(f)
                major_videos.extend(old_json.get("items", []))
        except Exception:
            pass

    total = len(pages_to_scrape)
    count = 0
    
    for name, url in pages_to_scrape.items():
        count += 1
        
        filepath = DATA_DIR / f"tuyen_sinh_{name}.txt"
        if filepath.exists():
            print(f"⏭️ Bỏ qua [{count}/{total}] {name} (Đã có file)")
            continue
            
        print(f"⏳ Scraping [{count}/{total}] {name}...")
        html = fetch_page(url)
        if html:
            text = extract_text_from_html(html)
            data[name] = text
            major_videos.extend(extract_major_videos(html, url))
            print(f"   ✅ OK ({len(text)} ký tự)")
        else:
            print(f"   ⚠️  Không lấy được (có thể URL không tồn tại)")

    # Khử trùng lặp theo URL video.
    dedup = {}
    for item in major_videos:
        key = item.get("video_url", "")
        if key and key not in dedup:
            dedup[key] = item

    return data, list(dedup.values())

#LUU file thanh txt 
def save_to_file(data: dict, major_videos: List[Dict[str, str]]) -> None:#ham luu file thanh txt save_to_file la ham luu file thanh txt
    """Lưu dữ liệu vào file .txt (với cleaning)"""
    # Lưu từng trang riêng
    for name, content in data.items():#lap qua tung trang
        if content:#kiem tra neu content ton tai
            cleaned = clean_text(content)#loai bo khoang trang thua
            filepath = DATA_DIR / f"tuyen_sinh_{name}.txt"#tao duong dan file
            with open(filepath, 'w', encoding='utf-8') as f:#mo file de ghi
                f.write(f"=== DỮ LIỆU TUYỂN SINH: {name.upper()} ===\n")#ghi ten nganh
                f.write(f"Ngày lấy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")#ghi ngay lay
                f.write(f"Nguồn: {BASE_URL}\n\n")#ghi nguon
                f.write(cleaned)#ghi du lieu da duoc lam sach
            print(f"💾 Lưu: {filepath}")#in ra duong dan file
    
    # Lưu tất cả vào 1 file
    txt_files = sorted([f for f in DATA_DIR.glob("tuyen_sinh_*.txt") if f.name != "tuyen_sinh_2026.txt"])
    all_content = []
    for txt in txt_files:
        with open(txt, 'r', encoding='utf-8') as f:
            all_content.append(f.read().strip())

    filepath_all = DATA_DIR / "tuyen_sinh_2026.txt"
    with open(filepath_all, 'w', encoding='utf-8') as f:
        f.write(f"=== DỮ LIỆU TUYỂN SINH ĐẠI HỌC CẦN THƠ 2026 ===\n")
        f.write(f"Ngày cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Nguồn: {BASE_URL}\n\n")
        f.write("\n\n" + "-"*60 + "\n\n".join(all_content))
    print(f"💾 Lưu toàn bộ: {filepath_all}")

    # Lưu dữ liệu video ngành dạng JSON để chatbot có thể tra cứu trực tiếp.
    if major_videos:#kiem tra neu major_videos ton tai
        json_path = DATA_DIR / "nganh_video_index.json"#tao duong dan file
        with open(json_path, 'w', encoding='utf-8') as f:#mo file de ghi
            json.dump(#ham luu du lieu vao file json
                {
                    "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),#ghi ngay lay
                    "source": BASE_URL,#ghi nguon
                    "total": len(major_videos),#ghi tong so video
                    "items": major_videos,#ghi danh sach video
                },
                f,
                ensure_ascii=False,#khong ghi ki tu dac biet
                indent=2,#ghi du lieu de de doc
            )
        print(f"🎬 Lưu video ngành: {json_path} ({len(major_videos)} mục)")

#cau dan chay
def main():
    """Chạy scraper"""
    print("=" * 60)
    print("🚀 SCRAPER DỮ LIỆU TUYỂN SINH ĐH CẦN THƠ")
    print("=" * 60)
    
    # Scrape dữ liệu
    data, major_videos = scrape_all_pages()
    
    if not data:
        print("❌ Không thể lấy dữ liệu từ website!")
        return
    
    # Lưu dữ liệu
    print("\n📁 Đang lưu dữ liệu...")
    save_to_file(data, major_videos)
    
    print("\n✅ Hoàn thành!")
    print(f"📂 Dữ liệu được lưu trong: {DATA_DIR}")


if __name__ == "__main__":
    main()
