from modules.core import *

class FactureDetailDialog(tk.Toplevel):
    """Dialogue de détail et impression de facture"""
    
    def __init__(self, parent, facture_id, parent_window=None):
        super().__init__(parent)
        self.facture_id = facture_id
        self.parent_window = parent_window or self
        self.title("Détail Facture")
        self.configure(bg=CLR_BG)
        self.geometry("1400x750")
        self.minsize(1200, 650)
        self._load_data()
        self._build()
        center_window(self, 1200, 750)
    
    def _load_data(self):
        conn = get_conn()
        self.facture = conn.execute("""
            SELECT f.*, c.nom as client_nom, c.adresse as client_adresse, 
                   c.tel as client_tel, c.email as client_email,
                   bv.numero as bon_numero, bv.date_bon
            FROM factures f
            JOIN clients c ON f.client_id = c.id
            JOIN bons_vente bv ON f.bon_vente_id = bv.id
            WHERE f.id = ?
        """, (self.facture_id,)).fetchone()
        
        # Lignes du bon de vente
        self.lignes = conn.execute("""
            SELECT l.*, p.designation, p.unite
            FROM lignes_vente l
            JOIN produits p ON l.produit_id = p.id
            WHERE l.bon_id = ?
        """, (self.facture["bon_vente_id"],)).fetchall()
        self.tva_details = conn.execute("""
            SELECT * FROM facture_tva_details WHERE facture_id = ? """, (self.facture_id,)).fetchall()
        conn.close()
    
    def _build(self):
        main_container = tk.Frame(self, bg=CLR_BG)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ✅ Ajouter cette ligne — indispensable pour que la colonne gauche s'étire
        main_container.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=0)

        # ========== COLONNE GAUCHE ==========
        left_container = tk.Frame(main_container, bg=CLR_BG)
        left_container.grid(row=0, column=0, sticky="nsew")

        canvas = tk.Canvas(left_container, bg=CLR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CLR_BG)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)

        # ========== COLONNE DROITE ==========
        right_container = tk.Frame(main_container, bg=CLR_SIDEBAR, width=180)
        right_container.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        right_container.grid_propagate(False)  # ✅ grid_propagate et non pack_propagate

        lbl(right_container, "ACTIONS", 10, True, color=CLR_ACCENT).pack(pady=(15, 10))

        sep = tk.Frame(right_container, bg=CLR_BORDER, height=2)
        sep.pack(fill="x", padx=10, pady=5)

        btn_print = tk.Button(right_container, text="🖨  Imprimer", command=self.print_facture,
                            bg=CLR_ACCENT, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=15, pady=10,
                            cursor="hand2", width=12)
        btn_print.pack(pady=8, padx=10)

        btn_pdf = tk.Button(right_container, text="📄  PDF", command=self.export_pdf,
                            bg=CLR_GREEN, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=15, pady=10,
                            cursor="hand2", width=12)
        btn_pdf.pack(pady=8, padx=10)

        sep2 = tk.Frame(right_container, bg=CLR_BORDER, height=2)
        sep2.pack(fill="x", padx=10, pady=5)

        btn_close = tk.Button(right_container, text="❌  Fermer", command=self.destroy,
                            bg=CLR_RED, fg="white", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=15, pady=10,
                            cursor="hand2", width=12)
        btn_close.pack(pady=8, padx=10)
        
        # ========== CONTENU SCROLLABLE ==========
        
        # En-tête avec profil entreprise
        profil = get_profil_by_type("facture")
        if profil:
            nom_entreprise = profil.get("nom", "") or "VOTRE SOCIÉTÉ"
            adresse_entreprise = profil.get("adresse", "") or ""
            ville_entreprise = profil.get("ville", "") or ""
            telephone_entreprise = profil.get("telephone", "") or ""
            email_entreprise = profil.get("email", "") or ""
            nif = profil.get("nif", "") or ""
            nis = profil.get("nis", "") or ""
            nrc = profil.get("nrc", "") or ""
        else:
            nom_entreprise = "VOTRE SOCIÉTÉ"
            adresse_entreprise = ville_entreprise = telephone_entreprise = ""
            email_entreprise = nif = nis = nrc = ""
        
        header_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=20, pady=15)
        header_frame.pack(fill="x", pady=(0,15))
        
        lbl(header_frame, nom_entreprise, 18, True, color=CLR_ACCENT).pack(anchor="center")
        if adresse_entreprise:
            lbl(header_frame, adresse_entreprise, 9, color=CLR_MUTED).pack(anchor="center")
        if ville_entreprise:
            lbl(header_frame, ville_entreprise, 9, color=CLR_MUTED).pack(anchor="center")
        if telephone_entreprise:
            lbl(header_frame, f"Tél: {telephone_entreprise}", 9, color=CLR_MUTED).pack(anchor="center")
        if email_entreprise:
            lbl(header_frame, f"Email: {email_entreprise}", 9, color=CLR_MUTED).pack(anchor="center")
        
        fiscal_text = ""
        if nif:
            fiscal_text += f"NIF: {nif}  "
        if nis:
            fiscal_text += f"NIS: {nis}  "
        if nrc:
            fiscal_text += f"NRC: {nrc}"
        if fiscal_text:
            lbl(header_frame, fiscal_text, 8, color=CLR_MUTED).pack(anchor="center", pady=(5,0))
        
        lbl(header_frame, "="*60, 9, color=CLR_BORDER).pack(pady=8)
        lbl(header_frame, f"FACTURE N° {self.facture['numero']}", 16, True, color=CLR_GREEN).pack(anchor="center")
        
        # Frame pour les informations client et facture (2 colonnes)
        info_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=15, pady=10)
        info_frame.pack(fill="x", pady=10)
        
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)
        
        # Colonne gauche - Client
        left_info = tk.LabelFrame(info_frame, text="📌 CLIENT", bg=CLR_CARD, fg=CLR_ACCENT, 
                                  font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        left_info.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        lbl(left_info, self.facture['client_nom'], 10, True).pack(anchor="w", pady=2)
        if self.facture['client_adresse']:
            lbl(left_info, self.facture['client_adresse'], 9, color=CLR_MUTED).pack(anchor="w", pady=2)
        if self.facture['client_tel']:
            lbl(left_info, f"Tél: {self.facture['client_tel']}", 9, color=CLR_MUTED).pack(anchor="w", pady=2)
        if self.facture['client_email']:
            lbl(left_info, f"Email: {self.facture['client_email']}", 9, color=CLR_MUTED).pack(anchor="w", pady=2)
        
        # Colonne droite - Facture
        right_info = tk.LabelFrame(info_frame, text="📄 FACTURE", bg=CLR_CARD, fg=CLR_ACCENT,
                                   font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        right_info.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        lbl(right_info, f"Numéro: {self.facture['numero']}", 9).pack(anchor="w", pady=2)
        lbl(right_info, f"Date: {self.facture['date_facture']}", 9).pack(anchor="w", pady=2)
        lbl(right_info, f"Bon de vente: {self.facture['bon_numero']}", 9).pack(anchor="w", pady=2)
        if self.facture['date_echeance']:
            lbl(right_info, f"Échéance: {self.facture['date_echeance']}", 9).pack(anchor="w", pady=2)
        
        statut_color = CLR_GREEN if self.facture['statut'] == 'Payée' else (CLR_RED if self.facture['statut'] == 'Annulée' else CLR_ORANGE)
        lbl(right_info, f"Statut: {self.facture['statut']}", 9, True, color=statut_color).pack(anchor="w", pady=2)
        
        # Tableau des produits
        table_frame = tk.LabelFrame(scrollable_frame, text="📦 DÉTAIL DES PRODUITS", 
                                    bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 10, "bold"),
                                    padx=10, pady=10)
        table_frame.pack(fill="both", expand=True, pady=10)
        
        cols = ["Désignation", "Quantité", "Unité", "Prix Unitaire", "Total"]
        widths = [350, 80, 60, 100, 120]
        
        tree_frame = tk.Frame(table_frame, bg=CLR_CARD)
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        
        for i, col in enumerate(cols):
            tree.heading(col, text=col)
            if col in ["Quantité", "Unité"]:
                tree.column(col, width=widths[i], anchor="center")
            elif col in ["Prix Unitaire", "Total"]:
                tree.column(col, width=widths[i], anchor="e")
            else:
                tree.column(col, width=widths[i], anchor="w")
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        for l in self.lignes:
            tree.insert("", "end", values=(
                l["designation"],
                f"{l['quantite']:.2f}",
                l["unite"] or "Pcs",
                f"{l['prix_unitaire']:.2f}",
                f"{l['total']:.2f}"
            ))
        
        # Totaux
        total_frame = tk.Frame(scrollable_frame, bg=CLR_CARD, padx=15, pady=10)
        total_frame.pack(fill="x", pady=10)
        
        tva_montant = self.facture['total_ht'] * self.facture['tva'] / 100
        
        total_inner = tk.Frame(total_frame, bg=CLR_CARD)
        total_inner.pack(side="right")
        
        row1 = tk.Frame(total_inner, bg=CLR_CARD)
        row1.pack(fill="x", pady=3)
        lbl(row1, "Total HT:", 11, True, color=CLR_MUTED).pack(side="left", padx=10)
        lbl(row1, f"{self.facture['total_ht']:,.2f} DA", 11, True, color=CLR_TEXT).pack(side="left", padx=10)
        
        # Détail TVA par taux
        for tva_d in self.tva_details:
            row_tva = tk.Frame(total_inner, bg=CLR_CARD)
            row_tva.pack(fill="x", pady=2)
            lbl(row_tva, f"TVA ({tva_d['taux_tva']:.0f}%) sur {tva_d['total_ht']:,.2f} DA:", 10, False, color=CLR_MUTED).pack(side="left", padx=10)
            lbl(row_tva, f"{tva_d['total_tva']:,.2f} DA", 10, True, color=CLR_ORANGE).pack(side="left", padx=10)
        row3 = tk.Frame(total_inner, bg=CLR_CARD)
        row3.pack(fill="x", pady=5)
        lbl(row3, "TOTAL TTC:", 13, True, color=CLR_MUTED).pack(side="left", padx=10)
        lbl(row3, f"{self.facture['total_ttc']:,.2f} DA", 15, True, color=CLR_GREEN).pack(side="left", padx=10)
        
        # Observations
        if self.facture['observations']:
            obs_frame = tk.LabelFrame(scrollable_frame, text="📝 OBSERVATIONS", 
                                      bg=CLR_CARD, fg=CLR_ACCENT, font=("Segoe UI", 9, "bold"),
                                      padx=15, pady=10)
            obs_frame.pack(fill="x", pady=10)
            lbl(obs_frame, self.facture['observations'], 9, color=CLR_TEXT, wraplength=800).pack(anchor="w")
        
        # Footer
        footer_frame = tk.Frame(scrollable_frame, bg=CLR_BG, padx=15, pady=15)
        footer_frame.pack(fill="x")
        
        lbl(footer_frame, "Merci pour votre confiance !", 9, color=CLR_MUTED).pack()
        lbl(footer_frame, f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}", 8, color=CLR_MUTED).pack()
    
    def _get_html(self) -> str:
        from modules.core import get_profil_by_type
        profil = get_profil_by_type("facture")
        fac = dict(self.facture)
        fac["bon_numero"] = self.facture.get("bon_numero", "")
        
        html = hr.build_facture_html(
            profil      = profil,
            facture     = fac,
            lignes      = [dict(l) for l in self.lignes],
            tva_details = [dict(t) for t in self.tva_details],
        )
        
        # ✅ AJOUT DES STYLES D'IMPRESSION
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
 
    def print_facture(self):
        viewer = hr.DocumentViewer(self)
        viewer.show(self._get_html(), f"Facture {self.facture['numero']}")
 
    def export_pdf(self):
        viewer = hr.DocumentViewer(self)
        viewer.export_pdf(
            self._get_html(),
            default_name=f"Facture_{self.facture['numero']}.pdf",
        )

# ========== PAGE PRODUITS ==========

