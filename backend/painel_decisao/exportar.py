def exportar_excel(df, path="resultado_export.xlsx"):
    df.to_excel(path, index=False)
    return path
