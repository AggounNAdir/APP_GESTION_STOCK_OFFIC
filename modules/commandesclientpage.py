import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from modules.core import *

class CommandesClientsPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self.pack(fill="both", expand=True)
        self.create_widgets()
        self.load_commandes()

    def create_widgets(self):
        lbl(self, "🛒 Commandes du Portail Client", 16, True).pack(pady=10)
        
        columns = ("id", "numero", "date", "client", "total", "statut")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=100)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = tk.Frame(self, bg=CLR_BG)
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Button(btn_frame, text="Voir Détail", command=self.voir_detail, bg=CLR_ACCENT, fg="white", relief="flat", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Valider Totalement", command=lambda: self.valider_commande(complete=True), bg=CLR_GREEN, fg="white", relief="flat", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Valider Ajusté (Stock Réel)", command=lambda: self.valider_commande(complete=False), bg=CLR_ORANGE, fg="white", relief="flat", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Actualiser", command=self.load_commandes, bg=CLR_INPUT, fg=CLR_TEXT, relief="flat", padx=10).pack(side="left", padx=5)

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
            if not cmd:
                messagebox.showerror("Erreur", "Commande introuvable")
                return
            
            lignes = conn.execute("SELECT * FROM lignes_commande_client WHERE commande_id=?", (cmd_id,)).fetchall()
            
            today = date.today().strftime("%Y%m%d")
            num_bon = f"BV-{today}-{cmd_id:04d}"
            
            total_reel = 0.0
            valides = []
            
            for l in lignes:
                # 1. Récupérer le stock actuel ET le facteur de conversion du produit
                prod = conn.execute(
                    "SELECT stock_actuel, COALESCE(facteur_conversion, 1) as facteur_conversion FROM produits WHERE id=?",
                    (l["produit_id"],)
                ).fetchone()
                
                stock_dispo = float(prod["stock_actuel"] or 0) if prod else 0.0
                facteur = float(prod["facteur_conversion"] or 1) if prod else 1.0
                if facteur <= 0:
                    facteur = 1.0
                
                # 2. La commande portail est exprimée en COLIS, le stock en PIÈCES
                qte_colis = float(l["quantite"] or 0)
                stock_dispo_colis = stock_dispo / facteur
                
                qte_finale_colis = qte_colis
                if not complete and qte_finale_colis > stock_dispo_colis:
                    qte_finale_colis = max(0.0, stock_dispo_colis)
                
                if qte_finale_colis > 0:
                    # 3. Quantité réelle en pièces de base à déstocker (ex: 1 colis x 24 = 24 pièces)
                    qte_pieces = qte_finale_colis * facteur
                    prix_unitaire = float(l["prix_unitaire_estime"] or 0.0)
                    
                    # 4. Total de la ligne en tenant compte du colisage : 24 x 40 = 960 DA
                    total_ligne = round(qte_pieces * prix_unitaire, 2)
                    
                    valides.append({
                        "id": l["produit_id"],
                        "qte_colis": qte_finale_colis,
                        "qte_pieces": qte_pieces,
                        "prix": prix_unitaire,
                        "total": total_ligne,
                        "facteur": facteur
                    })
                    total_reel += total_ligne
            
            if not valides:
                messagebox.showwarning("Attention", "Aucun article disponible pour validation.")
                return
            
            # 5. Création du Bon de Vente avec le total réel (ex: 960 DA)
            cursor = conn.execute(
                "INSERT INTO bons_vente (numero, date_bon, client_id, total, statut) VALUES (?, ?, ?, ?, 'Validé')",
                (num_bon, date.today().isoformat(), cmd["client_id"], total_reel)
            )
            bon_vente_id = cursor.lastrowid
            
            for v in valides:
                # Dans lignes_vente, la quantité enregistrée est en unités de base (pièces)
                conn.execute(
                    "INSERT INTO lignes_vente (bon_id, produit_id, quantite, prix_unitaire, total) VALUES (?, ?, ?, ?, ?)",
                    (bon_vente_id, v["id"], v["qte_pieces"], v["prix"], v["total"])
                )
                # Déstockage de la quantité réelle en pièces (ex: 24 pièces)
                recalculer_cout_stock_apres_sortie(
                    conn, v["id"], v["qte_pieces"],
                    type_mouvement="VENTE", document_type="bon_vente",
                    document_id=bon_vente_id, date_document=date.today().isoformat(),
                    motif=f"Validation de la commande portail n°{cmd_id}",
                )
            
            # 6. Mise à jour du solde du client avec le montant réel (+960 DA)
            conn.execute(
                "UPDATE clients SET solde = COALESCE(solde, 0) + ? WHERE id=?",
                (total_reel, cmd["client_id"])
            )
                
            conn.execute("UPDATE commandes_clients SET statut='Validée', bon_vente_id=? WHERE id=?", (bon_vente_id, cmd_id))
            conn.commit()
            messagebox.showinfo("Succès", f"Commande validée (Total: {total_reel:.2f} DA)")
            self.load_commandes()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", str(e))
        finally:
            conn.close()
