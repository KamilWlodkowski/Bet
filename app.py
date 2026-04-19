import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO


def parsuj_artykuly(plik) -> dict[str, str]:
    """
    Wyciąga unikalne pary (numer_artykułu -> nazwa) z PDF Kontrola Braków.
    
    Zwraca słownik: {"81175": "DESPERADOS RED 400ML", ...}
    """
    artykuly = {}

    with pdfplumber.open(plik) as pdf:
        for page in pdf.pages:
            tekst = page.extract_text()
            if not tekst:
                continue

            for line in tekst.split("\n"):
                parts = line.split()
                if not parts:
                    continue

                # Pierwszy token musi być samymi cyframi (numer artykułu)
                if not parts[0].isdigit():
                    continue

                numer = parts[0]
                nazwa_tokens = []

                for token in parts[1:]:
                    # Stop gdy trafimy na półkę (np. "106-01.103"), MKT, RES, SZT
                    if token in ("MKT", "RES", "SZT", "Razem:"):
                        break
                    if re.match(r"^\d{3}-\d{2}", token):
                        break
                    nazwa_tokens.append(token)

                nazwa = " ".join(nazwa_tokens).strip()

                # Zapisz tylko jeśli nazwa nie jest pusta i artykułu jeszcze nie ma
                if nazwa and numer not in artykuly:
                    artykuly[numer] = nazwa

    return artykuly


# ── UI ──────────────────────────────────────────────────────────────────────

st.title("📦 Parser artykułów – Kontrola Braków")
st.write("Wgraj plik PDF z kontroli braków, aby wyciągnąć listę artykułów.")

uploaded_file = st.file_uploader("Wybierz plik PDF", type="pdf")

if uploaded_file:
    with st.spinner("Parsowanie pliku..."):
        try:
            artykuly = parsuj_artykuly(uploaded_file)
        except Exception as e:
            st.error(f"Błąd podczas parsowania: {e}")
            st.stop()

    st.success(f"Znaleziono **{len(artykuly)}** unikalnych artykułów.")

    # Tabela
    df = pd.DataFrame(
        [(numer, nazwa) for numer, nazwa in artykuly.items()],
        columns=["Numer artykułu", "Nazwa artykułu"],
    )

    # Pole wyszukiwania
    szukaj = st.text_input("🔍 Filtruj po nazwie lub numerze")
    if szukaj:
        maska = (
            df["Numer artykułu"].str.contains(szukaj, case=False)
            | df["Nazwa artykułu"].str.contains(szukaj, case=False)
        )
        df_filtered = df[maska]
    else:
        df_filtered = df

    st.dataframe(df_filtered, use_container_width=True, hide_index=True)

    # Eksport do CSV
    csv = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Pobierz jako CSV",
        data=csv,
        file_name="artykuly.csv",
        mime="text/csv",
    )