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
        self.thumbnails_per_batch = 21
        
        self.setup_ui()
        self.log_status("Application started. Use buttons to load files.")
    
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
        
        # Green DONE button with custom styling
        style = ttk.Style()
        style.configure("Green.TButton", 
                       foreground="white", 
                       background="green",
                       font=("Arial", 10, "bold"))
        
        done_btn = ttk.Button(control_frame, text="DONE - Next Batch", 
                             command=self.next_batch, style="Green.TButton")
        done_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Save Results", command=self.save_results).pack(side=tk.LEFT, padx=(0, 10))
        
        # Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left - Thumbnails
        left_frame = ttk.LabelFrame(content_frame, text="Detection Thumbnails")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.canvas = tk.Canvas(left_frame, bg='lightgray')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Button-1>", self.on_click)
        
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
        legend_frame = ttk.LabelFrame(right_frame, text="Legend")
        legend_frame.pack(fill=tk.X)
        
        ttk.Label(legend_frame, text="🔵 Blue: True", foreground="blue").pack(anchor=tk.W)
        ttk.Label(legend_frame, text="🔴 Red: False", foreground="red").pack(anchor=tk.W)
    
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
                
                # Color based on annotation: Blue=True, Red=False
                if detection['annotated'] == True:
                    color = "blue"
                    border_width = 6
                elif detection['annotated'] == False:
                    color = "red" 
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
    
    def on_click(self, event):
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("thumb_"):
                    idx = int(tag.split("_")[1])
                    detection = self.detection_boxes[idx]
                    
                    # Toggle annotation: True (Blue) -> False (Red) -> True (Blue)
                    if detection['annotated'] == True:
                        detection['annotated'] = False  # Blue to Red
                    elif detection['annotated'] == False:
                        detection['annotated'] = True   # Red to Blue
                    else:
                        detection['annotated'] = True   # Default to Blue
                    
                    self.update_display()
                    status_map = {True: "True (Blue)", False: "False (Red)"}
                    self.log_status(f"🖱️ Detection {idx+1}: {status_map[detection['annotated']]}")
                    return
    
    def next_batch(self):
        if not self.detection_boxes:
            return
        
        self.current_batch_index += self.thumbnails_per_batch
        if self.current_batch_index >= len(self.detection_boxes):
            self.current_batch_index = 0
            self.log_status("🔄 Reset to first batch")
        
        self.update_display()
        self.update_batch_info()
    
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
                        'verified': detection['annotated']  # True or False
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