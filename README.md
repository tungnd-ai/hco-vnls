# Dashboard phân bổ ngân sách khuyến mãi

Bản app-only HCO-VNLS V5 cho Store 44, 15 nhóm, kỳ lịch sử 16–22/08/2017. Giá trị tiền là USD tham chiếu/mô phỏng, không phải lợi nhuận kế toán thực. Mỗi lần bấm chạy thực thi HCO rồi VNLS; không huấn luyện lại CatBoost, không đọc nghiệm tối ưu đã lưu.

## Bản đồng bộ cuối ngày 24/10/2026

Gói dùng cùng mã ứng dụng, mô-đun và cấu hình với project chính. Giữ các nhãn USD ngắn; dòng giải thích luôn có ở đầu giao diện xác nhận tiền là tham chiếu/mô phỏng, không phải kế toán thực. Không thay công thức hoặc tham số nghiên cứu.

Manifest kiểm tra 19 tệp chạy/đầu vào cùng README và .gitignore: 21 mục mã băm; tính cả chính manifest, gói có 22 tệp. Không tải thêm các báo cáo kiểm thử của project vào gói. Hồ sơ nghiệm thu lần đồng bộ được lưu riêng tại `reports/deployment_sync_*` của project gốc; không ghi đè báo cáo lịch sử.

## Cấu trúc repository

```text
app.py
requirements.txt
.gitignore
.streamlit/config.toml
src/__init__.py
src/v5/                  # Các mô-đun khoa học Python
src/v5_ui/               # Trình bày, biểu đồ, điều phối kịch bản
outputs/
  step5_v5_economic_lookup.csv
  step5_v5_family_index.csv
  step5_v5_metadata.json
DEPLOYMENT_MANIFEST.json
README.md
```

Không cần notebook, dữ liệu Kaggle thô, mô hình CatBoost, báo cáo hoặc nghiệm Step 6–8. Chỉ tải nội dung bên trong thư mục này, không tải toàn bộ project khóa luận. Giữ nguyên byte của ba file đầu vào vì ứng dụng kiểm tra SHA-256 trước chạy. Metadata giữ nguyên để bảo toàn nguồn nghiên cứu; một số đường dẫn nguồn trong đó chỉ là xuất xứ, không phải phụ thuộc runtime.

## Chạy cục bộ

Trong môi trường Python riêng, cài `python -m pip install -r requirements.txt`. Chạy từ thư mục repository:

```bash
python -B -m streamlit run app.py --server.address 127.0.0.1 --server.port 8505 --browser.gatherUsageStats false
```

Mặc định ngân sách 768, seed giao diện 42. Bốn kịch bản mặc định 650/768/900/2091; chỉ chạy sau nút xác nhận riêng. Biểu đồ và tải CSV không gọi tối ưu lại. Phiên người dùng riêng; khóa tiến trình chỉ cho một yêu cầu tối ưu hoạt động tại một thời điểm. Nếu bận, người dùng khác nhận thông báo thử lại, không bị nhận kết quả của phiên khác.

## Đưa lên GitHub riêng tư

1. Đăng nhập GitHub, chọn New repository, ví dụ `hco-vnls-v5-dashboard`, chọn **Private**. Tên này là gợi ý, chưa được tạo bởi trợ lý.
2. Chọn Add file → Upload files; tải nội dung bản app-only này. Giữ nguyên cấu trúc `src/`, `outputs/`, `.streamlit/` và các file ẩn cần thiết. Không tải `.env`, secrets, `.venv` hoặc `__pycache__`.
3. Commit vào nhánh `main`. Mở repository kiểm tra có `app.py` ở gốc và đủ ba file CSV/JSON.
4. Repository nguồn có thể giữ Private trong khi ứng dụng được chia sẻ Public. Không đổi repository sang Public để khắc phục lỗi quyền một cách tùy tiện.

## Streamlit Community Cloud

