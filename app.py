import os

import streamlit as st

# Allow Streamlit secrets to feed the spiders (env var takes priority)
try:
    if "GROQ_API_KEY" not in os.environ:
        os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    pass

from spiders import ALL_SPIDERS
from spiders.coordinator import QueenCoordinator

st.set_page_config(page_title="Spider Network", page_icon="🕷️", layout="wide")

st.title("🕷️ Spider Network Operations")

if not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY is missing! Add it to Streamlit Secrets (or .streamlit/secrets.toml).")
    st.stop()


@st.cache_resource
def get_coordinator() -> QueenCoordinator:
    return QueenCoordinator()


tab1, tab2 = st.tabs(["🚀 Fast Lane", "🛡️ Guarded Lane"])

with tab1:
    st.subheader("Spider Tasks Management")

    mode = st.radio("Execution mode:", ["Queen routing (auto)", "Manual selection"])
    if mode == "Manual selection":
        selected = st.multiselect("Select spiders:", list(ALL_SPIDERS), default=["affiliate"])
    else:
        selected = None

    task_prompt = st.text_area(
        "Task Description or Target Product:",
        placeholder="Enter task details here...",
    )

    if st.button("Run Spider 🚀"):
        if not task_prompt.strip():
            st.warning("Please enter the task description first.")
        else:
            st.info("Queen spider is analyzing the task and coordinating the network...")
            try:
                if selected:
                    # Manual mode: run selected spiders without queen routing
                    coordinator = get_coordinator()
                    results = {}
                    for name in selected:
                        with st.spinner(f"Running {name} ..."):
                            spider = ALL_SPIDERS[name]()
                            res = spider.run(task_prompt)
                            results[name] = res.to_dict()
                    targets, combined = selected, ""
                else:
                    coordinator = get_coordinator()
                    state = coordinator.run(task_prompt)
                    targets, results, combined = (
                        state["targets"], state["results"], state["combined"]
                    )

                st.success("Task completed successfully!")
                st.markdown(f"**Queen routed to:** {', '.join(targets)}")

                for name, res in results.items():
                    st.markdown(f"### 🕷️ {name}")
                    if res["ok"]:
                        st.markdown(res["output"])
                    else:
                        st.error(f"Execution failed: {res['error']}")
            except Exception as e:
                st.error(f"Execution failed: {e}")

with tab2:
    st.subheader("Strategic Supervision Zone")
    st.info("This section is reserved for sensitive financial and strategic decisions.")

    st.markdown("#### 📐 Engineering Spider — real physics check")
    with st.form("bracket_form"):
        col1, col2 = st.columns(2)
        length = col1.number_input("Length (mm)", 10.0, 500.0, 60.0)
        width = col1.number_input("Width (mm)", 10.0, 200.0, 30.0)
        thickness = col2.number_input("Thickness (mm)", 0.5, 50.0, 5.0)
        load = col2.number_input("Load (N)", 1.0, 1000.0, 50.0)
        material = st.selectbox(
            "Material", ["PLA", "ABS", "aluminum_6061", "steel_1018"]
        )
        submitted = st.form_submit_button("Compute strength 🧮")

    if submitted:
        from spiders.engineering import compute_bracket_strength, generate_openscad_bracket
        calc = compute_bracket_strength(length, width, thickness, load, material)
        if calc["safe"]:
            st.success(f"SAFE (draft) — Safety factor: {calc['safety_factor']}")
        else:
            st.error(f"NOT SAFE — Safety factor: {calc['safety_factor']}. "
                     "Increase thickness/width or reduce load.")
        st.json(calc)
        st.caption("⚠️ Draft calculation. Requires licensed engineer review before manufacturing.")

    st.markdown("#### ⚡ Electronics Spider — real Ohm's law check")
    with st.form("led_form"):
        col3, col4 = st.columns(2)
        source_v = col3.number_input("Source voltage (V)", 1.0, 24.0, 5.0)
        led_vf = col3.number_input("LED forward voltage (V)", 0.1, 12.0, 2.0)
        led_ma = col4.number_input("LED current (mA)", 1.0, 100.0, 20.0)
        submitted_led = st.form_submit_button("Compute resistor 🧮")

    if submitted_led:
        from spiders.electronics import led_series_resistor
        try:
            calc = led_series_resistor(source_v, led_vf, led_ma)
            st.success(f"Use a ~{calc['recommended_resistor']}Ω resistor "
                       f"({calc['recommended_power_rating_w']}W rating)")
            st.json(calc)
        except ValueError as e:
            st.error(str(e))
