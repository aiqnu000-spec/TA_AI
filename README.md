# TA_AI – Retrieval-Augmented Generation (RAG)

> Hệ thống hỏi đáp thông minh dựa trên tài liệu cá nhân, ứng dụng kiến trúc Retrieval-Augmented Generation (RAG), kết hợp mô hình Embedding, cơ sở dữ liệu Vector và mô hình ngôn ngữ lớn (LLM).

---

## 1. Giới thiệu và khái niệm

### 1.1. RAG là gì?

**Retrieval-Augmented Generation (RAG)** là một phương pháp kết hợp giữa kỹ thuật truy xuất thông tin (Information Retrieval) và mô hình ngôn ngữ lớn (Large Language Model – LLM).

Thay vì để mô hình ngôn ngữ tự trả lời hoàn toàn dựa trên kiến thức đã được huấn luyện, RAG cho phép hệ thống tìm kiếm thông tin từ một nguồn tài liệu bên ngoài, sau đó sử dụng những thông tin tìm được làm ngữ cảnh để tạo câu trả lời.

Một hệ thống RAG cơ bản bao gồm hai giai đoạn chính:

- **Indexing:** Đọc, xử lý, chia nhỏ tài liệu và chuyển đổi nội dung thành vector để lưu trữ.
- **Retrieval & Generation:** Tiếp nhận câu hỏi, tìm kiếm những đoạn tài liệu liên quan và sử dụng LLM để tạo câu trả lời.

### 1.2. Giới thiệu dự án TA_AI

TA_AI là dự án xây dựng hệ thống hỏi đáp thông minh dựa trên kho tài liệu do người dùng cung cấp.

Hệ thống hướng đến việc giúp người dùng khai thác thông tin từ các tài liệu cá nhân mà không cần đọc toàn bộ nội dung thủ công.

Dự án sử dụng mô hình RAG để tìm kiếm thông tin có liên quan trước khi đưa dữ liệu vào mô hình ngôn ngữ lớn. Nhờ đó, câu trả lời được định hướng dựa trên nội dung tài liệu thay vì chỉ dựa vào kiến thức tổng quát của mô hình.

**Mục tiêu của dự án:**

- Xây dựng hệ thống đọc và xử lý nhiều định dạng tài liệu.
- Tự động phân tích, chia nhỏ và lập chỉ mục nội dung.
- Tìm kiếm thông tin theo ngữ nghĩa.
- Sinh câu trả lời dựa trên nội dung đã truy xuất.
- Hạn chế việc mô hình tự suy đoán khi tài liệu không có thông tin phù hợp.
- Cung cấp thông tin nguồn để hỗ trợ kiểm chứng câu trả lời.

### 1.3. Phạm vi hiện tại

Phiên bản hiện tại tập trung xây dựng lõi RAG và vận hành thông qua giao diện dòng lệnh (CLI).

Các chức năng được tổ chức thành những module riêng biệt để thuận tiện cho việc kiểm thử, bảo trì và phát triển những giai đoạn tiếp theo.

---

## 2. Hướng dẫn cài đặt và chạy dự án

### 2.1. Yêu cầu hệ thống

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ lập trình | Python |
| Mô hình ngôn ngữ | Qwen 2.5 |
| Embedding Model | BGE-M3 |
| Vector Database | ChromaDB |
| Database quản lý | SQLite |
| AI Runtime | Ollama |
| Kiểm thử | Pytest |

Yêu cầu cài đặt:
- Python 3.14 theo cấu hình hướng dẫn hiện tại.
- Ollama.
- Git.
- Kết nối Internet khi tải thư viện và mô hình lần đầu.

### 2.2. Tải mã nguồn

```bash
git clone https://github.com/aiqnu000-spec/TA_AI.git

cd TA_AI
```

### 2.3. Tạo môi trường ảo

Trên Windows:

```bash
py -3.14 -m venv .venv

.venv\Scripts\activate
```

### 2.4. Cài đặt thư viện

```bash
python -m pip install --upgrade pip

pip install -r requirements.txt
```

### 2.5. Cài đặt và tải mô hình AI

Cài đặt Ollama từ:

https://ollama.com/

Tải mô hình Embedding:

```bash
ollama pull bge-m3
```

Tải mô hình ngôn ngữ:

```bash
ollama pull qwen2.5:3b
```

Đảm bảo Ollama đang hoạt động trước khi chạy các chức năng RAG.

### 2.6. Chuẩn bị tài liệu

Tạo thư mục lưu trữ tài liệu:

```text
data/
└── documents/
```

Đưa các tài liệu cần xử lý vào thư mục `data/documents/`.

Các định dạng hiện được hỗ trợ:

- PDF
- DOCX
- TXT
- MD

