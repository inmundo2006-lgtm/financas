"""
Aplicativo de Gestão de Finanças Pessoais
Desenvolvido com Streamlit para aprendizado de Python
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from database import (
    init_database,
    adicionar_transacao,
    adicionar_conta_fixa,
    adicionar_compra_parcelada,
    obter_transacoes,
    obter_todos_com_futuros,
    obter_a_vencer,
    obter_total_pendente_mes,
    obter_resumo_mensal,
    obter_gastos_por_categoria,
    obter_saldo_acumulado,
    obter_saldo_anterior,
    obter_disponivel_gastar,
    excluir_transacao,
    excluir_grupo,
    marcar_como_pago,
    STATUS_PAGO, STATUS_PENDENTE, STATUS_ATRASADO,
    TIPO_NORMAL, TIPO_FIXA, TIPO_PARCELADA
)

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

st.set_page_config(page_title="Finanças Pessoais", page_icon="💰", layout="wide")

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        transition: transform .15s, box-shadow .15s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,.4);
    }
    .alerta-negativo {
        background: rgba(255,79,109,.1);
        border-left: 3px solid #ff4f6d;
        padding: .6rem 1rem;
        border-radius: 0 8px 8px 0;
        color: #ff4f6d; font-weight: 600; margin-top: .5rem;
    }
    .card-vencer {
        background: rgba(251,191,36,.08);
        border: 1px solid rgba(251,191,36,.3);
        border-radius: 10px; padding: .75rem 1rem; margin-bottom: .5rem;
    }
    .card-atrasado {
        background: rgba(255,79,109,.08);
        border: 1px solid rgba(255,79,109,.3);
        border-radius: 10px; padding: .75rem 1rem; margin-bottom: .5rem;
    }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════════════════
def _verificar_credenciais(usuario: str, senha: str) -> bool:
    try:
        u = st.secrets["login"]["usuario"]
        s = st.secrets["login"]["senha"]
        return usuario.strip() == u and senha == s
    except KeyError:
        # Se ainda não configurou o secrets, aceita credenciais padrão
        return usuario.strip() == "admin" and senha == "admin123"


def _tela_login():
    col_esq, col_centro, col_dir = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align:center; margin-bottom: 1.5rem;">
                <div style="font-size:3rem;">💰</div>
                <h2 style="margin:0; color:#e2e8f0;">Finanças Pessoais</h2>
                <p style="color:#8892a4; margin-top:.25rem;">Faça login para continuar</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("form_login"):
            usuario = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
            senha   = st.text_input("🔒 Senha:", type="password", placeholder="Digite sua senha")
            entrar  = st.form_submit_button("Entrar →", use_container_width=True, type="primary")

            if entrar:
                if _verificar_credenciais(usuario, senha):
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")

        st.markdown(
            "<p style='text-align:center; color:#4a5568; font-size:.8rem; margin-top:1rem;'>"
            "🔐 Acesso restrito ao proprietário</p>",
            unsafe_allow_html=True
        )


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    _tela_login()
    st.stop()


# ── A partir daqui só chega quem está logado ────────────────────────────────
init_database()

st.title("💰 Gestão de Finanças Pessoais")
st.markdown("---")

with st.sidebar:
    st.header("📊 Menu")
    pagina = st.radio("Navegação:", [
        "Dashboard", "Nova Transação", "Contas Fixas",
        "Compras Parceladas", "A Vencer", "Histórico", "Relatórios"
    ])
    st.markdown("---")
    st.info("💡 **Dica:** Use este app para controlar suas receitas e despesas!")
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
if pagina == "Dashboard":
    st.header("📈 Dashboard Financeiro")

    col1, col2, col3 = st.columns([3, 3, 1])
    with col1:
        mes_sel = st.selectbox("Mês:", range(1, 13),
                               index=datetime.now().month - 1,
                               format_func=lambda x: MESES_PT[x])
    with col2:
        ano_sel = st.selectbox("Ano:", range(2020, 2031),
                               index=list(range(2020, 2031)).index(datetime.now().year))
    with col3:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar", use_container_width=True):
            from database import _ler_dataframe
            _ler_dataframe.clear()
            st.rerun()

    resumo         = obter_resumo_mensal(mes_sel, ano_sel)
    pendente       = obter_total_pendente_mes(mes_sel, ano_sel)
    saldo_anterior = obter_saldo_anterior(mes_sel, ano_sel)
    saldo_mes      = resumo["receitas"] - resumo["despesas"]
    saldo_final    = saldo_anterior + saldo_mes

    # Linha 1: saldo anterior + métricas do mês
    if saldo_anterior != 0:
        cor_ant = "normal" if saldo_anterior >= 0 else "inverse"
        st.info(
            f"💼 **Saldo transportado do período anterior:** "
            f"R$ {saldo_anterior:,.2f}"
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💵 Receitas", f"R$ {resumo['receitas']:,.2f}",
              help=f"Pagas: R$ {resumo.get('receitas_pagas', 0):,.2f}")
    c2.metric("💸 Despesas", f"R$ {resumo['despesas']:,.2f}",
              help=f"Pagas: R$ {resumo.get('despesas_pagas', 0):,.2f}")
    c3.metric("💰 Saldo do Mês", f"R$ {saldo_mes:,.2f}",
              delta=f"R$ {saldo_mes:,.2f}" if saldo_mes >= 0 else f"-R$ {abs(saldo_mes):,.2f}",
              delta_color="normal" if saldo_mes >= 0 else "inverse",
              help="Receitas − Despesas do mês (inclui pendentes)")
    c4.metric("🏦 Saldo Acumulado", f"R$ {saldo_final:,.2f}",
              delta=f"R$ {saldo_final:,.2f}" if saldo_final >= 0 else f"-R$ {abs(saldo_final):,.2f}",
              delta_color="normal" if saldo_final >= 0 else "inverse",
              help="Saldo anterior + saldo do mês atual")
    c5.metric("⏳ Pendente",   f"R$ {pendente:,.2f}")

    if saldo_mes < 0:
        st.markdown('<div class="alerta-negativo">⚠️ Despesas acima das receitas!</div>',
                    unsafe_allow_html=True)

    # ── Card "Quanto posso gastar hoje?" ────────────────────────────────────
    disponivel, saldo_atual, compromissos = obter_disponivel_gastar(mes_sel, ano_sel)
    if disponivel >= 0:
        cor   = "#00c896"
        emoji = "✅"
        msg   = f"Você pode gastar até **R$ {disponivel:,.2f}** hoje sem comprometer as contas de {MESES_PT[mes_sel]}."
    else:
        cor   = "#ff4f6d"
        emoji = "⚠️"
        msg   = f"As contas de {MESES_PT[mes_sel]} superam seu saldo atual em **R$ {abs(disponivel):,.2f}**. Cuidado com novos gastos!"

    st.markdown(
        f"""
        <div style="background:{'rgba(0,200,150,.08)' if disponivel >= 0 else 'rgba(255,79,109,.08)'};
                    border:1px solid {cor};
                    border-radius:12px;
                    padding:1rem 1.5rem;
                    margin-top:.75rem;">
            <div style="font-size:1.1rem;font-weight:700;color:{cor};">
                {emoji} Quanto posso gastar hoje?
            </div>
            <div style="font-size:2rem;font-weight:800;color:{cor};margin:.25rem 0;">
                R$ {disponivel:,.2f}
            </div>
            <div style="color:#8892a4;font-size:.85rem;">{msg}</div>
            <div style="color:#8892a4;font-size:.8rem;margin-top:.5rem;">
                💰 Saldo atual (pago): R$ {saldo_atual:,.2f} &nbsp;|&nbsp;
                📋 Compromissos pendentes: R$ {compromissos:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Alertas de vencimento
    vencer_7  = obter_a_vencer(7)
    vencer_30 = obter_a_vencer(30)

    if not vencer_7.empty:
        st.markdown("---")
        st.subheader("🚨 Vencem nos próximos 7 dias")
        for _, row in vencer_7.iterrows():
            dias = (pd.Timestamp(row["data_vencimento"]).date() - date.today()).days
            label = "hoje" if dias == 0 else f"em {dias} dia(s)"
            st.markdown(
                f'<div class="card-vencer">⚠️ <b>{row["descricao"]}</b> — '
                f'R$ {float(row["valor"]):,.2f} — vence <b>{label}</b> '
                f'({pd.Timestamp(row["data_vencimento"]).strftime("%d/%m/%Y")})</div>',
                unsafe_allow_html=True)
    elif not vencer_30.empty:
        st.markdown("---")
        st.info(f"📅 {len(vencer_30)} conta(s) vencem nos próximos 30 dias.")

    st.markdown("---")

    if resumo["total_transacoes"] > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Despesas por Categoria")
            gastos = obter_gastos_por_categoria(mes_sel, ano_sel)
            if not gastos.empty:
                fig = px.pie(gastos, values="total", names="categoria",
                             title="Distribuição de Despesas", hole=0.45,
                             color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#e2e8f0", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma despesa paga neste período")

        with col2:
            st.subheader("📈 Evolução Diária Acumulada")
            transacoes = obter_transacoes(mes_sel, ano_sel)
            if not transacoes.empty:
                pagas = transacoes[transacoes["status"] == STATUS_PAGO].copy()
                pagas["dia"] = pagas["data_vencimento"].fillna(pagas["data"]).dt.day
                max_dia = int(pagas["dia"].max()) if not pagas.empty else 1

                rec_dia = (pagas[pagas["tipo"] == "Receita"]
                           .groupby("dia")["valor"].sum()
                           .reindex(range(1, max_dia + 1), fill_value=0)
                           .cumsum().reset_index().rename(columns={"valor": "Receitas"}))
                desp_dia = (pagas[pagas["tipo"] == "Despesa"]
                            .groupby("dia")["valor"].sum()
                            .reindex(range(1, max_dia + 1), fill_value=0)
                            .cumsum().reset_index().rename(columns={"valor": "Despesas"}))
                ev = rec_dia.merge(desp_dia, on="dia")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ev["dia"], y=ev["Receitas"],
                                         mode="lines+markers", name="Receitas",
                                         line=dict(color="#00c896", width=2.5),
                                         fill="tozeroy", fillcolor="rgba(0,200,150,.08)"))
                fig.add_trace(go.Scatter(x=ev["dia"], y=ev["Despesas"],
                                         mode="lines+markers", name="Despesas",
                                         line=dict(color="#ff4f6d", width=2.5),
                                         fill="tozeroy", fillcolor="rgba(255,79,109,.08)"))
                fig.update_layout(title="Acumulado no Mês", xaxis_title="Dia",
                                  yaxis_title="Valor (R$)", hovermode="x unified",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#e2e8f0",
                                  xaxis=dict(gridcolor="#2a2d3a"),
                                  yaxis=dict(gridcolor="#2a2d3a"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma transação paga neste período")
    else:
        st.info("🚀 Nenhuma transação ainda. Comece adicionando uma nova transação!")


# ════════════════════════════════════════════════════════════════════════════
# NOVA TRANSAÇÃO
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Nova Transação":
    st.header("➕ Adicionar Transação Avulsa")
    st.caption("Para contas fixas mensais ou compras parceladas, use os menus específicos.")

    tipo = st.selectbox("Tipo:", ["Receita", "Despesa"])
    categorias = (["Salário", "Freelance", "Investimentos", "Presente", "Outras Receitas"]
                  if tipo == "Receita"
                  else ["Alimentação", "Transporte", "Moradia", "Saúde", "Educação",
                        "Lazer", "Compras", "Contas", "Outras Despesas"])

    st.markdown("---")

    with st.form("form_avulso", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            valor     = st.number_input("Valor (R$):", min_value=0.01, step=0.01, format="%.2f")
            data      = st.date_input("Data do lançamento:", value=datetime.now(), format="DD/MM/YYYY")
        with col2:
            categoria = st.selectbox("Categoria:", categorias)
            descricao = st.text_input("Descrição:", placeholder="Ex: Supermercado...", max_chars=100)
            status    = st.selectbox("Status:", [STATUS_PAGO, STATUS_PENDENTE])

        col3, col4 = st.columns(2)
        with col3:
            usa_vencimento = st.checkbox("Informar data de vencimento", value=True,
                                         help="Marque para registrar a data em que a compra vencerá (ex: fatura do cartão)")
        with col4:
            data_venc = None
            if usa_vencimento:
                data_venc = st.date_input("Data de vencimento:", value=datetime.now(), format="DD/MM/YYYY")

        submitted = st.form_submit_button("💾 Salvar", use_container_width=True)
        if submitted:
            erros = []
            if not descricao.strip():
                erros.append("Adicione uma descrição.")
            if valor <= 0:
                erros.append("Valor precisa ser maior que R$ 0,00.")
            if erros:
                for e in erros:
                    st.error(f"⚠️ {e}")
            else:
                try:
                    adicionar_transacao(
                        tipo=tipo, valor=valor, categoria=categoria,
                        descricao=descricao.strip(), data=str(data),
                        status=status,
                        data_vencimento=str(data_venc) if data_venc else None
                    )
                    st.success(f"✅ {tipo} de **R$ {valor:,.2f}** salva com sucesso!")
                    if tipo == "Receita":
                        st.balloons()
                    else:
                        st.snow()
                except Exception as e:
                    st.error(f"❌ Erro: {type(e).__name__}")
                    st.code(str(e))


# ════════════════════════════════════════════════════════════════════════════
# CONTAS FIXAS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Contas Fixas":
    st.header("🔄 Cadastrar Conta Fixa Recorrente")
    st.caption("Gera lançamentos mensais automáticos para despesas (água, energia, internet) ou receitas (salário, aluguel recebido, etc.)")

    # Tipo FORA do form para atualizar categorias dinamicamente
    tipo_fixa = st.selectbox("Tipo:", ["Despesa", "Receita"], key="tipo_fixa_sel")
    cats_despesa = ["Contas", "Moradia", "Transporte", "Saúde", "Educação", "Internet", "Telefone", "Outras Despesas"]
    cats_receita = ["Salário", "Freelance", "Aluguel Recebido", "Pensão Recebida", "Investimentos", "Outras Receitas"]
    cats_fixa = cats_receita if tipo_fixa == "Receita" else cats_despesa

    placeholder_desc = "Ex: Salário empresa X" if tipo_fixa == "Receita" else "Ex: Conta de luz"

    with st.form("form_fixa", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            valor_fixa = st.number_input("Valor mensal (R$):", min_value=0.01, step=0.01, format="%.2f")
            dia_venc   = st.number_input("Dia de vencimento:", min_value=1, max_value=31, value=10, step=1)
        with col2:
            cat_fixa   = st.selectbox("Categoria:", cats_fixa)
            desc_fixa  = st.text_input("Descrição:", placeholder=placeholder_desc, max_chars=80)
            meses_fixa = st.slider("Gerar para quantos meses:", 1, 36, 12)
            data_primeira_input = st.date_input("Início (opcional, deixe vazio para mês atual):",
                                                value=None, format="DD/MM/YYYY")

        submitted_fixa = st.form_submit_button("🔄 Gerar Lançamentos", use_container_width=True)
        if submitted_fixa:
            if not desc_fixa.strip():
                st.error("⚠️ Adicione uma descrição.")
            elif valor_fixa <= 0:
                st.error("⚠️ Valor precisa ser maior que R$ 0,00.")
            else:
                try:
                    with st.spinner(f"Gerando {meses_fixa} lançamentos..."):
                        adicionar_conta_fixa(
                            tipo=tipo_fixa, valor=valor_fixa,
                            categoria=cat_fixa, descricao=desc_fixa.strip(),
                            dia_vencimento=int(dia_venc),
                            meses_a_adicionar=meses_fixa,
                            data_primeira=str(data_primeira_input) if data_primeira_input else None
                        )
                    st.success(f"✅ {meses_fixa} lançamentos de **{desc_fixa}** gerados!")
                    st.info("💡 Meses já vencidos foram marcados como Pago automaticamente.")
                except Exception as e:
                    st.error(f"❌ Erro: {type(e).__name__}")
                    st.code(str(e))

    st.markdown("---")
    st.subheader("📋 Contas Fixas Cadastradas")
    df_todos = obter_todos_com_futuros()
    if not df_todos.empty:
        fixas = df_todos[df_todos["tipo_lancamento"] == TIPO_FIXA].copy()
        if not fixas.empty:
            resumo_fixas = (fixas.groupby(["id_grupo", "descricao", "categoria"])
                            .agg(total_=("id", "count"),
                                 valor=("valor", "first"),
                                 pendentes=("status", lambda x: (x == STATUS_PENDENTE).sum()))
                            .reset_index())
            for _, row in resumo_fixas.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{row['descricao']}** ({row['categoria']})")
                c2.write(f"R$ {float(row['valor']):,.2f}/mês")
                c3.write(f"⏳ {int(row['pendentes'])} pendentes")
        else:
            st.info("Nenhuma conta fixa cadastrada ainda.")
    else:
        st.info("Nenhuma conta fixa cadastrada ainda.")


# ════════════════════════════════════════════════════════════════════════════
# COMPRAS PARCELADAS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Compras Parceladas":
    st.header("💳 Registrar Compra Parcelada")
    st.caption("Divide o valor total em parcelas mensais automaticamente.")

    with st.form("form_parcela", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo_parc   = st.selectbox("Tipo:", ["Despesa", "Receita"])
            valor_total = st.number_input("Valor total (R$):", min_value=0.01, step=0.01, format="%.2f")
            n_parcelas  = st.number_input("Número de parcelas:", min_value=2, max_value=60, value=12, step=1)
        with col2:
            cat_parc     = st.selectbox("Categoria:", ["Compras", "Eletrônicos", "Móveis",
                                                        "Viagem", "Saúde", "Educação", "Outras Despesas"])
            desc_parc    = st.text_input("Descrição:", placeholder="Ex: Notebook Samsung", max_chars=80)
            primeira_venc = st.date_input("Vencimento da 1ª parcela:", value=datetime.now(), format="DD/MM/YYYY")

        valor_parcela = valor_total / n_parcelas if n_parcelas > 0 else 0
        st.info(f"💡 Cada parcela: **R$ {valor_parcela:,.2f}**")

        submitted_parc = st.form_submit_button("💳 Gerar Parcelas", use_container_width=True)
        if submitted_parc:
            if not desc_parc.strip():
                st.error("⚠️ Adicione uma descrição.")
            elif valor_total <= 0:
                st.error("⚠️ Valor precisa ser maior que R$ 0,00.")
            else:
                try:
                    with st.spinner(f"Gerando {n_parcelas} parcelas..."):
                        adicionar_compra_parcelada(
                            tipo=tipo_parc, valor_total=valor_total,
                            categoria=cat_parc, descricao=desc_parc.strip(),
                            n_parcelas=int(n_parcelas), data_primeira=primeira_venc
                        )
                    st.success(f"✅ {n_parcelas}x de R$ {valor_parcela:,.2f} geradas para **{desc_parc}**!")
                except Exception as e:
                    st.error(f"❌ Erro: {type(e).__name__}")
                    st.code(str(e))

    st.markdown("---")
    st.subheader("📋 Compras Parceladas em Aberto")
    df_todos = obter_todos_com_futuros()
    if not df_todos.empty:
        parc = df_todos[(df_todos["tipo_lancamento"] == TIPO_PARCELADA) &
                        (df_todos["status"] != STATUS_PAGO)].copy()
        if not parc.empty:
            grupos = parc.groupby("id_grupo")
            for gid, grupo in grupos:
                desc  = grupo["descricao"].iloc[0].rsplit(" (", 1)[0]
                total = grupo["total_parcelas"].iloc[0]
                pend  = len(grupo)
                prox  = grupo["data_vencimento"].min().strftime("%d/%m/%Y")
                val   = grupo["valor"].iloc[0]
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"**{desc}** ({grupo['categoria'].iloc[0]})")
                c2.write(f"R$ {float(val):,.2f}/parc.")
                c3.write(f"⏳ {pend}/{int(total)} restantes")
                c4.write(f"📅 próx. {prox}")
        else:
            st.info("Nenhuma parcela em aberto.")
    else:
        st.info("Nenhuma compra parcelada cadastrada ainda.")


# ════════════════════════════════════════════════════════════════════════════
# A VENCER
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "A Vencer":
    st.header("⏳ Contas a Vencer")

    col1, col2 = st.columns(2)
    with col1:
        dias_filtro = st.selectbox("Mostrar contas para:", [7, 15, 30, 60, 90],
                                   index=2, format_func=lambda x: f"próximos {x} dias")
    with col2:
        tipo_filtro = st.selectbox("Tipo:", ["Todos", "Despesa", "Receita"])

    df_vencer = obter_a_vencer(dias_filtro)
    df_todos  = obter_todos_com_futuros()
    atrasados = pd.DataFrame()

    if not df_todos.empty:
        atrasados = df_todos[df_todos["status"] == STATUS_ATRASADO].copy()

    if tipo_filtro != "Todos":
        df_vencer = df_vencer[df_vencer["tipo"] == tipo_filtro]
        if not atrasados.empty:
            atrasados = atrasados[atrasados["tipo"] == tipo_filtro]

    if not atrasados.empty:
        st.subheader("🚨 Em Atraso")
        st.error(f"Total em atraso: **R$ {float(atrasados['valor'].sum()):,.2f}**")
        for _, row in atrasados.iterrows():
            dias_atr = (date.today() - pd.Timestamp(row["data_vencimento"]).date()).days
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.markdown(
                f'<div class="card-atrasado">🔴 <b>{row["descricao"]}</b> — '
                f'{row["categoria"]} — venceu há {dias_atr} dia(s) '
                f'({pd.Timestamp(row["data_vencimento"]).strftime("%d/%m/%Y")})</div>',
                unsafe_allow_html=True)
            c2.metric("Valor", f"R$ {float(row['valor']):,.2f}")
            with c3:
                if st.button("✅ Pagar", key=f"pagar_atr_{row['id']}"):
                    marcar_como_pago(int(row["id"]))
                    st.success("Marcado como pago!")
                    st.rerun()
                if st.button("✏️ Editar", key=f"editar_atr_{row['id']}"):
                    st.session_state[f"editando_{row['id']}"] = True
            if st.session_state.get(f"editando_{row['id']}"):
                novo = st.number_input(f"Novo valor para {row['descricao']}:", 
                                        value=float(row['valor']), step=0.01, format="%.2f",
                                        key=f"nv_atr_{row['id']}")
                if st.button("✅ Confirmar", key=f"conf_atr_{row['id']}"):
                    marcar_como_pago(int(row["id"]), novo_valor=novo)
                    st.session_state.pop(f"editando_{row['id']}", None)
                    st.success(f"Pago com valor atualizado: R$ {novo:,.2f}")
                    st.rerun()

    if not df_vencer.empty:
        st.subheader(f"📅 Próximos {dias_filtro} dias")
        st.warning(f"Total a vencer: **R$ {float(df_vencer['valor'].sum()):,.2f}**")
        for _, row in df_vencer.iterrows():
            dias_rest = (pd.Timestamp(row["data_vencimento"]).date() - date.today()).days
            label = "Vence hoje!" if dias_rest == 0 else f"em {dias_rest} dia(s)"
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.markdown(
                f'<div class="card-vencer">🟡 <b>{row["descricao"]}</b> — '
                f'{row["categoria"]} — vence {label} '
                f'({pd.Timestamp(row["data_vencimento"]).strftime("%d/%m/%Y")})</div>',
                unsafe_allow_html=True)
            c2.metric("Valor", f"R$ {float(row['valor']):,.2f}")
            with c3:
                if st.button("✅ Pagar", key=f"pagar_{row['id']}"):
                    marcar_como_pago(int(row["id"]))
                    st.success("Marcado como pago!")
                    st.rerun()
                if st.button("✏️ Editar", key=f"editar_{row['id']}"):
                    st.session_state[f"editando_{row['id']}"] = True
            if st.session_state.get(f"editando_{row['id']}"):
                novo = st.number_input(f"Novo valor para {row['descricao']}:", 
                                        value=float(row['valor']), step=0.01, format="%.2f",
                                        key=f"nv_{row['id']}")
                if st.button("✅ Confirmar", key=f"conf_{row['id']}"):
                    marcar_como_pago(int(row["id"]), novo_valor=novo)
                    st.session_state.pop(f"editando_{row['id']}", None)
                    st.success(f"Pago com valor atualizado: R$ {novo:,.2f}")
                    st.rerun()

    if df_vencer.empty and atrasados.empty:
        st.success("🎉 Nenhuma conta pendente ou em atraso!")


# ════════════════════════════════════════════════════════════════════════════
# HISTÓRICO
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Histórico":
    st.header("📜 Histórico de Transações")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        mes_filtro = st.selectbox("Mês:", ["Todos"] + list(range(1, 13)),
                                   format_func=lambda x: "Todos" if x == "Todos" else MESES_PT[x])
    with col2:
        ano_filtro = st.selectbox("Ano:", ["Todos"] + list(range(2020, 2031)),
                                   format_func=lambda x: "Todos" if x == "Todos" else str(x))
    with col3:
        tipo_filtro = st.selectbox("Tipo:", ["Todos", "Receita", "Despesa"])
    with col4:
        status_filtro = st.selectbox("Status:", ["Todos", STATUS_PAGO, STATUS_PENDENTE, STATUS_ATRASADO])

    mostrar_futuros = st.checkbox("Incluir lançamentos futuros", value=True)

    mes = None if mes_filtro == "Todos" else mes_filtro
    ano = None if ano_filtro == "Todos" else ano_filtro

    transacoes = (obter_todos_com_futuros(mes, ano) if mostrar_futuros
                  else obter_transacoes(mes, ano))

    if tipo_filtro != "Todos":
        transacoes = transacoes[transacoes["tipo"] == tipo_filtro]
    if status_filtro != "Todos":
        transacoes = transacoes[transacoes["status"] == status_filtro]

    if not transacoes.empty:
        total_rec  = transacoes[transacoes["tipo"] == "Receita"]["valor"].sum()
        total_desp = transacoes[transacoes["tipo"] == "Despesa"]["valor"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Registros", len(transacoes))
        c2.metric("💵 Receitas",  f"R$ {float(total_rec):,.2f}")
        c3.metric("💸 Despesas",  f"R$ {float(total_desp):,.2f}")

        st.markdown("---")

        exibir = transacoes.copy()
        exibir["Data Venc."] = pd.to_datetime(exibir["data_vencimento"], errors="coerce").dt.strftime("%d/%m/%Y")
        exibir["Data"]       = pd.to_datetime(exibir["data"], errors="coerce").dt.strftime("%d/%m/%Y")
        exibir["Valor"]      = exibir["valor"].apply(lambda x: f"R$ {float(x):,.2f}")

        def fmt_status(s):
            if s == STATUS_PAGO:     return "✅ Pago"
            if s == STATUS_PENDENTE: return "⏳ Pendente"
            if s == STATUS_ATRASADO: return "🔴 Atrasado"
            return s

        exibir["Status"]     = exibir["status"].apply(fmt_status)
        exibir["Modalidade"] = exibir["tipo_lancamento"]
        exibir = exibir[["id", "Data", "Data Venc.", "tipo", "categoria",
                          "descricao", "Valor", "Status", "Modalidade"]]
        exibir.columns = ["ID", "Data", "Vencimento", "Tipo", "Categoria",
                          "Descrição", "Valor", "Status", "Modalidade"]

        st.dataframe(exibir, use_container_width=True, hide_index=True)

        # Marcar como pago (com edição de valor)
        pendentes_df = transacoes[transacoes["status"].isin([STATUS_PENDENTE, STATUS_ATRASADO])]
        if not pendentes_df.empty:
            st.markdown("---")
            st.subheader("✅ Confirmar Pagamento / Recebimento")
            st.caption("Você pode ajustar o valor antes de confirmar — útil para contas que variam (energia, água) ou salário com reajuste.")

            opcoes_pagar = {
                f"[{int(r['id'])}] {r['descricao']} — R$ {float(r['valor']):,.2f} "
                f"({pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')})": r
                for _, r in pendentes_df.iterrows()
            }
            sel_label = st.selectbox("Selecione:", list(opcoes_pagar.keys()))
            row_sel   = opcoes_pagar[sel_label]
            valor_orig = float(row_sel["valor"])

            col_val, col_btn = st.columns([2, 1])
            with col_val:
                valor_confirmado = st.number_input(
                    "Valor a confirmar (R$):",
                    min_value=0.01,
                    value=valor_orig,
                    step=0.01,
                    format="%.2f",
                    help="Altere se o valor real foi diferente do previsto"
                )
                if abs(valor_confirmado - valor_orig) > 0.001:
                    st.info(f"💡 Diferença: R$ {valor_confirmado - valor_orig:+,.2f} em relação ao valor lançado.")
            with col_btn:
                st.write("")
                st.write("")
                tipo_acao = "Recebimento" if row_sel["tipo"] == "Receita" else "Pagamento"
                if st.button(f"✅ Confirmar {tipo_acao}", use_container_width=True, type="primary"):
                    novo_val = valor_confirmado if abs(valor_confirmado - valor_orig) > 0.001 else None
                    marcar_como_pago(int(row_sel["id"]), novo_valor=novo_val)
                    if novo_val:
                        st.success(f"✅ Confirmado com valor atualizado: R$ {valor_confirmado:,.2f}")
                    else:
                        st.success(f"✅ {tipo_acao} confirmado: R$ {valor_orig:,.2f}")
                    st.rerun()

        # Excluir
        st.markdown("---")
        st.subheader("🗑️ Excluir Transação")
        opcoes = {
            f"[{int(r['ID'])}] {r['Data']} · {r['Tipo']} · {r['Categoria']} · "
            f"{r['Descrição']} · {r['Valor']}": int(r["ID"])
            for _, r in exibir.iterrows()
        }
        selecao   = st.selectbox("Escolha a transação:", list(opcoes.keys()))
        col_btn, col_av = st.columns([1, 3])
        with col_btn:
            confirmar = st.checkbox("✅ Confirmar exclusão")
            if st.button("🗑️ Excluir", use_container_width=True,
                         type="primary", disabled=not confirmar):
                with st.spinner("Excluindo..."):
                    if excluir_transacao(opcoes[selecao]):
                        st.success("Excluída com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir.")
        with col_av:
            if confirmar:
                st.warning(f"⚠️ Prestes a excluir: **{selecao}**")
    else:
        st.warning("Nenhuma transação encontrada.")


# ════════════════════════════════════════════════════════════════════════════
# RELATÓRIOS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Relatórios":
    st.header("📊 Relatórios Detalhados")

    col1, col2 = st.columns(2)
    with col1:
        mes_rel = st.selectbox("Mês:", range(1, 13),
                               index=datetime.now().month - 1,
                               format_func=lambda x: MESES_PT[x])
    with col2:
        ano_rel = st.selectbox("Ano:", range(2020, 2031),
                               index=list(range(2020, 2031)).index(datetime.now().year))

    transacoes = obter_todos_com_futuros(mes_rel, ano_rel)

    if not transacoes.empty:
        despesas = transacoes[transacoes["tipo"] == "Despesa"]
        receitas = transacoes[transacoes["tipo"] == "Receita"]

        if not despesas.empty:
            st.subheader("📊 Despesas por Categoria")
            desp_cat = despesas.groupby("categoria")["valor"].sum().reset_index()
            fig_bar  = px.bar(desp_cat.sort_values("valor", ascending=True),
                              x="valor", y="categoria", orientation="h",
                              title="Despesas por Categoria", color="valor",
                              color_continuous_scale=["#ff4f6d", "#ffb347"],
                              labels={"valor": "Total (R$)", "categoria": ""})
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#e2e8f0",
                                  xaxis=dict(gridcolor="#2a2d3a"),
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        st.subheader("📋 Resumo por Status")
        c1, c2, c3 = st.columns(3)
        pagas     = transacoes[transacoes["status"] == STATUS_PAGO]["valor"].sum()
        pendentes = transacoes[transacoes["status"] == STATUS_PENDENTE]["valor"].sum()
        atrasadas = transacoes[transacoes["status"] == STATUS_ATRASADO]["valor"].sum()
        c1.metric("✅ Pagas",     f"R$ {float(pagas):,.2f}")
        c2.metric("⏳ Pendentes", f"R$ {float(pendentes):,.2f}")
        c3.metric("🔴 Atrasadas", f"R$ {float(atrasadas):,.2f}")

        st.markdown("---")

        st.subheader("💳 Análise por Categoria")
        col1, col2 = st.columns(2)
        with col1:
            if not despesas.empty:
                st.markdown("**📉 Despesas:**")
                desp_c = despesas.groupby("categoria")["valor"].sum().sort_values(ascending=False)
                tot    = desp_c.sum()
                for cat, val in desp_c.items():
                    pct = val / tot * 100
                    st.write(f"• **{cat}**: R$ {float(val):,.2f} ({pct:.1f}%)")
                    st.progress(pct / 100)
            else:
                st.info("Nenhuma despesa no período")
        with col2:
            if not receitas.empty:
                st.markdown("**📈 Receitas:**")
                rec_c = receitas.groupby("categoria")["valor"].sum().sort_values(ascending=False)
                tot   = rec_c.sum()
                for cat, val in rec_c.items():
                    pct = val / tot * 100
                    st.write(f"• **{cat}**: R$ {float(val):,.2f} ({pct:.1f}%)")
                    st.progress(pct / 100)
            else:
                st.info("Nenhuma receita no período")

        st.markdown("---")
        csv = transacoes.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name=f"financas_{MESES_PT[mes_rel]}_{ano_rel}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("Nenhuma transação encontrada no período.")


st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#8892a4;font-size:.85rem;'>"
    "💡 <b>Desenvolvido para aprendizado de Python</b> &nbsp;·&nbsp;"
    "Streamlit + Google Sheets + Plotly</div>",
    unsafe_allow_html=True
)
