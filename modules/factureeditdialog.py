from modules.core import *
from modules.facturedetaildialog import FactureDetailDialog

class FactureEditDialog(tk.Toplevel):
    """Dialogue de modification de facture"""
    
    def __init__(self, parent, facture_id):
        super().__init__(parent)
        self.facture_id = facture_id
        self.title("Modifier Facture")
        self.configure(bg=CLR_BG)
        self.geometry("750x550")
        self._load_data()
        self._build()
        center_window(self, 750, 550)
    
    def _load_data(self):
        conn = get_conn()
        self.facture = conn.execute("""
            SELECT f.*, c.nom as client_nom, bv.numero as bon_numero
            FROM factures f
            JOIN clients c ON f.client_id = c.id
            JOIN bons_vente bv ON f.bon_vente_id = bv.id
            WHERE f.id = ?
        """, (self.facture_id,)).fetchone()
        conn.close()
    
    def _build(self):
            main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            lbl(main_frame, "✏ MODIFICATION FACTURE", 14, True, CLR_ACCENT).pack(pady=(0,15))
            
            # Informations
            frame_info = tk.LabelFrame(main_frame, text="Informations", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
            frame_info.pack(fill="x", pady=10)
            
            # Numéro (non modifiable)
            row1 = tk.Frame(frame_info, bg=CLR_CARD)
            row1.pack(fill="x", pady=5)
            lbl(row1, "Numéro facture:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.num_var = tk.StringVar(value=self.facture["numero"])
            entry(row1, width=20, textvariable=self.num_var, state="readonly").pack(side="left", padx=10)
            
            lbl(row1, "Bon de vente:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            lbl1 = tk.Label(row1, text=self.facture["bon_numero"], bg=CLR_CARD, fg=CLR_GREEN, font=("Segoe UI", 9, "bold"))
            lbl1.pack(side="left", padx=10)
            
            # Date facture
            row2 = tk.Frame(frame_info, bg=CLR_CARD)
            row2.pack(fill="x", pady=5)
            lbl(row2, "Date facture:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.date_var = tk.StringVar(value=self.facture["date_facture"])
            entry(row2, width=15, textvariable=self.date_var).pack(side="left", padx=10)
            
            lbl(row2, "Client:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            lbl2 = tk.Label(row2, text=self.facture["client_nom"], bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 9, "bold"))
            lbl2.pack(side="left", padx=10)
            
            # Date échéance
            row3 = tk.Frame(frame_info, bg=CLR_CARD)
            row3.pack(fill="x", pady=5)
            lbl(row3, "Date échéance:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.echeance_var = tk.StringVar(value=self.facture["date_echeance"] or "")
            entry(row3, width=15, textvariable=self.echeance_var).pack(side="left", padx=10)
            
            # Statut
            lbl(row3, "Statut:", 9, False, CLR_MUTED).pack(side="left", padx=(20,5))
            self.statut_var = tk.StringVar(value=self.facture["statut"])
            statut_combo = combo(row3, ["Émise", "Payée", "Annulée"], width=12, textvariable=self.statut_var)
            statut_combo.pack(side="left", padx=10)
            
            # TVA
            row4 = tk.Frame(frame_info, bg=CLR_CARD)
            row4.pack(fill="x", pady=5)
            lbl(row4, "TVA (%):", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.tva_var = tk.StringVar(value=str(self.facture["tva"]))
            tva_spin = tk.Spinbox(row4, from_=0, to=50, increment=1, width=10,
                                textvariable=self.tva_var, bg=CLR_INPUT, fg=CLR_TEXT,
                                relief="flat", font=("Segoe UI", 10))
            tva_spin.pack(side="left", padx=10)
            
            # Observations
            row5 = tk.Frame(frame_info, bg=CLR_CARD)
            row5.pack(fill="x", pady=5)
            lbl(row5, "Observations:", 9, False, CLR_MUTED).pack(side="left", padx=5)
            self.obs_var = tk.StringVar(value=self.facture["observations"] or "")
            entry(row5, width=50, textvariable=self.obs_var).pack(side="left", padx=10, fill="x", expand=True)
            
            # Récapitulatif
            frame_recap = tk.LabelFrame(main_frame, text="Récapitulatif", 
                                        bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                        padx=15, pady=10)
            frame_recap.pack(fill="x", pady=10)
            
            recap_inner = tk.Frame(frame_recap, bg=CLR_CARD)
            recap_inner.pack(fill="x")
            
            # CORRECTION : utilisation directe de tk.Label
            lbl_ht = tk.Label(recap_inner, text="Total HT:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl_ht.grid(row=0, column=0, sticky="w", padx=5, pady=2)
            self.total_ht_var = tk.StringVar(value=f"{self.facture['total_ht']:,.2f} DA")
            val_ht = tk.Label(recap_inner, textvariable=self.total_ht_var, bg=CLR_CARD, fg=CLR_TEXT, font=("Segoe UI", 11, "bold"))
            val_ht.grid(row=0, column=1, sticky="w", padx=10, pady=2)
            
            lbl_tva = tk.Label(recap_inner, text="TVA montant:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl_tva.grid(row=1, column=0, sticky="w", padx=5, pady=2)
            tva_montant = self.facture['total_ht'] * self.facture['tva'] / 100
            self.tva_montant_var = tk.StringVar(value=f"{tva_montant:,.2f} DA")
            val_tva = tk.Label(recap_inner, textvariable=self.tva_montant_var, bg=CLR_CARD, fg=CLR_ORANGE, font=("Segoe UI", 11, "bold"))
            val_tva.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            
            lbl_ttc = tk.Label(recap_inner, text="Total TTC:", bg=CLR_CARD, fg=CLR_MUTED, font=("Segoe UI", 10, "bold"))
            lbl_ttc.grid(row=2, column=0, sticky="w", padx=5, pady=2)
            self.total_ttc_var = tk.StringVar(value=f"{self.facture['total_ttc']:,.2f} DA")
            val_ttc = tk.Label(recap_inner, textvariable=self.total_ttc_var, bg=CLR_CARD, fg=CLR_GREEN, font=("Segoe UI", 14, "bold"))
            val_ttc.grid(row=2, column=1, sticky="w", padx=10, pady=2)
            
            # Mettre à jour quand TVA change
            self.tva_var.trace_add("write", self.update_totals)
            
            # Boutons
            btn_frame = tk.Frame(main_frame, bg=CLR_BG)
            btn_frame.pack(fill="x", pady=15)
            
            tk.Button(btn_frame, text="💾 ENREGISTRER", command=self.save,
                    bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 11, "bold"),
                    padx=25, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
            
            tk.Button(btn_frame, text="🖨 APERÇU/IMPRESSION", command=self.print_facture,
                    bg=CLR_ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                    padx=20, pady=10, cursor="hand2").pack(side="left", padx=10, expand=True, fill="x")
            
            tk.Button(btn_frame, text="❌ ANNULER", command=self.destroy,
                    bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                    padx=20, pady=10, cursor="hand2").pack(side="right", padx=10)
    
    def update_totals(self, *args):
        try:
            total_ht = self.facture["total_ht"]
            tva_pct = float(self.tva_var.get() or 0)
            tva_montant = total_ht * tva_pct / 100
            total_ttc = total_ht + tva_montant
            
            self.tva_montant_var.set(f"{tva_montant:,.2f} DA")
            self.total_ttc_var.set(f"{total_ttc:,.2f} DA")
        except (ValueError, TypeError):
            pass
    
    def save(self):
        conn = get_conn()
        try:
            # ✅ Recalculer le TTC depuis les détails TVA réels (pas depuis le champ tva%)
            tva_details = conn.execute(
                "SELECT * FROM facture_tva_details WHERE facture_id=?",
                (self.facture_id,)
            ).fetchall()

            if tva_details:
                total_tva = sum(d["total_tva"] for d in tva_details)
                total_ht  = sum(d["total_ht"]  for d in tva_details)
                total_ttc = total_ht + total_tva
                # tva_moyenne pour compat avec l'ancien champ
                tva_pct = (total_tva / total_ht * 100) if total_ht > 0 else 0
            else:
                # Fallback si pas de détails (ancienne facture)
                try:
                    tva_pct = float(self.tva_var.get() or 0)
                except ValueError:
                    messagebox.showerror("Erreur", "TVA invalide")
                    return
                total_ht  = self.facture["total_ht"]
                total_tva = total_ht * tva_pct / 100
                total_ttc = total_ht + total_tva

            conn.execute("""
                UPDATE factures
                SET date_facture=?, tva=?, total_ttc=?, statut=?,
                    date_echeance=?, observations=?
                WHERE id=?
            """, (
                self.date_var.get(), tva_pct, total_ttc,
                self.statut_var.get(),
                self.echeance_var.get() or None,
                self.obs_var.get() or None,
                self.facture_id
            ))
            conn.commit()
            messagebox.showinfo("Succès", "Facture modifiée avec succès")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()
    
    def print_facture(self):
        """Afficher l'aperçu de la facture"""
        d = FactureDetailDialog(self, self.facture_id, parent=self)
        # Ne pas attendre la fermeture