**Lưu ý:** PDF dạng ảnh hoặc tài liệu scan chưa được hỗ trợ OCR trong giai đoạn hiện tại.

### 2.7. Kiểm tra và khởi chạy

Kiểm tra kết nối Ollama và các mô hình:

```bash
python rag_cli.py check
```

Nạp tài liệu vào hệ thống:

```bash
python rag_cli.py ingest
```

Liệt kê tài liệu đã được lập chỉ mục:

```bash
python rag_cli.py docs
```

Xem thống kê:

```bash
python rag_cli.py stats
```

Đặt câu hỏi:

```bash
python rag_cli.py ask "Nội dung bạn muốn tìm kiếm"
```

Bật chế độ Debug để xem kết quả truy xuất:

```bash
python rag_cli.py ask "Nội dung câu hỏi" --debug
```

Trò chuyện liên tục:

```bash
python rag_cli.py chat
```

Thoát chế độ trò chuyện bằng lệnh:

```text
exit
```

### 2.8. Kiểm thử hệ thống

Chạy bộ đánh giá RAG:

```bash
python rag_eval.py
```

Đánh giá cả bước sinh câu trả lời bằng LLM:

```bash
python rag_eval.py --llm
```

Chạy kiểm thử:

```bash
pytest -q
```

---

## 3. Cấu trúc thư mục dự án

```text
TA_AI/
│
├── cmd_module/
│
├── config/
│
├── rag/
│   ├── __init__.py
│   ├── settings.py
│   ├── loaders.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── store.py
│   ├── ingest.py
│   └── query.py
│
├── tests/
│
├── eval/
│   └── questions.json
│
├── data/
│   ├── documents/
│   └── index/
│
├── rag_cli.py
├── rag_eval.py
├── requirements.txt
└── README.md
```

### Chức năng các thành phần

| Thành phần | Chức năng |
|---|---|
| `cmd_module/` | Module lệnh và các thành phần liên quan |
| `config/` | Quản lý cấu hình |
| `rag/` | Chứa các module xử lý lõi RAG |
| `tests/` | Chứa các chương trình kiểm thử |
| `eval/` | Chứa dữ liệu câu hỏi đánh giá |
| `data/documents/` | Lưu trữ tài liệu đầu vào |
| `data/index/` | Lưu trữ dữ liệu lập chỉ mục |
| `rag_cli.py` | Điểm khởi chạy hệ thống RAG |
| `rag_eval.py` | Chương trình đánh giá chất lượng RAG |
| `requirements.txt` | Danh sách thư viện cần thiết |

### Các module trong thư mục rag/

**`settings.py`**

Quản lý các thông số cấu hình như đường dẫn tài liệu, mô hình AI, kích thước Chunk, số lượng kết quả truy xuất và ngưỡng tương đồng.

**`loaders.py`**

Đọc và làm sạch nội dung từ các định dạng PDF, DOCX, TXT và Markdown.

**`chunker.py`**

Chia nội dung tài liệu thành những đoạn văn bản nhỏ hơn, có cơ chế Overlap để duy trì ngữ cảnh.

**`embedder.py`**

Sử dụng Ollama và mô hình BGE-M3 để chuyển đổi văn bản thành các vector biểu diễn ngữ nghĩa.

**`store.py`**

Quản lý dữ liệu vector bằng ChromaDB và thông tin tài liệu bằng SQLite.

**`ingest.py`**

Điều phối quá trình nạp tài liệu, kiểm tra thay đổi, tạo Chunk, Embedding và cập nhật dữ liệu vào hệ thống.

**`query.py`**

Thực hiện truy xuất thông tin, lọc kết quả, xây dựng ngữ cảnh và gọi mô hình ngôn ngữ để tạo câu trả lời.

---

## 4. Tác dụng và chức năng của hệ thống

### 4.1. Đối với người sử dụng

- Tra cứu thông tin từ nhiều tài liệu trong cùng một kho dữ liệu.
- Đặt câu hỏi bằng ngôn ngữ tự nhiên.
- Tìm kiếm thông tin theo ý nghĩa thay vì chỉ khớp từ khóa.
- Nhận câu trả lời kèm thông tin nguồn.
- Hạn chế câu trả lời không có căn cứ trong tài liệu.
- Tiết kiệm thời gian đọc và tổng hợp thông tin.

### 4.2. Đối với quá trình quản lý tài liệu

- Hỗ trợ nhiều định dạng tài liệu.
- Tự động chia nhỏ nội dung.
- Tạo vector biểu diễn ngữ nghĩa.
- Lưu trữ và truy xuất dữ liệu bằng Vector Database.
- Theo dõi tài liệu đã xử lý.
- Phát hiện tài liệu mới, tài liệu thay đổi và tài liệu bị xóa.
- Hạn chế xử lý lại những tài liệu không thay đổi.

