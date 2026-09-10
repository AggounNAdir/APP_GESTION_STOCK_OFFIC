from modules.core import *

class DatePicker(tk.Toplevel):
    """Fenêtre de sélection de date avec calendrier"""
    
    def __init__(self, parent, date_var, title="Sélectionner une date"):
        super().__init__(parent)
        self.parent = parent
        self.date_var = date_var
        self.title(title)
        self.configure(bg=CLR_BG)
        self.geometry("320x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Date actuelle
        current_date = self.date_var.get()
        if current_date and self._validate_date(current_date):
            self.selected_date = datetime.strptime(current_date, "%Y-%m-%d").date()
        else:
            self.selected_date = date.today()
        
        self.year = self.selected_date.year
        self.month = self.selected_date.month
        
        self._build()
        self._draw_calendar()
        center_window(self, 320, 350)
    
    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def _build(self):
        # Frame principal
        main_frame = tk.Frame(self, bg=CLR_BG, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # Navigation
        nav_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=5, pady=5)
        nav_frame.pack(fill="x", pady=(0, 10))
        
        # Bouton Mois précédent
        btn_prev = tk.Button(nav_frame, text="◄", command=self.prev_month,
                            bg=CLR_ACCENT, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=8, pady=4,
                            cursor="hand2")
        btn_prev.pack(side="left")
        
        # Affichage mois/année
        self.month_year_label = tk.Label(nav_frame, text="", 
                                         bg=CLR_CARD, fg=CLR_TEXT,
                                         font=("Segoe UI", 12, "bold"))
        self.month_year_label.pack(side="left", expand=True)
        
        # Bouton Mois suivant
        btn_next = tk.Button(nav_frame, text="►", command=self.next_month,
                            bg=CLR_ACCENT, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=8, pady=4,
                            cursor="hand2")
        btn_next.pack(side="right")
        
        # Cadre du calendrier
        self.calendar_frame = tk.Frame(main_frame, bg=CLR_CARD)
        self.calendar_frame.pack(fill="both", expand=True)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="Aujourd'hui", command=self.select_today,
                 bg=CLR_GREEN, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Effacer", command=self.clear_date,
                 bg=CLR_ORANGE, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Valider", command=self.select_date,
                 bg=CLR_ACCENT, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="right", padx=5)
        
        tk.Button(btn_frame, text="Annuler", command=self.destroy,
                 bg=CLR_RED, fg="white", relief="flat",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                 cursor="hand2").pack(side="right", padx=5)
    
    def _draw_calendar(self):
        # Nettoyer le cadre
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        
        # Mettre à jour le label mois/année
        month_name = calendar.month_name[self.month]
        self.month_year_label.config(text=f"{month_name} {self.year}")
        
        # Jours de la semaine
        days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        for i, day in enumerate(days):
            lbl = tk.Label(self.calendar_frame, text=day, 
                          bg=CLR_CARD, fg=CLR_ACCENT,
                          font=("Segoe UI", 8, "bold"), width=4)
            lbl.grid(row=0, column=i, padx=2, pady=2)
        
        # Calendrier
        cal = calendar.monthcalendar(self.year, self.month)
        
        # Couleur pour les dates sélectionnées
        today = date.today()
        
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(self.calendar_frame, text="", 
                                  bg=CLR_CARD, width=4)
                else:
                    current_date = date(self.year, self.month, day)
                    
                    # Déterminer la couleur
                    bg_color = CLR_INPUT
                    fg_color = CLR_TEXT
                    
                    if current_date == self.selected_date:
                        bg_color = CLR_ACCENT
                        fg_color = "white"
                    elif current_date == today:
                        bg_color = CLR_ORANGE
                        fg_color = "white"
                    
                    lbl = tk.Label(self.calendar_frame, text=str(day),
                                  bg=bg_color, fg=fg_color,
                                  font=("Segoe UI", 10), width=4,
                                  relief="flat", cursor="hand2")
                    lbl.bind("<Button-1>", lambda e, d=current_date: self.on_day_click(d))
                
                lbl.grid(row=row_idx+1, column=col_idx, padx=2, pady=2)
    
    def on_day_click(self, date_obj):
        self.selected_date = date_obj
        self._draw_calendar()
    
    def prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._draw_calendar()
    
    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._draw_calendar()
    
    def select_today(self):
        self.selected_date = date.today()
        self.year = self.selected_date.year
        self.month = self.selected_date.month
        self._draw_calendar()
    
    def clear_date(self):
        self.date_var.set("")
        self.destroy()
    
    def select_date(self):
        self.date_var.set(self.selected_date.strftime("%Y-%m-%d"))
        self.destroy()


