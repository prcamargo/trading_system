import streamlit as st
import sqlite3
import pandas as pd

# Função para obter as ordens do banco de dados
def get_orders_from_db():
    conn = sqlite3.connect('trading_bot.db')
    query = "SELECT * FROM orders"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def dash():
    # Layout do dashboard
    st.title("Dashboard Bot Trader")

    st.header("Ordens Executadas")
    orders_df = get_orders_from_db()
    st.dataframe(orders_df)

    st.header("Situação da Carteira")
    # Substituir com dados reais do bot
    st.write("Saldo BTC: 0.0005")
    st.write("Saldo USDT: 50")

    # Cálculo de lucro ou prejuízo
    st.header("Resumo de Performance")
    lucro_total = orders_df["total_value"].sum()  # Aqui pode-se ajustar para calcular o lucro real
    st.metric("Lucro Total (USDT)", f"{lucro_total:.2f}")

dash()