### 4.3. Đối với phát triển hệ thống

Kiến trúc module giúp tách biệt từng nhiệm vụ, hỗ trợ:

- Dễ dàng bảo trì và nâng cấp.
- Kiểm thử độc lập từng thành phần.
- Thay đổi mô hình AI hoặc thông số cấu hình.
- Mở rộng thêm phương thức truy xuất và giao diện sử dụng.

---

## 5. Thuật toán và quy trình xử lý

TA_AI sử dụng kiến trúc Retrieval-Augmented Generation với hai quy trình chính: xử lý tài liệu và truy vấn câu hỏi.

### 5.1. Quy trình xử lý tài liệu (Indexing Pipeline)

**Bước 1: Thu thập tài liệu**

Hệ thống quét thư mục `data/documents/` và xác định các tài liệu có định dạng được hỗ trợ.

**Bước 2: Đọc và chuẩn hóa dữ liệu**

Sử dụng các thư viện tương ứng để trích xuất nội dung từ PDF, DOCX, TXT và MD.

Dữ liệu sau khi trích xuất được chuẩn hóa Unicode NFC, loại bỏ ký tự không cần thiết và xử lý các khoảng trắng dư thừa.

**Bước 3: Chia nhỏ văn bản (Text Chunking)**

Sử dụng thuật toán chia văn bản thành các đoạn nhỏ (Chunking).

Nguyên tắc:
- Ưu tiên chia theo ranh giới đoạn văn.
- Nếu đoạn quá dài, tiếp tục chia theo câu.
- Kết hợp các phần văn bản cho đến khi đạt kích thước mục tiêu.
- Sử dụng Overlap để giữ lại một phần nội dung giữa hai Chunk liên tiếp.

Thông số mặc định:

| Tham số | Giá trị |
|---|---:|
| Chunk Size | 800 ký tự |
| Chunk Overlap | 100 ký tự |

Mỗi Chunk lưu thông tin nguồn và số trang để phục vụ truy xuất và trích dẫn.

**Bước 4: Tạo Embedding**

Sử dụng mô hình BGE-M3 thông qua Ollama để chuyển đổi từng Chunk thành vector số học.

Vector biểu diễn ngữ nghĩa của văn bản, giúp hệ thống tìm kiếm những nội dung có ý nghĩa gần với câu hỏi.

**Bước 5: Lưu trữ dữ liệu**

Sử dụng hai hệ thống lưu trữ:

- ChromaDB: Lưu nội dung Chunk, vector Embedding và Metadata.
- SQLite: Quản lý thông tin tài liệu, mã SHA-256, trạng thái xử lý, số lượng Chunk và thời gian lập chỉ mục.

**Bước 6: Đồng bộ tài liệu**

Hệ thống kiểm tra dung lượng, thời gian chỉnh sửa và mã SHA-256 để xác định tài liệu mới, tài liệu thay đổi hoặc không thay đổi.

Những tài liệu đã bị xóa khỏi thư mục nguồn cũng được loại bỏ khỏi chỉ mục.

### 5.2. Quy trình truy vấn và sinh câu trả lời (Retrieval & Generation)

**Bước 1: Tiếp nhận câu hỏi**

Người dùng nhập câu hỏi bằng ngôn ngữ tự nhiên.

**Bước 2: Chuyển câu hỏi thành Embedding**

Sử dụng cùng mô hình BGE-M3 để chuyển câu hỏi thành vector.

**Bước 3: Truy xuất thông tin (Vector Search)**

Sử dụng ChromaDB để tìm kiếm các Chunk có vector gần nhất với vector câu hỏi.

Hệ thống sử dụng phép đo Cosine Similarity để đánh giá độ tương đồng.

Công thức:

\[
\operatorname{CosSim}(A,B)=
\frac{A\cdot B}{\|A\|\|B\|}
\]

Trong đó:
- A: Vector của câu hỏi.
- B: Vector của đoạn tài liệu.
- Giá trị càng gần 1 thể hiện mức độ tương đồng càng cao.

**Bước 4: Lọc kết quả**

Lấy tối đa Top-K đoạn tài liệu có độ tương đồng cao nhất.

Chỉ những đoạn đạt ngưỡng `MIN_SCORE` mới được đưa vào ngữ cảnh.

Thông số mặc định:

- Top-K: 5.
- MIN_SCORE: 0.40.

Nếu không có đoạn tài liệu nào đạt ngưỡng, hệ thống trả về thông báo không tìm thấy thông tin phù hợp và không gọi LLM.

**Bước 5: Xây dựng Context**

Ghép những đoạn tài liệu đã truy xuất thành phần ngữ cảnh.

Mỗi đoạn được đánh số và gắn thông tin nguồn để mô hình có thể tham chiếu trong câu trả lời.

