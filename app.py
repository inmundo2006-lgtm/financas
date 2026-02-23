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
    excluir_transacao,
    excluir_grupo,
    marcar_como_pago,
    obter_saldo_acumulado,
    STATUS_PAGO, STATUS_PENDENTE, STATUS_ATRASADO,
    TIPO_NORMAL, TIPO_FIXA, TIPO_PARCELADA,
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

    resumo  = obter_resumo_mensal(mes_sel, ano_sel)
    pendente = obter_total_pendente_mes(mes_sel, ano_sel)

    saldo_mes = resumo["receitas"] - resumo["despesas"]

    if mes_sel == 1:
        saldo_inicial = obter_saldo_acumulado(12, ano_sel - 1)
    else:
        saldo_inicial = obter_saldo_acumulado(mes_sel - 1, ano_sel)

    saldo = saldo_inicial + saldo_mes

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💵 Receitas",     f"R$ {resumo['receitas']:,.2f}",
              help=f"Pagas: R$ {resumo.get('receitas_pagas', resumo['receitas']):,.2f}")
    c2.metric("💸 Despesas",     f"R$ {resumo['despesas']:,.2f}",
              help=f"Pagas: R$ {resumo.get('despesas_pagas', resumo['despesas']):,.2f}")
    c3.metric("💰 Saldo Projetado", f"R$ {saldo:,.2f}",
              delta=f"R$ {saldo_mes:,.2f}" if saldo_mes >= 0 else f"-R$ {abs(saldo_mes):,.2f}",
              delta_color="normal" if saldo_mes >= 0 else "inverse",
              help="Saldo acumulado (mês anterior + mês atual)")
    c4.metric("⏳ Pendente",     f"R$ {pendente:,.2f}")
    c5.metric("📝 Transações",   resumo["total_transacoes"])

    if saldo < 0:
        st.markdown('<div class="alerta-negativo">⚠️ Despesas acima das receitas!</div>',
                    unsafe_allow_html=True)

    vencer_7  = obter_a_vencer(7)
    vencer_30 = obter_a_vencer(30)

    if not vencer_7.empty:
        st.markdown("---")
        st.subheader("🚨 Vencem nos próximos 7 dias")
        for _, row in vencer_7.iterrows():
            dias_restantes = (pd.Timestamp(row["data_vencimento"]).date() - date.today()).days
            label = "hoje" if dias_restantes == 0 else f"em {dias_restantes} dia(s)"
            st.markdown(
                f'<div class="card-vencer">⚠️ <b>{row["descricao"]}</b> — '
                f'R$ {float(row["valor"]):,.2f} — vence <b>{label}</b> '
                f'({pd.Timestamp(row["data_vencimento"]).strftime("%d/%m/%Y")})</div>',
                unsafe_allow_html=True
            )
    elif not vencer_30.empty:
        st.markdown("---")
        st.info(f"📅 {len(vencer_30)} conta(s) vencem nos próximos 30 dias.")

    # ... (o restante do Dashboard continua igual ao seu código original) ...

# ════════════════════════════════════════════════════════════════════════════
# NOVA TRANSAÇÃO (avulsa)
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Nova Transação":
    # ... (mantido exatamente como você enviou) ...
    pass  # substitua pelo seu código completo dessa seção se precisar

