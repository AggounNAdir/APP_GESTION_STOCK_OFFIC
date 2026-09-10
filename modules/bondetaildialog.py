from modules.core import *

class BonDetailDialog(tk.Toplevel):
    def __init__(self, parent, bon_type, bon_id):
        super().__init__(parent)
        self.bon_type = bon_type
        self.title("Détail du Bon")
        self.configure(bg=CLR_BG)
        self.geometry("800x750")
        self.bon_id = bon_id
        self._load(bon_id)
        center_window(self, 800, 600)

    def _load(self, bon_id):
        conn = get_conn()
        if self.bon_type == "achat":
            bon = conn.execute("""SELECT b.*, f.nom as tiers, 
                                        b.date_creation, b.date_livraison, 
                                        b.num_facture_fournisseur, b.num_bl_fournisseur,
                                        b.ancien_solde, b.nouveau_solde
                                FROM bons_achat b
                                JOIN fournisseurs f ON b.fournisseur_id = f.id 
                                WHERE b.id = ?""", (bon_id,)).fetchone()
            lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.unite, p.facteur_conversion
                                    FROM lignes_achat l
                                    JOIN produits p ON l.produit_id = p.id 
                                    WHERE l.bon_id = ?""", (bon_id,)).fetchall()
            # ✅ Récupérer les remises par produit pour les achats
            remises = conn.execute("""
                SELECT * FROM remises WHERE achat_id = ?
            """, (bon_id,)).fetchall()
        else:
            bon = conn.execute("""SELECT b.*, c.nom as tiers 
                                FROM bons_vente b
                                JOIN clients c ON b.client_id = c.id 
                                WHERE b.id = ?""", (bon_id,)).fetchone()
            lignes = conn.execute("""SELECT l.*, p.code, p.designation, p.unite, p.facteur_conversion
                                    FROM lignes_vente l
                                    JOIN produits p ON l.produit_id = p.id 
                                    WHERE l.bon_id = ?""", (bon_id,)).fetchall()
            # ✅ Récupérer les remises par produit pour les ventes
            remises = conn.execute("""
                SELECT * FROM remises WHERE vente_id = ?""", (bon_id,)).fetchall()
        conn.close()

        self.bon_data = dict(bon) if bon else {}
        self.lignes_data = lignes
        self.remises_data = remises

        # ========== EN-TÊTE ==========
        f = tk.Frame(self, bg=CLR_CARD, padx=20, pady=15)
        f.pack(fill="x", padx=15, pady=15)

        titre = "BON D'ACHAT" if self.bon_type == "achat" else "BON DE VENTE"
        lbl(f, f"📄 {titre} N° {bon['numero']}", 14, True, CLR_ACCENT).pack(anchor="w", pady=(0,8))

        ligne1 = tk.Frame(f, bg=CLR_CARD)
        ligne1.pack(fill="x", pady=2)
        lbl(ligne1, "Date:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
        lbl(ligne1, bon["date_bon"], 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

        tiers_label = "Fournisseur:" if self.bon_type == "achat" else "Client:"
        lbl(ligne1, tiers_label, 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
        lbl(ligne1, bon["tiers"], 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

        statut_color = CLR_GREEN if bon["statut"] == "Validé" else CLR_RED
        lbl(ligne1, "Statut:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
        lbl(ligne1, bon["statut"], 9, True, statut_color).pack(side="left")

        if self.bon_type == "achat":
            ligne2 = tk.Frame(f, bg=CLR_CARD)
            ligne2.pack(fill="x", pady=2)
            lbl(ligne2, "📅 Date livraison:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne2, bon["date_livraison"] or "-", 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

            lbl(ligne2, "📄 N° Facture Fourn.:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne2, bon["num_facture_fournisseur"] or "-", 9, False, CLR_TEXT).pack(side="left", padx=(0,20))

            lbl(ligne2, "🚚 N° BL Fournisseur:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne2, bon["num_bl_fournisseur"] or "-", 9, False, CLR_TEXT).pack(side="left")

            ligne3 = tk.Frame(f, bg=CLR_CARD)
            ligne3.pack(fill="x", pady=2)
            lbl(ligne3, "Ancien solde:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne3, f"{bon['ancien_solde']:,.2f} DA", 9, False, CLR_ORANGE).pack(side="left", padx=(0,20))

            lbl(ligne3, "Nouveau solde:", 9, True, CLR_MUTED).pack(side="left", padx=(0,5))
            lbl(ligne3, f"{bon['nouveau_solde']:,.2f} DA", 9, False, CLR_GREEN).pack(side="left")

        # ✅ Tableau des produits AVEC colonne Remise
        cols = ["Code", "Produit", "Qté unités", "Qté cartons", "Unité", "Prix Unit.", "Remise", "Total"]
        widths = [100, 180, 80, 80, 60, 100, 70, 120]
        tf, tree = make_tree(self, cols, widths)
        tf.pack(fill="both", expand=True, padx=15, pady=5)
        
        # ✅ Créer un dictionnaire des remises par produit
        remises_dict = {}
        for remise in self.remises_data:
            remise = dict(remise)
            # Si la remise est liée à un produit, on la stocke
            produit_id = remise.get("produit_id")
            if produit_id:
                remises_dict[produit_id] = remise
        
        for l in lignes:
            facteur = l["facteur_conversion"] or 1
            qte_carton = l["quantite"] / facteur if facteur else l["quantite"]
            
            # ✅ Vérifier si ce produit a une remise
            remise_info = remises_dict.get(l["produit_id"])
            if remise_info:
                remise_valeur = remise_info.get("valeur", 0)
                remise_affichage = f"{remise_valeur:.0f}%"
            else:
                remise_affichage = "-"
            
            tree.insert("", "end", values=(
                l["code"],
                l["designation"],
                f"{l['quantite']:.2f}",
                f"{qte_carton:.2f}",
                l["unite"],
                f"{l['prix_unitaire']:.2f}",
                remise_affichage,  # ✅ Nouvelle colonne Remise
                f"{l['total']:.2f}"
            ))

        # ========== FOOTER ==========
        foot = tk.Frame(self, bg=CLR_BG, padx=15, pady=10)
        foot.pack(fill="x")
        
        # ✅ Calcul des totaux
        total_ttc = self.bon_data['total']
        total_ht = sum(l["total"] for l in self.lignes_data)
        
        # ✅ Calcul de la TVA
        tva_montant = 0
        for l in self.lignes_data:
            conn_tmp = get_conn()
            p = conn_tmp.execute("SELECT tva FROM produits WHERE id=?", (l["produit_id"],)).fetchone()
            conn_tmp.close()
            tva_taux = p["tva"] if p else 19
            if self.bon_type == "vente":
                tva_taux = 0
            ht_l = l["total"]
            tva_montant += ht_l * tva_taux / 100
        
        total_ttc_calc = total_ht + tva_montant
        
        # ✅ Total HT
        row_ht = tk.Frame(foot, bg=CLR_BG)
        row_ht.pack(side="left", padx=10)
        lbl(row_ht, "Total HT:", 10, True, CLR_MUTED).pack(side="left", padx=5)
        lbl(row_ht, f"{total_ht:,.2f} DA", 10, True, CLR_TEXT).pack(side="left", padx=5)
        
        # ✅ TVA
        if tva_montant > 0:
            row_tva = tk.Frame(foot, bg=CLR_BG)
            row_tva.pack(side="left", padx=20)
            lbl(row_tva, "TVA:", 10, True, CLR_MUTED).pack(side="left", padx=5)
            lbl(row_tva, f"{tva_montant:,.2f} DA", 10, True, CLR_ORANGE).pack(side="left", padx=5)
        
        # ✅ Total TTC
        lbl(foot, f"⭐ TOTAL TTC:  {total_ttc_calc:,.2f} DA", 12, True, CLR_GREEN).pack(side="right", padx=10)
        
        # ✅ Boutons
        btn_frame = tk.Frame(foot, bg=CLR_BG)
        btn_frame.pack(side="left", pady=(10,0))
        
        tk.Button(btn_frame, text="🖨 Imprimer", command=self.print_bon,
                bg=CLR_ACCENT, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="📄 Exporter PDF", command=self.export_pdf,
                bg=CLR_GREEN, fg="white", relief="flat",
                font=("Segoe UI", 9, "bold"), padx=12, pady=6, cursor="hand2").pack(side="left", padx=4)
        
        tk.Button(btn_frame, text="❌ Fermer", command=self.destroy,
                bg=CLR_BORDER, fg=CLR_TEXT, relief="flat",
                font=("Segoe UI", 9), padx=14, pady=6, cursor="hand2").pack(side="left", padx=4)
    def _get_html(self) -> str:
        """Génère le HTML via le module centralisé."""
        from modules.core import get_profil_by_type, get_conn
        profil = get_profil_by_type("bon_livraison")
        conn = get_conn()
        remises = conn.execute(
            "SELECT * FROM remises WHERE vente_id = ?" if self.bon_type == "vente"
            else "SELECT * FROM remises WHERE achat_id = ?",
            (self.bon_id,)
        ).fetchall()
        conn.close()
        remises_dicts = [dict(r) for r in remises]
        
        # ============================================================
        # ✅ SUPPRIMER COMPLÈTEMENT LA COLONNE "code"
        # ============================================================
        lignes_sans_code = []
        for l in self.lignes_data:
            l_dict = dict(l)
            # Supprimer la clé "code" (supprime aussi l'en-tête)
            l_dict.pop("code", None)  # pop() supprime la clé si elle existe
            lignes_sans_code.append(l_dict)
        
        html = hr.build_bon_html(
            profil        = profil,
            bon_data      = self.bon_data,
            lignes        = lignes_sans_code,  # ✅ Lignes sans la clé "code"
            remises       = remises_dicts,
            bon_type      = self.bon_type,
        )
        
        # ✅ STYLES D'IMPRESSION (déjà dans votre code)
        print_styles = """
        <style>
            @media print {
                * {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    box-shadow: none !important;
                    text-shadow: none !important;
                    background-image: none !important;
                    filter: none !important;
                    -webkit-filter: none !important;
                    opacity: 1 !important;
                }
                
                body {
                    background-color: #ffffff !important;
                    margin: 15px !important;
                    font-size: 11pt !important;
                    color: #000000 !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                }
                
                th {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    font-weight: 700 !important;
                    font-size: 11pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    border: 2px solid #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                    text-align: center !important;
                    padding: 8px 12px !important;
                    vertical-align: middle !important;
                    page-break-inside: avoid !important;
                }
                
                td {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border: 1px solid #888888 !important;
                    padding: 6px 10px !important;
                    font-size: 10pt !important;
                    font-family: 'Arial', 'Helvetica', sans-serif !important;
                    text-align: center !important;
                }
                
                tr:nth-child(even) td {
                    background-color: #f5f5f5 !important;
                }
                
                .header-section, .header, .bg-primary, .bg-dark {
                    background-color: #ffffff !important;
                    color: #000000 !important;
                    border-bottom: 3px solid #000000 !important;
                }
                
                .header-section h1, .header-section h2, .header-section h3 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                h1, h2, h3, h4, h5 {
                    color: #000000 !important;
                    font-weight: 700 !important;
                }
                
                table {
                    border-collapse: collapse !important;
                    width: 100% !important;
                    page-break-inside: auto !important;
                }
                
                thead {
                    display: table-header-group !important;
                }
                
                tr {
                    page-break-inside: avoid !important;
                    page-break-after: auto !important;
                }
                
                .total-row td, .grand-total td {
                    font-weight: 700 !important;
                    border-top: 3px solid #000000 !important;
                }
                
                .footer, .footer p, .footer div {
                    color: #000000 !important;
                    border-top: 2px solid #000000 !important;
                    padding-top: 10px !important;
                    margin-top: 15px !important;
                }
            }
        </style>
        """
        
        if '</head>' in html:
            html = html.replace('</head>', print_styles + '</head>')
        else:
            html = html.replace('<body>', print_styles + '<body>')
        
        return html
        
    def print_bon(self):
        viewer = hr.DocumentViewer(self)
        viewer.show(self._get_html(), f"BON N°{self.bon_data['numero']}")
 
    def export_pdf(self):
        viewer = hr.DocumentViewer(self)
        viewer.export_pdf(
            self._get_html(),
            default_name=f"Bon_{self.bon_data['numero']}.pdf",
        )

# ========== APPLICATION PRINCIPALE ==========

