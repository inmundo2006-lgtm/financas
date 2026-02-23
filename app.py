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
    excluir_transacao,
    excluir_grupo,
    marcar_como_pago,
    obter_saldo_acumulado,   # 🔥 IMPORTANTE: saldo acumulado
    STATUS_PAGO, STATUS_PENDENTE, STATUS_ATRASADO,
    TIPO_NORMAL, TIPO_FIXA, TIPO_PARCELADA
)

# ── Meses ────────────────────────────────────────────────────────────────────
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Finanças Pessoais", page_icon="💰", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
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
        color: #ff4f6d;
        font-weight: 600;
        margin-top: .5rem;
    }
    .card-vencer {
        background: rgba(251,191,36,.08);
        border: 1px solid rgba(251,191,36,.3);
        border-radius: 10px;
        padding: .75rem 1rem;
        margin-bottom: .5rem;
    }
    .card-atrasado {
        background: rgba(255,79,109,.08);
        border: 1px solid rgba(255,79,109,.3);
        border-radius: 10px;
        padding: .75rem 1rem;
        margin-bottom: .5rem;
    }
    .badge-pago     { color: #00c896; font-weight: 700; }
    .badge-pendente { color: #fbbf24; font-weight: 700; }
    .badge-atrasado { color: #ff4f6d; font-weight: 700; }
    .badge-fixa     { color: #818cf8; font-weight: 600; font-size:.8rem; }
    .badge-parcela  { color: #38bdf8; font-weight: 600; font-size:.8rem; }
</style>
""", unsafe_allow_html=True)

# ── Init ─────────────────────────────────────────────────────────────────────
init_database()

st.title("💰 Gestão de Finanças Pessoais")
st.markdown("---")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📊 Menu")
    pagina = st.radio(
        "Navegação:",
        ["Dashboard", "Nova Transação", "Contas Fixas", "Compras Parceladas",
         "A Vencer", "Histórico", "Relatórios"]
    )
    st.markdown("---")
    st.info("💡 **Dica:** Use este app para controlar suas receitas e despesas!")


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
        if st.button("🔄 Atualizar", use_container_width=True, help="Força atualização dos dados"):
            from database import _ler_dataframe
            _ler_dataframe.clear()
            st.rerun()

    # 🔥 RESUMO DO MÊS
    resumo  = obter_resumo_mensal(mes_sel, ano_sel)
    pendente = obter_total_pendente_mes(mes_sel, ano_sel)

    # 🔥 SALDO INICIAL (acumulado até o mês anterior)
    if mes_sel == 1:
        saldo_inicial = obter_saldo_acumulado(12, ano_sel - 1)
    else:
        saldo_inicial = obter_saldo_acumulado(mes_sel - 1, ano_sel)

    # 🔥 SALDO DO MÊS
    saldo_mes = resumo["receitas"] - resumo["despesas"]

    # 🔥 SALDO FINAL ACUMULADO
    saldo_final = saldo_inicial + saldo_mes

    # ── Métricas ────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("💵 Receitas", f"R$ {resumo['receitas']:,.2f}",
              help=f"Pagas: R$ {resumo.get('receitas_pagas', resumo['receitas']):,.2f}")

    c2.metric("💸 Despesas", f"R$ {resumo['despesas']:,.2f}",
              help=f"Pagas: R$ {resumo.get('despesas_pagas', resumo['despesas']):,.2f}")

    c3.metric("📘 Saldo Inicial", f"R$ {saldo_inicial:,.2f}",
              help="Saldo acumulado até o mês anterior")

    c4.metric("💰 Saldo do Mês", f"R$ {saldo_mes:,.2f}",
              delta=f"R$ {saldo_mes:,.2f}" if saldo_mes >= 0 else f"-R$ {abs(saldo_mes):,.2f}",
              delta_color="normal" if saldo_mes >= 0 else "inverse")

    c5.metric("📗 Saldo Final (Acumulado)", f"R$ {saldo_final:,.2f}",
              help="Saldo inicial + saldo do mês")

    c6.metric("⏳ Pendente", f"R$ {pendente:,.2f}")
        # ── Marcar como pago em lote ─────────────────────────────────────────
        pendentes_df = transacoes[transacoes["status"].isin([STATUS_PENDENTE, STATUS_ATRASADO])]
        if not pendentes_df.empty:
            st.markdown("---")
            st.subheader("✅ Marcar como Pago")
            opcoes_pagar = {
                f"[{int(r['id'])}] {r['descricao']} — R$ {float(r['valor']):,.2f} "
                f"({pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')})": int(r["id"])
                for _, r in pendentes_df.iterrows()
            }
            sel_pagar = st.selectbox("Selecione:", list(opcoes_pagar.keys()))
            if st.button("✅ Marcar como Pago", use_container_width=True):
                marcar_como_pago(opcoes_pagar[sel_pagar])
                st.success("Marcado como pago!")
                st.rerun()

        # ── Excluir ──────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🗑️ Excluir Transação")
        opcoes = {
            f"[{int(r['ID'])}] {r['Data']} · {r['Tipo']} · {r['Categoria']} · "
            f"{r['Descrição']} · {r['Valor']}": int(r["ID"])
            for _, r in exibir.iterrows()
        }
        selecao = st.selectbox("Escolha a transação:", list(opcoes.keys()))
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
                st.warning(f"⚠️ Você está prestes a excluir: **{selecao}**")
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

        # ── Gráfico barras ────────────────────────────────────────────────────
        if not despesas.empty:
            st.subheader("📊 Despesas por Categoria")
            desp_cat = despesas.groupby("categoria")["valor"].sum().reset_index()
            fig_bar  = px.bar(desp_cat.sort_values("valor", ascending=True),
                              x="valor", y="categoria", orientation="h",
                              title="Despesas por Categoria",
                              color="valor",
                              color_continuous_scale=["#ff4f6d", "#ffb347"],
                              labels={"valor": "Total (R$)", "categoria": ""})
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#e2e8f0",
                                  xaxis=dict(gridcolor="#2a2d3a"),
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # ── Breakdown por status ──────────────────────────────────────────────
        st.subheader("📋 Resumo por Status")
        c1, c2, c3 = st.columns(3)
        pagas     = transacoes[transacoes["status"] == STATUS_PAGO]["valor"].sum()
        pendentes = transacoes[transacoes["status"] == STATUS_PENDENTE]["valor"].sum()
        atrasadas = transacoes[transacoes["status"] == STATUS_ATRASADO]["valor"].sum()
        c1.metric("✅ Pagas",    f"R$ {float(pagas):,.2f}")
        c2.metric("⏳ Pendentes", f"R$ {float(pendentes):,.2f}")
        c3.metric("🔴 Atrasadas", f"R$ {float(atrasadas):,.2f}")

        st.markdown("---")

        # ── Análise por categoria ─────────────────────────────────────────────
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

        # ── Exportar ──────────────────────────────────────────────────────────
        st.subheader("💾 Exportar Dados")
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


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#8892a4;font-size:.85rem;'>"
    "💡 <b>Desenvolvido para aprendizado de Python</b> &nbsp;·&nbsp;"
    "Streamlit + Google Sheets + Plotly</div>",
    unsafe_allow_html=True
)

