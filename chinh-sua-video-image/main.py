import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random

class KeyboardUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter UI with Keyboard Controls")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.counter = tk.IntVar(value=0)
        self.text_content = tk.StringVar(value="Type something...")
        
        # Configure styles
        self.setup_styles()
        
        # Create main layout
        self.create_layout()
        
        # Bind keyboard events
        self.setup_keyboard_bindings()
        
        # Focus on root to capture key events
        self.root.focus_set()
    
    def setup_styles(self):
        """Configure ttk styles for better appearance"""
        style = ttk.Style()
        style.theme_use('clam')  # Use a modern theme
        
        # Configure button style
        style.configure('Action.TButton', 
                       font=('Arial', 10, 'bold'),
                       padding=(10, 5))
        
        # Configure label style
        style.configure('Title.TLabel', 
                       font=('Arial', 14, 'bold'),
                       background='#f0f0f0')
    
    def create_layout(self):
        """Create the main UI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Keyboard-Controlled UI Demo", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Counter section
        self.create_counter_section(main_frame, row=1)
        
        # Text input section
        self.create_text_section(main_frame, row=2)
        
        # Control buttons section
        self.create_button_section(main_frame, row=3)
        
        # Output/Log section
        self.create_output_section(main_frame, row=4)
        
        # Status bar
        self.create_status_bar(main_frame, row=5)
        
        # Keyboard help
        self.create_help_section(main_frame, row=6)
    
    def create_counter_section(self, parent, row):
        """Create counter controls"""
        frame = ttk.LabelFrame(parent, text="Counter (Use +/- keys)", padding="10")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(frame, text="Value:").grid(row=0, column=0, padx=(0, 10))
        
        self.counter_label = ttk.Label(frame, textvariable=self.counter, 
                                      font=('Arial', 16, 'bold'))
        self.counter_label.grid(row=0, column=1, padx=10)
        
        ttk.Button(frame, text="Reset", command=self.reset_counter,
                  style='Action.TButton').grid(row=0, column=2, padx=10)
    
    def create_text_section(self, parent, row):
        """Create text input area"""
        frame = ttk.LabelFrame(parent, text="Text Input (Focus with F1)", padding="10")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        frame.columnconfigure(0, weight=1)
        
        self.text_entry = ttk.Entry(frame, textvariable=self.text_content, 
                                   font=('Arial', 12), width=50)
        self.text_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(frame, text="Clear", command=self.clear_text,
                  style='Action.TButton').grid(row=0, column=1)
    
    def create_button_section(self, parent, row):
        """Create control buttons"""
        frame = ttk.LabelFrame(parent, text="Actions (Use number keys 1-4)", padding="10")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        buttons = [
            ("1. Random Color", self.change_color),
            ("2. Show Message", self.show_message),
            ("3. Add Random Text", self.add_random_text),
            ("4. Clear Output", self.clear_output)
        ]
        
        for i, (text, command) in enumerate(buttons):
            ttk.Button(frame, text=text, command=command,
                      style='Action.TButton').grid(row=i//2, column=i%2, 
                                                  padx=5, pady=2, sticky=tk.W)
    
    def create_output_section(self, parent, row):
        """Create output text area"""
        frame = ttk.LabelFrame(parent, text="Output Log", padding="10")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(frame, height=8, width=70,
                                                    font=('Courier', 10))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initial message
        self.log_message("UI initialized. Use keyboard shortcuts to interact!")
    
    def create_status_bar(self, parent, row):
        """Create status bar"""
        self.status_var = tk.StringVar(value="Ready - Press H for help")
        status_label = ttk.Label(parent, textvariable=self.status_var, 
                                relief=tk.SUNKEN, padding="5")
        status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def create_help_section(self, parent, row):
        """Create help information"""
        frame = ttk.LabelFrame(parent, text="Keyboard Shortcuts", padding="10")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        help_text = """
