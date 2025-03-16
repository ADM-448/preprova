import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import generate_questions  # Importa a função de geração de questões
import time
import re
import tempfile
from urllib import request, parse

# Inicializa o cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_pdf():
    st.title("Upload de Arquivo PDF")

    # 🔍 **Verificação de Usuário**
    user_id = st.session_state.get("user_id")

    if not user_id:
        try:
            user_data = supabase.auth.get_user()
            if user_data and hasattr(user_data, "user") and user_data.user:
                user_id = user_data.user.id
                st.session_state["user_id"] = user_id
        except Exception as e:
            st.error(f"❌ DEBUG - Erro ao recuperar usuário do Supabase: {str(e)}")
            return

    st.write(f"🔍 DEBUG - user_id na sessão: {user_id}")

    if not user_id:
        st.error("❌ Usuário não autenticado. Faça login novamente.")
        return

    uploaded_file = st.file_uploader("Selecione um arquivo PDF", type="pdf")

    if uploaded_file:
        if uploaded_file.size > 10 * 1024 * 1024:  # Limite de 10MB
            st.error("O arquivo excede o tamanho máximo permitido (10MB).")
            return

        with st.spinner("Carregando PDF..."):
            try:
                # 🔹 Remove espaços e caracteres especiais do nome do arquivo
                safe_file_name = re.sub(r'\s+', '_', uploaded_file.name)
                safe_file_name = re.sub(r'[^\w\-.]', '', safe_file_name)  # Remove caracteres especiais
                
                # 🔹 Adiciona timestamp para evitar duplicação
                timestamp = int(time.time())  
                file_path = f"pdfs/{timestamp}_{safe_file_name}"

                # 🔍 **Verificação do Bucket**
                st.write("📂 DEBUG - Listando buckets disponíveis no Supabase...")
                try:
                    bucket_list = supabase.storage.list_buckets()
                    bucket_names = [bucket.id for bucket in bucket_list]
                    st.write(f"📂 DEBUG - Buckets Disponíveis: {bucket_names}")

                    if "pdfs" not in bucket_names:
                        st.error("❌ Erro: O bucket 'pdfs' não existe no Supabase! Verifique no painel.")
                        return
                except Exception as e:
                    st.error(f"❌ DEBUG - Erro ao verificar buckets: {str(e)}")
                    return

                # 🔹 Salva o arquivo temporariamente antes do upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                    temp_file_path = temp_file.name
                
                # 🔍 **Debug do Caminho**
                st.write(f"📂 **DEBUG - Caminho do Arquivo no Supabase:** {file_path}")
                
                # 🔹 Faz o upload para o Supabase Storage
                with open(temp_file_path, "rb") as file_data:
                    storage_response = supabase.storage.from_("pdfs").upload(file_path, file_data)

                # 🔍 **Verificação do Upload**
                st.write(f"📤 DEBUG - Resposta do Upload: {storage_response}")

                if not storage_response:
                    st.error("❌ **DEBUG - O arquivo pode não ter sido enviado corretamente.**")
                    return
                
                # 🔹 Gera a URL final garantindo que o formato seja correto
                pdf_url = f"{SUPABASE_URL}/storage/v1/object/public/{file_path}"
                
                # 🔹 Corrige barras duplicadas "//"
                pdf_url = pdf_url.replace(":/", "://").replace("public//", "public/")

                # 🔍 **Debug da URL final**
                st.write(f"📄 **DEBUG - PDF armazenado:** [{safe_file_name}]({pdf_url})")
                st.write(f"🔗 **DEBUG - URL Final Corrigida:** {pdf_url}")

                # 🔍 **Aguarda 10 segundos antes de acessar o arquivo**
                st.write("⏳ **DEBUG - Aguardando 10 segundos para garantir que o Supabase processe o arquivo...**")
                time.sleep(10)

                # 🔍 **Verifica se a URL está acessível**
                try:
                    response = request.urlopen(pdf_url)
                    if response.status == 200:
                        st.write("✅ **DEBUG - O arquivo está acessível no Supabase.**")
                    else:
                        raise Exception(f"Erro ao acessar o arquivo no Supabase Storage. Código: {response.status}")
                except Exception as e:
                    st.error(f"❌ **DEBUG - Erro ao acessar o PDF no Supabase:** {str(e)}")
                    return

                # 🔍 **Verificação da Permissão para INSERT**
                st.write("📊 **DEBUG - Verificando permissões da tabela preprovas**")
                try:
                    perm_query = supabase.rpc("has_table_privilege", {"table_name": "preprovas", "privilege": "INSERT"}).execute()
                    st.write(f"🔍 DEBUG - Permissões INSERT na tabela preprovas: {perm_query}")
                except Exception as e:
                    st.error(f"❌ DEBUG - Erro ao verificar permissões da tabela preprovas: {str(e)}")
                    
                # 🔹 Insere no banco de dados
                st.write("📊 **DEBUG - Tentando inserir na tabela preprovas**")
                st.write(f"📊 **DEBUG - user_id:** {user_id}")
                st.write(f"📊 **DEBUG - pdf_url:** {pdf_url}")

                response = supabase.table("preprovas").insert({"user_id": user_id, "pdf_url": pdf_url}).execute()
                st.write(f"📊 DEBUG - Resposta do INSERT: {response}")

                if response.data:
                    preprova_id = response.data[0]["id"]
                    st.session_state["preprova_id"] = preprova_id
                    st.success("✅ PDF carregado com sucesso! Gerando sua pré-prova...")

                    # 🔹 Chama a API da OpenAI para gerar perguntas automaticamente
                    with st.spinner("📝 Gerando questões... Isso pode levar alguns segundos."):
                        success = generate_questions.generate_questions(preprova_id, pdf_url)
                        if success:
                            st.success("🎉 Questões geradas com sucesso! Acesse sua pré-prova.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao gerar questões. Tente novamente.")
                else:
                    st.error("❌ Erro ao criar pré-prova no banco de dados.")
            except Exception as e:
                st.error(f"❌ **DEBUG - Erro no upload para o Supabase:** {str(e)}")
