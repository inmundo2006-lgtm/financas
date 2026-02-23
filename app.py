"""
Aplicativo de Gestão de Finanças Pessoais
Desenvolvido com Streamlit para aprendizado de Python
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import locale
from database import (
    init_database, 
    adicionar_transacao, 
    obter_transacoes,
    obter_resumo_mensal,
    obter_gastos_por_categoria,
    excluir_transacao
)

# Tentar configurar locale para português do Brasil
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except:
        pass

# Dicionário de meses em português
MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

# Configuração da página
st.set_page_config(
    page_title="Finanças Pessoais",
    page_icon="💰",
    layout="wide"
)

# Inicializar banco de dados
init_database()

# Título principal
st.title("💰 Gestão de Finanças Pessoais")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 Menu")
    pagina = st.radio(
        "Navegação:",
        ["Dashboard", "Nova Transação", "Histórico", "Relatórios"]
    )
    
    st.markdown("---")
    st.info("💡 **Dica:** Use este app para controlar suas receitas e despesas!")

# ==================== DASHBOARD ====================
if pagina == "Dashboard":
    st.header("📈 Dashboard Financeiro")
    
    col1, col2 = st.columns(2)
    with col1:
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        mes_selecionado = st.selectbox(
            "Mês:",
            range(1, 13),
            index=mes_atual - 1,
            format_func=lambda x: MESES_PT[x]
        )
    with col2:
        ano_selecionado = st.selectbox(
            "Ano:",
            range(2020, 2031),
            index=range(2020, 2031).index(ano_atual)
        )
    
    resumo = obter_resumo_mensal(mes_selecionado, ano_selecionado)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💵 Receitas", f"R$ {resumo['receitas']:.2f}")
    
    with col2:
        st.metric("💸 Despesas", f"R$ {resumo['despesas']:.2f}")
    
    with col3:
        saldo = resumo['receitas'] - resumo['despesas']
        st.metric(
            "💰 Saldo",
            f"R$ {saldo:.2f}",
            delta=f"R$ {saldo:.2f}" if saldo >= 0 else f"-R$ {abs(saldo):.2f}",
            delta_color="normal" if saldo >= 0 else "inverse"
        )
    
    with col4:
        st.metric("📝 Transações", resumo["total_transacoes"])
    
    st.markdown("---")
    
    if resumo["total_transacoes"] > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Despesas por Categoria")
            gastos = obter_gastos_por_categoria(mes_selecionado, ano_selecionado)
            
            if not gastos.empty:
                fig = px.pie(
                    gastos,
                    values='total',
                    names='categoria',
                    title='Distribuição de Despesas',
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma despesa registrada neste período")
        
        with col2:
            st.subheader("📈 Evolução Mensal")
            transacoes = obter_transacoes(mes_selecionado, ano_selecionado)
            
            if not transacoes.empty:
                transacoes['data'] = pd.to_datetime(transacoes['data'])
                evolucao = transacoes.groupby([transacoes['data'].dt.day, 'tipo']).agg({
                    'valor': 'sum'
                }).reset_index()
                
                fig = go.Figure()
                
                receitas_dia = evolucao[evolucao['tipo'] == 'Receita']
                if not receitas_dia.empty:
                    fig.add_trace(go.Scatter(
                        x=receitas_dia['data'],
                        y=receitas_dia['valor'].cumsum(),
                        mode='lines+markers',
                        name='Receitas',
                        line=dict(color='green', width=2)
                    ))
                
                despesas_dia = evolucao[evolucao['tipo'] == 'Despesa']
                if not despesas_dia.empty:
                    fig.add_trace(go.Scatter(
                        x=despesas_dia['data'],
                        y=despesas_dia['valor'].cumsum(),
                        mode='lines+markers',
                        name='Despesas',
                        line=dict(color='red', width=2)
                    ))
                
                fig.update_layout(
                    title='Acumulado no Mês',
                    xaxis_title='Dia',
                    yaxis_title='Valor (R$)',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma transação registrada neste período")
    else:
        st.info("Nenhuma transação registrada. Comece adicionando uma nova transação!")

# ==================== NOVA TRANSAÇÃO ====================
elif pagina == "Nova Transação":
    st.header("➕ Adicionar Nova Transação")
    
    tipo = st.selectbox("Tipo de Transação:", ["Receita", "Despesa"], key="tipo_transacao")
    
    if tipo == "Receita":
        categorias = ["Salário", "Freelance", "Investimentos", "Presente", "Outras Receitas"]
    else:
        categorias = ["Alimentação", "Transporte", "Moradia", "Saúde", "Educação", "Lazer", "Compras", "Contas", "Outras Despesas"]
    
    st.markdown("---")
    
    with st.form("form_transacao"):
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor (R$):", min_value=0.01, step=0.01, format="%.2f")
            data = st.date_input("Data:", value=datetime.now(), format="DD/MM/YYYY")
            st.caption(f"📅 Data selecionada: {data.strftime('%d/%m/%Y')}")
        
        with col2:
            categoria = st.selectbox("Categoria:", categorias)
            descricao = st.text_input("Descrição:", placeholder="Ex: Supermercado, Conta de luz...")
        
        submitted = st.form_submit_button("💾 Salvar Transação", use_container_width=True)
        
        if submitted:
            if descricao.strip() == "":
                st.error("⚠️ Por favor, adicione uma descrição!")
            else:
                adicionar_transacao(
                    tipo=tipo,
                    valor=valor,
                    categoria=categoria,
                    descricao=descricao,
                    data=str(data)   # 🔥 CORREÇÃO AQUI
                )
                st.success(f"✅ {tipo} de R$ {valor:.2f} adicionada com sucesso!")
                st.balloons()

# ==================== HISTÓRICO ====================
elif pagina == "Histórico":
    st.header("📜 Histórico de Transações")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mes_filtro = st.selectbox(
            "Filtrar por mês:",
            ["Todos"] + list(range(1, 13)),
            format_func=lambda x: "Todos os meses" if x == "Todos" else MESES_PT[x]
        )
    
    with col2:
        ano_filtro = st.selectbox(
            "Filtrar por ano:",
            ["Todos"] + list(range(2020, 2031)),
            format_func=lambda x: "Todos os anos" if x == "Todos" else str(x)
        )
    
    with col3:
        tipo_filtro = st.selectbox("Tipo:", ["Todos", "Receita", "Despesa"])
    
    mes = None if mes_filtro == "Todos" else mes_filtro
    ano = None if ano_filtro == "Todos" else ano_filtro
    
    transacoes = obter_transacoes(mes, ano)
    
    if tipo_filtro != "Todos":
        transacoes = transacoes[transacoes['tipo'] == tipo_filtro]
    
    if not transacoes.empty:
        st.info(f"📊 Total de {len(transacoes)} transações encontradas")
        
        transacoes_display = transacoes.copy()
        transacoes_display['data'] = pd.to_datetime(transacoes_display['data']).dt.strftime('%d/%m/%Y')
        transacoes_display['valor'] = transacoes_display['valor'].apply(lambda x: f"R$ {x:.2f}")
        
        transacoes_display = transacoes_display[['data', 'tipo', 'categoria', 'descricao', 'valor', 'id']]
        
        st.dataframe(transacoes_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🗑️ Excluir Transação")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            id_excluir = st.number_input("ID da transação a excluir:", min_value=1, step=1)
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Excluir", use_container_width=True):
                if excluir_transacao(id_excluir):
                    st.success("Transação excluída com sucesso!")
                    st.rerun()
                else:
                    st.error("ID não encontrado!")
    else:
        st.warning("Nenhuma transação encontrada com os filtros selecionados")

# ==================== RELATÓRIOS ====================
elif pagina == "Relatórios":
    st.header("📊 Relatórios Detalhados")
    
    col1, col2 = st.columns(2)
    with col1:
        mes_relatorio = st.selectbox(
            "Mês:",
            range(1, 13),
            index=datetime.now().month - 1,
            format_func=lambda x: MESES_PT[x]
        )
    with col2:
        ano_relatorio = st.selectbox(
            "Ano:",
            range(2020, 2031),
            index=range(2020, 2031).index(datetime.now().year)
        )
    
    transacoes = obter_transacoes(mes_relatorio, ano_relatorio)
    
    if not transacoes.empty:
        st.subheader("💳 Análise por Categoria")
        
        despesas = transacoes[transacoes['tipo'] == 'Despesa']
        receitas = transacoes[transacoes['tipo'] == 'Receita']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not despesas.empty:
                st.markdown("**📉 Despesas:**")
                despesas_cat = despesas.groupby('categoria')['valor'].sum().sort_values(ascending=False)
                for cat, valor in despesas_cat.items():
                    st.write(f"• {cat}: R$ {valor:.2f}")
            else:
                st.info("Nenhuma despesa no período")
        
        with col2:
            if not receitas.empty:
                st.markdown("**📈 Receitas:**")
                receitas_cat = receitas.groupby('categoria')['valor'].sum().sort_values(ascending=False)
                for cat, valor in receitas_cat.items():
                    st.write(f"• {cat}: R$ {valor:.2f}")
            else:
                st.info("Nenhuma receita no período")
        
        st.markdown("---")
        
        st.subheader("💾 Exportar Dados")
        
        csv = transacoes.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name=f"financas_{mes_relatorio}_{ano_relatorio}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("Nenhuma transação encontrada no período selecionado")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>💡 <b>Desenvolvido para aprendizado de Python</b></p>
        <p>Streamlit + Google Sheets + Plotly</p>
    </div>
    """,
    unsafe_allow_html=True
)
