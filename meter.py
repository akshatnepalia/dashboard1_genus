# ===== Improved: Total meters (k) labels (bottom clean style) ===== #
fig.add_trace(go.Scatter(
    x=df_view["date"],
    y=[-50] * len(df_view),  # Small offset to prevent overlap with bars
    mode="text",
    text=[f"<b>{kfmt(v)}</b>" for v in df_view["Total_WC_DT"]],
    textposition="bottom center",
    textfont=dict(
        size=10,          # Slightly reduced size
        color="#1A1A1A",  # Darker for contrast
        family="Arial",
    ),
    hoverinfo="skip",
    showlegend=False
))
