import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import pandas as pd
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import os
from datetime import datetime, timedelta

class VideoDetectionValidator:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Detection Validator")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Video and data variables
        self.video_path = "test.mp4"
        self.excel_path = "test.xlsx"
        self.output_excel_path = "test_validated.xlsx"
        
        self.cap = None
        self.df = None
        self.current_frame = None
        self.current_detections = []
        self.current_row_index = 0
        self.total_detections = 0
        self.is_playing = False
        self.video_fps = 30
        self.video_start_time = None
        
        # UI variables
        self.frame_label = None
        self.status_var = tk.StringVar(value="Ready - Load video and Excel file")
        self.progress_var = tk.StringVar(value="0/0")
        self.timestamp_var = tk.StringVar(value="00:00:00")
        
        # Detection validation results
        self.validation_results = []
        
        self.setup_ui()
        self.bind_keyboard_events()
        self.load_data()
    
    def setup_ui(self):
        """Create the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Video Detection Validator", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Control panel (left side)
        self.create_control_panel(main_frame)
        
        # Video display (center)
        self.create_video_display(main_frame)
        
        # Info panel (right side)
        self.create_info_panel(main_frame)
        
        # Status bar (bottom)
        self.create_status_bar(main_frame)
    
    def create_control_panel(self, parent):
        """Create control buttons and information"""
        control_frame = ttk.LabelFrame(parent, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # File loading buttons
        ttk.Button(control_frame, text="Load Video", 
                  command=self.load_video).grid(row=0, column=0, pady=5, sticky=tk.W+tk.E)
        ttk.Button(control_frame, text="Load Excel", 
                  command=self.load_excel).grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Separator
        ttk.Separator(control_frame, orient='horizontal').grid(row=2, column=0, 
                                                              sticky=tk.W+tk.E, pady=10)
        
        # Video controls
        ttk.Label(control_frame, text="Video Controls:", 
                 font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W)
        
        control_buttons_frame = ttk.Frame(control_frame)
        control_buttons_frame.grid(row=4, column=0, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(control_buttons_frame, text="Play/Pause", 
                  command=self.toggle_playback).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_buttons_frame, text="Previous", 
                  command=self.prev_detection).grid(row=0, column=1, padx=5)
        ttk.Button(control_buttons_frame, text="Next", 
                  command=self.next_detection).grid(row=0, column=2, padx=5)
        
        # Separator
        ttk.Separator(control_frame, orient='horizontal').grid(row=5, column=0, 
                                                              sticky=tk.W+tk.E, pady=10)
        
        # Validation controls
        ttk.Label(control_frame, text="Detection Validation:", 
                 font=('Arial', 10, 'bold')).grid(row=6, column=0, sticky=tk.W)
        
        validation_frame = ttk.Frame(control_frame)
        validation_frame.grid(row=7, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Validation buttons with keyboard shortcuts
        false_btn = ttk.Button(validation_frame, text="False Detection (M)", 
                              command=lambda: self.mark_detection(False))
        false_btn.grid(row=0, column=0, pady=2, sticky=tk.W+tk.E)
        false_btn.configure(style='False.TButton')
        
        true_btn = ttk.Button(validation_frame, text="True Detection (Z)", 
                             command=lambda: self.mark_detection(True))
        true_btn.grid(row=1, column=0, pady=2, sticky=tk.W+tk.E)
        true_btn.configure(style='True.TButton')
        
        # Configure button styles
        style = ttk.Style()
        style.configure('False.TButton', foreground='red')
        style.configure('True.TButton', foreground='green')
        
        # Export button
        ttk.Separator(control_frame, orient='horizontal').grid(row=8, column=0, 
                                                              sticky=tk.W+tk.E, pady=10)
        ttk.Button(control_frame, text="Export Results", 
                  command=self.export_results).grid(row=9, column=0, pady=5, sticky=tk.W+tk.E)
    
    def create_video_display(self, parent):
        """Create video display area"""
        video_frame = ttk.LabelFrame(parent, text="Video Display", padding="10")
        video_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        # Video display label
        self.frame_label = ttk.Label(video_frame, text="Load video file to display", 
                                    background='black', foreground='white',
                                    font=('Arial', 12))
        self.frame_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Video info
        info_frame = ttk.Frame(video_frame)
        info_frame.grid(row=1, column=0, pady=(10, 0), sticky=tk.W+tk.E)
        
        ttk.Label(info_frame, text="Timestamp:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, textvariable=self.timestamp_var).grid(row=0, column=1, padx=(5, 20))
        
        ttk.Label(info_frame, text="Progress:").grid(row=0, column=2, sticky=tk.W)
        ttk.Label(info_frame, textvariable=self.progress_var).grid(row=0, column=3, padx=5)
    
    def create_info_panel(self, parent):
        """Create information panel"""
        info_frame = ttk.LabelFrame(parent, text="Detection Info", padding="10")
        info_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Current detection info
        self.detection_info = tk.Text(info_frame, height=15, width=30, 
                                     font=('Courier', 9))
        self.detection_info.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for text
        scrollbar = ttk.Scrollbar(info_frame, orient="vertical", 
                                 command=self.detection_info.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.detection_info.configure(yscrollcommand=scrollbar.set)
        
        # Keyboard shortcuts info
        shortcuts_frame = ttk.LabelFrame(info_frame, text="Keyboard Shortcuts", padding="5")
        shortcuts_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky=tk.W+tk.E)
        
        shortcuts_text = """M: Mark as False Detection
