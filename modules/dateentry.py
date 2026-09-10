from modules.core import *
from modules.datepicker import DatePicker

class DateEntry(tk.Frame):
    """Widget combiné : champ de texte + bouton calendrier"""
    
    def __init__(self, parent, date_var, width=12, label_text="", **kw):
        super().__init__(parent, bg=parent["bg"] if hasattr(parent, "bg") else CLR_BG)
        
        self.date_var = date_var
        
        # Label si spécifié
        if label_text:
            lbl(self, label_text, 9, False, CLR_MUTED).pack(side="left", padx=(0,5))
        
        # Champ de texte
        self.entry = tk.Entry(self, bg=CLR_INPUT, fg=CLR_TEXT, 
                              insertbackground=CLR_TEXT,
                              relief="flat", width=width,
                              highlightthickness=1, 
                              highlightbackground=CLR_BORDER,
                              highlightcolor=CLR_ACCENT,
                              textvariable=date_var, readonlybackground=CLR_INPUT, state="readonly", **kw)
        self.entry.pack(side="left", padx=(0,5))
        self.entry.bind("<FocusOut>", self.on_focus_out)
        
        # Bouton calendrier
        btn_cal = tk.Button(self, text="📅", command=self.show_calendar,
                           bg=CLR_ACCENT, fg="white", relief="flat",
                           font=("Segoe UI", 9), padx=4, pady=2,
                           cursor="hand2")
        btn_cal.pack(side="left")
        
        # Bouton Effacer
        btn_clear = tk.Button(self, text="✕", command=self.clear_date,
                             bg=CLR_RED, fg="white", relief="flat",
                             font=("Segoe UI", 9), padx=4, pady=2,
                             cursor="hand2")
        btn_clear.pack(side="left", padx=(2,0))
    
    def show_calendar(self):
        DatePicker(self, self.date_var)
    
    def clear_date(self):
        self.date_var.set("")
    
    def on_focus_out(self, event):
        """Valider la date saisie manuellement"""
        date_str = self.date_var.get().strip()
        if date_str:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # Si la date est invalide, effacer
                self.date_var.set("")     