# ════════════════════════════════════════════════════════════════════════════
# CONTAS FIXAS - versão atualizada com data inicial opcional
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Contas Fixas":
    st.header("🔄 Cadastrar Conta Fixa Recorrente")
    st.caption("Gera lançamentos mensais automáticos (água, energia, internet, etc.)")

    with st.form("form_fixa", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo_fixa = st.selectbox("Tipo:", ["Despesa", "Receita"])
            valor_fixa = st.number_input("Valor mensal (R$):", min_value=0.01,
                                         step=0.01, format="%.2f")
            dia_venc = st.number_input("Dia de vencimento:", min_value=1, max_value=31,
                                       value=10, step=1)
        with col2:
            cats_fixa = ["Contas", "Moradia", "Transporte", "Saúde",
                         "Educação", "Internet", "Telefone", "Outras Despesas"]
            cat_fixa = st.selectbox("Categoria:", cats_fixa)
            desc_fixa = st.text_input("Descrição:", placeholder="Ex: Conta de luz", max_chars=80)

            # Novo campo opcional
            data_primeira_input = st.date_input(
                "Data da primeira parcela (opcional)",
                value=None,
                min_value=date.today(),
                format="DD/MM/YYYY",
                help="Se preenchida, a série começa exatamente nessa data.\n"
                     "Deixe vazio para iniciar automaticamente no próximo vencimento futuro."
            )

            meses_fixa = st.slider("Gerar para quantos meses:", 1, 36, 12)

        submitted_fixa = st.form_submit_button("🔄 Gerar Lançamentos", use_container_width=True)

        if submitted_fixa:
            if not desc_fixa.strip():
                st.error("⚠️ Adicione uma descrição.")
            elif valor_fixa <= 0:
                st.error("⚠️ Valor precisa ser maior que R$ 0,00.")
            else:
                try:
                    data_primeira_str = data_primeira_input.strftime("%Y-%m-%d") if data_primeira_input else None

                    with st.spinner(f"Gerando {meses_fixa} lançamentos..."):
                        adicionar_conta_fixa(
                            tipo=tipo_fixa,
                            valor=valor_fixa,
                            categoria=cat_fixa,
                            descricao=desc_fixa.strip(),
                            dia_vencimento=int(dia_venc),
                            meses_a_adicionar=meses_fixa,
                            data_primeira=data_primeira_str
                        )
                    st.success(f"✅ {meses_fixa} lançamentos de **{desc_fixa}** gerados com sucesso!")
                    st.info("💡 Meses já vencidos foram marcados como **Pago** automaticamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao gerar: {str(e)}")

    # ── Preview das contas fixas já cadastradas ─────────────────────────────
    st.markdown("---")
    st.subheader("📋 Contas Fixas Cadastradas")
    df_todos = obter_todos_com_futuros()
    if not df_todos.empty:
        fixas = df_todos[df_todos["tipo_lancamento"] == TIPO_FIXA].copy()
        if not fixas.empty:
            fixas["data_vencimento"] = pd.to_datetime(fixas["data_vencimento"])
            resumo_fixas = (fixas.groupby(["id_grupo", "descricao", "categoria"])
                            .agg(total_parcelas_=("id", "count"),
                                 valor=("valor", "first"),
                                 pendentes=("status", lambda x: (x == STATUS_PENDENTE).sum()))
                            .reset_index())
            for _, row in resumo_fixas.iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{row['descricao']}** ({row['categoria']})")
                col2.write(f"R$ {row['valor']:,.2f}/mês")
                col3.write(f"⏳ {int(row['pendentes'])} pendentes")
        else:
            st.info("Nenhuma conta fixa cadastrada ainda.")
    else:
        st.info("Nenhuma conta fixa cadastrada ainda.")

# ════════════════════════════════════════════════════════════════════════════
# COMPRAS PARCELADAS (mantido como você enviou)
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Compras Parceladas":
    # ... (seu código completo dessa página permanece igual) ...
    pass  # substitua pelo seu bloco original se precisar de ajustes

# ════════════════════════════════════════════════════════════════════════════
# A VENCER, HISTÓRICO, RELATÓRIOS
# ════════════════════════════════════════════════════════════════════════════
# ... (mantenha exatamente como você enviou nessas seções) ...

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#8892a4;font-size:.85rem;'>"
    "💡 <b>Desenvolvido para aprendizado de Python</b> · Streamlit + Google Sheets + Plotly</div>",
    unsafe_allow_html=True
)