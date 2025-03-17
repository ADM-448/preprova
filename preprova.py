import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def delete_preprova(preprova_id):
    """Apaga a pré-prova do banco de dados e do armazenamento."""
    try:
        # Obtém a pré-prova para deletar o arquivo do Supabase Storage
        response = supabase.table("preprovas").select("pdf_url").eq("id", preprova_id).execute()
        
        if not response.data:
            st.error("Erro: Pré-prova não encontrada.")
            return

        pdf_url = response.data[0]["pdf_url"]
        file_name = pdf_url.split("/")[-1]  # Extrai o nome do arquivo do Supabase Storage
        
        # Apaga o arquivo do Supabase Storage
        supabase.storage.from_("pdfs").remove([file_name])

        # Apaga as questões associadas à pré-prova
        supabase.table("questoes").delete().eq("preprova_id", preprova_id).execute()

        # Apaga a pré-prova do banco de dados
        supabase.table("preprovas").delete().eq("id", preprova_id).execute()

        st.success(f"🗑️ Pré-prova {preprova_id} apagada com sucesso! Atualize a página para ver as mudanças.")

        # Atualiza a lista de pré-provas no session state
        st.session_state["preprovas"] = [p for p in st.session_state.get("preprovas", []) if p["id"] != preprova_id]

    except Exception as e:
        st.error(f"❌ Erro ao apagar a pré-prova: {str(e)}")

def preprova_page():
    st.title("Minhas Pré-Provas")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ Usuário não autenticado. Faça login novamente.")
        return

    # Se as pré-provas ainda não foram carregadas na sessão, busca do banco
    if "preprovas" not in st.session_state:
        response = supabase.table("preprovas").select("*").eq("user_id", user_id).execute()
       
