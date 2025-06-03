import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
from PIL import Image
import threading

class MediaConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Media Converter")
        self.root.geometry("800x600")
        
        self.input_file = ""
        self.output_dir = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # File selection
        ttk.Label(main_frame, text="Input File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.file_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.file_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_file).grid(row=0, column=2)
        
        # Output directory
        ttk.Label(main_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_var, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(row=1, column=2)
        
        # File type detection
        ttk.Label(main_frame, text="File Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.file_type_var = tk.StringVar()
        self.file_type_label = ttk.Label(main_frame, textvariable=self.file_type_var)
        self.file_type_label.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Conversion options frame
        options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Output format
        ttk.Label(options_frame, text="Output Format:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(options_frame, textvariable=self.format_var, state="readonly")
        self.format_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        # Resolution options
        ttk.Label(options_frame, text="Resolution:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.resolution_var = tk.StringVar()
        self.resolution_combo = ttk.Combobox(options_frame, textvariable=self.resolution_var, state="readonly")
        self.resolution_combo['values'] = ('Keep Original', '1920x1080', '1280x720', '854x480', '640x360', '320x240', 'Custom')
        self.resolution_combo.set('Keep Original')
        self.resolution_combo.grid(row=1, column=1, padx=5, sticky=tk.W)
        self.resolution_combo.bind('<<ComboboxSelected>>', self.on_resolution_change)
        
        # Custom resolution inputs
        self.custom_frame = ttk.Frame(options_frame)
        self.custom_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Label(self.custom_frame, text="Width:").grid(row=0, column=0, padx=5)
        self.width_var = tk.StringVar()
        ttk.Entry(self.custom_frame, textvariable=self.width_var, width=8).grid(row=0, column=1, padx=5)
        
        ttk.Label(self.custom_frame, text="Height:").grid(row=0, column=2, padx=5)
        self.height_var = tk.StringVar()
        ttk.Entry(self.custom_frame, textvariable=self.height_var, width=8).grid(row=0, column=3, padx=5)
        
        self.custom_frame.grid_remove()  # Hide initially
        
        # Video specific options
        self.video_frame = ttk.LabelFrame(options_frame, text="Video Options", padding="5")
        self.video_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.video_frame, text="Bitrate (kbps):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.bitrate_var = tk.StringVar()
        self.bitrate_combo = ttk.Combobox(self.video_frame, textvariable=self.bitrate_var, state="readonly")
        self.bitrate_combo['values'] = ('Auto', '500', '1000', '2000', '4000', '8000', '16000', 'Custom')
        self.bitrate_combo.set('Auto')
        self.bitrate_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        self.bitrate_combo.bind('<<ComboboxSelected>>', self.on_bitrate_change)
        
        # Custom bitrate
        self.custom_bitrate_var = tk.StringVar()
        self.custom_bitrate_entry = ttk.Entry(self.video_frame, textvariable=self.custom_bitrate_var, width=10)
        self.custom_bitrate_entry.grid(row=0, column=2, padx=5)
        self.custom_bitrate_entry.grid_remove()
        
        # Image specific options
        self.image_frame = ttk.LabelFrame(options_frame, text="Image Options", padding="5")
        self.image_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.image_frame, text="Quality (1-100):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.quality_var = tk.StringVar(value="95")
        ttk.Entry(self.image_frame, textvariable=self.quality_var, width=10).grid(row=0, column=1, padx=5)
        
        # Output filename
        ttk.Label(main_frame, text="Output Filename:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.output_name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_name_var, width=50).grid(row=4, column=1, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=3, pady=5)
        
        # Export button
        self.export_btn = ttk.Button(main_frame, text="Export", command=self.export_file, style="Accent.TButton")
        self.export_btn.grid(row=7, column=1, pady=20)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
    def browse_file(self):
        file_types = [
            ("All Supported", "*.mp4;*.avi;*.mov;*.mkv;*.wmv;*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tiff"),
            ("Video files", "*.mp4;*.avi;*.mov;*.mkv;*.wmv"),
            ("Image files", "*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tiff"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select input file",
            filetypes=file_types
        )
        
        if filename:
            self.input_file = filename
            self.file_var.set(filename)
            self.detect_file_type()
            self.generate_output_name()
            
    def browse_output(self):
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.output_dir = directory
            self.output_var.set(directory)
            
    def detect_file_type(self):
        if not self.input_file:
            return
            
        ext = os.path.splitext(self.input_file)[1].lower()
        
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        if ext in video_exts:
            self.file_type_var.set("Video")
            self.format_combo['values'] = ('mp4', 'avi', 'mov', 'mkv', 'webm')
            self.format_combo.set('mp4')
            self.video_frame.grid()
            self.image_frame.grid_remove()
        elif ext in image_exts:
            self.file_type_var.set("Image")
            self.format_combo['values'] = ('jpg', 'png', 'gif', 'bmp', 'tiff', 'webp')
            self.format_combo.set('jpg')
            self.video_frame.grid_remove()
            self.image_frame.grid()
        else:
            self.file_type_var.set("Unknown")
            self.format_combo['values'] = ()
            
    def generate_output_name(self):
        if not self.input_file:
            return
            
        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.output_name_var.set(f"{base_name}_converted")
        
    def on_resolution_change(self, event):
        if self.resolution_var.get() == 'Custom':
            self.custom_frame.grid()
        else:
            self.custom_frame.grid_remove()
            
    def on_bitrate_change(self, event):
        if self.bitrate_var.get() == 'Custom':
            self.custom_bitrate_entry.grid()
        else:
            self.custom_bitrate_entry.grid_remove()
            
    def validate_inputs(self):
        if not self.input_file or not os.path.exists(self.input_file):
            messagebox.showerror("Error", "Please select a valid input file")
            return False
            
        if not self.output_dir or not os.path.exists(self.output_dir):
            messagebox.showerror("Error", "Please select a valid output directory")
            return False
            
        if not self.output_name_var.get().strip():
            messagebox.showerror("Error", "Please enter an output filename")
            return False
            
        if not self.format_var.get():
            messagebox.showerror("Error", "Please select an output format")
            return False
            
        return True
        
    def export_file(self):
        if not self.validate_inputs():
            return
            
        # Disable export button during processing
        self.export_btn.config(state='disabled')
        self.progress.start()
        
        # Run conversion in separate thread to prevent UI freezing
        thread = threading.Thread(target=self.convert_file)
        thread.daemon = True
        thread.start()
        
    def convert_file(self):
        try:
            file_type = self.file_type_var.get()
            
            if file_type == "Video":
                self.convert_video()
            elif file_type == "Image":
                self.convert_image()
            else:
                raise Exception("Unsupported file type")
                
        except Exception as e:
            self.root.after(0, lambda: self.conversion_complete(False, str(e)))
        else:
            self.root.after(0, lambda: self.conversion_complete(True))
            
    def convert_video(self):
        input_file = self.input_file
        output_format = self.format_var.get()
        output_name = self.output_name_var.get()
        output_file = os.path.join(self.output_dir, f"{output_name}.{output_format}")
        
        # Build FFmpeg command
        cmd = ['ffmpeg', '-i', input_file, '-y']  # -y to overwrite output files
        
        # Resolution settings
        resolution = self.resolution_var.get()
        if resolution != 'Keep Original':
            if resolution == 'Custom':
                width = self.width_var.get()
                height = self.height_var.get()
                if width and height:
                    cmd.extend(['-vf', f'scale={width}:{height}'])
            else:
                cmd.extend(['-vf', f'scale={resolution}'])
                
        # Bitrate settings
        bitrate = self.bitrate_var.get()
        if bitrate != 'Auto':
            if bitrate == 'Custom':
                custom_bitrate = self.custom_bitrate_var.get()
                if custom_bitrate:
                    cmd.extend(['-b:v', f'{custom_bitrate}k'])
            else:
                cmd.extend(['-b:v', f'{bitrate}k'])
                
        cmd.append(output_file)
        
        self.root.after(0, lambda: self.status_var.set("Converting video..."))
        
        # Run FFmpeg
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {process.stderr}")
            
    def convert_image(self):
        input_file = self.input_file
        output_format = self.format_var.get().upper()
        if output_format == 'JPG':
            output_format = 'JPEG'
            
        output_name = self.output_name_var.get()
        output_file = os.path.join(self.output_dir, f"{output_name}.{self.format_var.get()}")
        
        self.root.after(0, lambda: self.status_var.set("Converting image..."))
        
        # Open and process image
        with Image.open(input_file) as img:
            # Convert RGBA to RGB if saving as JPEG
            if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
                
            # Resolution settings
            resolution = self.resolution_var.get()
            if resolution != 'Keep Original':
                if resolution == 'Custom':
                    width = int(self.width_var.get()) if self.width_var.get() else img.width
                    height = int(self.height_var.get()) if self.height_var.get() else img.height
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                else:
                    width, height = map(int, resolution.split('x'))
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                    
            # Save with quality settings
            save_kwargs = {'format': output_format}
            if output_format == 'JPEG':
                save_kwargs['quality'] = int(self.quality_var.get())
                save_kwargs['optimize'] = True
                
            img.save(output_file, **save_kwargs)
            
    def conversion_complete(self, success, error_msg=None):
        self.progress.stop()
        self.export_btn.config(state='normal')
        
        if success:
            self.status_var.set("Conversion completed successfully!")
            messagebox.showinfo("Success", "File exported successfully!")
        else:
            self.status_var.set(f"Conversion failed: {error_msg}")
            messagebox.showerror("Error", f"Conversion failed:\n{error_msg}")

def main():
    root = tk.Tk()
    app = MediaConverterApp(root)
    
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        messagebox.showwarning(
            "FFmpeg Not Found", 
            "FFmpeg is not installed or not in PATH.\n"
            "Video conversion will not work.\n"
            "Please install FFmpeg for video processing."
        )
    
    root.mainloop()

if __name__ == "__main__":
    main()