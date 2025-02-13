# Fall Detection System using YOLO & Flask

ระบบตรวจจับการล้มโดยใช้ **YOLOv8**, **Flask**, และ **Firebase** สำหรับ **Jetson Nano และ Windows**

## 🔧 การติดตั้ง
รองรับการติดตั้งบน **Jetson Nano (Ubuntu/Linux)** และ **Windows**

### 🖥️ **ติดตั้งบน Windows**
1. **ดาวน์โหลดโค้ดโปรเจ็กต์**
   ```sh
   git clone https://github.com/your-repo-name/fall-detection.git
   cd fall-detection
   ```
2. **แก้ไขค่า RTSP ใน `main.py`**
   เปิดไฟล์ `main.py` และแก้ไขบรรทัดที่เกี่ยวข้องกับ RTSP URL:
   ```python
   camera_ip = "your_camera_ip"
   username = "your_username"
   password = "your_password"
   rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:554/stream1?transport=tcp"
   ```
   แทนที่ `your_camera_ip`, `your_username`, และ `your_password` ด้วยค่าของคุณเอง

3. **รันสคริปต์ติดตั้ง**
   ดับเบิ้ลคลิกไฟล์ `setup.bat` หรือใช้ Command Prompt:
   ```sh
   setup.bat
   ```
4. **เสร็จสิ้น!** สามารถรันระบบได้ทันที 🎉

---

### 🖥️ **ติดตั้งบน Jetson Nano / Ubuntu**
1. **อัปเดตแพ็กเกจและติดตั้ง Git** *(ถ้ายังไม่มี)*
   ```sh
   sudo apt update && sudo apt install git -y
   ```
2. **โคลนโปรเจ็กต์จาก GitHub**
   ```sh
   git clone https://github.com/your-repo-name/fall-detection.git
   cd fall-detection
   ```
3. **แก้ไขค่า RTSP ใน `main.py`**
   เปิดไฟล์ `main.py` และแก้ไขบรรทัดที่เกี่ยวข้องกับ RTSP URL:
   ```python
   camera_ip = "your_camera_ip"
   username = "your_username"
   password = "your_password"
   rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:554/stream1?transport=tcp"
   ```
   แทนที่ `your_camera_ip`, `your_username`, และ `your_password` ด้วยค่าของคุณเอง

4. **ให้สิทธิ์และรันสคริปต์ติดตั้ง**
   ```sh
   chmod +x setup.sh
   ./setup.sh
   ```
5. **เปิดใช้งาน Virtual Environment** *(ถ้าใช้)*
   ```sh
   source fall_detection_env/bin/activate
   ```
6. **เสร็จสิ้น! สามารถเริ่มใช้งานระบบได้ทันที 🎉**

---

## 🚀 การใช้งาน
### **เริ่มรันเซิร์ฟเวอร์ Flask**
```sh
python main.py
```

### **เข้าถึงวิดีโอสตรีม (Web UI)**
เปิดเบราว์เซอร์และไปที่:
```sh
http://localhost:5000/video_feed/{camera_id}
```

---

## 🛠️ เทคโนโลยีที่ใช้
- **YOLOv8** - ใช้สำหรับตรวจจับการล้ม
- **Flask** - ใช้สำหรับแสดงผลวิดีโอสตรีมมิ่ง
- **Firebase** - ใช้เก็บข้อมูลเหตุการณ์การล้มและแจ้งเตือน
- **OpenCV** - ใช้ประมวลผลภาพจากกล้อง
- **Jetson Nano (รองรับ)** - รองรับการใช้งานบนฮาร์ดแวร์ฝังตัว

---

## 🔗 ข้อมูลเพิ่มเติม
- **YOLOv8 Documentation**: [Ultralytics YOLO](https://docs.ultralytics.com/)
- **Flask Documentation**: [Flask](https://flask.palletsprojects.com/)
- **Firebase Documentation**: [Firebase](https://firebase.google.com/docs)

---

## 🤝 ติดต่อเรา
หากพบปัญหาหรือมีข้อสงสัย สามารถเปิด **Issue** ใน GitHub หรือส่งอีเมลมาที่: `panithankunkaewpd@gmail.com` 🚀

