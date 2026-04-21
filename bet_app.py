import streamlit as st
import pdfplumber
import re
import pandas as pd


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

                if nazwa and numer not in artykuly:
                    artykuly[numer] = nazwa

    return artykuly


# ── Session state ────────────────────────────────────────────────────────────

if "artykuly" not in st.session_state:
    st.session_state.artykuly = {}

if "wgrane_pliki" not in st.session_state:
    st.session_state.wgrane_pliki = []

# ── UI ───────────────────────────────────────────────────────────────────────

st.title("📦 Parser artykułów – Kontrola Braków")
st.write("Wgrywaj kolejne pliki PDF — artykuły będą dodawane do wspólnej bazy.")

uploaded_file = st.file_uploader("Wybierz plik PDF", type="pdf")

if uploaded_file:
    # Nie parsuj tego samego pliku dwa razy
    if uploaded_file.name not in st.session_state.wgrane_pliki:
        with st.spinner("Parsowanie pliku..."):
            try:
                nowe = parsuj_artykuly(uploaded_file)
            except Exception as e:
                st.error(f"Błąd podczas parsowania: {e}")
                st.stop()

        przed = len(st.session_state.artykuly)
        st.session_state.artykuly.update(nowe)
        po = len(st.session_state.artykuly)
        st.session_state.wgrane_pliki.append(uploaded_file.name)

        st.success(f"Dodano **{po - przed}** nowych artykułów. Łącznie w bazie: **{po}**.")
    else:
        st.info(f"Plik **{uploaded_file.name}** był już wgrany wcześniej.")

# ── Wgrane pliki ─────────────────────────────────────────────────────────────

if st.session_state.wgrane_pliki:
    with st.expander(f"📂 Wgrane pliki ({len(st.session_state.wgrane_pliki)})"):
        for nazwa in st.session_state.wgrane_pliki:
            st.write(f"✅ {nazwa}")

# ── Tabela ───────────────────────────────────────────────────────────────────

if st.session_state.artykuly:
    df = pd.DataFrame(
        [(numer, nazwa) for numer, nazwa in st.session_state.artykuly.items()],
        columns=["Numer artykułu", "Nazwa artykułu"],
    )

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

    # Czyszczenie bazy
    if st.button("🗑️ Wyczyść bazę"):
        st.session_state.artykuly = {}
        st.session_state.wgrane_pliki = []
        st.rerun()
else:
    st.info("Baza jest pusta. Wgraj plik PDF aby rozpocząć.")
