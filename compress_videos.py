import os
from moviepy import VideoFileClip

def compress_video(input_path, output_path, target_height=720, target_bitrate="1000k"):
    try:
        print(f"Processing {input_path}...")
        
        # Load video
        clip = VideoFileClip(input_path)
        
        # Resize if needed
        if clip.h > target_height:
            print(f"Resizing from {clip.h}p to {target_height}p...")
            clip = clip.resized(height=target_height)
        
        # Write compressed file
        print(f"Writing to {output_path} with bitrate {target_bitrate}...")
        clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac', 
            bitrate=target_bitrate,
            preset='medium',
            threads=4,
            logger='bar'
        )
        
        # Check size
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        new_size = os.path.getsize(output_path) / (1024 * 1024)
        
        print(f"Done! Reduced {original_size:.2f}MB -> {new_size:.2f}MB")
        return True
        
    except Exception as e:
        print(f"Error compressing {input_path}: {e}")
        return False
    finally:
        if 'clip' in locals():
            clip.close()

if __name__ == "__main__":
    videos = [
        "videos/video1.mov",
        "videos/video2.mov"
    ]
    
    for video in videos:
        if os.path.exists(video):
            filename = os.path.basename(video)
            name, ext = os.path.splitext(filename)
            output = os.path.join("videos", f"{name}_compressed.mp4")
            
            compress_video(video, output)
        else:
            print(f"File not found: {video}")