Z: Mark as True Detection
Space: Play/Pause video
←/→: Previous/Next detection
Ctrl+S: Export results"""
        
        ttk.Label(shortcuts_frame, text=shortcuts_text, 
                 font=('Arial', 9), justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E, pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                relief=tk.SUNKEN, padding="5")
        status_label.grid(row=0, column=0, sticky=tk.W+tk.E)
    
    def bind_keyboard_events(self):
        """Bind keyboard events"""
        self.root.bind('<KeyPress-m>', lambda e: self.mark_detection(False))
        self.root.bind('<KeyPress-M>', lambda e: self.mark_detection(False))
        self.root.bind('<KeyPress-z>', lambda e: self.mark_detection(True))
        self.root.bind('<KeyPress-Z>', lambda e: self.mark_detection(True))
        self.root.bind('<space>', lambda e: self.toggle_playback())
        self.root.bind('<Left>', lambda e: self.prev_detection())
        self.root.bind('<Right>', lambda e: self.next_detection())
        self.root.bind('<Control-s>', lambda e: self.export_results())
        
        # Make root focusable for keyboard events
        self.root.focus_set()
    
    def load_data(self):
        """Load video and Excel data automatically"""
        try:
            # Check if files exist
            if os.path.exists(self.video_path) and os.path.exists(self.excel_path):
                self.load_video_file(self.video_path)
                self.load_excel_file(self.excel_path)
                self.status_var.set(f"Loaded: {self.video_path} and {self.excel_path}")
            else:
                missing_files = []
                if not os.path.exists(self.video_path):
                    missing_files.append(self.video_path)
                if not os.path.exists(self.excel_path):
                    missing_files.append(self.excel_path)
                self.status_var.set(f"Missing files: {', '.join(missing_files)}")
        except Exception as e:
            self.status_var.set(f"Error loading data: {str(e)}")
    
    def load_video(self):
        """Load video file dialog"""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("MP4 files", "*.mp4"), ("All video files", "*.mp4;*.avi;*.mov")]
        )
        if file_path:
            self.video_path = file_path
            self.load_video_file(file_path)
    
    def load_video_file(self, file_path):
        """Load video file"""
        try:
            if self.cap:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                raise Exception("Could not open video file")
            
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.status_var.set(f"Video loaded: {os.path.basename(file_path)}")
            
            # Display first frame
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                self.display_frame()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video: {str(e)}")
    
    def load_excel(self):
        """Load Excel file dialog"""
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            self.excel_path = file_path
            self.load_excel_file(file_path)
    
    def load_excel_file(self, file_path):
        """Load Excel file with detection data"""
        try:
            self.df = pd.read_excel(file_path)
            
            # Check if we have at least 5 columns
            if len(self.df.columns) < 5:
                raise Exception(f"Excel file must have at least 5 columns. Found: {len(self.df.columns)}")
            
            # Use column positions: C=2, D=3, E=4, F=5, G=6 (0-indexed)
            # Or use actual column names if they exist
            column_mapping = {}
            
            # Try to find columns by position (C, D, E, F, G correspond to columns 2, 3, 4, 5, 6)
            if len(self.df.columns) >= 5:
                # Use positional mapping - assuming timestamp is in 3rd column (index 2) and boxes in next 4
                timestamp_col = self.df.columns[2]  # Column C (3rd column)
                x1_col = self.df.columns[3]         # Column D (4th column)  
                y1_col = self.df.columns[4]         # Column E (5th column)
                x2_col = self.df.columns[5] if len(self.df.columns) > 5 else self.df.columns[4]  # Column F
                y2_col = self.df.columns[6] if len(self.df.columns) > 6 else self.df.columns[4]  # Column G
                
                column_mapping = {
                    timestamp_col: 'timestamp',
                    x1_col: 'x1',
                    y1_col: 'y1',
                    x2_col: 'x2', 
                    y2_col: 'y2'
                }
            
            # Alternative: Check if columns are actually named C, D, E, F, G
            if all(col in self.df.columns for col in ['C', 'D', 'E', 'F', 'G']):
                column_mapping = {
                    'C': 'timestamp',
                    'D': 'x1',
                    'E': 'y1',
                    'F': 'x2',
                    'G': 'y2'
                }
            
            # Print column information for debugging
            print(f"Excel columns found: {list(self.df.columns)}")
            print(f"Using column mapping: {column_mapping}")
            
            # Rename columns for easier access
            self.df = self.df.rename(columns=column_mapping)
            
            # Validate that we have the required columns after mapping
            required_cols = ['timestamp', 'x1', 'y1', 'x2', 'y2']
            missing_cols = [col for col in required_cols if col not in self.df.columns]
            if missing_cols:
                raise Exception(f"Missing required columns after mapping: {missing_cols}")
            
            # Convert numeric columns to proper types
            for col in ['x1', 'y1', 'x2', 'y2']:
                try:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                except Exception as convert_error:
                    print(f"Warning: Could not convert column {col} to numeric: {convert_error}")
            
            # Check for any NaN values in coordinates
            nan_coords = self.df[['x1', 'y1', 'x2', 'y2']].isna().sum().sum()
            if nan_coords > 0:
                print(f"Warning: Found {nan_coords} NaN values in coordinate columns")
            
            # Print sample data for debugging
            print("Sample data:")
            print(self.df[['timestamp', 'x1', 'y1', 'x2', 'y2']].head())
            
            # Initialize validation results
            self.validation_results = [None] * len(self.df)
            self.total_detections = len(self.df)
            self.current_row_index = 0
            
            self.update_progress()
            self.update_detection_info()
            self.go_to_detection(0)
            
            self.status_var.set(f"Excel loaded: {self.total_detections} detections found")
            
        except Exception as e:
            error_msg = f"Failed to load Excel file: {str(e)}"
            print(f"Excel loading error: {error_msg}")
            print(f"Full error details: {repr(e)}")
            messagebox.showerror("Error", error_msg)
    
    def go_to_detection(self, index):
        """Navigate to specific detection"""
        if self.df is None or self.cap is None or index >= len(self.df):
            return
        
        try:
            self.current_row_index = index
            detection = self.df.iloc[index]
            
            # Parse timestamp and seek to frame
            timestamp = detection['timestamp']
            if isinstance(timestamp, str):
                # Parse timestamp format (assuming HH:MM:SS or similar)
                time_parts = timestamp.split(':')
                if len(time_parts) == 3:
                    hours, minutes, seconds = map(float, time_parts)
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                else:
                    total_seconds = float(timestamp)
            else:
                total_seconds = float(timestamp)
            
            # Seek to frame
            frame_number = int(total_seconds * self.video_fps)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame.copy()
                self.current_detections = [{
                    'x1': int(detection['x1']),
                    'y1': int(detection['y1']),
                    'x2': int(detection['x2']),
                    'y2': int(detection['y2'])
                }]
                
                self.display_frame()
                self.update_progress()
                self.update_detection_info()
                
                # Update timestamp display
                self.timestamp_var.set(str(timestamp))
            
        except Exception as e:
            self.status_var.set(f"Error navigating to detection: {str(e)}")
    
    def display_frame(self):
        """Display current frame with detection boxes"""
        if self.current_frame is None:
            return
        
        try:
            frame = self.current_frame.copy()
            
            # Draw detection boxes
            for detection in self.current_detections:
                x1, y1, x2, y2 = detection['x1'], detection['y1'], detection['x2'], detection['y2']
                
                # Determine box color based on validation status
                validation_status = self.validation_results[self.current_row_index]
                if validation_status is True:
                    color = (0, 255, 0)  # Green for true detection
                    label = "TRUE"
                elif validation_status is False:
                    color = (0, 0, 255)  # Red for false detection
                    label = "FALSE"
                else:
                    color = (255, 255, 0)  # Yellow for unvalidated
                    label = "UNVALIDATED"
                
                # Draw rectangle
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label
                cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, color, 2)
            
            # Convert to PIL Image and then to PhotoImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Resize for display
            display_width = 640
            display_height = int(pil_image.height * display_width / pil_image.width)
            pil_image = pil_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(pil_image)
            self.frame_label.configure(image=photo, text="")
            self.frame_label.image = photo  # Keep a reference
            
        except Exception as e:
            self.status_var.set(f"Error displaying frame: {str(e)}")
    
    def mark_detection(self, is_true_detection):
        """Mark current detection as true or false"""
        if self.current_row_index < len(self.validation_results):
            self.validation_results[self.current_row_index] = is_true_detection
            
            # Update display
            self.display_frame()
            self.update_detection_info()
            
            # Status message
            status = "TRUE" if is_true_detection else "FALSE"
            self.status_var.set(f"Detection {self.current_row_index + 1} marked as {status}")
            
            # Auto-advance to next detection
            if self.current_row_index < self.total_detections - 1:
                self.next_detection()
    
    def prev_detection(self):
        """Go to previous detection"""
        if self.current_row_index > 0:
            self.go_to_detection(self.current_row_index - 1)
    
    def next_detection(self):
        """Go to next detection"""
        if self.current_row_index < self.total_detections - 1:
            self.go_to_detection(self.current_row_index + 1)
    
    def toggle_playback(self):
        """Toggle video playback"""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_video()
        self.status_var.set("Playing" if self.is_playing else "Paused")
    
    def play_video(self):
        """Play video in a separate thread"""
        def video_thread():
            while self.is_playing and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame
                    self.display_frame()
                    time.sleep(1.0 / self.video_fps)
                else:
                    self.is_playing = False
                    break
        
        if self.is_playing:
            threading.Thread(target=video_thread, daemon=True).start()
    
    def update_progress(self):
        """Update progress display"""
        if self.total_detections > 0:
            validated_count = sum(1 for v in self.validation_results if v is not None)
            self.progress_var.set(f"{self.current_row_index + 1}/{self.total_detections} "
                                f"(Validated: {validated_count})")
    
    def update_detection_info(self):
        """Update detection information display"""
        if self.df is None or self.current_row_index >= len(self.df):
            return
        
        detection = self.df.iloc[self.current_row_index]
        validation_status = self.validation_results[self.current_row_index]
        
        info_text = f"""CURRENT DETECTION #{self.current_row_index + 1}

