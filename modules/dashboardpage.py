from modules.core import *

class DashboardPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=CLR_BG)
        self._build()

    def _build(self):
        lbl(self,"🏠  Tableau de Bord",18,True).pack(padx=25,pady=(25,5),anchor="w")
        lbl(self,"Vue d'ensemble de votre activité",10,color=CLR_MUTED).pack(padx=25,anchor="w")
        self.cards_frame = tk.Frame(self,bg=CLR_BG)
        self.cards_frame.pack(fill="x",padx=20,pady=20)
        self.alert_frame = tk.Frame(self,bg=CLR_BG)
        self.alert_frame.pack(fill="both",expand=True,padx=20)
        self.refresh()

    def refresh(self):
        for w in self.cards_frame.winfo_children(): w.destroy()
        for w in self.alert_frame.winfo_children(): w.destroy()

        conn = get_conn()
        nb_prod = conn.execute("SELECT COUNT(*) FROM produits").fetchone()[0]
        nb_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        nb_fourn = conn.execute("SELECT COUNT(*) FROM fournisseurs").fetchone()[0]
        nb_bv = conn.execute("SELECT COUNT(*) FROM bons_vente WHERE statut='Validé'").fetchone()[0]
        nb_ba = conn.execute("SELECT COUNT(*) FROM bons_achat WHERE statut='Validé'").fetchone()[0]
        nb_factures = conn.execute("SELECT COUNT(*) FROM factures").fetchone()[0]
        ca_vente = conn.execute("SELECT COALESCE(SUM(total),0) FROM bons_vente WHERE statut='Validé'").fetchone()[0]
        ca_achat = conn.execute("SELECT COALESCE(SUM(total),0) FROM bons_achat WHERE statut='Validé'").fetchone()[0]
        stock_alerte = conn.execute("SELECT COUNT(*) FROM produits WHERE stock_actuel<=stock_min").fetchone()[0]
        clients_solde = conn.execute("SELECT COUNT(*) FROM clients WHERE solde>0").fetchone()[0]
        conn.close()

        kpis = [
            ("📦 Produits",str(nb_prod),CLR_ACCENT),
            ("👥 Clients",str(nb_clients),CLR_GREEN),
            ("🏭 Fournisseurs",str(nb_fourn),CLR_ORANGE),
            ("🛒 Bons Achat",str(nb_ba),CLR_ACCENT),
            ("🏷️ Bons Vente",str(nb_bv),CLR_GREEN),
            ("🧾 Factures",str(nb_factures),CLR_ACCENT),
            ("💰 CA Ventes",f"{ca_vente:,.0f} DA",CLR_GREEN),
            ("📥 Total Achats",f"{ca_achat:,.0f} DA",CLR_ORANGE),
            ("⚠️ Alertes Stock",str(stock_alerte),CLR_RED),
        ]
        for i,(title,val,clr) in enumerate(kpis):
            card = tk.Frame(self.cards_frame,bg=CLR_CARD,padx=22,pady=16,relief="flat")
            card.grid(row=i//3, column=i%3, padx=8, pady=8, sticky="ew")
            self.cards_frame.grid_columnconfigure(i%3, weight=1)
            lbl(card,title,9,color=CLR_MUTED).pack(anchor="w")
            lbl(card,val,18,True,color=clr).pack(anchor="w",pady=(4,0))

        lbl(self.alert_frame,"⚠️  Alertes & Notifications",12,True,CLR_ORANGE).pack(anchor="w",pady=(10,8))
        conn = get_conn()
        alerts = conn.execute("SELECT code,designation,unite,facteur_conversion,stock_actuel,stock_min FROM produits WHERE stock_actuel<=stock_min ORDER BY stock_actuel").fetchall()
        conn.close()
        if alerts:
            for a in alerts[:8]:
                af = tk.Frame(self.alert_frame,bg=CLR_CARD,padx=15,pady=8)
                af.pack(fill="x",pady=2)
                facteur = a['facteur_conversion'] or 1
                stock_cartons = a['stock_actuel'] / facteur if facteur else a['stock_actuel']
                min_cartons = a['stock_min'] / facteur if facteur else a['stock_min']
                unit_label = "cartons" if facteur != 1 else a['unite'] or "unités"
                lbl(af,f"📦 {a['designation']} ({a['code']})  —  Stock: {stock_cartons:.1f} {unit_label}  /  Min: {min_cartons:.1f} {unit_label}",
                    9,color=CLR_RED).pack(side="left")
        else:
            lbl(self.alert_frame,"✅  Aucune alerte — Tous les stocks sont suffisants",
                10,color=CLR_GREEN).pack(anchor="w")


# ========== PAGE CLIENTS / FOURNISSEURS ==========

