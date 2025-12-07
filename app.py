import os
import time
import threading
from flask import Flask, render_template, request, jsonify
import yt_dlp
from moviepy.editor import VideoFileClip

app = Flask(__name__)

# 設定路徑
DOWNLOAD_FOLDER = 'downloads'
OUTPUT_FOLDER = 'static/outputs'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 定期清理舊檔案的函數 (避免雲端硬碟爆滿)
def cleanup_old_files():
    now = time.time()
    # 刪除超過 10 分鐘的檔案
    for folder in [DOWNLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                if now - os.path.getmtime(file_path) > 600: 
                    try:
                        os.remove(file_path)
                    except:
                        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_short():
    # 每次請求時順便觸發清理 (簡單實作)
    threading.Thread(target=cleanup_old_files).start()

    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({'error': '請提供 YouTube 網址'}), 400

    try:
        # 1. 下載影片
        filename = f"video_{int(time.time())}"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename}.%(ext)s'),
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            video_path = ydl.prepare_filename(info_dict)

        # 2. 影片處理 (通用型邏輯)
        clip = VideoFileClip(video_path)
        
        # 限制處理長度 (雲端免費版通常有 CPU 限制，避免處理太長的影片導致 Timeout)
        # 這裡設定只取前 60 秒或中間 60 秒
        target_duration = 60
        if clip.duration > target_duration:
            start_time = (clip.duration - target_duration) / 2
            sub_clip = clip.subclip(start_time, start_time + target_duration)
        else:
            sub_clip = clip

        # 3. 智慧置中裁切 (16:9 -> 9:16)
        w, h = sub_clip.size
        target_ratio = 9 / 16
        new_w = h * target_ratio
        
        if new_w <= w:
            x_center = w / 2
            sub_clip = sub_clip.crop(x1=x_center - new_w/2, y1=0, x2=x_center + new_w/2, y2=h)

        # 4. 輸出
        output_filename = f"{filename}_short.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # 使用 ultrafast preset 加速雲端轉檔
        sub_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', preset='ultrafast')
        
        # 關閉資源
        clip.close()
        sub_clip.close()
        
        # 刪除原始檔
        if os.path.exists(video_path):
            os.remove(video_path)

        # 回傳完整的 URL (如果是在 render 上，相對路徑即可)
        return jsonify({
            'success': True, 
            'video_url': f'/static/outputs/{output_filename}',
            'message': '生成成功！'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)