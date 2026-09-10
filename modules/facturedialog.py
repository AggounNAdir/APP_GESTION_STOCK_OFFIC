from modules.core import *

class FactureDialog(tk.Toplevel):
    """Dialogue de création de facture"""
    
    def __init__(self, parent, pre_selected_bon=None):
        super().__init__(parent)
        self.pre_selected_bon = pre_selected_bon
        self.title("Nouvelle Facture")
        self.configure(bg=CLR_BG)
        self.geometry("750x600")
        self._build()
        center_window(self, 750, 600)
    
    def _build(self):
            main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            # Titre
            lbl(main_frame, "📄 CRÉATION DE FACTURE", 14, True, CLR_ACCENT).pack(pady=(0,15))
            
            # Sélection du bon de vente
            frame_bon = tk.LabelFrame(main_frame, text="1. Sélectionner le Bon de Vente", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
            frame_bon.pack(fill="x", pady=10)
            
            lbl(frame_bon, "Bon de vente:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            
            # Charger les bons de vente non facturés
            conn = get_conn()
            bons = conn.execute("""
                SELECT bv.id, bv.numero, c.nom as client_nom, bv.total, bv.date_bon
                FROM bons_vente bv
                JOIN clients c ON bv.client_id = c.id
                WHERE bv.id NOT IN (SELECT bon_vente_id FROM factures WHERE bon_vente_id IS NOT NULL)
                AND bv.statut = 'Validé'
                ORDER BY bv.date_bon DESC
            """).fetchall()
            conn.close()
            
            self.bons_map = {}
            bon_liste = []
            for b in bons:
                display = f"{b['numero']} - {b['client_nom']} - {b['total']:,.2f} DA"
                self.bons_map[display] = dict(b)
                bon_liste.append(display)
            
            self.bon_var = tk.StringVar()
            self.bon_combo = combo(frame_bon, bon_liste, width=40, textvariable=self.bon_var)
            self.bon_combo.pack(side="left", padx=10, fill="x", expand=True)
            self.bon_combo.bind("<<ComboboxSelected>>", self.on_bon_selected)
            
            if bon_liste:
                self.bon_var.set(bon_liste[0])
            
            # Informations de la facture
            frame_info = tk.LabelFrame(main_frame, text="2. Informations de la facture", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
            frame_info.pack(fill="x", pady=10)
            
            # Numéro de facture (auto)
            row1 = tk.Frame(frame_info, bg=CLR_CARD)
            row1.pack(fill="x", pady=5)
            lbl(row1, "Numéro facture:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.num_var = tk.StringVar(value=next_numero("FC", "factures"))
            entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(side="left", padx=10)
            
            # Date facture
            lbl(row1, "Date facture:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
            entry(row1, width=15, textvariable=self.date_var).pack(side="left", padx=10)
            
            # Date échéance
            row2 = tk.Frame(frame_info, bg=CLR_CARD)
            row2.pack(fill="x", pady=5)
            lbl(row2, "Date échéance:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.echeance_var = tk.StringVar(value="")
            entry(row2, width=15, textvariable=self.echeance_var).pack(side="left", padx=10)
            lbl(row2, "(Optionnel - format YYYY-MM-DD)", 8, False, CLR_MUTED).pack(side="left", padx=10)
            
            # TVA - mode automatique basé sur les produits
            row3 = tk.Frame(frame_info, bg=CLR_CARD)
            row3.pack(fill="x", pady=5)
            lbl(row3, "TVA:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            lbl(row3, "Calculée automatiquement par produit", 9, False, True, CLR_GREEN).pack(side="left", padx=10)            
            # Observations
            row4 = tk.Frame(frame_info, bg=CLR_CARD)
            row4.pack(fill="x", pady=5)
            lbl(row4, "Observations:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.obs_var = tk.StringVar(value="")
            entry(row4, width=50, textvariable=self.obs_var).pack(side="left", padx=10, fill="x", expand=True)
            
            # Récapitulatif
            frame_recap = tk.LabelFrame(main_frame, text="3. Récapitulatif", 
                                        bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                        padx=15, pady=10)
            frame_recap.pack(fill="x", pady=10)
            
            recap_inner = tk.Frame(frame_recap, bg=CLR_CARD)
            recap_inner.pack(fill="x")
            
            # CORRECTION : ordre correct des arguments pour lbl()
            lbl1 = tk.Label(recap_inner, text="Total HT:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl1.grid(row=0, column=0, sticky="w", padx=5, pady=2)
            self.total_ht_var = tk.StringVar(value="0.00 DA")
            lbl1_val = tk.Label(recap_inner, textvariable=self.total_ht_var, bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 11, "bold"))
            lbl1_val.grid(row=0, column=1, sticky="w", padx=10, pady=2)
            
            lbl2 = tk.Label(recap_inner, text="TVA:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl2.grid(row=1, column=0, sticky="w", padx=5, pady=2)
            self.tva_montant_var = tk.StringVar(value="0.00 DA")
            lbl2_val = tk.Label(recap_inner, textvariable=self.tva_montant_var, bg=CLR_CARD, fg=CLR_ORANGE, font=("Segoe UI", 11, "bold"))
            lbl2_val.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            
            lbl3 = tk.Label(recap_inner, text="Total TTC:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl3.grid(row=2, column=0, sticky="w", padx=5, pady=2)
            self.total_ttc_var = tk.StringVar(value="0.00 DA")
            lbl3_val = tk.Label(recap_inner, textvariable=self.total_ttc_var, bg=CLR_CARD, fg=CLR_GREEN, font=("Segoe UI", 14, "bold"))
            lbl3_val.grid(row=2, column=1, sticky="w", padx=10, pady=2)
            
            # Boutons
            btn_frame = tk.Frame(main_frame, bg=CLR_BG)
            btn_frame.pack(fill="x", pady=15)
            
            tk.Button(btn_frame, text="✅ CRÉER LA FACTURE", command=self.save,
                    bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                    padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
            
            tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                    bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                    padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
            
            # Initialiser l'affichage
            self.on_bon_selected()
    
    def on_bon_selected(self, event=None):
        """Mettre à jour le récapitulatif quand un bon est sélectionné"""
        key = self.bon_var.get()
        if key and key in self.bons_map:
            bon = self.bons_map[key]
            
            conn = get_conn()
            lignes = conn.execute("""
                SELECT l.total, p.tva
                FROM lignes_vente l
                JOIN produits p ON l.produit_id = p.id
                WHERE l.bon_id = ?
            """, (bon["id"],)).fetchall()
            conn.close()
            
            # Regrouper par taux de TVA
            self.tva_details = {}  # {taux: total_ht}
            total_ht = 0
            total_tva = 0
            for l in lignes:
                taux = l["tva"] if l["tva"] is not None else 19
                ht = l["total"]
                tva_montant = ht * taux / 100
                self.tva_details[taux] = self.tva_details.get(taux, 0) + ht
                total_ht += ht
                total_tva += tva_montant
            
            total_ttc = total_ht + total_tva
            
            self.total_ht_var.set(f"{total_ht:,.2f} DA")
            self.tva_montant_var.set(f"{total_tva:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
    
    def save(self):
        key = self.bon_var.get()
        if not key or key not in self.bons_map:
            messagebox.showerror("Erreur", "Sélectionnez un bon de vente")
            return
        
        bon = self.bons_map[key]
        
        conn = get_conn()
        try:
            bon_data = conn.execute("SELECT client_id FROM bons_vente WHERE id = ?", (bon["id"],)).fetchone()
            if not bon_data:
                messagebox.showerror("Erreur", "Bon de vente non trouvé")
                return
            client_id = bon_data["client_id"]
            
            # Recalculer HT/TVA/TTC par produit
            lignes = conn.execute("""
                SELECT l.total, p.tva
                FROM lignes_vente l
                JOIN produits p ON l.produit_id = p.id
                WHERE l.bon_id = ?
            """, (bon["id"],)).fetchall()
            
            tva_details = {}
            total_ht = 0
            total_tva = 0
            for l in lignes:
                taux = l["tva"] if l["tva"] is not None else 19
                ht = l["total"]
                tva_montant = ht * taux / 100
                if taux not in tva_details:
                    tva_details[taux] = {"ht": 0, "tva": 0}
                tva_details[taux]["ht"] += ht
                tva_details[taux]["tva"] += tva_montant
                total_ht += ht
                total_tva += tva_montant
            
            total_ttc = total_ht + total_tva
            
            # TVA "moyenne" pour compat avec l'ancien champ tva (en %)
            tva_moyenne = (total_tva / total_ht * 100) if total_ht > 0 else 0
            
            conn.execute("""
                INSERT INTO factures(numero, date_facture, bon_vente_id, client_id, 
                                    total_ht, tva, total_ttc, statut, date_echeance, observations)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.num_var.get(), self.date_var.get(), bon["id"], client_id,
                total_ht, tva_moyenne, total_ttc, "Émise", 
                self.echeance_var.get() or None, self.obs_var.get() or None
            ))
            
            facture_id = conn.execute("SELECT id FROM factures WHERE numero=?", (self.num_var.get(),)).fetchone()["id"]
            
            for taux, vals in tva_details.items():
                conn.execute("""
                    INSERT INTO facture_tva_details(facture_id, taux_tva, total_ht, total_tva)
                    VALUES(?, ?, ?, ?)
                """, (facture_id, taux, vals["ht"], vals["tva"]))
            
            conn.commit()
            messagebox.showinfo("Succès", f"Facture {self.num_var.get()} créée avec succès !")
            self.destroy()
        except sqlite3.IntegrityError:
            nouveau_num = next_numero("FC", "factures")
            self.num_var.set(nouveau_num)
            messagebox.showwarning("Numéro dupliqué", 
                                 f"Le numéro existait déjà.\nNouveau numéro: {nouveau_num}\nVeuillez réessayer.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {str(e)}")
            conn.rollback()
        finally:
            conn.close()