Timestamp: {detection['timestamp']}
Bounding Box:
  X1: {detection['x1']}
  Y1: {detection['y1']} 
  X2: {detection['x2']}
  Y2: {detection['y2']}

Box Size: {detection['x2'] - detection['x1']} x {detection['y2'] - detection['y1']}

Validation Status: """
        
        if validation_status is True:
            info_text += "TRUE DETECTION ✓"
        elif validation_status is False:
            info_text += "FALSE DETECTION ✗"
        else:
            info_text += "UNVALIDATED ?"
        
        info_text += f"""

VALIDATION SUMMARY:
Total Detections: {self.total_detections}
Validated: {sum(1 for v in self.validation_results if v is not None)}
True Detections: {sum(1 for v in self.validation_results if v is True)}
False Detections: {sum(1 for v in self.validation_results if v is False)}
Remaining: {sum(1 for v in self.validation_results if v is None)}"""
        
        self.detection_info.delete(1.0, tk.END)
        self.detection_info.insert(1.0, info_text)
    
    def export_results(self):
        """Export validation results to new Excel file"""
        if self.df is None:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            # Create a copy of the dataframe
            export_df = self.df.copy()
            
            # Add validation results column
            validation_column = []
            for result in self.validation_results:
                if result is True:
                    validation_column.append("TRUE_DETECTION")
                elif result is False:
                    validation_column.append("FALSE_DETECTION")
                else:
                    validation_column.append("UNVALIDATED")
            
            export_df['Validation_Result'] = validation_column
            
            # Keep original column names (don't rename back since we used positional mapping)
            
            # Save to file
            export_df.to_excel(self.output_excel_path, index=False)
            
            messagebox.showinfo("Export Complete", 
                              f"Results exported to: {self.output_excel_path}\n\n"
                              f"Total validations: {sum(1 for v in self.validation_results if v is not None)}")
            
            self.status_var.set(f"Results exported to {self.output_excel_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.cap:
            self.cap.release()

def main():
    root = tk.Tk()
    app = VideoDetectionValidator(root)
    
    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    try:
        root.mainloop()
    finally:
        if hasattr(app, 'cap') and app.cap:
            app.cap.release()

if __name__ == "__main__":
    main()