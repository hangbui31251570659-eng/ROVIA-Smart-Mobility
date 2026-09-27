# 🚗 ROVIA – Smart Mobility

**Ứng dụng Trí tuệ Nhân tạo và Fuzzy Logic trong quản trị và tối ưu hóa dịch vụ di chuyển xe máy**

- 👩‍🎓 **Sinh viên:** Bùi Huỳnh Thúy Hằng
- 🆔 **MSSV:** 31251570659
- 👨‍🏫 **Giảng viên hướng dẫn:** GS.TS. Nguyễn Trường Thịnh
- 📚 **Môn học:** Trí Tuệ Nhân Tạo

## 📌 Giới thiệu

ROVIA là prototype Smart Mobility được xây dựng trong phạm vi môn Trí Tuệ Nhân Tạo. Ứng dụng tích hợp các chức năng quản lý tài khoản, đặt chuyến, bản đồ và tìm kiếm địa điểm, định tuyến, thông tin thời tiết, Smart Matching, Live Trip, thanh toán, đánh giá, Rewards, Safety Center và ROVIA AI/Fuzzy Logic trong một ứng dụng thống nhất.

## 🛠️ Công nghệ

- Python
- Flask
- HTML/CSS/JavaScript
- SQLite
- OpenStreetMap
- Nominatim
- OSRM
- Open-Meteo
- Fuzzy Logic

## 🚀 Chức năng chính

- Đăng ký / đăng nhập
- Trang chủ
- Đặt chuyến
- Bản đồ và tìm kiếm địa điểm
- Tuyến đường và tính khoảng cách/thời gian
- Weather & Road Intelligence
- Smart Matching
- Thông tin tài xế
- Live Trip
- Payment Center
- Rating và Problem Report
- Rewards & Loyalty
- Safety Center
- ROVIA AI / Fuzzy Logic
- Driver
- Admin

## 📂 Cấu trúc repository

```text
ROVIA-Smart-Mobility/
├── ROVIA_ONE_APP.py
├── README.md
├── requirements.txt
├── .gitignore
├── docs/
│   └── BAO_CAO_ROVIA_31251570659.docx
└── video/
    └── README.md
```

## ▶️ Chạy ứng dụng

Cài thư viện:

```bash
pip install -r requirements.txt
```

Chạy:

```bash
python ROVIA_ONE_APP.py
```

> File hiện tại được thiết kế để chạy trong Google Colab; code có cơ chế tìm port trống và hiển thị Flask app trong Colab.

## 🎥 Video demo

**Đang cập nhật link video demo.**

Sau khi upload video lên Google Drive hoặc YouTube, đặt liên kết tại đây.

## 📄 Báo cáo

Báo cáo môn học nằm trong thư mục `docs/`.

## 🗺️ Dữ liệu bản đồ và dịch vụ bên ngoài

Prototype sử dụng các dịch vụ bên ngoài để minh họa dữ liệu địa điểm, định tuyến và thời tiết. Khi chạy cần có kết nối Internet.

## ⚠️ Lưu ý

- Database SQLite được tạo tự động khi ứng dụng chạy nên không đưa file `.db` vào repository.
- Tài khoản trong source là **tài khoản demo phục vụ trình diễn**, không phải tài khoản thật.
- Các chức năng GPS tài xế realtime, cổng thanh toán thật và SOS kết nối cơ quan chức năng được trình bày ở mức prototype/mô phỏng theo phạm vi báo cáo.

## Video Demo

[▶️ Xem video demo ROVIA trên YouTube](https://youtu.be/o_yUJ2djhfg?si=jiz_saWJ_7Y60_YA)