**Bước 6: Sinh câu trả lời bằng LLM**

Đưa System Prompt, Context và câu hỏi vào mô hình Qwen 2.5 thông qua Ollama.

Mô hình tạo câu trả lời dựa trên ngữ cảnh được cung cấp, đồng thời được hướng dẫn không sử dụng kiến thức bên ngoài hoặc tự suy đoán khi tài liệu không đủ thông tin.

**Bước 7: Trả kết quả**

Hệ thống hiển thị câu trả lời và các nguồn tài liệu liên quan, bao gồm thông tin tên file, trang hoặc đoạn Chunk.

### 5.3. Sơ đồ tổng quan thuật toán

```text
             TÀI LIỆU ĐẦU VÀO
                     |
                     v
             Đọc và trích xuất
                     |
                     v
             Chuẩn hóa văn bản
                     |
                     v
                Chunking
              (Size + Overlap)
                     |
                     v
             Embedding BGE-M3
                     |
                     v
              Lưu vào ChromaDB
              + SQLite Metadata
                     |
                     |
              NGƯỜI DÙNG ĐẶT CÂU HỎI
                     |
                     v
             Embedding câu hỏi
                     |
                     v
              Vector Search
                     |
                     v
             Cosine Similarity
                     |
                     v
              Lọc theo MIN_SCORE
                     |
              +------+------+
              |             |
           Không đạt       Đạt
              |             |
              v             v
          NOT_FOUND      Top-K Context
                            |
                            v
                      System Prompt
                            |
                            v
                      Qwen 2.5 LLM
                            |
                            v
                    Câu trả lời + Nguồn
```

### 5.4. Thuật toán đánh giá

Dự án có module đánh giá chất lượng truy xuất thông tin thông qua bộ câu hỏi mẫu trong `eval/questions.json`.

Các tiêu chí đánh giá bao gồm:

- **Hit@K:** Kiểm tra tài liệu mong muốn có xuất hiện trong Top-K kết quả hay không.
- **Ranking:** Kiểm tra thứ hạng của tài liệu được tìm thấy.
- **Threshold Filtering:** Kiểm tra khả năng loại bỏ những kết quả không đủ độ tương đồng.
- **Refusal Evaluation:** Kiểm tra hệ thống có từ chối trả lời khi thông tin không tồn tại trong tài liệu hay không.
- **LLM Evaluation:** Đánh giá câu trả lời dựa trên từ khóa mong đợi và khả năng từ chối.

---

## 6. Công nghệ sử dụng

| Công nghệ | Vai trò |
|---|---|
| Python | Ngôn ngữ phát triển chính |
| Ollama | Môi trường chạy mô hình AI cục bộ |
| BGE-M3 | Mô hình tạo Embedding |
| Qwen 2.5 | Mô hình ngôn ngữ sinh câu trả lời |
| ChromaDB | Cơ sở dữ liệu vector |
| SQLite | Lưu trữ Metadata và trạng thái tài liệu |
| PyMuPDF | Đọc và trích xuất nội dung PDF |
| python-docx | Đọc tài liệu DOCX |
| python-dotenv | Quản lý cấu hình môi trường |
| Pytest | Kiểm thử phần mềm |

---

## 7. Giới hạn hiện tại và định hướng phát triển

### Giới hạn hiện tại

- Hệ thống đang tập trung vào lõi RAG chạy bằng CLI.
- Chưa hỗ trợ OCR cho PDF dạng ảnh hoặc scan.
- Chất lượng truy xuất phụ thuộc vào chất lượng tài liệu, mô hình Embedding và ngưỡng tương đồng.
- Câu trả lời phụ thuộc vào nội dung được truy xuất và khả năng của mô hình ngôn ngữ.
- Chưa thể đảm bảo loại bỏ hoàn toàn hiện tượng Hallucination.

### Định hướng phát triển

- Phát triển giao diện Web để người dùng tương tác trực quan.
- Xây dựng hệ thống quản lý và tải lên tài liệu.
- Tích hợp OCR cho tài liệu scan.
- Cải thiện thuật toán Chunking và Retrieval.
- Nghiên cứu Hybrid Search kết hợp tìm kiếm từ khóa và tìm kiếm ngữ nghĩa.
- Nghiên cứu Reranking để nâng cao chất lượng kết quả.
- Mở rộng bộ dữ liệu và phương pháp đánh giá.
- Tối ưu hiệu năng để phù hợp với máy tính có cấu hình thấp.

---

## 8. Giấy phép

Dự án được quản lý theo giấy phép được công bố trong file `LICENSE` tại thư mục gốc của repository.

---

## 9. Repository

**GitHub:** https://github.com/aiqnu000-spec/TA_AI

---

*TA_AI – Retrieval-Augmented Generation System.*
