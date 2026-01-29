import re
import csv
from pypdf import PdfReader

PDF_ENTRADA = "enel_filtrado.pdf"
ARQUIVO_CSV = "enel_consolidado.csv"

DEBUG_TEXTO = False


def normalizar(texto):
    return re.sub(r"\s+", " ", texto.lower()) if texto else ""


def extrair_instalacao(texto):
    m = re.search(r"\b(\d{8,12})\s*/\s*(\d{8,13})\b", texto)
    if m:
        return m.group(1)

    padroes = [
        r"instala[çc][aã]o[^0-9]{0,10}(\d[\d\s]{5,15})",
        r"\buc\b[^0-9]{0,10}(\d[\d\s]{5,15})",
        r"unidade\s+consumidora[^0-9]{0,10}(\d[\d\s]{5,15})",
        r"contrato[^0-9]{0,10}(\d[\d\s]{5,15})",
    ]

    for p in padroes:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return re.sub(r"\D", "", m.group(1))

    nums = re.findall(r"\b\d{8,12}\b", texto)
    return max(nums, key=len) if nums else ""


def extrair_referencia(texto, instalacao):
    t = re.sub(r"\s+", " ", texto)
    pos = t.find(instalacao)
    area = t[pos:pos+500] if pos != -1 else t
    area = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", "", area)

    m = re.search(r"\b(0[1-9]|1[0-2])/[0-9]{4}\b", area)
    return m.group(0) if m else ""


def extrair_total(texto):
    padroes = [
        r"total\s+a\s+pagar\s*r?\$?\s*([\d.,]+)",
        r"valor\s+total\s*r?\$?\s*([\d.,]+)",
        r"total\s+da\s+fatura\s*r?\$?\s*([\d.,]+)",
    ]
    for p in padroes:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return m.group(1)

    m = re.search(r"r\$\s*([\d.,]+)", texto.lower())
    return m.group(1) if m else ""


def extrair_ir(texto):
    texto = texto.lower()

    m = re.search(
        r"ret\.\s*art\.\s*64\s*lei\s*9430\s*-\s*1[,\.]20%\s*(?:[\d.,]+\s*){0,3}(-?\d[\d.,]*)",
        texto
    )
    if m:
        return m.group(1).replace("-", "")

    m = re.search(r"irrf?\s*1[,\.]20\s*%\s*r?\$?\s*(-?\d[\d.,]*)", texto)
    if m:
        return m.group(1).replace("-", "")

    return "0,00"




def extrair_consumo(texto):
    texto = texto.upper()

    valores = []

    # Caso especial correto:
    # EN CONSUMIDA FAT TU KWH <valor>
    # EN FORNECIDA TU KWH <valor>
    padrao_especial = re.findall(
        r"EN (CONSUMIDA|FORNECIDA)\s+(?:FAT\s+)?TU\s+KWH\s+([\d.,]+)",
        texto
    )

    if padrao_especial:
        for _, v in padrao_especial:
            numero = float(v.replace(".", "").replace(",", "."))
            valores.append(numero)

    # Caso normal
    if not valores:
        m = re.search(
            r"(?:CONSUMO|USO SIST\. DISTR\.) .*?KWH\s+([\d.,]+)",
            texto
        )
        if m:
            numero = float(m.group(1).replace(".", "").replace(",", "."))
            valores.append(numero)

    if not valores:
        return ""

    total = sum(valores)

    return f"{total:.2f}".replace(".", ",")






def pagina_eh_fatura(texto):
    t = texto.lower()
    pontos = 0
    if "instala" in t or "uc" in t:
        pontos += 1
    if "vencimento" in t:
        pontos += 1
    if re.search(r"r\$\s*\d", t):
        pontos += 1
    return pontos >= 2


def processar_pdf():
    reader = PdfReader(PDF_ENTRADA)

    with open(ARQUIVO_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")

        writer.writerow([
            "Pagina",
            "Instalacao",
            "Referencia",
            "Consumo_kWh",
            "Total_Pagar",
            "IR_1_20"
        ])

        total_faturas = 0

        for i, page in enumerate(reader.pages):
            texto_original = page.extract_text()
            if not texto_original:
                continue

            if not pagina_eh_fatura(texto_original):
                continue

            texto = normalizar(texto_original)

            instalacao = extrair_instalacao(texto)
            referencia = extrair_referencia(texto, instalacao)
            total = extrair_total(texto)
            ir = extrair_ir(texto)
            consumo = extrair_consumo(texto_original)

            writer.writerow([
                i + 1,
                instalacao,
                referencia,
                consumo,
                total,
                ir
            ])

            total_faturas += 1
            print(f"Página {i+1} OK")

    print("\n==============================")
    print(f"Faturas encontradas: {total_faturas}")
    print(f"Arquivo gerado: {ARQUIVO_CSV}")
    print("==============================\n")


if __name__ == "__main__":
    processar_pdf()
