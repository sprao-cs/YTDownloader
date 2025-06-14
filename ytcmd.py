from datetime import datetime
import os
import subprocess
import sys

import yt_dlp


class YTDownloader:
    def __init__(self):
        pass

    def check_ffmpeg(self):
        """
        Check if FFmpeg is installed and accessible.
        Returns True if FFmpeg is available, False otherwise.
        """
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True)
            return True
        except FileNotFoundError:
            return False
        
    def format_size(self, bytes):
        """
        Convert bytes to human readable format, making file sizes easier to understand.
        Scales from bytes up to gigabytes automatically.
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} GB"
    
    def progress_hook(self, d):
        """
        Display download progress with detailed information about speed and time remaining.
        Provides real-time feedback during the download process.
        """
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            
            if total:
                percentage = (downloaded / total) * 100
                speed = d.get('speed', 0)
                speed_str = self.format_size(speed) + '/s' if speed else 'N/A'
                
                eta = d.get('eta', None)
                eta_str = str(datetime.fromtimestamp(eta).strftime('%M:%S')) if eta else 'N/A'
                
                progress = f"\rProgress: {percentage:.1f}% | Speed: {speed_str} | ETA: {eta_str}"
                sys.stdout.write(progress)
                sys.stdout.flush()

    def get_best_format(self, formats, target_height, ffmpeg_available):
        """
        Select the best video format based on desired quality and FFmpeg availability.
        Handles both cases where FFmpeg is available and where it isn't.
        """
        if ffmpeg_available:
            # When FFmpeg is available, we can use separate video and audio streams
            return f'bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={target_height}][ext=mp4]/best'
        else:
            # When FFmpeg isn't available, we need a merged format
            return f'best[height<={target_height}][ext=mp4]/best[ext=mp4]/best'
        
    def download_video(self, url, preferred_quality=None, output_path='downloads'):
        """
        Download a YouTube video with specified quality using yt-dlp.
        Handles cases both with and without FFmpeg installed.
        
        Args:
            url (str): YouTube video URL
            preferred_quality (str): Preferred video quality (e.g., '720p', '1080p')
            output_path (str): Directory to save the downloaded video
        """
        try:
            # Check if FFmpeg is available
            ffmpeg_available = self.check_ffmpeg()

            if not ffmpeg_available:
                print("\nNotice: FFmpeg is not installed. Some high-quality options may be limited.")
                print("The script will automatically select the best available compatible format.")
                print("To enable all quality options, please install FFmpeg and add it to your system PATH.")

            # Create output directory if it doesn't exist
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            # Configure yt-dlp options
            ydl_opts = {
                'progress_hooks': [self.progress_hook],
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'verbose': False
            }

            print("Fetching video information...")
        
            # Create a yt-dlp object and get video info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video information
                info = ydl.extract_info(url, download=False)
                
                # Display video information
                print(f"\nVideo Title: {info.get('title', 'Unknown')}")
                duration = int(info.get('duration', 0))
                print(f"Duration: {duration // 60}:{duration % 60:02d}")
                
                # Get available formats and filter based on FFmpeg availability
                formats = info.get('formats', [])
                quality_set = set()
                
                # Collect available qualities, considering FFmpeg availability
                for f in formats:
                    height = f.get('height')
                    # If FFmpeg isn't available, only include formats that have both video and audio
                    if height and (ffmpeg_available or f.get('acodec') != 'none'):
                        quality_set.add(f"{height}p")
                
                # Sort qualities from lowest to highest
                quality_list = sorted(quality_set, key=lambda x: int(x.replace('p', '')))
                
                print("\nAvailable qualities:")
                for i, quality in enumerate(quality_list, 1):
                    print(f"{i}. {quality}")

                # Handle quality selection
                if not preferred_quality or preferred_quality not in quality_set:
                    print("\nPlease select a quality from the available options:")
                    while True:
                        try:
                            choice = int(input("Enter the number of your choice: "))
                            if 1 <= choice <= len(quality_list):
                                preferred_quality = quality_list[choice-1]
                                break
                            else:
                                print("Invalid choice. Please try again.")
                        except ValueError:
                            print("Please enter a valid number.")

                # Set format based on selected quality and FFmpeg availability
                height = int(preferred_quality.replace('p', ''))
                ydl_opts['format'] = self.get_best_format(formats, height, ffmpeg_available)
                
                print(f"\nDownloading video in {preferred_quality}...")
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                print("\nDownload completed successfully!")
        except Exception as e:
            print(f"An error occurred: {e}")
            return False