+/-: Increment/Decrement counter  |  1-4: Action buttons  |  F1: Focus text input
Ctrl+Q: Quit  |  Ctrl+R: Reset all  |  H: Show help  |  Space: Random action
ESC: Clear focus  |  Enter: Process text input"""
        
        ttk.Label(frame, text=help_text, font=('Arial', 9), 
                 justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
    
    def setup_keyboard_bindings(self):
        """Set up all keyboard event bindings"""
        # Counter controls
        self.root.bind('<plus>', lambda e: self.increment_counter())
        self.root.bind('<KP_Add>', lambda e: self.increment_counter())
        self.root.bind('<minus>', lambda e: self.decrement_counter())
        self.root.bind('<KP_Subtract>', lambda e: self.decrement_counter())
        
        # Action buttons (1-4)
        self.root.bind('<Key-1>', lambda e: self.change_color())
        self.root.bind('<Key-2>', lambda e: self.show_message())
        self.root.bind('<Key-3>', lambda e: self.add_random_text())
        self.root.bind('<Key-4>', lambda e: self.clear_output())
        
        # Focus and utility keys
        self.root.bind('<F1>', lambda e: self.text_entry.focus_set())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        self.root.bind('<Control-r>', lambda e: self.reset_all())
        self.root.bind('<Escape>', lambda e: self.root.focus_set())
        self.root.bind('<Return>', lambda e: self.process_text_input())
        self.root.bind('<space>', lambda e: self.random_action())
        self.root.bind('<h>', lambda e: self.show_help())
        self.root.bind('<H>', lambda e: self.show_help())
        
        # Text entry specific bindings
        self.text_entry.bind('<Return>', lambda e: self.process_text_input())
    
    # Action methods
    def increment_counter(self):
        self.counter.set(self.counter.get() + 1)
        self.log_message(f"Counter incremented to {self.counter.get()}")
        self.update_status("Counter incremented")
    
    def decrement_counter(self):
        self.counter.set(self.counter.get() - 1)
        self.log_message(f"Counter decremented to {self.counter.get()}")
        self.update_status("Counter decremented")
    
    def reset_counter(self):
        self.counter.set(0)
        self.log_message("Counter reset to 0")
        self.update_status("Counter reset")
    
    def change_color(self):
        colors = ['#ffcccc', '#ccffcc', '#ccccff', '#ffffcc', '#ffccff', '#ccffff']
        color = random.choice(colors)
        self.root.configure(bg=color)
        self.log_message(f"Background color changed to {color}")
        self.update_status("Color changed")
    
    def show_message(self):
        messagebox.showinfo("Keyboard Action", "You pressed key '2' or clicked the message button!")
        self.log_message("Message dialog shown")
        self.update_status("Message shown")
    
    def add_random_text(self):
        words = ["Hello", "World", "Python", "Tkinter", "Keyboard", "Amazing", "Code", "UI"]
        random_text = " ".join(random.choices(words, k=3))
        current_text = self.text_content.get()
        if current_text == "Type something...":
            self.text_content.set(random_text)
        else:
            self.text_content.set(current_text + " " + random_text)
        self.log_message(f"Added random text: {random_text}")
        self.update_status("Random text added")
    
    def clear_text(self):
        self.text_content.set("")
        self.log_message("Text input cleared")
        self.update_status("Text cleared")
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.log_message("Output log cleared")
        self.update_status("Output cleared")
    
    def process_text_input(self):
        text = self.text_content.get().strip()
        if text and text != "Type something...":
            self.log_message(f"Processed input: '{text}'")
            self.update_status(f"Processed: {text[:20]}...")
        else:
            self.update_status("No text to process")
    
    def random_action(self):
        actions = [self.increment_counter, self.change_color, self.add_random_text]
        action = random.choice(actions)
        action()
        self.log_message("Random action executed")
    
    def reset_all(self):
        self.counter.set(0)
        self.text_content.set("Type something...")
        self.root.configure(bg='#f0f0f0')
        self.output_text.delete(1.0, tk.END)
        self.log_message("All components reset")
        self.update_status("Everything reset")
    
    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Keyboard Shortcuts Help")
        help_window.geometry("500x400")
        help_window.configure(bg='#f0f0f0')
        
        help_content = """
KEYBOARD SHORTCUTS REFERENCE

COUNTER CONTROLS:
  + or Numpad +     : Increment counter
  - or Numpad -     : Decrement counter

ACTION BUTTONS:
  1                 : Change background color randomly
  2                 : Show message dialog
  3                 : Add random text to input field
  4                 : Clear output log

NAVIGATION & FOCUS:
  F1                : Focus on text input field
  ESC               : Return focus to main window
  Enter             : Process text input

UTILITY FUNCTIONS:
  Spacebar          : Execute random action
  H                 : Show this help dialog
  Ctrl + R          : Reset all components
  Ctrl + Q          : Quit application

TEXT INPUT:
  - Click in the text field or press F1 to focus
  - Type normally and press Enter to process
  - Use "Clear" button or key '4' to clear output

TIPS:
  - Most actions are logged in the output area
  - Status bar shows the last performed action
  - You can use both keyboard and mouse interactions
        """
        
        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, 
                                               font=('Courier', 10), 
                                               bg='white', fg='black')
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(1.0, help_content)
        text_widget.configure(state='disabled')  # Make read-only
        
        ttk.Button(help_window, text="Close", 
                  command=help_window.destroy).pack(pady=5)
    
    def quit_app(self):
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.root.quit()
    
    # Utility methods
    def log_message(self, message):
        """Add message to output log"""
        self.output_text.insert(tk.END, f"[{self.get_timestamp()}] {message}\n")
        self.output_text.see(tk.END)  # Auto-scroll to bottom
    
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(f"{message} - Press H for help")
    
    def get_timestamp(self):
        """Get current time for logging"""
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")

def main():
    root = tk.Tk()
    app = KeyboardUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()