1. Mở https://share.streamlit.io, đăng nhập tài khoản của bạn.
2. Nếu dùng repository riêng tư, kiểm tra và tự chấp thuận quyền GitHub mà Streamlit yêu cầu. Có thể cần quyền quản trị repository và quyền đọc repo riêng tư/deploy key.
3. Create app → chọn repository, nhánh `main`, entrypoint `app.py`.
4. Advanced settings → chọn **Python 3.11**. Không dùng mặc định mà chưa kiểm tra. Các thư viện đã khóa phiên bản trong requirements; không cần secrets hoặc gói hệ điều hành.
5. Deploy, theo dõi nhật ký cài đặt và khởi động.
6. Settings → Sharing → Who can view this app → **This app is public and searchable**. Repository vẫn có thể Private.
7. Mở URL thật bằng cửa sổ riêng tư chưa đăng nhập. Xác nhận người xem không bị yêu cầu đăng nhập chủ sở hữu.

Tài liệu chính thức đã tham khảo:
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app
- https://docs.streamlit.io/deploy/streamlit-community-cloud/status

Community Cloud dùng Linux; bản sao không phụ thuộc đường dẫn tuyệt đối Windows. Khả năng hoạt động và giới hạn RAM/CPU thực tế cần được kiểm tra trên Cloud sau triển khai, không suy ra chỉ từ kiểm thử Windows. Chưa có URL công khai nào được tạo hoặc xác minh trong gói này; người dùng yêu cầu tự tải lên.
`requirements.txt` khóa thêm Starlette 1.2.1: kiểm tra máy chủ với Python 3.11 phát hiện Starlette 1.9.0 gây lỗi lớp xử lý HTTP của Streamlit 1.58. Không tự bỏ khóa này khi triển khai; nếu cập nhật thư viện cần kiểm tra khởi động máy chủ thật, không chỉ kiểm thử hàm.

## Nghiệm thu trước khi chèn link vào Word

- B = 768: chi phí 742; còn lại 26; lợi nhuận tăng thêm 8420.902173667862; uplift 8518.410221693824; cải thiện VNLS khoảng 34.395664%; 8 bước nhận, 11 lượt.
- B = 2091: kiểm tra theo kết quả chạy thật; ví dụ đã xác minh toàn mức 3, chi phí 2091, lợi nhuận 14911.037776894607, cải thiện 0%, 0 bước nhận, 3 lượt N1–N3.
- Thử bốn kịch bản, biểu đồ, cả hai CSV; đổi đầu vào kiểm tra ẩn kết quả cũ; ngân sách 0 phải báo lỗi.
- Kiểm tra link từ thiết bị/tài khoản khác. Chỉ chép URL thực tế đã mở được vào Word, không dùng URL minh họa.

## Cập nhật và phục hồi

Mỗi lần cập nhật: kiểm thử project gốc, tạo lại bản app-only theo danh sách cho phép, tải đúng các file đã thay đổi lên nhánh Cloud đang theo dõi. GitHub commit mới sẽ kích hoạt cập nhật; thay requirements có thể cần cài lại môi trường. Không thay dữ liệu để ép qua kiểm tra mã băm.

Nếu lỗi: mở Manage app → logs; kiểm tra phiên bản Python, requirements, cấu trúc file, tên chữ hoa/thường và ba file đầu vào. Nếu quá tải, chờ/reboot app rồi kiểm tra lại; không giảm vòng HCO hoặc bỏ lân cận VNLS. Có thể quay về commit triển khai trước trên repository app-only. Không sửa notebook/output nghiên cứu để sửa lỗi hosting.

## Giới hạn khoa học

Nhu cầu là dự báo, không phải doanh thu; uplift không chứng minh nhân quả. Profit đã trừ chi phí, không trừ lần hai. Mức 0–3 không phải % giảm giá. Khả thi không chứng minh tối ưu toàn cục. Một seed và bốn ngân sách không chứng minh ưu thế thống kê hoặc tốt hơn GA/PSO/DE. Không bảo đảm tìm thấy nghiệm khả thi với mọi ngân sách/seed. 2.091 USD là ngưỡng chi phí từ bảng hiện tại, không phải ngân sách kinh doanh tối ưu đã được xác lập.
