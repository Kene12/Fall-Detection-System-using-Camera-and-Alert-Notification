import os
import cv2
import json
import jwt
import requests
import threading
from flask import Flask, Response
from ultralytics import YOLO
from collections import deque
import time
import datetime
import firebase_admin
import schedule
from firebase_admin import credentials, firestore, storage

# ตั้งค่า Firebase
current_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(current_dir, "firebase_credentials", "test01-project-c4cc5-firebase-adminsdk-i1si8-8a69f1355f.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {'storageBucket': 'test01-project-c4cc5.appspot.com'})
db = firestore.client()

# สร้างโฟลเดอร์สำหรับเก็บภาพการล้มและก่อนล้ม
fall_folder = os.path.join(current_dir, "images", "fall")
before_fall_folder = os.path.join(current_dir, "images", "before_falling")
os.makedirs(fall_folder, exist_ok=True)
os.makedirs(before_fall_folder, exist_ok=True)

data_file_path = os.path.join(current_dir, "data.txt")

# ชื่อไฟล์สำหรับบันทึกการล้ม
fall_image_path = os.path.join(fall_folder, "fall.jpg")

# ตั้งค่า YOLO
model_path = os.path.join(current_dir, "models", "SitSFBS_best.pt")
model = YOLO(model_path)
# รายชื่อคลาสในโมเดล
class_names = ["Sitting", "Standing", "Falling", "Bed", "Sofa"]
class_colors = {
    0: (255, 0, 0),  # Blue for Sitting
    1: (0, 255, 0),  # Green for Standing
    2: (0, 0, 255),  # Red for Falling
    3: (0, 255, 255),  # Yellow for Bed
    4: (0, 255, 255),  # Yellow for Sofa
}

# ตัวแปรเก็บผลลัพธ์
results = None
stop_processing = False
show_output = True
fall_detected = False
fall_reset_time = 30
last_fall_time = 0

db = firestore.client()
special_zones_active = True  # ตั้งเป็น False เพื่อปิดการทำงานของ special_zones
fall_reset_time = 30  # เวลาระหว่างการล้มแต่ละครั้ง (วินาที)
show_boxes = True  # ตั้งเป็น False เพื่อปิดการแสดงกรอบ

# ตั้งค่ากล้อง
camera_ip = "192.168.137.144"
username = "conmicat"
password = "12345678"
rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:554/stream1?transport=tcp"

# ตัวแปรสำหรับ Flask
app = Flask(__name__)
output_frames = {}
frame_locks = {}
frame_queues = {}
max_frames_per_camera = 15  # จำนวนเฟรมสูงสุดที่เก็บในคิวสำหรับแต่ละกล้อง
frame_offsets = [4, 3, 1]
fall_wait_time = 60

# ฟังก์ชันสำหรับอ่านจำนวนการล้มจากไฟล์
def read_fall_count(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                return int(file.read().strip())
            except ValueError:
                return 0
    return 0

# ฟังก์ชันสำหรับเขียนจำนวนการล้มลงในไฟล์
def write_fall_count(count, file_path):
    with open(file_path, "w") as file:
        file.write(str(count))
    print(f"Updated fall count to: {count} in {file_path}")

# อ่านจำนวนการล้มเริ่มต้น
fall_event_counter = read_fall_count(data_file_path)
print(f"Initial fall count: {fall_event_counter}")

def upload_image_to_firebase(image_path, destination_path):
    bucket = storage.bucket()
    blob = bucket.blob(destination_path)
    blob.upload_from_filename(image_path)
    blob.make_public()
    print(f"File URL: {blob.public_url}")
    return blob.public_url

# ฟังก์ชันเพื่อหาชื่อ document ถัดไป
def get_next_document_name():
    db = firestore.client()
    docs = db.collection('Fall_history').stream()
    existing_docs = [doc.id for doc in docs if doc.id.startswith('Fall_')]
    
    if not existing_docs:
        return 'Fall_1'
    
    max_number = 0
    for doc_name in existing_docs:
        number = int(doc_name.split('_')[1])
        max_number = max(max_number, number)
    
    return f'Fall_{max_number + 1}'

def get_fcm_token():
    db = firestore.client()
    doc_ref = db.collection('fcm_tokens').document('tokenApp')
    doc = doc_ref.get()
    return doc.to_dict().get('token') if doc.exists else None

# ส่งการแจ้งเตือนผ่าน FCM
def send_fcm_notification(image_url, title, body):
    with open(cred_path, 'r') as f:
        service_account = json.load(f)

    payload = {
        'iss': service_account['client_email'],
        'sub': service_account['client_email'],
        'aud': 'https://oauth2.googleapis.com/token',
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600,
        'scope': 'https://www.googleapis.com/auth/firebase.messaging'
    }

    encoded_jwt = jwt.encode(payload, service_account['private_key'], algorithm='RS256')

    response = requests.post('https://oauth2.googleapis.com/token', data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': encoded_jwt
    })

    if response.status_code == 200:
        oauth2_token = response.json()['access_token']
        print(f"Access Token: {oauth2_token}")

        headers = {
            'Authorization': 'Bearer ' + oauth2_token,
            'Content-Type': 'application/json; UTF-8',
        }

        message = {
            'message': {
                'token': get_fcm_token(),
                'notification': {
                    'title': title,
                    'body': body,
                    'image': image_url
                }
            }
        }

        response = requests.post('https://fcm.googleapis.com/v1/projects/test01-project-c4cc5/messages:send', 
                                 headers=headers, 
                                 data=json.dumps(message))

        if response.status_code == 200:
            print('Message sent successfully:', response.json())
        else:
            print('Failed to send message:', response.text)
    else:
        print('Failed to obtain access token:', response.text)

# สร้างข้อมูลที่จะเพิ่ม
data = {
    'date': datetime.datetime.now().strftime('%Y-%m-%d'),
    'time': datetime.datetime.now().strftime('%H:%M:%S'),
}

def is_in_special_zone(fall_box, special_zones):
    # ตรวจสอบว่า special_zones กำลังทำงานหรือไม่
    if not special_zones_active:
        return False  # ไม่ต้องการใช้งาน special_zones
    fx1, fy1, fx2, fy2 = fall_box
    for sx1, sy1, sx2, sy2 in special_zones:
        if not (fx2 < sx1 or fx1 > sx2 or fy2 < sy1 or fy1 > sy2):
            return True  # จุดอยู่ในโซนพิเศษ
    return False

def delete_old_fall_history(days=7):

    db = firestore.client()
    collection_ref = db.collection('Fall_history')
    now = datetime.datetime.now()

    # คำนวณเวลา 7 วันที่ผ่านมา
    cutoff_date = now - datetime.timedelta(days=days)
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')  # แปลงเป็นสตริง

    # Query เอกสารที่มีวันที่น้อยกว่าวันที่ตัดเกณฑ์
    print(f"Checking for records older than {cutoff_date_str} to delete...")
    old_docs = collection_ref.where('date', '<', cutoff_date_str).stream()

    delete_count = 0
    for doc in old_docs:
        print(f"Deleting document: {doc.id}")
        collection_ref.document(doc.id).delete()
        delete_count += 1
    
    if delete_count > 0:
        print(f"Successfully deleted {delete_count} record(s) older than {days} days.")
    else:
        print("No records found that are older than the specified threshold.")

def schedule_task():
    print("Scheduler started: Old records will be deleted every 7 days automatically...")
    schedule.every().day.at("00:00").do(delete_old_fall_history, days=7)  # ตั้งเวลาเที่ยงคืนทุกวัน

    while True:
        schedule.run_pending()  # ตรวจสอบว่ามีงานที่ต้องทำหรือไม่
        time.sleep(1)  # รอ 1 วินาที เพื่อลดโหลด CPU

# ฟังก์ชันเปิดกล้อง
def open_cam(source):
    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG if isinstance(source, str) else 0)
    if not cap.isOpened():
        raise Exception(f"Unable to open camera source: {source}")
    return cap

