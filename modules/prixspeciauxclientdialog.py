from modules.core import *

class PrixSpeciauxClientDialog(tk.Toplevel):
    """Dialogue pour gérer les prix spéciaux d'un client spécifique"""
    
    def __init__(self, parent, client_id, client_nom):
        super().__init__(parent)
        self.client_id = client_id
        self.client_nom = client_nom
        self.title(f"Prix Spéciaux - {client_nom}")
        self.configure(bg=CLR_BG)
        self.geometry("900x600")
        self._build()
        self.refresh()
        center_window(self, 900, 600)
    
    def _build(self):
        main_frame = tk.Frame(self, bg=CLR_BG, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        lbl(main_frame, f"💰 PRIX SPÉCIAUX POUR {self.client_nom}", 14, True, CLR_ACCENT).pack(pady=(0,15))
        
        # Sélection du produit
        select_frame = tk.Frame(main_frame, bg=CLR_CARD, padx=15, pady=10)
        select_frame.pack(fill="x", pady=10)
        
        lbl(select_frame, "Produit:", 9, True, CLR_MUTED).pack(side="left", padx=5)
        
        conn = get_conn()
        produits = conn.execute("SELECT id, code, designation, prix_vente FROM produits WHERE actif = 1 ORDER BY designation").fetchall()
        conn.close()
        
        self.produits_map = {f"{p['code']} - {p['designation']}": dict(p) for p in produits}
        self.produit_var = tk.StringVar()
        produit_combo = combo(select_frame, list(self.produits_map.keys()), width=40, textvariable=self.produit_var)
        produit_combo.pack(side="left", padx=10)
        
        lbl(select_frame, "Prix spécial:", 9, True, CLR_MUTED).pack(side="left", padx=(20,5))
        self.prix_special_var = tk.StringVar()
        entry(select_frame, width=12, textvariable=self.prix_special_var, font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        lbl(select_frame, "DA", 9, False, CLR_MUTED).pack(side="left")
        
        tk.Button(select_frame, text="➕ AJOUTER/MODIFIER", command=self.ajouter_prix_special,
                 bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=20)
        
        # Tableau des prix spéciaux existants
        table_frame = tk.LabelFrame(main_frame, text="Prix spéciaux existants", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=10)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        cols = ["Code", "Produit", "Prix standard", "Prix spécial", "Remise", "Actions"]
        widths = [100, 250, 100, 100, 80, 100]
        tf, self.tree = make_tree(table_frame, cols, widths)
        tf.pack(fill="both", expand=True)
        
        # Boutons
        btn_frame = tk.Frame(main_frame, bg=CLR_BG)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="🗑 Supprimer", command=self.supprimer_prix_special,
                 bg=CLR_RED, fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                 padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                 bg=CLR_BORDER, fg=CLR_TEXT, relief="flat", font=("Segoe UI", 9),
                 padx=12, pady=6, cursor="hand2").pack(side="right", padx=5)
    
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        
        conn = get_conn()
        prix_speciaux = conn.execute("""
            SELECT psc.*, pr.code, pr.designation,
                   COALESCE(NULLIF(pr.prix_vente, 0), pr.prix_detail, 0) as prix_standard
            FROM prix_speciaux_clients psc
            JOIN produits pr ON psc.produit_id = pr.id
            WHERE psc.client_id = ? AND psc.actif = 1""", (self.client_id,)).fetchall()
        conn.close()
        
        for ps in prix_speciaux:
            prix_std = ps["prix_standard"] or 0
            remise = ((prix_std - ps["prix_special"]) / prix_std * 100) if prix_std > 0 else 0
            self.tree.insert("", "end", iid=ps["id"], values=(
                ps["code"], ps["designation"],
                f"{prix_std:.2f} DA",
                f"{ps['prix_special']:.2f} DA",
                f"{remise:.1f}%",
                "✏ Modifier"
            ))
    
    def ajouter_prix_special(self):
        produit_key = self.produit_var.get()
        if not produit_key or produit_key not in self.produits_map:
            messagebox.showerror("Erreur", "Sélectionnez un produit")
            return
        
        try:
            prix_special = parse_decimal(self.prix_special_var.get())
            if prix_special <= 0:
                messagebox.showerror("Erreur", "Prix spécial invalide")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Prix spécial invalide")
            return
        
        produit = self.produits_map[produit_key]
        
        conn = get_conn()
        try:
            # Vérifier si un prix spécial existe déjà
            existing = conn.execute("""
                SELECT id FROM prix_speciaux_clients 
                WHERE client_id = ? AND produit_id = ?
            """, (self.client_id, produit["id"])).fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE prix_speciaux_clients 
                    SET prix_special = ?,
                        date_modification = datetime('now')
                    WHERE id = ?
                """, (prix_special, existing["id"]))
                messagebox.showinfo("Succès", "Prix spécial mis à jour")
            else:
                conn.execute("""
                    INSERT INTO prix_speciaux_clients(client_id, produit_id, prix_special)
                    VALUES(?, ?, ?)
                """, (self.client_id, produit["id"], prix_special))
                messagebox.showinfo("Succès", "Prix spécial ajouté")
            
            conn.commit()
            self.refresh()
            self.prix_special_var.set("")
            self.produit_var.set("")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            conn.rollback()
        finally:
            conn.close()
    
    def supprimer_prix_special(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("", "Sélectionnez un prix spécial à supprimer")
            return
        
        if messagebox.askyesno("Confirmation", "Supprimer ce prix spécial ?"):
            conn = get_conn()
            try:
                conn.execute("UPDATE prix_speciaux_clients SET actif = 0 WHERE id = ?", (sel[0],))
                conn.commit()
                messagebox.showinfo("Succès", "Prix spécial supprimé")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                conn.rollback()
            finally:
                conn.close()


