if __name__ == "__main__":
    from data_pulling.pdf_analysis import analyze_pdf, plotit_asset_tables
    id = 1
    report_pdf_url = "https://assets.ctfassets.net/vyse88cgwfbl/6GbUTVK4tTYAytefu5daIi/6cac18eb4b526c9c52640a3d2bed9642/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_31-10-2025.pdf"
    stablecoin = "USDT"
    asset_table = analyze_pdf(id=id,report_pdf_url=report_pdf_url,stablecoin=stablecoin)
    plotit_asset_tables(stablecoin="USDT", asset_table=asset_table)

