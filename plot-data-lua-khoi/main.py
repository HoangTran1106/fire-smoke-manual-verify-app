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
        self.root.geometry("1200x800")
        
        # Data storage
        self.current_frame = None
        self.excel_data = None
        self.detection_boxes = []
        self.current_batch_index = 0
        self.thumbnails_per_batch = 10
        
        self.setup_ui()
        self.log_status("Application started. Use buttons to load files.")
        
        # Bind spacebar globally to root window
        self.root.bind("<KeyPress-space>", self.on_space_press)
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<Button-1>", self.on_window_click)  # Re-focus on click
        self.root.bind("<Left>", self.on_left_arrow)  # Previous batch
        self.root.bind("<Right>", self.on_right_arrow)  # Next batch
        self.root.bind("<Tab>", self.on_tab_press)  # Show full size
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="Load Excel", command=self.load_excel).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Load Video", command=self.load_video).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Plot", command=self.run_detection).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Resume from Annotations", command=self.resume_from_excel).pack(side=tk.LEFT, padx=(0, 10))
        
        # Green DONE button with custom styling
        style = ttk.Style()
        style.configure("Green.TButton", 
                       foreground="black",  # Black text
                       background="green",
                       font=("Arial", 10, "bold"))
        
        done_btn = ttk.Button(control_frame, text="DONE - Next Batch", 
                             command=self.next_batch, style="Green.TButton")
        done_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Save Results As...", command=self.save_results).pack(side=tk.LEFT, padx=(0, 10))
        
        # Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left - Thumbnails
        left_frame = ttk.LabelFrame(content_frame, text="Detection Thumbnails")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.canvas = tk.Canvas(left_frame, bg='lightgray')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Button-1>", self.on_left_click)  # Left click
        self.canvas.bind("<Button-3>", self.on_right_click)  # Right click
        self.canvas.bind("<MouseWheel>", self.on_scroll)  # Scroll wheel (Windows)
        self.canvas.bind("<Button-4>", self.on_scroll_up)  # Scroll up (Linux)
        self.canvas.bind("<Button-5>", self.on_scroll_down)  # Scroll down (Linux)
        self.canvas.bind("<Motion>", self.on_mouse_motion)  # Track mouse movement
        
        # Make canvas focusable for keyboard events
        self.canvas.configure(highlightthickness=1)
        self.canvas.focus_set()
        self.canvas.bind("<KeyPress-space>", self.on_space_press)
        self.canvas.bind("<KeyPress>", self.on_key_press)  # Catch all key presses
        self.canvas.bind("<Left>", self.on_left_arrow)  # Previous batch
        self.canvas.bind("<Right>", self.on_right_arrow)  # Next batch
        self.canvas.bind("<Tab>", self.on_tab_press)  # Show full size
        
        # Right - Info
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status
        status_frame = ttk.LabelFrame(right_frame, text="Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_text = tk.Text(status_frame, width=40, height=10)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Batch info
        batch_frame = ttk.LabelFrame(right_frame, text="Batch Info")
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.batch_label = ttk.Label(batch_frame, text="No data loaded")
        self.batch_label.pack(padx=5, pady=5)
        
        # Legend
        legend_frame = ttk.LabelFrame(right_frame, text="Legend & Controls")
        legend_frame.pack(fill=tk.X)
        
        ttk.Label(legend_frame, text="🔵 Blue: True (Scroll Wheel)", foreground="blue").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="🔴 Red: False (Left Click)", foreground="red").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="🟢 Green: Unclear (Right Click)", foreground="green").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="⌨️ Spacebar: Next Batch", foreground="purple", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="← → Arrow Keys: Prev/Next Batch", foreground="orange", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="Tab: Show Full Size (hover first)", foreground="brown", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(legend_frame, text="💡 Click canvas first for keyboard focus", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W)
    
    def log_status(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        print(f"[{timestamp}] {message}")
    
    def load_excel(self):
        default_path = r"D:\Desktop\General\Cap\z-phase2\paths\chua-detect-video"
        if not os.path.exists(default_path):
            initial_dir = os.getcwd()
        else:
            initial_dir = default_path
            
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            initialdir=initial_dir,
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.excel_data = pd.read_excel(file_path)
                self.current_excel_path = file_path  # Store the file path
                self.log_status(f"✅ Excel loaded: {os.path.basename(file_path)} ({len(self.excel_data)} rows)")
            except Exception as e:
                self.log_status(f"❌ Excel load error: {e}")
    
    def load_video(self):
        if not CV2_AVAILABLE:
            self.log_status("❌ OpenCV not available")
            return
            
        default_path = r"D:\Desktop\General\Cap\z-phase2\paths\chua-detect-video"
        if not os.path.exists(default_path):
            initial_dir = os.getcwd()
        else:
            initial_dir = default_path
            
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            initialdir=initial_dir,
            filetypes=[("Video files", "*.mp4 *.avi *.mov"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                cap = cv2.VideoCapture(file_path)
                ret, frame = cap.read()
                if ret:
                    self.current_frame = frame
                    self.log_status(f"✅ Video loaded: {os.path.basename(file_path)}")
                cap.release()
            except Exception as e:
                self.log_status(f"❌ Video load error: {e}")
    
    def run_detection(self):
        if self.excel_data is None:
            self.log_status("❌ Load Excel file first")
            return
        if self.current_frame is None:
            self.log_status("❌ Load video file first")
            return
        
        self.detection_boxes = []
        self.current_batch_index = 0
        
        # Process Excel data
        for idx, row in self.excel_data.iterrows():
            try:
                detection = {
                    'x': int(row['bbox_x1']),
                    'y': int(row['bbox_y1']),
                    'width': int(row['bbox_width']),
                    'height': int(row['bbox_height']),
                    'type': row['class_name'],
                    'confidence': float(row['confidence']),
                    'annotated': True,  # Blue initially = True
                    'row_index': idx
                }
                self.detection_boxes.append(detection)
            except Exception as e:
                self.log_status(f"⚠️ Skipped row {idx}: {e}")
        
        self.update_display()
        self.update_batch_info()
        self.log_status(f"🔵 Loaded {len(self.detection_boxes)} detections")

    def resume_from_excel(self):
        """Resume editing from a previously saved annotation file"""
        print("Resume function called")  # Debug
        
        # Load annotation file (from "Save Annotated Results")
        file_path = filedialog.askopenfilename(
            title="Select Previously Saved Annotation File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv")]
        )
        
        if not file_path:
            print("No file selected")  # Debug
            return
            
        print(f"Selected file: {file_path}")  # Debug
        
        if self.current_frame is None:
            self.log_status("❌ Load video file first")
            return
        
        if self.excel_data is None:
            self.log_status("❌ Load original Excel file first")
            return
        
        try:
            print("Loading annotation file...")  # Debug
            
            # Load the annotation file
            if file_path.lower().endswith('.csv'):
                annotation_data = pd.read_csv(file_path)
            else:
                annotation_data = pd.read_excel(file_path)
            
            print(f"Annotation data loaded. Shape: {annotation_data.shape}")  # Debug
            print(f"Columns: {list(annotation_data.columns)}")  # Debug
            
            # Check if it has the expected format
            if 'verified' not in annotation_data.columns:
                messagebox.showerror("Error", "No 'verified' column found in annotation file")
                return
            
            print("Starting to process detections...")  # Debug
            
            self.detection_boxes = []
            self.current_batch_index = 0
            
            # Simple approach: assume same order and count
            annotation_index = 0
            for idx, original_row in self.excel_data.iterrows():
                try:
                    # Get annotation if available
                    if annotation_index < len(annotation_data):
                        ann_verified = annotation_data.iloc[annotation_index]['verified']
                        
                        # Convert to our format
                        if str(ann_verified).lower() == 'false':
                            verified_status = False
                        elif str(ann_verified).lower() == 'unclear':
                            verified_status = "unclear"
                        else:
                            verified_status = True
                        
                        annotation_index += 1
                    else:
                        verified_status = True  # Default
                    
                    detection = {
                        'x': int(original_row['bbox_x1']),
                        'y': int(original_row['bbox_y1']),
                        'width': int(original_row['bbox_width']),
                        'height': int(original_row['bbox_height']),
                        'type': original_row['class_name'],
                        'confidence': float(original_row['confidence']),
                        'annotated': verified_status,
                        'row_index': idx
                    }
                    self.detection_boxes.append(detection)
                    
                    if idx % 100 == 0:  # Progress indicator
                        print(f"Processed {idx} detections...")
                    
                except Exception as e:
                    print(f"Error processing row {idx}: {e}")
                    continue
            
            print(f"Finished processing. Total detections: {len(self.detection_boxes)}")  # Debug
            
            self.update_display()
            self.update_batch_info()
            self.log_status(f"🔄 Resumed from: {os.path.basename(file_path)} ({len(self.detection_boxes)} detections)")
            
            messagebox.showinfo("Success", f"Resumed from annotation file!\n{os.path.basename(file_path)}\nDetections: {len(self.detection_boxes)}")
            
        except Exception as e:
            error_msg = f"Failed to resume: {str(e)}"
            print(f"Error: {error_msg}")  # Debug
            self.log_status(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)

    def auto_save_to_original_excel(self):
        """Auto-save current annotations back to original Excel file"""
        if self.current_excel_path and self.excel_data is not None:
            try:
                # Update the verified column with current annotations
                for detection in self.detection_boxes:
                    row_idx = detection['row_index']
                    if row_idx < len(self.excel_data):
                        self.excel_data.loc[row_idx, 'verified'] = detection['annotated']
                
                # Save back to original Excel file
                self.excel_data.to_excel(self.current_excel_path, index=False)
                self.log_status(f"💾 Auto-saved annotations to original Excel: {os.path.basename(self.current_excel_path)}")
                
            except Exception as e:
                self.log_status(f"❌ Auto-save error: {e}")

    def save_annotations_to_original(self):
        """Save current annotations back to the original Excel file"""
        if self.current_excel_path and self.excel_data is not None:
            try:
                # Ensure 'verified' column exists
                if 'verified' not in self.excel_data.columns:
                    self.excel_data['verified'] = True
                
                # Update annotations
                for detection in self.detection_boxes:
                    row_idx = detection['row_index']
                    if row_idx < len(self.excel_data):
                        self.excel_data.loc[row_idx, 'verified'] = detection['annotated']
                
                # Save to original file
                self.excel_data.to_excel(self.current_excel_path, index=False)
                self.log_status(f"💾 Annotations saved to original Excel: {os.path.basename(self.current_excel_path)}")
                messagebox.showinfo("Saved", f"Annotations saved to original Excel!\n{os.path.basename(self.current_excel_path)}")
                
            except Exception as e:
                self.log_status(f"❌ Save to original error: {e}")
                messagebox.showerror("Error", f"Failed to save to original Excel: {e}")
        else:
            messagebox.showwarning("Warning", "No original Excel file path available")
        
        # Auto-save back to original Excel file to preserve the 'verified' column
        self.auto_save_to_original_excel()
    
    def update_display(self):
        if not self.detection_boxes or self.current_frame is None:
            return
        
        self.canvas.delete("all")
        
        # Get current batch
        start_idx = self.current_batch_index
        end_idx = min(start_idx + self.thumbnails_per_batch, len(self.detection_boxes))
        current_batch = self.detection_boxes[start_idx:end_idx]
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self.update_display)
            return
        
        # Calculate thumbnail size to fill entire screen area
        padding = 20
        available_width = canvas_width - (2 * padding)
        available_height = canvas_height - (2 * padding)
        
        # Force multiple rows to use full screen height
        max_cols = 8  # Maximum columns per row
        cols = min(len(current_batch), max_cols)
        rows = (len(current_batch) - 1) // cols + 1
        
        # Calculate thumbnail size to fill the available space
        thumb_width = (available_width - (cols - 1) * padding) // cols if cols > 0 else 100
        thumb_height = (available_height - (rows - 1) * padding - 60) // rows if rows > 0 else 100  # 60px for labels
        
        # Use square thumbnails, but make them large
        thumb_size = min(thumb_width, thumb_height)
        thumb_size = max(thumb_size, 120)  # Minimum 120px
        thumb_size = min(thumb_size, 250)  # Maximum 250px
        
        # Recalculate optimal columns based on thumb size
        actual_cols = min(cols, available_width // (thumb_size + padding))
        actual_rows = (len(current_batch) - 1) // actual_cols + 1
        
        # Center the grid
        total_grid_width = actual_cols * thumb_size + (actual_cols - 1) * padding
        total_grid_height = actual_rows * thumb_size + (actual_rows - 1) * padding + 60  # 60 for labels
        
        start_x = (canvas_width - total_grid_width) // 2
        start_y = (canvas_height - total_grid_height) // 2
        
        self.thumbnail_photos = []
        
        for i, detection in enumerate(current_batch):
            try:
                # Calculate grid position
                col = i % actual_cols
                row = i // actual_cols
                
                # Extract thumbnail
                x1, y1 = detection['x'], detection['y']
                x2 = x1 + detection['width']
                y2 = y1 + detection['height']
                
                # Crop with bounds checking
                x1, y1 = max(0, x1), max(0, y1)
                x2 = min(self.current_frame.shape[1], x2)
                y2 = min(self.current_frame.shape[0], y2)
                
                cropped = self.current_frame[y1:y2, x1:x2]
                if cropped.size == 0:
                    continue
                
                # Convert and resize
                cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                cropped_resized = cv2.resize(cropped_rgb, (thumb_size, thumb_size))
                
                # Create photo
                pil_img = Image.fromarray(cropped_resized)
                photo = ImageTk.PhotoImage(pil_img)
                self.thumbnail_photos.append(photo)
                
                # Position in grid - spread across entire canvas
                x_pos = start_x + col * (thumb_size + padding) + thumb_size // 2
                y_pos = start_y + row * (thumb_size + padding + 40) + thumb_size // 2  # 40px space for labels
                
                # Color based on annotation: Blue=True, Red=False, Green=Unclear
                if detection['annotated'] == True:
                    color = "blue"
                    border_width = 6
                elif detection['annotated'] == False:
                    color = "red" 
                    border_width = 6
                elif detection['annotated'] == "unclear":
                    color = "green"  # Green for unclear
                    border_width = 6
                else:
                    color = "gray"  # Neutral state
                    border_width = 4
                
                # Draw border
                actual_idx = start_idx + i
                border_offset = border_width // 2 + 2
                self.canvas.create_rectangle(
                    x_pos - thumb_size//2 - border_offset, 
                    y_pos - thumb_size//2 - border_offset,
                    x_pos + thumb_size//2 + border_offset, 
                    y_pos + thumb_size//2 + border_offset,
                    outline=color, width=border_width, tags=f"thumb_{actual_idx}"
                )
                
                # Create thumbnail image
                self.canvas.create_image(x_pos, y_pos, image=photo, tags=f"thumb_{actual_idx}")
                
                # Label with appropriate font size
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
        
        # Batch indicator in top-right corner
        total_batches = (len(self.detection_boxes) - 1) // self.thumbnails_per_batch + 1
        current_batch_num = self.current_batch_index // self.thumbnails_per_batch + 1
        self.canvas.create_text(
            canvas_width - 20, 20,
            text=f"Batch {current_batch_num}/{total_batches}",
            anchor=tk.NE, font=("Arial", 14, "bold"), fill="black"
        )
        
        # Show grid info
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
                    
                    # Left click sets to False (Red)
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
                    
                    # Right click sets to Unclear (Green)
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
                    
                    # Scroll wheel sets to True (Blue)
                    detection['annotated'] = True
                    
                    self.update_display()
                    self.log_status(f"🖱️ Scroll Wheel - Detection {idx+1}: True (Blue)")
                    return

    def on_scroll_up(self, event):
        """Handle scroll up to set annotation to True (Blue) - Linux"""
        self.on_scroll(event)

    def on_mouse_motion(self, event):
        """Track mouse movement to identify hovered detection"""
        # Initialize if not exists
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
        
        # Update cursor if hover state changed
        if old_hover != self.hovered_detection_idx:
            if self.hovered_detection_idx is not None:
                self.canvas.config(cursor="hand2")
            else:
                self.canvas.config(cursor="")

    def on_tab_press(self, event):
        """Show full size detection when Tab is pressed while hovering"""
        # Initialize if not exists
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
        # Initialize fullsize_window if not exists
        if not hasattr(self, 'fullsize_window'):
            self.fullsize_window = None
            
        if self.fullsize_window:
            self.fullsize_window.destroy()
        
        # Extract full size detection area
        x1, y1 = detection['x'], detection['y']
        x2 = x1 + detection['width']
        y2 = y1 + detection['height']
        
        # Bounds checking
        x1, y1 = max(0, x1), max(0, y1)
        x2 = min(self.current_frame.shape[1], x2)
        y2 = min(self.current_frame.shape[0], y2)
        
        cropped = self.current_frame[y1:y2, x1:x2]
        
        if cropped.size == 0:
            self.log_status("❌ Invalid detection area")
            return
        
        # Create popup window
        self.fullsize_window = tk.Toplevel(self.root)
        self.fullsize_window.title(f"Full Size - Detection {idx + 1}")
        self.fullsize_window.geometry("600x600")
        
        # Convert and display
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        
        # Scale to fit window while maintaining aspect ratio
        max_size = 550
        h, w = cropped_rgb.shape[:2]
        if max(h, w) > max_size:
            if h > w:
                new_h, new_w = max_size, int(w * max_size / h)
            else:
                new_h, new_w = int(h * max_size / w), max_size
            cropped_rgb = cv2.resize(cropped_rgb, (new_w, new_h))
        
        # Create and display image
        pil_img = Image.fromarray(cropped_rgb)
        photo = ImageTk.PhotoImage(pil_img)
        
        label = tk.Label(self.fullsize_window, image=photo)
        label.image = photo  # Keep reference
        label.pack(expand=True)
        
        # Add info
        info_text = f"Detection {idx + 1}\nType: {detection['type']}\nConfidence: {detection['confidence']:.1%}\nOriginal Size: {detection['width']}x{detection['height']}px"
        info_label = tk.Label(self.fullsize_window, text=info_text, font=("Arial", 12))
        info_label.pack(pady=10)
        
        # Close button
        close_btn = tk.Button(self.fullsize_window, text="Close", command=self.fullsize_window.destroy)
        close_btn.pack(pady=5)
        
        # Focus and bring to front
        self.fullsize_window.focus_set()
        self.fullsize_window.lift()

    def on_scroll_down(self, event):
        """Handle scroll down to set annotation to True (Blue) - Linux"""
        self.on_scroll(event)

    def on_space_press(self, event):
        """Handle spacebar press for next batch"""
        print("Spacebar pressed!")  # Debug
        self.log_status("⌨️ Spacebar pressed - Next batch")
        self.next_batch()
        return "break"  # Prevent event propagation

    def on_key_press(self, event):
        """Handle all key presses for debugging"""
        print(f"Key pressed: {event.keysym}")  # Debug
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
        print("Left arrow pressed!")  # Debug
        self.log_status("⌨️ Left Arrow - Previous batch")
        self.prev_batch()
        return "break"
    
    def on_right_arrow(self, event):
        """Handle right arrow key for next batch"""
        print("Right arrow pressed!")  # Debug
        self.log_status("⌨️ Right Arrow - Next batch")
        self.next_batch()
        return "break"
    
    def on_window_click(self, event):
        """Re-focus window when clicked"""
        self.root.focus_set()
        self.canvas.focus_set()
        """Handle spacebar press for next batch"""
        print("Spacebar pressed!")  # Debug
        self.log_status("⌨️ Spacebar pressed - Next batch")
        self.next_batch()
        return "break"  # Prevent event propagation

    def on_key_press(self, event):
        """Handle all key presses for debugging"""
        print(f"Key pressed: {event.keysym}")  # Debug
        if event.keysym == "space":
            self.on_space_press(event)
        return "break"
    
    def on_window_click(self, event):
        """Re-focus window when clicked"""
        self.root.focus_set()
        self.canvas.focus_set()
    
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
        
        self.update_display()
        self.update_batch_info()
        
        # Ensure focus remains for keyboard events
        self.root.focus_set()
        self.canvas.focus_set()

    def prev_batch(self):
        """Navigate to previous batch"""
        if not self.detection_boxes:
            self.log_status("⚠️ No detection boxes to navigate")
            return
        
        self.current_batch_index -= self.thumbnails_per_batch
        if self.current_batch_index < 0:
            # Go to last batch
            total_batches = (len(self.detection_boxes) - 1) // self.thumbnails_per_batch + 1
            self.current_batch_index = (total_batches - 1) * self.thumbnails_per_batch
            self.log_status("🔄 Wrapped to last batch")
        else:
            current_batch_num = self.current_batch_index // self.thumbnails_per_batch + 1
            self.log_status(f"⬅️ Moved to batch {current_batch_num}")
        
        self.update_display()
        self.update_batch_info()
        
        # Ensure focus remains for keyboard events
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
                # Create results dataframe
                results = []
                for detection in self.detection_boxes:
                    row_idx = detection['row_index']
                    original_row = self.excel_data.iloc[row_idx]
                    
                    result = {
                        'timestamp': original_row.get('timestamp', ''),
                        'detected_object': detection['type'],
                        'accuracy': f"{detection['confidence']:.1%}",
                        'verified': detection['annotated']  # True, False, or "unclear"
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
    print("Starting Simple Fire Detection App...")
    
    root = tk.Tk()
    app = SimpleFireDetector(root)
    
    # Handle window resize
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