fall_start_times = {}
fall_detected_flags = {}
last_fall_times = {}
special_zones = {}
# ฟังก์ชันประมวลผลเฟรม
def detection(frame, source_name):
    global fall_event_counter
    if source_name not in fall_start_times:
        fall_start_times[source_name] = None
    if source_name not in fall_detected_flags:
        fall_detected_flags[source_name] = False
    if source_name not in last_fall_times:
        last_fall_times[source_name] = 0
    if source_name not in special_zones:
        special_zones[source_name] = []
    fall_detection_duration = 10  # เวลาที่ต้องจับการล้ม (วินาที)
    fall_reset_time = 30
    
    frame_offsets = [4, 3, 1]
    special_zones_active = True
    results = model(frame)
    fall_detected_now = False  # ใช้ตรวจสอบว่ามีการล้มในเฟรมปัจจุบันหรือไม่
    bed_sofa_timer = {}
    for result in results:
            for box in result.boxes:
                cls = int(box.cls)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                fall_box = (x1, y1, x2, y2)  # Bounding box ของการล้ม
                if is_in_special_zone(fall_box, special_zones[source_name]):
                    print("Falling detected in special zone. No action taken.")
                    continue  # ข้ามการดำเนินการถ้าอยู่ในโซนพิเศษ
                #(

                if show_boxes:
                    color = class_colors.get(cls, (255, 255, 255))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{class_names[cls]} ({cls})"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                #) ลบได้ test
                
                if cls == 0:  
                    fall_detected_flags[source_name] = False
                    fall_start_times[source_name] = None  # รีเซ็ตการจับเวลา

                elif cls == 1:  
                    fall_detected_flags[source_name] = False
                    fall_start_times[source_name] = None  # รีเซ็ตการจับเวลา

                elif cls == 2:  # Falling
                    fall_detected_flags[source_name] = True
                    current_time = time.time()
                    if not fall_detected_flags[source_name] or current_time - last_fall_times[source_name] > fall_reset_time:
                        if fall_start_times[source_name] is None:
                            fall_start_times[source_name] = current_time  # บันทึกเวลาเริ่มต้น
                        elif current_time - fall_start_times[source_name] >= 5:
                            elapsed_time = current_time - fall_start_times[source_name]
                            if elapsed_time >= fall_detection_duration:
                                data = {
                                    'date': datetime.datetime.now().strftime('%Y-%m-%d'),
                                    'time': datetime.datetime.now().strftime('%H:%M:%S'),
                                }
                                document_name = get_next_document_name()
                                db.collection('Fall_history').document(document_name).set(data)
                                fall_event_counter += 1
                                write_fall_count(fall_event_counter, data_file_path)
                                cv2.imwrite(fall_image_path, frame)
                                print(f"Saved fall image: {fall_image_path}")
                                destination_path = f"fall_img/fall/fall_event_{fall_event_counter}.jpg"
                                image_url = upload_image_to_firebase(fall_image_path, destination_path)
                                db.collection('Fall_history').document(document_name).update({'image_url': image_url})
                                before_fall_urls = []
                                for idx, offset in enumerate(frame_offsets):
                                    if len(frame_queues[source_name]) > offset:
                                        before_fall_path = os.path.join(
                                            before_fall_folder, f"before{fall_event_counter}_fall_{idx + 1}.jpg"
                                        )
                                        queued_frame = list(frame_queues[source_name])[-offset - 1]
                                        cv2.imwrite(before_fall_path, queued_frame)
                                        before_fall_dest = f"fall_img/before_falling/before{fall_event_counter}_fall_{idx + 1}.jpg"
                                        before_fall_urls.append(upload_image_to_firebase(before_fall_path, before_fall_dest))
                                if before_fall_urls:
                                    db.collection('Fall_history').document(document_name).update({'image_url_before': before_fall_urls})
                                send_fcm_notification(image_url, 'เหตุการณ์การล้ม', 'รายละเอียดการล้มเกิดขึ้น')
                                fall_start_times[source_name] = None  # รีเซ็ตการจับเวลา
                                last_fall_times[source_name] = current_time  # บันทึกเวลาการล้มครั้งล่าสุด
                                fall_detected_flags[source_name] = True
                elif cls in [3, 4]:  # Bed หรือ Sofa
                    current_time = time.time()
                    zone_key = (x1, y1, x2, y2)  # ใช้ตำแหน่งเป็นกุญแจสำหรับตัวจับเวลา

                    # ถ้าเจอโซนนี้เป็นครั้งแรก ให้ตั้งเวลาเริ่มต้น
                    if zone_key not in bed_sofa_timer:
                        bed_sofa_timer[zone_key] = current_time

                    # ถ้าตำแหน่งนี้อยู่ต่อเนื่องนานพอ (เช่น 5 วินาที)
                    elif current_time - bed_sofa_timer[zone_key] >= 5:  
                        if zone_key not in special_zones[source_name]:
                            special_zones[source_name].append(zone_key)
                            print(f"Added to special_zones: {zone_key}")
                    fall_detected_flags[source_name] = False
                    fall_start_times[source_name] = None
            if special_zones_active:
                for sx1, sy1, sx2, sy2 in special_zones[source_name]:
                    cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), (0, 255, 0), 2)  # สีเขียว
                    cv2.putText(frame, "Special Zone", (sx1, sy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame

# ฟังก์ชันสำหรับ Webcam
def process_webcam(source, source_name):
    global output_frames, frame_locks
    cap = open_cam(source)
    frame_queues[source_name] = deque(maxlen=max_frames_per_camera)
    frame_locks[source_name] = threading.Lock()
    print(f"Webcam {source_name} started.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Webcam {source_name} disconnected. Reconnecting...")
            cap = open_cam(source)
            continue

        frame = cv2.resize(frame, (640, 320))
        frame_queues[source_name].append(frame)
        processed_frame = detection(frame, source_name)

        # บันทึกเฟรมสำหรับการสตรีมผ่าน Flask
        with frame_locks[source_name]:
            output_frames[source_name] = processed_frame
        
        # แสดงเฟรมด้วย OpenCV
        cv2.imshow(f"Webcam {source_name}", processed_frame)
        if cv2.waitKey(1) & 0xFF == 27:  # กด ESC เพื่อออก
            break

    cap.release()
    cv2.destroyAllWindows()

# ฟังก์ชันสำหรับ IP Camera
def process_ip_camera(rtsp_url, source_name):
    global output_frames, frame_locks
    cap = open_cam(rtsp_url)
    frame_queues[source_name] = deque(maxlen=max_frames_per_camera)
    frame_locks[source_name] = threading.Lock()
    print(f"IP Camera {source_name} started.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"IP Camera {source_name} disconnected. Reconnecting...")
            cap = open_cam(rtsp_url)
            continue

        frame = cv2.resize(frame, (640, 320))
        frame_queues[source_name].append(frame)
        processed_frame = detection(frame, source_name)

        # บันทึกเฟรมสำหรับการสตรีมผ่าน Flask
        with frame_locks[source_name]:
            output_frames[source_name] = processed_frame
        
        # แสดงเฟรมด้วย OpenCV
        cv2.imshow(f"IP Camera {source_name}", processed_frame)
        if cv2.waitKey(1) & 0xFF == 27:  # กด ESC เพื่อออก
            break

    cap.release()
    cv2.destroyAllWindows()

# ฟังก์ชันสตรีมเฟรมผ่าน Flask
@app.route('/video_feed/<string:source_name>')
def video_feed(source_name):
    def generate_frames():
        global output_frames, frame_locks
        while True:
            with frame_locks[source_name]:
                if source_name in output_frames:
                    _, buffer = cv2.imencode('.jpg', output_frames[source_name])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                else:
                    time.sleep(0.1)

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Main
if __name__ == "__main__":
    # แยกกล้อง Webcam และ IP Camera
    webcam_sources = {"0": 0}  # Webcam
    ip_camera_sources = {"192.168.137.144": rtsp_url}  # IP Camera

    threads = []

    # เริ่มการประมวลผล Webcam
    for name, source in webcam_sources.items():
        t = threading.Thread(target=process_webcam, args=(source, name))
        t.start()
        threads.append(t)
    
    schedule_thread = threading.Thread(target=schedule_task, daemon=True)
    schedule_thread.start()

    # เริ่มการประมวลผล IP Camera
    for name, source in ip_camera_sources.items():
        t = threading.Thread(target=process_ip_camera, args=(source, name))
        t.start()
        threads.append(t)

    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)

    for t in threads:
        t.join()
