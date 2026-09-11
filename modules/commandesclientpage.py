import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from database import get_conn, recalculer_cout_stock_apres_sortie

class CommandesClientsPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="white")
        self.pack(fill="both", expand=True)
        self.create_widgets()
        self.load_commandes()

    def create_widgets(self):
        tk.Label(self, text="Commandes du Portail Client", font=("Segoe UI", 16, "bold"), bg="white").pack(pady=10)
        
        columns = ("id", "numero", "date", "client", "total", "statut")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=100)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(btn_frame, text="Voir Détail", command=self.voir_detail, bg="#17a2b8", fg="white", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Valider Totalement", command=lambda: self.valider_commande(complete=True), bg="#28a745", fg="white", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Valider Ajusté (Stock Réel)", command=lambda: self.valider_commande(complete=False), bg="#ffc107", fg="black", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Actualiser", command=self.load_commandes).pack(side="left", padx=5)

    def load_commandes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = get_conn()
        rows = conn.execute("SELECT c.*, cl.nom as nom_client FROM commandes_clients c JOIN clients cl ON c.client_id = cl.id ORDER BY c.id DESC").fetchall()
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["numero"], r["date_commande"], r["nom_client"], f"{r['total_estime']:.2f}", r["statut"]))
        conn.close()

    def voir_detail(self):
        selected = self.tree.selection()
        if not selected: return
        cmd_id = self.tree.item(selected[0])["values"][0]
        
        detail_win = tk.Toplevel(self)
        detail_win.title(f"Détail Commande {cmd_id}")
        
        tree = ttk.Treeview(detail_win, columns=("prod", "qte", "prix"), show="headings")
        tree.heading("prod", text="Produit"); tree.heading("qte", text="Qte"); tree.heading("prix", text="Prix")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        conn = get_conn()
        lignes = conn.execute("SELECT p.designation, l.quantite, l.prix_unitaire_estime FROM lignes_commande_client l JOIN produits p ON l.produit_id=p.id WHERE l.commande_id=?", (cmd_id,)).fetchall()
        for l in lignes:
            tree.insert("", "end", values=(l["designation"], l["quantite"], l["prix_unitaire_estime"]))
        conn.close()

    def valider_commande(self, complete=True):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attention", "Sélectionnez une commande")
            return
        
        cmd_id = self.tree.item(selected[0])["values"][0]
        conn = get_conn()
        try:
            cmd = conn.execute("SELECT * FROM commandes_clients WHERE id=?", (cmd_id,)).fetchone()
            lignes = conn.execute("SELECT * FROM lignes_commande_client WHERE commande_id=?", (cmd_id,)).fetchall()
            
            today = date.today().strftime("%Y%m%d")
            num_bon = f"BV-{today}-{cmd_id:04d}"
            
            total_reel = 0
            valides = []
            
            for l in lignes:
                prod = conn.execute("SELECT stock_actuel FROM produits WHERE id=?", (l["produit_id"],)).fetchone()
                stock_dispo = prod["stock_actuel"]
                
                qte_finale = l["quantite"]
                if not complete and qte_finale > stock_dispo:
                    qte_finale = stock_dispo
                
                if qte_finale > 0:
                    valides.append({"id": l["produit_id"], "qte": qte_finale, "prix": l["prix_unitaire_estime"], "total": qte_finale * l["prix_unitaire_estime"]})
                    total_reel += valides[-1]["total"]
            
            cursor = conn.execute("INSERT INTO bons_vente (numero, date_bon, client_id, total, statut) VALUES (?, ?, ?, ?, 'Validé')",
                                  (num_bon, date.today().isoformat(), cmd["client_id"], total_reel))
            bon_vente_id = cursor.lastrowid
            
            for v in valides:
                conn.execute("INSERT INTO lignes_vente (bon_id, produit_id, quantite, prix_unitaire, total) VALUES (?, ?, ?, ?, ?)",
                             (bon_vente_id, v["id"], v["qte"], v["prix"], v["total"]))
                recalculer_cout_stock_apres_sortie(conn, v["id"], v["qte"])
                
            conn.execute("UPDATE commandes_clients SET statut='Validée', bon_vente_id=? WHERE id=?", (bon_vente_id, cmd_id))
            conn.commit()
            messagebox.showinfo("Succès", f"Commande validée (Total: {total_reel:.2f})")
            self.load_commandes()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
