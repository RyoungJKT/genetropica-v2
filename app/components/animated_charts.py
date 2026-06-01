"""Animated chart component.

Renders a Plotly bar figure as a small embedded Plotly.js component whose bars
grow from zero on page load, then settle at their real values. Native Streamlit
Plotly charts render statically and strip the JS needed for this, so the chart is
emitted as a self-contained HTML component (the same iframe mechanism the 3D
binding viewer uses). A timed fallback guarantees the final values render even if
the entrance animation cannot run (for example in a backgrounded tab).
"""

import streamlit.components.v1 as components

_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Hanken+Grotesk:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  html, body { margin: 0; padding: 0; background: #F4F0E6; }
  #chart { width: 100%; }
</style>
</head>
<body>
<div id="chart"></div>
<script>
(function () {
  var FIG = __FIG_JSON__;

  function axis(a) {
    return Object.assign({ gridcolor: "#E2DAC8", linecolor: "#D8D0BD", zerolinecolor: "#E2DAC8" }, a || {});
  }
  var layout = Object.assign({}, FIG.layout || {});
  layout.paper_bgcolor = "rgba(0,0,0,0)";
  layout.plot_bgcolor = "rgba(0,0,0,0)";
  layout.font = Object.assign({ family: "Hanken Grotesk, system-ui, sans-serif", color: "#1C1A17", size: 13 }, layout.font || {});
  layout.xaxis = axis(layout.xaxis);
  layout.yaxis = axis(layout.yaxis);
  if (layout.title && typeof layout.title === "object") {
    layout.title.font = Object.assign({ family: "Fraunces, Georgia, serif", size: 18, color: "#1C1A17" }, layout.title.font || {});
  }
  // Hold the value axis at full scale so bars grow within a stable axis (no rescale jump).
  var vmax = 0, horiz = false;
  (FIG.data || []).forEach(function (t) {
    if (t.type === "bar") {
      if (t.orientation === "h") { horiz = true; (t.x || []).forEach(function (v) { if (typeof v === "number" && v > vmax) vmax = v; }); }
      else { (t.y || []).forEach(function (v) { if (typeof v === "number" && v > vmax) vmax = v; }); }
    }
  });
  if (vmax > 0) {
    var rng = [0, vmax * 1.08];
    if (horiz) { layout.xaxis = Object.assign({}, layout.xaxis, { range: rng, autorange: false }); }
    else { layout.yaxis = Object.assign({}, layout.yaxis, { range: rng, autorange: false }); }
  }
  var cfg = { responsive: true, displayModeBar: false };

  // Zeroed copy of the bar values for the pre-grow state.
  var zero = JSON.parse(JSON.stringify(FIG));
  (zero.data || []).forEach(function (t) {
    if (t.type === "bar") {
      if (t.orientation === "h") { t.x = (t.x || []).map(function () { return 0; }); }
      else { t.y = (t.y || []).map(function () { return 0; }); }
    }
  });

  Plotly.newPlot("chart", zero.data, layout, cfg).then(function () {
    function grow() {
      Plotly.animate("chart", { data: FIG.data },
        { transition: { duration: 1100, easing: "cubic-out" }, frame: { duration: 1100 } });
    }
    if (document.visibilityState === "visible") {
      requestAnimationFrame(function () { setTimeout(grow, 80); });
    } else {
      document.addEventListener("visibilitychange", function vc() {
        if (document.visibilityState === "visible") { document.removeEventListener("visibilitychange", vc); grow(); }
      });
    }
    // Fallback: guarantee the final values render even if the animation cannot run.
    setTimeout(function () { Plotly.react("chart", FIG.data, layout, cfg); }, 2400);
  });
})();
</script>
</body>
</html>
"""


def animated_figure(fig, extra_height: int = 24) -> None:
    """Render a Plotly bar ``go.Figure`` as a component whose bars grow from zero on load.

    Pass any figure built from bar traces (the existing chart builders work as-is).
    """
    try:
        base_height = int(fig.layout.height) if fig.layout.height else 400
    except (TypeError, ValueError):
        base_height = 400
    html = _HTML.replace("__FIG_JSON__", fig.to_json())
    components.html(html, height=base_height + extra_height)
