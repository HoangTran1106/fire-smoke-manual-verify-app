import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
from PIL import Image, ImageTk
import os
from datetime import datetime

# Safe OpenCV import
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    messagebox.showerror("Missing Dependency", "OpenCV not found. Please install: pip install opencv-python")

class SimpleFireDetector:
    def __init__(self, root):
        self.root = root
        self.root.title("Fire & Smoke Detection System")
        self.root.geometry("1400x900")
        
        # Data storage
        self.current_frame = None
        self.excel_data = None
        self.detection_boxes = []
        self.current_batch_index = 0
        self.thumbnails_per_batch = 21
        self.data_format = None  # Track which format is being used
        self.original_video_size = (3840, 2160)  # Default expected size
        self.actual_video_size = None  # Actual loaded video size
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0
        self.search_results = []
        self.current_search_index = 0
        self.frame_cache = {}  # Cache for loaded frames
        self.cache_window = 10  # Number of batches to cache before/after current
        
        self.setup_ui()
        self.log_status("Application started. Use buttons to load files.")
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control buttons row 1
        control_frame1 = ttk.Frame(main_frame)
        control_frame1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(control_frame1, text="Load Excel", command=self.load_excel).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame1, text="Load Video", command=self.load_video).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame1, text="Plot", command=self.run_detection).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame1, text="Resume from Annotations", command=self.resume_from_excel).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame1, text="Save Results As...", command=self.save_results).pack(side=tk.LEFT, padx=(0, 10))
        
        # Control buttons row 2 - Search and Navigation
        control_frame2 = ttk.Frame(main_frame)
        control_frame2.pack(fill=tk.X, pady=(0, 10))
        
        # Search section
        search_frame = ttk.LabelFrame(control_frame2, text="Search & Navigation")
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Search controls
        search_controls = ttk.Frame(search_frame)
        search_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_controls, text="Search:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        
        # Simple text entry without complex bindings
        self.search_entry = tk.Entry(search_controls, width=15, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.search_entry.bind("<Return>", self.on_search_enter)
        
        # Search type dropdown
        self.search_type = tk.StringVar(value="Frame")
        search_type_combo = ttk.Combobox(search_controls, textvariable=self.search_type, 
                                        values=["Frame", "Batch", "Object ID", "Category"], 
                                        width=10, state="readonly")
        search_type_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(search_controls, text="🔍 Search", command=self.search_detection).pack(side=tk.LEFT, padx=(0, 20))
        
        # Navigation buttons
        ttk.Button(search_controls, text="⏮️ First", command=self.go_to_first_batch, width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(search_controls, text="⏭️ Last", command=self.go_to_last_batch, width=8).pack(side=tk.LEFT, padx=(0, 5))
        
        # Green DONE button
        style = ttk.Style()
        style.configure("Green.TButton", 
                       foreground="black",
                       background="green",
                       font=("Arial", 10, "bold"))
        
        done_btn = ttk.Button(search_controls, text="DONE - Next Batch", 
                             command=self.next_batch, style="Green.TButton")
        done_btn.pack(side=tk.RIGHT)
        
        # Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left - Thumbnails
        left_frame = ttk.LabelFrame(content_frame, text="Detection Thumbnails")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.canvas = tk.Canvas(left_frame, bg='lightgray')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<Button-4>", self.on_scroll_up)
        self.canvas.bind("<Button-5>", self.on_scroll_down)
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        
        # Make canvas focusable for keyboard events
        self.canvas.configure(highlightthickness=1)
        self.canvas.bind("<KeyPress-space>", self.on_space_press)
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.canvas.bind("<Left>", self.on_left_arrow)
        self.canvas.bind("<Right>", self.on_right_arrow)
        self.canvas.bind("<Tab>", self.on_tab_press)
        
        # Right - Info panels
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status
        status_frame = ttk.LabelFrame(right_frame, text="Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_text = tk.Text(status_frame, width=40, height=8)
        status_scroll = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scroll.set)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Search results info
        search_info_frame = ttk.LabelFrame(right_frame, text="Search Results")
        search_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_info_label = ttk.Label(search_info_frame, text="No search performed", 
                                          wraplength=180, justify=tk.LEFT)
        self.search_info_label.pack(padx=5, pady=5)
        
        # Batch info
        batch_frame = ttk.LabelFrame(right_frame, text="Batch Info")
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.batch_label = ttk.Label(batch_frame, text="No data loaded")
        self.batch_label.pack(padx=5, pady=5)
        
        # Video size info
        size_frame = ttk.LabelFrame(right_frame, text="Video Info")
        size_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.video_info_label = ttk.Label(size_frame, text="No video loaded", wraplength=180)
        self.video_info_label.pack(padx=5, pady=5)
        
        # Format info
        format_frame = ttk.LabelFrame(right_frame, text="Data Format")
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.format_label = ttk.Label(format_frame, text="No format detected")
        self.format_label.pack(padx=5, pady=5)
        
        # Legend
        legend_frame = ttk.LabelFrame(right_frame, text="Legend & Controls")
        legend_frame.pack(fill=tk.X)
        
        ttk.Label(legend_frame, text="🔵 Blue: True (Scroll Wheel)", foreground="blue").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="🔴 Red: False (Left Click)", foreground="red").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="🟢 Green: Unclear (Right Click)", foreground="green").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="⌨️ Spacebar: Next Batch", foreground="purple", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="← → Arrow Keys: Prev/Next Batch", foreground="orange", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="Tab: Show Full Size (hover first)", foreground="brown", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="🔍 Search: Frame/Batch/Object/Category", foreground="darkblue", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="⏮️⏭️ First/Last Batch Navigation", foreground="darkorange", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="💡 Click canvas first for keyboard focus", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W)
    
    def detect_data_format(self, df):
        """Detect which data format is being used based on column names"""
        columns = [col.strip() for col in df.columns]
        columns_lower = [col.lower().strip() for col in df.columns]
        
        print(f"Debug - Actual columns: {columns}")
        print(f"Debug - Lowercase columns: {columns_lower}")
        
        # Format 1: Original format
        format1_cols = ['bbox_x1', 'bbox_y1', 'bbox_width', 'bbox_height', 'class_name', 'confidence']
        format1_match = all(col in columns_lower for col in format1_cols)
        
        # Format 2: New format
        format2_cols = ['frame_number', 'video_time', 'real_time', 'object_id', 'category', 'confidence', 'x1', 'y1', 'x2', 'y2', 'width', 'height', 'area']
        format2_match = all(col in columns_lower for col in format2_cols)
        
        # Also check for exact case matches for Format 2
        format2_cols_exact = ['Frame_Number', 'Video_Time', 'Real_Time', 'Object_ID', 'Category', 'Confidence', 'X1', 'Y1', 'X2', 'Y2', 'Width', 'Height', 'Area']
        format2_exact_match = all(col in columns for col in format2_cols_exact)
        
        print(f"Debug - Format1 match: {format1_match}")
        print(f"Debug - Format2 match: {format2_match}")
        print(f"Debug - Format2 exact match: {format2_exact_match}")
        
        if format1_match:
            return "format1"
        elif format2_match or format2_exact_match:
            return "format2"
        else:
            bbox_indicators = ['bbox', 'x1', 'y1', 'x2', 'y2', 'width', 'height']
            class_indicators = ['class', 'category', 'type', 'object']
            
            has_bbox = any(indicator in ' '.join(columns_lower) for indicator in bbox_indicators)
            has_class = any(indicator in ' '.join(columns_lower) for indicator in class_indicators)
            
            if has_bbox and has_class:
                if any('bbox' in col for col in columns_lower):
                    return "format1_partial"
                elif any(col in columns_lower for col in ['x1', 'x2', 'frame_number']):
                    return "format2_partial"
            
            return "unknown"
    
    def log_status(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        print(f"[{timestamp}] {message}")
    
    def load_excel(self):
        # Try multiple default paths
        default_paths = [
            r"D:\Desktop\Gen\anno-data\mid-processed-video\done\detection_logs",
            r"D:\Desktop\General\Cap\z-phase2\paths\chua-detect-video"
        ]
        
        initial_dir = os.getcwd()
        for path in default_paths:
            if os.path.exists(path):
                initial_dir = path
                break
            
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            initialdir=initial_dir,
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.lower().endswith('.csv'):
                    self.excel_data = pd.read_csv(file_path)
                else:
                    self.excel_data = pd.read_excel(file_path)
                    
                self.current_excel_path = file_path
                
                self.data_format = self.detect_data_format(self.excel_data)
                
                format_text = {
                    "format1": "Format 1: bbox_x1, bbox_y1, etc.",
                    "format2": "Format 2: X1, Y1, X2, Y2, etc.",
                    "format1_partial": "Format 1 (partial match)",
                    "format2_partial": "Format 2 (partial match)",
                    "unknown": "Unknown format"
                }
                self.format_label.config(text=format_text.get(self.data_format, "Unknown"))
                
                self.log_status(f"✅ Excel loaded: {os.path.basename(file_path)} ({len(self.excel_data)} rows)")
                self.log_status(f"📊 Detected format: {self.data_format}")
                self.log_status(f"📋 Columns: {', '.join(self.excel_data.columns[:10])}{'...' if len(self.excel_data.columns) > 10 else ''}")
                
            except Exception as e:
                self.log_status(f"❌ Excel load error: {e}")
    
    def load_video(self):
        if not CV2_AVAILABLE:
            self.log_status("❌ OpenCV not available")
            return
            
        # Try multiple default paths
        default_paths = [
            r"D:\Desktop\General\Da\Cap\z-phase2\paths\chua-detect-video",
            r"D:\Desktop\General\Cap\z-phase2\paths\chua-detect-video"
        ]
        
        initial_dir = os.getcwd()
        for path in default_paths:
            if os.path.exists(path):
                initial_dir = path
                break
            
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            initialdir=initial_dir,
            filetypes=[("Video files", "*.mp4 *.avi *.mov"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.video_path = file_path  # Store video path for frame extraction
                cap = cv2.VideoCapture(file_path)
                
                # Get video properties
                self.video_fps = cap.get(cv2.CAP_PROP_FPS)
                self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                ret, frame = cap.read()
                if ret:
                    self.current_frame = frame
                    
                    self.actual_video_size = (frame.shape[1], frame.shape[0])
                    
                    self.scale_factor_x = self.actual_video_size[0] / self.original_video_size[0]
                    self.scale_factor_y = self.actual_video_size[1] / self.original_video_size[1]
                    
                    self.log_status(f"✅ Video loaded: {os.path.basename(file_path)}")
                    self.log_status(f"📐 Video size: {self.actual_video_size[0]}x{self.actual_video_size[1]}")
                    self.log_status(f"🎬 FPS: {self.video_fps:.1f}, Total frames: {self.total_frames}")
                    self.log_status(f"🔄 Scale factors: X={self.scale_factor_x:.3f}, Y={self.scale_factor_y:.3f}")
                    
                    info_text = f"Size: {self.actual_video_size[0]}x{self.actual_video_size[1]}\nFPS: {self.video_fps:.1f}\nFrames: {self.total_frames}\nScale: {self.scale_factor_x:.3f}x{self.scale_factor_y:.3f}"
                    self.video_info_label.config(text=info_text)
                    
                cap.release()
            except Exception as e:
                self.log_status(f"❌ Video load error: {e}")
    
    def get_frame_at_number(self, frame_number):
        """Extract specific frame from video by frame number with caching"""
        if not hasattr(self, 'video_path'):
            return None
        
        # Check cache first
        if frame_number in self.frame_cache:
            return self.frame_cache[frame_number]
            
        try:
            cap = cv2.VideoCapture(self.video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Cache the frame
                self.frame_cache[frame_number] = frame
                self.cleanup_frame_cache()
                return frame
            else:
                return None
        except Exception as e:
            print(f"Error getting frame {frame_number}: {e}")
            return None
    
    def cleanup_frame_cache(self):
        """Keep only frames within cache window to manage RAM"""
        if not self.detection_boxes:
            return
            
        # Calculate current batch range
        current_batch = self.current_batch_index // self.thumbnails_per_batch
        batch_start = max(0, current_batch - self.cache_window)
        batch_end = min(self.get_total_batches(), current_batch + self.cache_window + 1)
        
        # Get frame numbers within cache window
        valid_frames = set()
        start_detection = batch_start * self.thumbnails_per_batch
        end_detection = min(batch_end * self.thumbnails_per_batch, len(self.detection_boxes))
        
        for i in range(start_detection, end_detection):
            if i < len(self.detection_boxes):
                frame_num = self.detection_boxes[i].get('frame_number')
                if frame_num and frame_num != 'N/A':
                    valid_frames.add(frame_num)
        
        # Remove frames outside cache window
        frames_to_remove = []
        for frame_num in self.frame_cache:
            if frame_num not in valid_frames:
                frames_to_remove.append(frame_num)
        
        for frame_num in frames_to_remove:
            del self.frame_cache[frame_num]
        
        if frames_to_remove:
            self.log_status(f"🧹 Cleaned cache: removed {len(frames_to_remove)} frames")
    
    def parse_detection_format1(self, row, idx):
        """Parse detection data from Format 1 (original format)"""
        try:
            detection = {
                'x': int(row['bbox_x1']),
                'y': int(row['bbox_y1']),
                'width': int(row['bbox_width']),
                'height': int(row['bbox_height']),
                'type': row['class_name'],
                'confidence': float(row['confidence']),
                'annotated': True,
                'row_index': idx,
                'frame_number': row.get('frame_number', 'N/A'),
                'timestamp': row.get('timestamp', 'N/A')
            }
            return detection
        except Exception as e:
            self.log_status(f"⚠️ Format 1 parse error row {idx}: {e}")
            return None
    
    def parse_detection_format2(self, row, idx):
        """Parse detection data from Format 2 (new format)"""
        try:
            def get_column_value(row, col_name):
                if col_name in row:
                    return row[col_name]
                if col_name.lower() in row:
                    return row[col_name.lower()]
                if col_name.title() in row:
                    return row[col_name.title()]
                if col_name.upper() in row:
                    return row[col_name.upper()]
                raise KeyError(f"Column {col_name} not found")
            
            x1_orig = int(get_column_value(row, 'X1'))
            y1_orig = int(get_column_value(row, 'Y1'))
            x2_orig = int(get_column_value(row, 'X2'))
            y2_orig = int(get_column_value(row, 'Y2'))
            
            x1 = int(x1_orig * self.scale_factor_x)
            y1 = int(y1_orig * self.scale_factor_y)
            x2 = int(x2_orig * self.scale_factor_x)
            y2 = int(y2_orig * self.scale_factor_y)
            
            width = x2 - x1
            height = y2 - y1
            
            if idx < 3:
                print(f"Debug - Detection {idx}: Original=({x1_orig},{y1_orig},{x2_orig},{y2_orig}) -> Scaled=({x1},{y1},{x2},{y2}) W={width} H={height}")
            
            detection = {
                'x': x1,
                'y': y1,
                'width': width,
                'height': height,
                'type': get_column_value(row, 'Category'),
                'confidence': float(get_column_value(row, 'Confidence')),
                'annotated': True,
                'row_index': idx,
                'frame_number': get_column_value(row, 'Frame_Number'),
                'video_time': get_column_value(row, 'Video_Time'),
                'real_time': get_column_value(row, 'Real_Time'),
                'object_id': get_column_value(row, 'Object_ID'),
                'area': get_column_value(row, 'Area') if 'Area' in row else width * height
            }
            return detection
        except Exception as e:
            self.log_status(f"⚠️ Format 2 parse error row {idx}: {e}")
            print(f"Debug - Parse error row {idx}: {e}")
            return None
    
    def run_detection(self):
        if self.excel_data is None:
            self.log_status("❌ Load Excel file first")
            return
        if self.current_frame is None:
            self.log_status("❌ Load video file first")
            return
        
        if self.data_format == "unknown":
            messagebox.showerror("Unknown Format", 
                               "Cannot recognize data format. Supported formats:\n"
                               "Format 1: bbox_x1, bbox_y1, bbox_width, bbox_height, class_name, confidence\n"
                               "Format 2: Frame_Number, Video_Time, Real_Time, Object_ID, Category, Confidence, X1, Y1, X2, Y2, Width, Height, Area")
            return
        
        self.detection_boxes = []
        self.current_batch_index = 0
        
        successful_detections = 0
        for idx, row in self.excel_data.iterrows():
            detection = None
            
            if self.data_format in ["format1", "format1_partial"]:
                detection = self.parse_detection_format1(row, idx)
            elif self.data_format in ["format2", "format2_partial"]:
                detection = self.parse_detection_format2(row, idx)
            
            if detection:
                self.detection_boxes.append(detection)
                successful_detections += 1
        
        if successful_detections == 0:
            messagebox.showerror("No Detections", "No valid detections could be parsed from the data.")
            return
        
        self.update_display()
        self.update_batch_info()
        self.log_status(f"🔵 Loaded {successful_detections} detections using {self.data_format}")

    def resume_from_excel(self):
        """Resume editing from a previously saved annotation file"""
        file_path = filedialog.askopenfilename(
            title="Select Previously Saved Annotation File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv")]
        )
        
        if not file_path:
            return
            
        if self.current_frame is None:
            self.log_status("❌ Load video file first")
            return
        
        if self.excel_data is None:
            self.log_status("❌ Load original Excel file first")
            return
        
        try:
            if file_path.lower().endswith('.csv'):
                annotation_data = pd.read_csv(file_path)
            else:
                annotation_data = pd.read_excel(file_path)
            
            if 'verified' not in annotation_data.columns:
                messagebox.showerror("Error", "No 'verified' column found in annotation file")
                return
            
            self.detection_boxes = []
            self.current_batch_index = 0
            
            annotation_index = 0
            for idx, original_row in self.excel_data.iterrows():
                try:
                    if annotation_index < len(annotation_data):
                        ann_verified = annotation_data.iloc[annotation_index]['verified']
                        
                        if str(ann_verified).lower() == 'false':
                            verified_status = False
                        elif str(ann_verified).lower() == 'unclear':
                            verified_status = "unclear"
                        else:
                            verified_status = True
                        
                        annotation_index += 1
                    else:
                        verified_status = True
                    
                    detection = None
                    if self.data_format in ["format1", "format1_partial"]:
                        detection = self.parse_detection_format1(original_row, idx)
                    elif self.data_format in ["format2", "format2_partial"]:
                        detection = self.parse_detection_format2(original_row, idx)
                    
                    if detection:
                        detection['annotated'] = verified_status
                        self.detection_boxes.append(detection)
                    
                except Exception as e:
                    print(f"Error processing row {idx}: {e}")
                    continue
            
            self.update_display()
            self.update_batch_info()
            self.log_status(f"🔄 Resumed from: {os.path.basename(file_path)} ({len(self.detection_boxes)} detections)")
            
            messagebox.showinfo("Success", f"Resumed from annotation file!\n{os.path.basename(file_path)}\nDetections: {len(self.detection_boxes)}")
            
        except Exception as e:
            error_msg = f"Failed to resume: {str(e)}"
            self.log_status(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)

    # Search functions
    def on_search_enter(self, event):
        """Handle Enter key press in search box"""
        self.search_detection()
    
    def setup_key_bindings(self):
        """Setup global key bindings after UI is created"""
        self.root.bind("<KeyPress-space>", self.on_space_press_global)
        self.root.bind("<KeyPress>", self.on_key_press_global)
        self.root.bind("<Button-1>", self.on_window_click)
        self.root.bind("<Left>", self.on_left_arrow_global)
        self.root.bind("<Right>", self.on_right_arrow_global)
        self.root.bind("<Tab>", self.on_tab_press_global)
    
    def on_search_click(self, event):
        """Handle click on search entry to ensure focus"""
        self.search_entry.focus_set()
        self.search_entry.icursor(tk.END)
    
    def on_search_focus_in(self, event):
        """Handle search entry gaining focus"""
        pass
    
    def on_space_press_global(self, event):
        """Handle spacebar globally but not when search entry has focus"""
        if self.search_entry != self.root.focus_get():
            self.on_space_press(event)
    
    def on_key_press_global(self, event):
        """Handle key press globally but not when search entry has focus"""
        if self.search_entry != self.root.focus_get():
            self.on_key_press(event)
    
    def on_left_arrow_global(self, event):
        """Handle left arrow globally but not when search entry has focus"""
        if self.search_entry != self.root.focus_get():
            self.on_left_arrow(event)
    
    def on_right_arrow_global(self, event):
        """Handle right arrow globally but not when search entry has focus"""
        if self.search_entry != self.root.focus_get():
            self.on_right_arrow(event)
    
    def on_tab_press_global(self, event):
        """Handle tab globally but not when search entry has focus"""
        if self.search_entry != self.root.focus_get():
            self.on_tab_press(event)
    
    def search_detection(self):
        """Search for specific detections based on search type and query"""
        if not self.detection_boxes:
            self.log_status("❌ No detection data loaded")
            return
        
        # Get text from Entry widget
        search_query = self.search_entry.get().strip()
        if not search_query:
            self.log_status("⚠️ Enter search term")
            return
        
        search_type = self.search_type.get()
        found_indices = []
        
        try:
            if search_type == "Frame":
                target_frame = int(search_query)
                for i, detection in enumerate(self.detection_boxes):
                    if detection.get('frame_number') == target_frame:
                        found_indices.append(i)
                        
            elif search_type == "Batch":
                target_batch = int(search_query)
                if 1 <= target_batch <= self.get_total_batches():
                    batch_start_idx = (target_batch - 1) * self.thumbnails_per_batch
                    self.current_batch_index = batch_start_idx
                    self.update_display()
                    self.update_batch_info()
                    self.log_status(f"🎯 Jumped to batch {target_batch}")
                    self.search_info_label.config(text=f"Showing Batch {target_batch}")
                    return
                else:
                    self.log_status(f"❌ Batch {target_batch} not found (1-{self.get_total_batches()})")
                    return
                    
            elif search_type == "Object ID":
                for i, detection in enumerate(self.detection_boxes):
                    obj_id = str(detection.get('object_id', ''))
                    if search_query.lower() in obj_id.lower():
                        found_indices.append(i)
                        
            elif search_type == "Category":
                for i, detection in enumerate(self.detection_boxes):
                    category = detection.get('type', '').lower()
                    if search_query.lower() in category:
                        found_indices.append(i)
            
            if found_indices:
                first_idx = found_indices[0]
                target_batch = first_idx // self.thumbnails_per_batch
                self.current_batch_index = target_batch * self.thumbnails_per_batch
                
                self.update_display()
                self.update_batch_info()
                
                self.highlight_detection(first_idx)
                
                if len(found_indices) == 1:
                    result_text = f"Found 1 match at position {first_idx + 1}"
                else:
                    result_text = f"Found {len(found_indices)} matches\nShowing first at position {first_idx + 1}"
                
                self.search_info_label.config(text=result_text)
                self.log_status(f"🔍 {search_type} search: '{search_query}' - {len(found_indices)} matches")
                
                self.search_results = found_indices
                self.current_search_index = 0
                
            else:
                self.log_status(f"❌ No matches found for {search_type}: '{search_query}'")
                self.search_info_label.config(text=f"No matches for '{search_query}'")
                
        except ValueError:
            self.log_status(f"❌ Invalid {search_type} number: '{search_query}'")
    
    def highlight_detection(self, detection_idx):
        """Highlight a specific detection in the current batch"""
        self.root.after(100, lambda: self._add_highlight(detection_idx))
    
    def _add_highlight(self, detection_idx):
        """Add visual highlight to a detection"""
    def _add_highlight(self, detection_idx):
        """Add visual highlight to a detection"""
        try:
            start_idx = self.current_batch_index
            end_idx = min(start_idx + self.thumbnails_per_batch, len(self.detection_boxes))
            
            if start_idx <= detection_idx < end_idx:
                items = self.canvas.find_withtag(f"thumb_{detection_idx}")
                if items:
                    bbox = self.canvas.bbox(f"thumb_{detection_idx}")
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        highlight_rect = self.canvas.create_rectangle(
                            x1-10, y1-10, x2+10, y2+10,
                            outline="yellow", width=8, tags="search_highlight"
                        )
                        self.root.after(3000, lambda: self.canvas.delete("search_highlight"))
                        
        except Exception as e:
            print(f"Highlight error: {e}")
    
    def get_total_batches(self):
        """Get total number of batches"""
        if not self.detection_boxes:
            return 0
        return (len(self.detection_boxes) - 1) // self.thumbnails_per_batch + 1
    
    def go_to_first_batch(self):
        """Go to the first batch"""
        if not self.detection_boxes:
            self.log_status("⚠️ No detection boxes to navigate")
            return
        
        self.current_batch_index = 0
        self.update_display()
        self.update_batch_info()
        self.log_status("⏮️ Jumped to first batch")
        self.search_info_label.config(text="At first batch")
    
    def go_to_last_batch(self):
        """Go to the last batch"""
        if not self.detection_boxes:
            self.log_status("⚠️ No detection boxes to navigate")
            return
        
        total_batches = self.get_total_batches()
        self.current_batch_index = (total_batches - 1) * self.thumbnails_per_batch
        self.update_display()
        self.update_batch_info()
        self.log_status("⏭️ Jumped to last batch")
        self.search_info_label.config(text="At last batch")
    
    def update_display(self):
        if not self.detection_boxes:
            self.log_status("⚠️ No detection boxes available")
            return
        if self.current_frame is None:
            self.log_status("⚠️ No video frame loaded")
            return
        
        self.log_status(f"🔄 Updating display - Batch {self.current_batch_index // self.thumbnails_per_batch + 1}")
        self.log_status(f"📦 Total detections: {len(self.detection_boxes)}, Current batch start: {self.current_batch_index}")
        
        self.canvas.delete("all")
        
        start_idx = self.current_batch_index
        end_idx = min(start_idx + self.thumbnails_per_batch, len(self.detection_boxes))
        current_batch = self.detection_boxes[start_idx:end_idx]
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self.update_display)
            return
        
        padding = 20
        available_width = canvas_width - (2 * padding)
        available_height = canvas_height - (2 * padding)
        
        max_cols = 8
        cols = min(len(current_batch), max_cols)
        rows = (len(current_batch) - 1) // cols + 1
        
        thumb_width = (available_width - (cols - 1) * padding) // cols if cols > 0 else 100
        thumb_height = (available_height - (rows - 1) * padding - 60) // rows if rows > 0 else 100
        
        thumb_size = min(thumb_width, thumb_height)
        thumb_size = max(thumb_size, 120)
        thumb_size = min(thumb_size, 250)
        
        actual_cols = min(cols, available_width // (thumb_size + padding))
        actual_rows = (len(current_batch) - 1) // actual_cols + 1
        
        total_grid_width = actual_cols * thumb_size + (actual_cols - 1) * padding
        total_grid_height = actual_rows * thumb_size + (actual_rows - 1) * padding + 60
        
        start_x = (canvas_width - total_grid_width) // 2
        start_y = (canvas_height - total_grid_height) // 2
        
        self.thumbnail_photos = []
        
        for i, detection in enumerate(current_batch):
            try:
                if i < 3:
                    self.log_status(f"🔍 Processing detection {i}: x={detection['x']}, y={detection['y']}, w={detection['width']}, h={detection['height']}")
                
                col = i % actual_cols
                row = i // actual_cols
                
                # Extract thumbnail using frame-specific extraction
                frame_number = detection.get('frame_number', 0)
                if frame_number and frame_number != 'N/A':
                    # Get the actual frame for this detection
                    frame_for_detection = self.get_frame_at_number(frame_number)
                    if frame_for_detection is not None:
                        current_frame = frame_for_detection
                    else:
                        current_frame = self.current_frame  # Fallback to first frame
                else:
                    current_frame = self.current_frame
                
                x1, y1 = detection['x'], detection['y']
                x2 = x1 + detection['width']
                y2 = y1 + detection['height']
                
                frame_height, frame_width = current_frame.shape[:2]
                if i < 3:
                    self.log_status(f"🖼️ Frame {frame_number}, size: {frame_width}x{frame_height}, Detection bounds: ({x1},{y1}) to ({x2},{y2})")
                
                x1, y1 = max(0, x1), max(0, y1)
                x2 = min(current_frame.shape[1], x2)
                y2 = min(current_frame.shape[0], y2)
                
                if x2 <= x1 or y2 <= y1:
                    if i < 3:
                        self.log_status(f"❌ Invalid crop bounds after correction: ({x1},{y1}) to ({x2},{y2})")
                    continue
                
                cropped = current_frame[y1:y2, x1:x2]
                if cropped.size == 0:
                    if i < 3:
                        self.log_status(f"❌ Empty cropped image for detection {i}")
                    continue
                
                if i < 3:
                    self.log_status(f"✅ Successfully cropped detection {i} from frame {frame_number}: {cropped.shape}")
                
                cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                cropped_resized = cv2.resize(cropped_rgb, (thumb_size, thumb_size))
                
                pil_img = Image.fromarray(cropped_resized)
                photo = ImageTk.PhotoImage(pil_img)
                self.thumbnail_photos.append(photo)
                
                x_pos = start_x + col * (thumb_size + padding) + thumb_size // 2
                y_pos = start_y + row * (thumb_size + padding + 40) + thumb_size // 2
                
                if detection['annotated'] == True:
                    color = "blue"
                    border_width = 6
                elif detection['annotated'] == False:
                    color = "red" 
                    border_width = 6
                elif detection['annotated'] == "unclear":
                    color = "green"
                    border_width = 6
                else:
                    color = "gray"
                    border_width = 4
                
                actual_idx = start_idx + i
                border_offset = border_width // 2 + 2
                self.canvas.create_rectangle(
                    x_pos - thumb_size//2 - border_offset, 
                    y_pos - thumb_size//2 - border_offset,
                    x_pos + thumb_size//2 + border_offset, 
                    y_pos + thumb_size//2 + border_offset,
                    outline=color, width=border_width, tags=f"thumb_{actual_idx}"
                )
                
                self.canvas.create_image(x_pos, y_pos, image=photo, tags=f"thumb_{actual_idx}")
                
                if 'frame_number' in detection and detection['frame_number'] != 'N/A':
                    label = f"F{detection['frame_number']}: {detection['type']}\n{detection['confidence']:.1%}"
                else:
                    label = f"{detection['type']}\n{detection['confidence']:.1%}"
                
                font_size = max(10, thumb_size // 12)
                self.canvas.create_text(
                    x_pos, y_pos + thumb_size//2 + 25,
                    text=label, fill=color, anchor=tk.N, 
                    font=("Arial", font_size, "bold"),
                    tags=f"thumb_{actual_idx}"
                )
                
            except Exception as e:
                self.log_status(f"⚠️ Thumbnail error {i}: {e}")
        
        total_batches = (len(self.detection_boxes) - 1) // self.thumbnails_per_batch + 1
        current_batch_num = self.current_batch_index // self.thumbnails_per_batch + 1
        self.canvas.create_text(
            canvas_width - 20, 20,
            text=f"Batch {current_batch_num}/{total_batches}",
            anchor=tk.NE, font=("Arial", 14, "bold"), fill="black"
        )
        
        self.canvas.create_text(
            canvas_width - 20, 50,
            text=f"Grid: {actual_cols}x{actual_rows}",
            anchor=tk.NE, font=("Arial", 10), fill="gray"
        )
    
    def on_left_click(self, event):
        """Handle left click to set annotation to False (Red)"""
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("thumb_"):
                    idx = int(tag.split("_")[1])
                    detection = self.detection_boxes[idx]
                    detection['annotated'] = False
                    self.update_display()
                    self.log_status(f"🖱️ Left Click - Detection {idx+1}: False (Red)")
                    return

    def on_right_click(self, event):
        """Handle right click to set annotation to Unclear (Green)"""
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("thumb_"):
                    idx = int(tag.split("_")[1])
                    detection = self.detection_boxes[idx]
                    detection['annotated'] = "unclear"
                    self.update_display()
                    self.log_status(f"🖱️ Right Click - Detection {idx+1}: Unclear (Green)")
                    return

    def on_scroll(self, event):
        """Handle scroll wheel to set annotation to True (Blue) - Windows"""
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("thumb_"):
                    idx = int(tag.split("_")[1])
                    detection = self.detection_boxes[idx]
                    detection['annotated'] = True
                    self.update_display()
                    self.log_status(f"🖱️ Scroll Wheel - Detection {idx+1}: True (Blue)")
                    return

    def on_scroll_up(self, event):
        """Handle scroll up to set annotation to True (Blue) - Linux"""
        self.on_scroll(event)

    def on_scroll_down(self, event):
        """Handle scroll down to set annotation to True (Blue) - Linux"""
        self.on_scroll(event)

    def on_mouse_motion(self, event):
        """Track mouse movement to identify hovered detection"""
        if not hasattr(self, 'hovered_detection_idx'):
            self.hovered_detection_idx = None
            
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        old_hover = self.hovered_detection_idx
        self.hovered_detection_idx = None
        
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("thumb_"):
                    self.hovered_detection_idx = int(tag.split("_")[1])
                    break
        
        if old_hover != self.hovered_detection_idx:
            if self.hovered_detection_idx is not None:
                self.canvas.config(cursor="hand2")
            else:
                self.canvas.config(cursor="")

    def on_tab_press(self, event):
        """Show full size detection when Tab is pressed while hovering"""
        if not hasattr(self, 'hovered_detection_idx'):
            self.hovered_detection_idx = None
            
        if (self.hovered_detection_idx is not None and 
            hasattr(self, 'detection_boxes') and 
            self.hovered_detection_idx < len(self.detection_boxes)):
            detection = self.detection_boxes[self.hovered_detection_idx]
            self.show_fullsize_detection(detection, self.hovered_detection_idx)
            self.log_status(f"🔍 Showing full size - Detection {self.hovered_detection_idx + 1}")
        else:
            self.log_status("⚠️ Hover over a detection first, then press Tab")
        return "break"

    def show_fullsize_detection(self, detection, idx):
        """Show detection in full original size in popup window"""
        if not hasattr(self, 'fullsize_window'):
            self.fullsize_window = None
            
        if self.fullsize_window:
            self.fullsize_window.destroy()
        
        x1, y1 = detection['x'], detection['y']
        x2 = x1 + detection['width']
        y2 = y1 + detection['height']
        
        x1, y1 = max(0, x1), max(0, y1)
        x2 = min(self.current_frame.shape[1], x2)
        y2 = min(self.current_frame.shape[0], y2)
        
        cropped = self.current_frame[y1:y2, x1:x2]
        
        if cropped.size == 0:
            self.log_status("❌ Invalid detection area")
            return
        
        self.fullsize_window = tk.Toplevel(self.root)
        self.fullsize_window.title(f"Full Size - Detection {idx + 1}")
        self.fullsize_window.geometry("600x600")
        
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        
        max_size = 550
        h, w = cropped_rgb.shape[:2]
        if max(h, w) > max_size:
            if h > w:
                new_h, new_w = max_size, int(w * max_size / h)
            else:
                new_h, new_w = int(h * max_size / w), max_size
            cropped_rgb = cv2.resize(cropped_rgb, (new_w, new_h))
        
        pil_img = Image.fromarray(cropped_rgb)
        photo = ImageTk.PhotoImage(pil_img)
        
        label = tk.Label(self.fullsize_window, image=photo)
        label.image = photo
        label.pack(expand=True)
        
        if self.data_format in ["format2", "format2_partial"]:
            info_text = (f"Detection {idx + 1}\n"
                        f"Frame: {detection.get('frame_number', 'N/A')}\n"
                        f"Category: {detection['type']}\n"
                        f"Confidence: {detection['confidence']:.1%}\n"
                        f"Object ID: {detection.get('object_id', 'N/A')}\n"
                        f"Size: {detection['width']}x{detection['height']}px\n"
                        f"Area: {detection.get('area', 'N/A')}")
        else:
            info_text = (f"Detection {idx + 1}\n"
                        f"Type: {detection['type']}\n"
                        f"Confidence: {detection['confidence']:.1%}\n"
                        f"Original Size: {detection['width']}x{detection['height']}px")
        
        info_label = tk.Label(self.fullsize_window, text=info_text, font=("Arial", 12))
        info_label.pack(pady=10)
        
        close_btn = tk.Button(self.fullsize_window, text="Close", command=self.fullsize_window.destroy)
        close_btn.pack(pady=5)
        
        self.fullsize_window.focus_set()
        self.fullsize_window.lift()

    def on_space_press(self, event):
        """Handle spacebar press for next batch"""
        self.log_status("⌨️ Spacebar pressed - Next batch")
        self.next_batch()
        return "break"

    def on_key_press(self, event):
        """Handle all key presses for debugging"""
        if event.keysym == "space":
            self.on_space_press(event)
        elif event.keysym == "Left":
            self.on_left_arrow(event)
        elif event.keysym == "Right":
            self.on_right_arrow(event)
        elif event.keysym == "Tab":
            self.on_tab_press(event)
        return "break"
    
    def on_left_arrow(self, event):
        """Handle left arrow key for previous batch"""
        self.log_status("⌨️ Left Arrow - Previous batch")
        self.prev_batch()
        return "break"
    
    def on_right_arrow(self, event):
        """Handle right arrow key for next batch"""
        self.log_status("⌨️ Right Arrow - Next batch")
        self.next_batch()
        return "break"
    
    def on_window_click(self, event):
        """Re-focus window when clicked"""
        pass  # Removed to avoid interfering with search entry
    
    def next_batch(self):
        if not self.detection_boxes:
            self.log_status("⚠️ No detection boxes to navigate")
            return
        
        self.current_batch_index += self.thumbnails_per_batch
        if self.current_batch_index >= len(self.detection_boxes):
            self.current_batch_index = 0
            self.log_status("🔄 Reset to first batch")
        else:
            current_batch_num = self.current_batch_index // self.thumbnails_per_batch + 1
            self.log_status(f"➡️ Moved to batch {current_batch_num}")
        
        # Clean cache when moving batches
        self.cleanup_frame_cache()
        
        self.update_display()
        self.update_batch_info()
        
        self.root.focus_set()
        self.canvas.focus_set()

    def prev_batch(self):
        """Navigate to previous batch"""
        if not self.detection_boxes:
            self.log_status("⚠️ No detection boxes to navigate")
            return
        
        self.current_batch_index -= self.thumbnails_per_batch
        if self.current_batch_index < 0:
            total_batches = (len(self.detection_boxes) - 1) // self.thumbnails_per_batch + 1
            self.current_batch_index = (total_batches - 1) * self.thumbnails_per_batch
            self.log_status("🔄 Wrapped to last batch")
        else:
            current_batch_num = self.current_batch_index // self.thumbnails_per_batch + 1
            self.log_status(f"⬅️ Moved to batch {current_batch_num}")
        
        # Clean cache when moving batches
        self.cleanup_frame_cache()
        
        self.update_display()
        self.update_batch_info()
        
        self.root.focus_set()
        self.canvas.focus_set()
    
    def update_batch_info(self):
        if self.detection_boxes:
            total = len(self.detection_boxes)
            current_batch = self.current_batch_index // self.thumbnails_per_batch + 1
            total_batches = (total - 1) // self.thumbnails_per_batch + 1
            start = self.current_batch_index + 1
            end = min(self.current_batch_index + self.thumbnails_per_batch, total)
            
            text = f"Batch {current_batch}/{total_batches}\nShowing {start}-{end} of {total}"
            self.batch_label.config(text=text)
        else:
            self.batch_label.config(text="No data loaded")
    
    def save_results(self):
        if self.excel_data is None or not self.detection_boxes:
            messagebox.showwarning("Warning", "No data to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Annotated Results",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
        )
        
        if file_path:
            try:
                results = []
                for detection in self.detection_boxes:
                    row_idx = detection['row_index']
                    original_row = self.excel_data.iloc[row_idx]
                    
                    if self.data_format in ["format2", "format2_partial"]:
                        result = {
                            'frame_number': detection.get('frame_number', ''),
                            'video_time': detection.get('video_time', ''),
                            'real_time': detection.get('real_time', ''),
                            'object_id': detection.get('object_id', ''),
                            'category': detection['type'],
                            'confidence': f"{detection['confidence']:.1%}",
                            'x1': detection['x'],
                            'y1': detection['y'],
                            'x2': detection['x'] + detection['width'],
                            'y2': detection['y'] + detection['height'],
                            'width': detection['width'],
                            'height': detection['height'],
                            'area': detection.get('area', detection['width'] * detection['height']),
                            'verified': detection['annotated']
                        }
                    else:
                        result = {
                            'timestamp': original_row.get('timestamp', ''),
                            'detected_object': detection['type'],
                            'accuracy': f"{detection['confidence']:.1%}",
                            'bbox_x1': detection['x'],
                            'bbox_y1': detection['y'],
                            'bbox_width': detection['width'],
                            'bbox_height': detection['height'],
                            'verified': detection['annotated']
                        }
                    results.append(result)
                
                results_df = pd.DataFrame(results)
                
                if file_path.endswith('.csv'):
                    results_df.to_csv(file_path, index=False)
                else:
                    results_df.to_excel(file_path, index=False)
                
                self.log_status(f"💾 Results saved: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", f"Results saved!\nFile: {os.path.basename(file_path)}\nRows: {len(results_df)}")
                
            except Exception as e:
                self.log_status(f"❌ Save error: {e}")
                messagebox.showerror("Error", f"Failed to save: {e}")

def main():
    print("Starting Enhanced Fire Detection App with Search...")
    
    root = tk.Tk()
    app = SimpleFireDetector(root)
    
    def on_resize(event):
        if hasattr(app, 'current_frame') and app.current_frame is not None:
            app.root.after(50, app.update_display)
    
    root.bind('<Configure>', on_resize)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted")
    except Exception as e:
        print(f"Application error: {e}")

if __name__ == "__main__":
    main()