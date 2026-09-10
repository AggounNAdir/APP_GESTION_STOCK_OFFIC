from modules.produitdialog import ProduitDialog
from modules.core import *

class ProduitPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self, bg=CLR_BG)
        hdr.pack(fill="x", padx=20, pady=(20,10))
        lbl(hdr, "📦  Gestion des Produits", 16, True).pack(side="left")
        
        tk.Button(hdr, text="+ Nouveau Produit", command=self.new_item,
                bg=CLR_GREEN, fg="white", relief="flat", font=("Segoe UI",9,"bold"),
                padx=14, pady=7, cursor="hand2").pack(side="right")

        sf = tk.Frame(self, bg=CLR_BG)
        sf.pack(fill="x", padx=20, pady=5)
        lbl(sf, "Recherche:", color=CLR_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        e = entry(sf, width=30, textvariable=self.search_var)
        e.pack(side="left", padx=8)

        cols = ["Code","Code Barre","Désignation","Marque","Unité","Facteur","Prix Achat","Prix Moyen","Variation","Prix Vente","TVA","Stock","Stock Min (cartons)"]
        widths = [80,140,180,100,60,60,90,90,80,90,60,80,120]
        tf, self.tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree.tag_configure("stock_ok", foreground=CLR_GREEN)
        self.tree.tag_configure("stock_low", foreground=CLR_RED)
        self.tree.tag_configure("var_pos", foreground=CLR_GREEN)
        self.tree.tag_configure("var_neg", foreground=CLR_RED)
        self.tree.tag_configure("var_zero", foreground=CLR_MUTED)

        bf = tk.Frame(self, bg=CLR_BG)
        bf.pack(fill="x", padx=20, pady=(0,15))
        tk.Button(bf, text="✏ Modifier", command=self.edit_item,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(bf, text="🗑 Supprimer", command=self.del_item,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        tk.Button(bf, text="🔄 Rafraîchir", command=self.refresh,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="right", padx=4)

        self.invent_filter_var = tk.StringVar(value="Tous")
        self.invent_sort_var = tk.StringVar(value="Désignation")

        tk.Label(bf, text="Filtrer unité:", bg=CLR_BG, fg=CLR_MUTED).pack(side="right", padx=(8,2))
        self.invent_filter_cb = combo(bf, ["Tous", "kg", "carton", "Pcs"], width=8, textvariable=self.invent_filter_var)
        self.invent_filter_cb.pack(side="right", padx=4)

        tk.Label(bf, text="Trier par:", bg=CLR_BG, fg=CLR_MUTED).pack(side="right", padx=(8,2))
        self.invent_sort_cb = combo(bf, ["Désignation", "Stock", "Prix Achat"], width=12, textvariable=self.invent_sort_var)
        self.invent_sort_cb.pack(side="right", padx=4)

        tk.Button(bf, text="📄 Export CSV", command=self.export_inventaire_csv,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bf, text="📄 Export PDF", command=self.export_inventaire_pdf,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=10, pady=6, cursor="hand2").pack(side="right", padx=6)
        tk.Button(bf, text="🖨 Imprimer Inventaire", command=self.print_inventaire,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=12, pady=6, cursor="hand2").pack(side="right", padx=8)
        tk.Button(bf, text="📁 Voir archivés", command=self.show_archived,
                bg=CLR_ORANGE, fg="white", relief="flat",
                font=("Segoe UI",9,"bold"), padx=10, pady=6, cursor="hand2").pack(side="right", padx=4)

    def show_archived(self):
        archive_win = tk.Toplevel(self)
        archive_win.title("Produits Archivés")
        archive_win.configure(bg=CLR_BG)
        archive_win.geometry("900x500")
        archive_win.transient(self)
        archive_win.grab_set()
        center_window(archive_win, 900, 500)
        
        main_frame = tk.Frame(archive_win, bg=CLR_BG)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        lbl(main_frame, "📁 Produits Archivés", 14, True).pack(anchor="w", pady=(0, 10))
        
        cols = ["Code", "Désignation", "Stock", "Prix Vente"]
        widths = [100, 300, 100, 100]
        tf, tree = make_tree(main_frame, cols, widths)
        tf.pack(fill="both", expand=True, pady=10)
        
        conn = get_conn()
        rows = conn.execute(
            "SELECT id, code, designation, stock_actuel, prix_vente FROM produits WHERE actif = 0 ORDER BY designation"
        ).fetchall()
        conn.close()
        
        for r in rows:
            tree.insert("", "end", iid=r["id"], values=(
                r["code"], r["designation"], f"{r['stock_actuel']:.2f}", f"{r['prix_vente']:.2f}"
            ))
        
        boutons_frame = tk.Frame(main_frame, bg=CLR_BG)
        boutons_frame.pack(fill="x", pady=10)
        
        def restaurer_produit():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Avertissement", "Sélectionnez un produit à restaurer")
                return
            produit_id = sel[0]
            
            if messagebox.askyesno("Confirmation", "Restaurer ce produit ?\nIl réapparaîtra dans la liste principale."):
                conn = get_conn()
                conn.execute("UPDATE produits SET actif = 1 WHERE id = ?", (produit_id,))
                conn.commit()
                conn.close()
                archive_win.destroy()
                self.refresh()
                messagebox.showinfo("Succès", "✅ Produit restauré avec succès")
        
        def supprimer_definitivement():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Avertissement", "Sélectionnez un produit à supprimer")
                return
            produit_id = sel[0]
            
            conn = get_conn()
            produit = conn.execute("SELECT designation FROM produits WHERE id=?", (produit_id,)).fetchone()
            conn.close()
            
            if messagebox.askyesno("Confirmation définitive", 
                                f"⚠️⚠️⚠️ ATTENTION ⚠️⚠️⚠️\n\n"
                                f"Supprimer définitivement '{produit['designation']}' ?\n\n"
                                "Cette action est IRRÉVERSIBLE et ne peut pas être annulée."):
                conn = get_conn()
                conn.execute("DELETE FROM produits WHERE id=?", (produit_id,))
                conn.commit()
                conn.close()
                for item in tree.get_children():
                    tree.delete(item)
                conn = get_conn()
                rows = conn.execute(
                    "SELECT id, code, designation, stock_actuel, prix_vente FROM produits WHERE actif = 0 ORDER BY designation"
                ).fetchall()
                conn.close()
                for r in rows:
                    tree.insert("", "end", iid=r["id"], values=(
                        r["code"], r["designation"], f"{r['stock_actuel']:.2f}", f"{r['prix_vente']:.2f}"
                    ))
                messagebox.showinfo("Succès", "Produit supprimé définitivement")
        
        tk.Button(boutons_frame, text="↩️ Restaurer", command=restaurer_produit,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(boutons_frame, text="⚠️ Supprimer définitivement", command=supprimer_definitivement,
                bg=CLR_RED, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(boutons_frame, text="❌ Fermer", command=archive_win.destroy,
                bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                font=("Segoe UI", 9), padx=12, pady=6, cursor="hand2").pack(side="right")

    def refresh(self):
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM produits WHERE actif = 1 ORDER BY designation"
        ).fetchall()
        conn.close()

        for r in rows:
            barcode_val = r["barcode"] if r["barcode"] else ""
            if q in r["code"].lower() or q in r["designation"].lower() or q in barcode_val.lower():
                facteur = r["facteur_conversion"] or 1
                prix_achat = r["prix_achat"] or 0
                stock_min_cartons = (r["stock_min"] / facteur) if facteur else r["stock_min"]
                tag = "stock_ok" if r["stock_actuel"] > r["stock_min"] else "stock_low"
                prix_moyen = r["prix_moyen_pondere"] if r["prix_moyen_pondere"] else prix_achat
                if prix_achat > 0:
                    variation = ((prix_moyen - prix_achat) / prix_achat) * 100
                    variation_text = f"{variation:+.1f}%" if abs(variation) > 0.01 else "0%"
                else:
                    variation_text = "0%"
                
                # ✅ AJOUTER LA MARQUE
                fournisseur = r["fournisseur"] or ""
                
                self.tree.insert("", "end", iid=r["id"],
                    values=(
                        r["code"], barcode_val, r["designation"],
                        fournisseur,  # ✅ NOUVEAU
                        r["unite"], f"{facteur:.0f}", f"{prix_achat:.2f}",
                        f"{prix_moyen:.2f}", variation_text,
                        f"{r['prix_vente']:.2f}", f"{(r['tva'] or 0):.0f}%",
                        f"{r['stock_actuel']:.2f}",
                        f"{stock_min_cartons:.2f}",
                    ),
                    tags=(tag,)
                )

    def _form(self, data=None):
        d = ProduitDialog(self, data)
        self.wait_window(d)
        self.refresh()

    def print_inventaire(self):
        headers, data = self.build_inventaire_data()
        print_preview(data, "Inventaire - Désignation / Qté / Qté cartons/kg / Prix Achat", headers)

    def build_inventaire_data(self):
        conn = get_conn()
        try:
            rows = conn.execute(
                "SELECT code, barcode, designation, unite, facteur_conversion, prix_achat, prix_vente, stock_actuel, stock_min FROM produits"
            ).fetchall()
        finally:
            conn.close()
        filter_val = (self.invent_filter_var.get() or "Tous").strip().lower()
        sort_val = (self.invent_sort_var.get() or "Désignation").strip()
        headers = ["Désignation", "Quantité en stock", "Qté (cartons/kg)", "Prix Achat"]
        data = []
        for r in rows:
            designation = r["designation"]
            stock = float(r["stock_actuel"] or 0)
            prix_achat = float(r["prix_achat"] or 0)
            facteur = float(r["facteur_conversion"] or 1)
            unite = (r["unite"] or "").strip().lower()
            if filter_val != "tous":
                if filter_val == "kg":
                    if "kg" not in unite:
                        continue
                elif filter_val == "carton":
                    if "cart" not in unite and unite != "carton":
                        continue
                else:
                    if filter_val != unite:
                        continue
            if "kg" in unite:
                secondaire = f"{stock:.2f}"
            else:
                secondaire_qty = stock / facteur if facteur and facteur > 0 else stock
                secondaire = f"{secondaire_qty:.2f}"
            data.append([designation, f"{stock:.2f}", secondaire, f"{prix_achat:.2f}"])
        try:
            if sort_val == "Désignation":
                data.sort(key=lambda x: x[0].lower())
            elif sort_val == "Stock":
                data.sort(key=lambda x: float(x[1]) if x[1] else 0, reverse=True)
            elif sort_val == "Prix Achat":
                data.sort(key=lambda x: float(x[3]) if x[3] else 0, reverse=True)
        except Exception:
            pass
        return headers, data

    def export_inventaire_csv(self):
        headers, data = self.build_inventaire_data()
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="inventaire.csv"
        )
        if filename:
            if export_to_csv(data, filename, headers):
                messagebox.showinfo("Succès", f"Fichier CSV créé: {filename}")

    def export_inventaire_pdf(self):
        from gestion_stock import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM produits WHERE actif=1 ORDER BY designation"
        ).fetchall()
        conn.close()
        html = hr.build_inventaire_html(
            [dict(r) for r in rows], titre="Inventaire des produits"
        )
        viewer = hr.DocumentViewer(self)
        viewer.export_pdf(html, "inventaire.pdf")
 
    def export_inventaire_html(self):
        from gestion_stock import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM produits WHERE actif=1 ORDER BY designation"
        ).fetchall()
        conn.close()
        html = hr.build_inventaire_html(
            [dict(r) for r in rows], titre="Inventaire des produits"
        )
        viewer = hr.DocumentViewer(self)
        viewer.export_html(html, "inventaire.html")

    def new_item(self): 
        self._form()

    def edit_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("Avertissement", "Sélectionnez un produit")
            return
        conn = get_conn()
        r = conn.execute("SELECT * FROM produits WHERE id=?", (sel[0],)).fetchone()
        conn.close()
        self._form(dict(r))

    def del_item(self):
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("Avertissement", "Sélectionnez un produit")
            return
        conn = get_conn()
        produit_id = sel[0]
        produit = conn.execute("SELECT designation, stock_actuel FROM produits WHERE id=?", (produit_id,)).fetchone()
        if not produit:
            conn.close()
            return
        nb_utilisations = conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM lignes_achat WHERE produit_id=?) +
                (SELECT COUNT(*) FROM lignes_vente WHERE produit_id=?) +
                (SELECT COUNT(*) FROM lignes_retour_vente WHERE produit_id=?) +
                (SELECT COUNT(*) FROM lignes_retour_achat WHERE produit_id=?) as total
        """, (produit_id, produit_id, produit_id, produit_id)).fetchone()[0]
        if nb_utilisations > 0 or produit['stock_actuel'] > 0:
            msg = f"⚠️ Ce produit est utilisé dans {nb_utilisations} transaction(s)\n"
            if produit['stock_actuel'] > 0:
                msg += f"   Stock restant: {produit['stock_actuel']}\n"
            msg += f"\n📦 Produit: {produit['designation']}\n\n"
            msg += "Il sera ARCHIVÉ (plus visible dans la liste)\n"
            msg += "mais restera dans l'historique.\n\n"
            msg += "Confirmer l'archivage ?"
            if messagebox.askyesno("Archiver le produit", msg):
                conn.execute("UPDATE produits SET actif = 0 WHERE id=?", (produit_id,))
                conn.commit()
                messagebox.showinfo("Succès", f"✅ Produit archivé avec succès")
        else:
            if messagebox.askyesno("Confirmation", 
                                f"⚠️ Supprimer définitivement '{produit['designation']}' ?\n"
                                "Cette action est irréversible."):
                conn.execute("DELETE FROM produits WHERE id=?", (produit_id,))
                conn.commit()
                messagebox.showinfo("Succès", "✅ Produit supprimé définitivement")
        conn.close()
        self.refresh()


